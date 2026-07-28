#!/usr/bin/env python3
"""Offline inference for painting authenticity (Phase 4).

Loads ai_perception/efficientnet_b0_authentication/models/bacchus_auth_effnet_b0.pt and scores images.
Supports GENUINE / FAKE / RECHECK via probability thresholds.

Examples:
  # single image
  python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py \\
    --image datasets/museum_auth_dataset/dataset/test/genuine/*.jpg

  # whole test split
  python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py --split-dir datasets/museum_auth_dataset/dataset/test

  # adjust thresholds
  python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py --split-dir ... \\
    --genuine-threshold 0.85 --fake-threshold 0.70
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

REPO = Path(__file__).resolve().parents[3]
DEFAULT_CKPT = REPO / "ai_perception" / "efficientnet_b0_authentication" / "models" / "bacchus_auth_effnet_b0.pt"
CLASS_NAMES = ("genuine", "fake")


def build_model(num_classes: int = 2) -> nn.Module:
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def load_checkpoint(path: Path, device: torch.device):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    classes = tuple(ckpt.get("classes", CLASS_NAMES))
    model = build_model(num_classes=len(classes))
    model.load_state_dict(ckpt["state_dict"])
    model.to(device)
    model.eval()
    return model, classes, ckpt


def build_transform() -> transforms.Compose:
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


def decide(
    p_g: float,
    p_f: float,
    *,
    mode: str,
    genuine_threshold: float,
    fake_threshold: float,
    margin: float,
) -> str:
    if mode == "argmax_margin":
        if abs(p_g - p_f) < margin:
            return "RECHECK"
        return "GENUINE" if p_g >= p_f else "FAKE"
    if p_g >= genuine_threshold:
        return "GENUINE"
    if p_f >= fake_threshold:
        return "FAKE"
    return "RECHECK"


@torch.no_grad()
def predict_one(
    model: nn.Module,
    image_path: Path,
    transform: transforms.Compose,
    device: torch.device,
    classes: tuple[str, ...],
    genuine_threshold: float,
    fake_threshold: float,
    mode: str = "argmax_margin",
    margin: float = 0.08,
) -> dict:
    img = Image.open(image_path).convert("RGB")
    x = transform(img).unsqueeze(0).to(device)
    logits = model(x)
    probs = torch.softmax(logits, dim=1)[0]
    class_to_idx = {c: i for i, c in enumerate(classes)}
    p_genuine = float(probs[class_to_idx["genuine"]].item())
    p_fake = float(probs[class_to_idx["fake"]].item())
    prediction = decide(
        p_genuine,
        p_fake,
        mode=mode,
        genuine_threshold=genuine_threshold,
        fake_threshold=fake_threshold,
        margin=margin,
    )

    return {
        "image": str(image_path),
        "genuine_probability": round(p_genuine, 4),
        "fake_probability": round(p_fake, 4),
        "prediction": prediction,
        "mode": mode,
        "thresholds": {
            "genuine": genuine_threshold,
            "fake": fake_threshold,
            "margin": margin,
        },
    }


def collect_images(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    if args.split_dir:
        root = Path(args.split_dir).expanduser()
        for cls in ("genuine", "fake"):
            d = root / cls
            if d.is_dir():
                paths.extend(sorted(d.glob("*.jpg")))
                paths.extend(sorted(d.glob("*.png")))
    for pattern in args.image or []:
        p = Path(pattern).expanduser()
        if p.is_file():
            paths.append(p)
        else:
            # allow shell-expanded globs already passed as multiple args
            paths.extend(sorted(Path(".").glob(pattern)))
    # unique preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Offline authenticity inference")
    p.add_argument("--checkpoint", type=Path, default=DEFAULT_CKPT)
    p.add_argument("--image", nargs="*", default=None, help="image path(s)")
    p.add_argument(
        "--split-dir",
        type=Path,
        default=None,
        help="e.g. datasets/museum_auth_dataset/dataset/test",
    )
    p.add_argument("--genuine-threshold", type=float, default=0.85)
    p.add_argument("--fake-threshold", type=float, default=0.70)
    p.add_argument(
        "--mode",
        choices=("argmax_margin", "threshold"),
        default="argmax_margin",
    )
    p.add_argument("--margin", type=float, default=0.08)
    p.add_argument("--json-out", type=Path, default=None)
    args = p.parse_args()

    ckpt_path = args.checkpoint.expanduser().resolve()
    if not ckpt_path.is_file():
        raise SystemExit(f"[FAIL] checkpoint not found: {ckpt_path}")

    images = collect_images(args)
    if not images:
        raise SystemExit(
            "[FAIL] no images — pass --split-dir .../dataset/test or --image path.jpg"
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, classes, _ckpt = load_checkpoint(ckpt_path, device)
    transform = build_transform()
    print(
        f"[INFO] device={device} classes={classes} mode={args.mode} "
        f"genuine_thr={args.genuine_threshold} fake_thr={args.fake_threshold} "
        f"margin={args.margin} n={len(images)}",
        flush=True,
    )

    results = []
    counts = {"GENUINE": 0, "FAKE": 0, "RECHECK": 0}
    for img_path in images:
        r = predict_one(
            model,
            img_path,
            transform,
            device,
            classes,
            args.genuine_threshold,
            args.fake_threshold,
            mode=args.mode,
            margin=args.margin,
        )
        results.append(r)
        counts[r["prediction"]] += 1
        print(
            f"image: {Path(r['image']).name}\n"
            f"genuine_probability: {r['genuine_probability']:.4f}\n"
            f"fake_probability: {r['fake_probability']:.4f}\n"
            f"prediction: {r['prediction']}\n",
            flush=True,
        )

    print(
        f"[SUMMARY] GENUINE={counts['GENUINE']} FAKE={counts['FAKE']} "
        f"RECHECK={counts['RECHECK']} total={len(results)}",
        flush=True,
    )

    if args.json_out:
        out = args.json_out.expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"results": results, "summary": counts}, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        print(f"[OK] wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
