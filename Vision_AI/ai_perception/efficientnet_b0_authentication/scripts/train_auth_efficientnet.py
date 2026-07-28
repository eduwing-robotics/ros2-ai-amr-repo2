#!/usr/bin/env python3
"""Train EfficientNet-B0 genuine/fake classifier (painting authenticity MVP).

Uses prepared ImageFolder-style tree from prepare_auth_dataset.py:
  datasets/museum_auth_dataset/dataset/{train,val,test}/{genuine,fake}/

Defaults match the Phase-3 MVP plan:
  - ImageNet pretrained EfficientNet-B0
  - freeze features; train classifier head (2 classes)
  - 224x224, AdamW 1e-4, CrossEntropy, mild augment only
  - save best validation checkpoint + test metrics

Example:
  source ros_env/bin/activate   # or your torch env
  python3 ai_perception/efficientnet_b0_authentication/scripts/train_auth_efficientnet.py --epochs 8 --batch-size 8
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, models, transforms
from torchvision.models import EfficientNet_B0_Weights

REPO = Path(__file__).resolve().parents[3]
DEFAULT_DATA = REPO / "ai_perception" / "efficientnet_b0_authentication" / "datasets" / "museum_auth_dataset" / "dataset"
DEFAULT_OUT = REPO / "ai_perception" / "efficientnet_b0_authentication" / "models" / "bacchus_auth_effnet_b0.pt"
CLASS_NAMES = ("genuine", "fake")  # index 0, 1


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_transforms(train: bool) -> transforms.Compose:
    if train:
        return transforms.Compose(
            [
                transforms.Resize((256, 256)),
                transforms.RandomRotation(degrees=5),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.04, 0.04),
                    scale=(0.92, 1.08),
                ),
                transforms.ColorJitter(brightness=0.15, contrast=0.15),
                transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.8)),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


def make_model(freeze_features: bool = True) -> nn.Module:
    weights = EfficientNet_B0_Weights.IMAGENET1K_V1
    model = models.efficientnet_b0(weights=weights)
    if freeze_features:
        for p in model.features.parameters():
            p.requires_grad = False
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 2)
    return model


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device, criterion: nn.Module):
    model.eval()
    total_loss = 0.0
    correct = 0
    n = 0
    all_y: list[int] = []
    all_p: list[int] = []
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        logits = model(x)
        loss = criterion(logits, y)
        total_loss += float(loss.item()) * y.size(0)
        pred = logits.argmax(dim=1)
        correct += int((pred == y).sum().item())
        n += int(y.size(0))
        all_y.extend(y.cpu().tolist())
        all_p.extend(pred.cpu().tolist())
    avg_loss = total_loss / max(n, 1)
    acc = correct / max(n, 1)
    cm = [[0, 0], [0, 0]]
    for yt, yp in zip(all_y, all_p):
        cm[yt][yp] += 1
    # per-class precision/recall for genuine(0) and fake(1)
    metrics = {}
    for i, name in enumerate(CLASS_NAMES):
        tp = cm[i][i]
        fp = cm[1 - i][i]
        fn = cm[i][1 - i]
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        metrics[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": int(sum(cm[i])),
        }
    return {
        "loss": round(avg_loss, 6),
        "accuracy": round(acc, 4),
        "confusion_matrix": {
            "labels": list(CLASS_NAMES),
            "matrix": cm,  # rows=true, cols=pred
        },
        "per_class": metrics,
        "n": n,
    }


def load_split(root: Path, transform) -> datasets.ImageFolder:
    """ImageFolder with forced class order genuine=0, fake=1 (not alphabetical)."""
    ds = datasets.ImageFolder(str(root), transform=transform)
    wanted = {"genuine": 0, "fake": 1}
    if ds.class_to_idx == wanted and list(ds.classes) == list(CLASS_NAMES):
        return ds
    samples = []
    for path, y in ds.samples:
        name = ds.classes[y]
        if name not in wanted:
            raise SystemExit(f"[FAIL] unexpected class folder {name!r} under {root}")
        samples.append((path, wanted[name]))
    ds.samples = samples
    ds.targets = [s[1] for s in samples]
    ds.classes = list(CLASS_NAMES)
    ds.class_to_idx = wanted
    return ds


def main() -> int:
    p = argparse.ArgumentParser(description="Train EfficientNet-B0 authenticity classifier")
    p.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--unfreeze", action="store_true", help="train full network (not just head)")
    p.add_argument("--no-balanced-sampler", action="store_true")
    args = p.parse_args()

    data_root = args.data_root.expanduser().resolve()
    for split in ("train", "val", "test"):
        d = data_root / split
        if not d.is_dir():
            raise SystemExit(f"[FAIL] missing split dir: {d} — run prepare_auth_dataset.py first")

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] device={device} data={data_root}", flush=True)

    train_ds = load_split(data_root / "train", build_transforms(True))
    val_ds = load_split(data_root / "val", build_transforms(False))
    test_ds = load_split(data_root / "test", build_transforms(False))

    print(f"[INFO] classes={train_ds.classes} class_to_idx={train_ds.class_to_idx}")
    if args.no_balanced_sampler:
        train_loader = DataLoader(
            train_ds,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=args.workers,
            pin_memory=device.type == "cuda",
        )
    else:
        # Balance genuine vs fake in each epoch (fake is majority in this dataset)
        counts = [0] * len(train_ds.classes)
        for _, y in train_ds.samples:
            counts[y] += 1
        weights = [1.0 / max(counts[y], 1) for _, y in train_ds.samples]
        sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
        train_loader = DataLoader(
            train_ds,
            batch_size=args.batch_size,
            sampler=sampler,
            num_workers=args.workers,
            pin_memory=device.type == "cuda",
        )
        print(f"[INFO] train class counts={dict(zip(train_ds.classes, counts))} (balanced sampler ON)")

    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    model = make_model(freeze_features=not args.unfreeze).to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_path = args.out.expanduser().resolve()
    best_path.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        running = 0.0
        seen = 0
        for x, y in train_loader:
            x = x.to(device)
            y = y.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            running += float(loss.item()) * y.size(0)
            seen += int(y.size(0))
        train_loss = running / max(seen, 1)
        val_m = evaluate(model, val_loader, device, criterion)
        history.append({"epoch": epoch, "train_loss": round(train_loss, 6), "val": val_m})
        print(
            f"[epoch {epoch}/{args.epochs}] "
            f"train_loss={train_loss:.4f} val_loss={val_m['loss']:.4f} "
            f"val_acc={val_m['accuracy']:.3f}  ({time.time() - t0:.1f}s)",
            flush=True,
        )
        if val_m["loss"] < best_val_loss:
            best_val_loss = val_m["loss"]
            ckpt = {
                "model": "efficientnet_b0",
                "exhibit_id": "bacchus_and_ariadne",
                "classes": list(CLASS_NAMES),
                "freeze_features": not args.unfreeze,
                "epoch": epoch,
                "val": val_m,
                "state_dict": model.state_dict(),
            }
            torch.save(ckpt, best_path)
            print(f"  -> saved best checkpoint: {best_path}", flush=True)

    # Reload best and test
    ckpt = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["state_dict"])
    test_m = evaluate(model, test_loader, device, criterion)
    print("[TEST]", json.dumps(test_m, ensure_ascii=False, indent=2), flush=True)

    report = {
        "checkpoint": str(best_path),
        "device": str(device),
        "epochs": args.epochs,
        "history": history,
        "best_val_loss": best_val_loss,
        "test": test_m,
        "train_counts": {c: sum(1 for _, y in train_ds.samples if y == i) for i, c in enumerate(train_ds.classes)},
        "val_counts": {c: sum(1 for _, y in val_ds.samples if y == i) for i, c in enumerate(val_ds.classes)},
        "test_counts": {c: sum(1 for _, y in test_ds.samples if y == i) for i, c in enumerate(test_ds.classes)},
    }
    report_path = best_path.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] wrote metrics {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
