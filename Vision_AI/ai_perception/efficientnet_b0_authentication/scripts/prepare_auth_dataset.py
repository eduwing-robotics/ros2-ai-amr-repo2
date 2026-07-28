#!/usr/bin/env python3
"""Phase 2 — session-based train/val/test split for painting authenticity.

Reads Phase 1 captures under datasets/museum_auth_dataset/ and materializes:

  dataset/
    train/{genuine,fake}/
    val/{genuine,fake}/
    test/{genuine,fake}/

Classes for learning: genuine vs fake (all fake_01/fake_02/fake_03 → fake).
Splits are ALWAYS by SESSION — never shuffle frames across train/val/test.

Does NOT train, infer, or touch YOLO nodes.

Prefer ROI crops (crops/) over full frames (raw/). Missing crops are skipped
with a warning.

Usage (explicit sessions):
  python3 ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.py \\
    --dataset-root datasets/museum_auth_dataset \\
    --train-sessions session_01,session_02,session_03 \\
    --val-sessions session_04 \\
    --test-sessions session_05 \\
    --force

Usage (auto split per class):
  python3 ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.py --auto --force

Auto defaults (documented):
  --train-ratio 0.6 --val-ratio 0.2 --test-ratio 0.2
  Sessions sorted lexicographically per label_family (genuine|fake).
  Few-session fallbacks (with WARN):
    0 → empty dataset message
    1 → all → train (val/test empty)
    2 → first → train, second → val (test empty)
    3+ → ratio buckets (at least 1 train when possible)

Or via wrapper:
  ./ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.sh --auto --force
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "ai_perception" / "efficientnet_b0_authentication" / "datasets" / "museum_auth_dataset"

LABEL_FAMILIES = ("genuine", "fake")
SPLITS = ("train", "val", "test")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

# stem = {session}_{YYYYMMDD}_{HHMMSS}_{mmm}_{idx}
_STEM_RE_TAIL = r"_(\d{8})_(\d{6})_(\d{3})_(\d{3})$"


@dataclass
class Capture:
    """One shot discovered from jsonl / metadata / crops tree."""

    stem: str
    session_id: str
    label: str  # genuine | fake_01 | fake_02 | fake_03
    label_family: str  # genuine | fake
    crop_path: Path | None
    source: str  # jsonl | metadata | crops_scan | raw_scan


@dataclass
class SplitPlan:
    """session_id sets per (label_family, split)."""

    mapping: dict[str, dict[str, list[str]]] = field(
        default_factory=lambda: {
            fam: {sp: [] for sp in SPLITS} for fam in LABEL_FAMILIES
        }
    )
    mode: str = "explicit"  # explicit | auto
    warnings: list[str] = field(default_factory=list)


def label_family(label: str) -> str | None:
    if label == "genuine":
        return "genuine"
    if label.startswith("fake"):
        return "fake"
    return None


def parse_csv_sessions(text: str | None) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for part in text.split(","):
        s = part.strip()
        if s and s not in out:
            out.append(s)
    return out


def parse_session_from_stem(stem: str) -> str | None:
    """Extract session_id from Phase 1 stem naming."""
    import re

    m = re.search(_STEM_RE_TAIL, stem)
    if not m:
        return None
    return stem[: m.start()]


def _rel_or_abs(dataset_root: Path, path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (dataset_root / p).resolve()


def load_jsonl_captures(dataset_root: Path) -> list[Capture]:
    jsonl = dataset_root / "metadata" / "captures.jsonl"
    if not jsonl.is_file():
        return []
    out: list[Capture] = []
    with jsonl.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"[WARN] captures.jsonl L{lineno}: {exc}")
                continue
            cap = _capture_from_meta(dataset_root, obj, source="jsonl")
            if cap is not None:
                out.append(cap)
    return out


def load_metadata_json_captures(dataset_root: Path) -> list[Capture]:
    meta_dir = dataset_root / "metadata"
    if not meta_dir.is_dir():
        return []
    out: list[Capture] = []
    for path in sorted(meta_dir.glob("*.json")):
        if path.name == "captures.jsonl":
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[WARN] skip metadata {path.name}: {exc}")
            continue
        if not isinstance(obj, dict):
            continue
        cap = _capture_from_meta(dataset_root, obj, source="metadata")
        if cap is not None:
            out.append(cap)
    return out


def _capture_from_meta(
    dataset_root: Path, obj: dict, *, source: str
) -> Capture | None:
    label = str(obj.get("label") or "").strip()
    fam = label_family(label)
    if fam is None:
        return None
    session_id = str(obj.get("session_id") or "").strip()
    stem = str(obj.get("stem") or "").strip()
    if not session_id and stem:
        session_id = parse_session_from_stem(stem) or ""
    if not stem and session_id:
        # best-effort; may still resolve crop via paths
        stem = session_id
    if not session_id:
        return None

    crop_path: Path | None = None
    paths = obj.get("paths") if isinstance(obj.get("paths"), dict) else {}
    crop_rel = paths.get("crop") if isinstance(paths, dict) else None
    if isinstance(crop_rel, str) and crop_rel:
        crop_path = _rel_or_abs(dataset_root, crop_rel)
    elif stem:
        # Phase 1 layout fallback
        if fam == "genuine":
            candidate = dataset_root / "crops" / "genuine" / f"{stem}_crop.jpg"
        else:
            candidate = dataset_root / "crops" / "fake" / label / f"{stem}_crop.jpg"
        crop_path = candidate

    return Capture(
        stem=stem or session_id,
        session_id=session_id,
        label=label,
        label_family=fam,
        crop_path=crop_path,
        source=source,
    )


def scan_crops_tree(dataset_root: Path) -> list[Capture]:
    crops = dataset_root / "crops"
    if not crops.is_dir():
        return []
    out: list[Capture] = []

    genuine_dir = crops / "genuine"
    if genuine_dir.is_dir():
        for img in sorted(genuine_dir.iterdir()):
            if not img.is_file() or img.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            stem = img.name
            for suf in ("_crop.jpg", "_crop.jpeg", "_crop.png", "_crop.webp"):
                if stem.lower().endswith(suf):
                    stem = stem[: -len(suf)]
                    break
            else:
                stem = img.stem
            session_id = parse_session_from_stem(stem)
            if not session_id:
                print(f"[WARN] cannot parse session from crop name: {img.name}")
                continue
            out.append(
                Capture(
                    stem=stem,
                    session_id=session_id,
                    label="genuine",
                    label_family="genuine",
                    crop_path=img.resolve(),
                    source="crops_scan",
                )
            )

    fake_root = crops / "fake"
    if fake_root.is_dir():
        for fake_dir in sorted(fake_root.iterdir()):
            if not fake_dir.is_dir():
                continue
            fake_id = fake_dir.name  # fake_01 etc.
            if not fake_id.startswith("fake"):
                continue
            for img in sorted(fake_dir.iterdir()):
                if not img.is_file() or img.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                stem = img.name
                for suf in ("_crop.jpg", "_crop.jpeg", "_crop.png", "_crop.webp"):
                    if stem.lower().endswith(suf):
                        stem = stem[: -len(suf)]
                        break
                else:
                    stem = img.stem
                session_id = parse_session_from_stem(stem)
                if not session_id:
                    print(f"[WARN] cannot parse session from crop name: {img.name}")
                    continue
                out.append(
                    Capture(
                        stem=stem,
                        session_id=session_id,
                        label=fake_id,
                        label_family="fake",
                        crop_path=img.resolve(),
                        source="crops_scan",
                    )
                )
    return out


def scan_raw_sessions(dataset_root: Path) -> list[Capture]:
    """Discover sessions from raw/ and attach matching crop paths when present."""
    raw = dataset_root / "raw"
    if not raw.is_dir():
        return []
    out: list[Capture] = []

    genuine_root = raw / "genuine"
    if genuine_root.is_dir():
        for session_dir in sorted(genuine_root.iterdir()):
            if not session_dir.is_dir() or session_dir.name.startswith("."):
                continue
            session_id = session_dir.name
            for rgb in sorted(session_dir.iterdir()):
                if not rgb.is_file() or rgb.suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                stem = rgb.name
                for suf in ("_rgb.jpg", "_rgb.jpeg", "_rgb.png"):
                    if stem.lower().endswith(suf):
                        stem = stem[: -len(suf)]
                        break
                else:
                    stem = rgb.stem
                crop = dataset_root / "crops" / "genuine" / f"{stem}_crop.jpg"
                out.append(
                    Capture(
                        stem=stem,
                        session_id=session_id,
                        label="genuine",
                        label_family="genuine",
                        crop_path=crop if crop.is_file() else crop,
                        source="raw_scan",
                    )
                )

    fake_root = raw / "fake"
    if fake_root.is_dir():
        for fake_dir in sorted(fake_root.iterdir()):
            if not fake_dir.is_dir() or not fake_dir.name.startswith("fake"):
                continue
            fake_id = fake_dir.name
            for session_dir in sorted(fake_dir.iterdir()):
                if not session_dir.is_dir() or session_dir.name.startswith("."):
                    continue
                session_id = session_dir.name
                for rgb in sorted(session_dir.iterdir()):
                    if not rgb.is_file() or rgb.suffix.lower() not in IMAGE_SUFFIXES:
                        continue
                    stem = rgb.name
                    for suf in ("_rgb.jpg", "_rgb.jpeg", "_rgb.png"):
                        if stem.lower().endswith(suf):
                            stem = stem[: -len(suf)]
                            break
                    else:
                        stem = rgb.stem
                    crop = (
                        dataset_root
                        / "crops"
                        / "fake"
                        / fake_id
                        / f"{stem}_crop.jpg"
                    )
                    out.append(
                        Capture(
                            stem=stem,
                            session_id=session_id,
                            label=fake_id,
                            label_family="fake",
                            crop_path=crop,
                            source="raw_scan",
                        )
                    )
    return out


def merge_captures(groups: Iterable[list[Capture]]) -> list[Capture]:
    """Dedupe by (label_family, stem); prefer entries that have an existing crop."""
    best: dict[tuple[str, str], Capture] = {}
    for group in groups:
        for cap in group:
            key = (cap.label_family, cap.stem)
            existing = best.get(key)
            if existing is None:
                best[key] = cap
                continue
            ex_ok = existing.crop_path is not None and existing.crop_path.is_file()
            new_ok = cap.crop_path is not None and cap.crop_path.is_file()
            if new_ok and not ex_ok:
                best[key] = cap
            elif new_ok == ex_ok:
                # Prefer metadata-backed records
                rank = {"jsonl": 3, "metadata": 2, "crops_scan": 1, "raw_scan": 0}
                if rank.get(cap.source, 0) > rank.get(existing.source, 0):
                    best[key] = cap
    return list(best.values())


def discover_captures(dataset_root: Path) -> list[Capture]:
    return merge_captures(
        [
            load_jsonl_captures(dataset_root),
            load_metadata_json_captures(dataset_root),
            scan_crops_tree(dataset_root),
            scan_raw_sessions(dataset_root),
        ]
    )


def sessions_by_family(
    captures: list[Capture],
) -> dict[str, list[str]]:
    """Unique session ids per label_family, sorted."""
    bags: dict[str, set[str]] = {fam: set() for fam in LABEL_FAMILIES}
    for cap in captures:
        bags[cap.label_family].add(cap.session_id)
    return {fam: sorted(bags[fam]) for fam in LABEL_FAMILIES}


def assign_explicit(
    sessions_map: dict[str, list[str]],
    train: list[str],
    val: list[str],
    test: list[str],
) -> SplitPlan:
    plan = SplitPlan(mode="explicit")
    assigned = {"train": set(train), "val": set(val), "test": set(test)}
    overlap = (
        (assigned["train"] & assigned["val"])
        | (assigned["train"] & assigned["test"])
        | (assigned["val"] & assigned["test"])
    )
    if overlap:
        raise SystemExit(
            f"[FAIL] session appears in multiple splits: {sorted(overlap)}"
        )

    all_listed = assigned["train"] | assigned["val"] | assigned["test"]
    for fam in LABEL_FAMILIES:
        available = set(sessions_map.get(fam, []))
        for sp in SPLITS:
            for sid in sorted(assigned[sp]):
                if sid in available:
                    plan.mapping[fam][sp].append(sid)
        unused = sorted(available - all_listed)
        if unused:
            plan.warnings.append(
                f"{fam}: sessions not listed in any split (ignored): {unused}"
            )
        missing = sorted(all_listed - available)
        if missing and available:
            plan.warnings.append(
                f"{fam}: listed sessions not present in data: {missing}"
            )
    return plan


def _bucket_by_ratios(
    sessions: list[str],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return (train, val, test, warnings). Sessions already sorted."""
    warns: list[str] = []
    n = len(sessions)
    if n == 0:
        return [], [], [], warns
    if n == 1:
        warns.append("only 1 session → all assigned to train (val/test empty)")
        return list(sessions), [], [], warns
    if n == 2:
        warns.append("only 2 sessions → train + val (test empty)")
        return [sessions[0]], [sessions[1]], [], warns

    # Ensure ratios roughly sum to 1
    total = train_ratio + val_ratio + test_ratio
    if total <= 0:
        raise SystemExit("[FAIL] ratios must sum to > 0")
    tr, vr, te = train_ratio / total, val_ratio / total, test_ratio / total

    n_train = max(1, int(round(n * tr)))
    n_val = int(round(n * vr))
    n_test = n - n_train - n_val
    # Fix rounding so all splits non-empty when n >= 3
    if n_test < 1 and te > 0 and n_train > 1:
        n_train -= 1
        n_test += 1
    if n_val < 1 and vr > 0 and n_train > 1:
        n_train -= 1
        n_val += 1
    if n_train + n_val + n_test != n:
        n_test = n - n_train - n_val
    if n_test < 0:
        n_val += n_test
        n_test = 0
    if n_val < 0:
        n_train += n_val
        n_val = 0

    train = sessions[:n_train]
    val = sessions[n_train : n_train + n_val]
    test = sessions[n_train + n_val :]
    return train, val, test, warns


def assign_auto(
    sessions_map: dict[str, list[str]],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
) -> SplitPlan:
    plan = SplitPlan(mode="auto")
    for fam in LABEL_FAMILIES:
        sessions = list(sessions_map.get(fam, []))
        train, val, test, warns = _bucket_by_ratios(
            sessions, train_ratio, val_ratio, test_ratio
        )
        plan.mapping[fam]["train"] = train
        plan.mapping[fam]["val"] = val
        plan.mapping[fam]["test"] = test
        for w in warns:
            plan.warnings.append(f"{fam}: {w}")
    return plan


def clear_dataset_dir(dataset_dir: Path) -> None:
    if not dataset_dir.exists():
        return
    for child in dataset_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def link_or_copy(src: Path, dst: Path, *, symlink: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    if symlink:
        os.symlink(src.resolve(), dst)
    else:
        shutil.copy2(src, dst)


def materialize(
    dataset_root: Path,
    captures: list[Capture],
    plan: SplitPlan,
    *,
    symlink: bool,
    force: bool,
) -> dict:
    dataset_dir = dataset_root / "dataset"
    if dataset_dir.exists() and any(dataset_dir.iterdir()):
        if not force:
            raise SystemExit(
                f"[FAIL] {dataset_dir} already exists and is not empty. "
                "Pass --force to clear and rebuild."
            )
        clear_dataset_dir(dataset_dir)

    # session → split lookup per family
    session_split: dict[str, dict[str, str]] = {fam: {} for fam in LABEL_FAMILIES}
    for fam in LABEL_FAMILIES:
        for sp in SPLITS:
            for sid in plan.mapping[fam][sp]:
                session_split[fam][sid] = sp

    counts: dict[str, dict[str, int]] = {
        sp: {fam: 0 for fam in LABEL_FAMILIES} for sp in SPLITS
    }
    skipped_no_crop = 0
    skipped_unassigned = 0
    files: list[dict] = []

    # Stable order
    ordered = sorted(
        captures,
        key=lambda c: (c.label_family, c.session_id, c.label, c.stem),
    )

    for cap in ordered:
        sp = session_split[cap.label_family].get(cap.session_id)
        if sp is None:
            skipped_unassigned += 1
            continue
        if cap.crop_path is None or not cap.crop_path.is_file():
            print(
                f"[WARN] missing crop for stem={cap.stem} "
                f"label={cap.label} session={cap.session_id} "
                f"path={cap.crop_path} — skip"
            )
            skipped_no_crop += 1
            continue

        # Avoid collisions across fake_01/fake_02 with identical stems
        if cap.label_family == "fake" and cap.label.startswith("fake_"):
            dest_name = f"{cap.label}__{cap.crop_path.name}"
        else:
            dest_name = cap.crop_path.name

        dest = dataset_dir / sp / cap.label_family / dest_name
        link_or_copy(cap.crop_path, dest, symlink=symlink)
        counts[sp][cap.label_family] += 1
        files.append(
            {
                "split": sp,
                "label_family": cap.label_family,
                "label": cap.label,
                "session_id": cap.session_id,
                "stem": cap.stem,
                "src": str(cap.crop_path.relative_to(dataset_root))
                if cap.crop_path.is_relative_to(dataset_root)
                else str(cap.crop_path),
                "dst": str(dest.relative_to(dataset_root)),
            }
        )

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(dataset_root),
        "mode": plan.mode,
        "symlink": symlink,
        "split_sessions": plan.mapping,
        "counts": counts,
        "totals": {
            "files": len(files),
            "skipped_no_crop": skipped_no_crop,
            "skipped_unassigned": skipped_unassigned,
        },
        "warnings": plan.warnings,
        "files": files,
    }
    dataset_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dataset_dir / "split_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return manifest


def print_discovery_summary(
    captures: list[Capture], sessions_map: dict[str, list[str]]
) -> None:
    print("=== Discovery ===")
    if not captures:
        print(
            "[INFO] No captures found under this dataset root.\n"
            "  Expected Phase 1 layout:\n"
            "    metadata/captures.jsonl\n"
            "    crops/genuine/*_crop.jpg\n"
            "    crops/fake/fake_0N/*_crop.jpg\n"
            "    raw/genuine/<session>/  and  raw/fake/fake_0N/<session>/\n"
            "  Capture first, e.g.:\n"
            "    python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py capture \\\n"
            "      --label genuine --session session_01 --count 10\n"
            "    python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py capture \\\n"
            "      --label fake_01 --session session_01 --count 10\n"
            "  Aim for ≥3 sessions per class (genuine and fake) so train/val/test\n"
            "  can each get at least one session."
        )
        return

    by_fam_sess: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_label: dict[str, int] = defaultdict(int)
    crops_ok = 0
    for cap in captures:
        by_fam_sess[cap.label_family][cap.session_id] += 1
        by_label[cap.label] += 1
        if cap.crop_path is not None and cap.crop_path.is_file():
            crops_ok += 1

    print(f"  shots discovered : {len(captures)}  (crops present: {crops_ok})")
    print(f"  labels           : {dict(by_label)}")
    for fam in LABEL_FAMILIES:
        sess = sessions_map.get(fam, [])
        detail = ", ".join(
            f"{s}={by_fam_sess[fam][s]}" for s in sess
        ) or "(none)"
        print(f"  {fam:8s} sessions: {len(sess)}  [{detail}]")


def print_manifest_summary(manifest: dict) -> None:
    print("=== Split summary ===")
    print(f"  mode     : {manifest['mode']}")
    print(f"  symlink  : {manifest['symlink']}")
    for fam in LABEL_FAMILIES:
        print(f"  {fam}:")
        for sp in SPLITS:
            sessions = manifest["split_sessions"][fam][sp]
            n = manifest["counts"][sp][fam]
            print(f"    {sp:5s} sessions={sessions}  files={n}")
    tot = manifest["totals"]
    print(
        f"  total files={tot['files']}  "
        f"skipped_no_crop={tot['skipped_no_crop']}  "
        f"skipped_unassigned={tot['skipped_unassigned']}"
    )
    for w in manifest.get("warnings") or []:
        print(f"[WARN] {w}")
    print(f"[OK] wrote {manifest['dataset_root']}/dataset/split_manifest.json")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Phase 2: session-based train/val/test split for "
            "painting authenticity ROI crops"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dataset-root",
        default=str(DEFAULT_DATASET_ROOT),
        help=f"dataset root (default: {DEFAULT_DATASET_ROOT})",
    )
    p.add_argument(
        "--auto",
        action="store_true",
        help="auto-assign sessions per class by sorted order + ratios",
    )
    p.add_argument(
        "--train-sessions",
        default="",
        help="comma-separated session ids for train (explicit mode)",
    )
    p.add_argument(
        "--val-sessions",
        default="",
        help="comma-separated session ids for val (explicit mode)",
    )
    p.add_argument(
        "--test-sessions",
        default="",
        help="comma-separated session ids for test (explicit mode)",
    )
    p.add_argument(
        "--train-ratio",
        type=float,
        default=0.6,
        help="auto mode train fraction (default: 0.6)",
    )
    p.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="auto mode val fraction (default: 0.2)",
    )
    p.add_argument(
        "--test-ratio",
        type=float,
        default=0.2,
        help="auto mode test fraction (default: 0.2)",
    )
    p.add_argument(
        "--symlink",
        action="store_true",
        help="symlink crops into dataset/ instead of copying (default: copy)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="clear existing dataset/ before writing",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="discover + plan only; do not write dataset/",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dataset_root = Path(args.dataset_root).expanduser().resolve()
    if not dataset_root.is_dir():
        print(f"[FAIL] dataset root does not exist: {dataset_root}")
        print(
            "  Create it via Phase 1 capture, or mkdir and capture into it first."
        )
        return 2

    captures = discover_captures(dataset_root)
    sessions_map = sessions_by_family(captures)
    print_discovery_summary(captures, sessions_map)

    if not captures:
        return 1

    train = parse_csv_sessions(args.train_sessions)
    val = parse_csv_sessions(args.val_sessions)
    test = parse_csv_sessions(args.test_sessions)
    explicit = bool(train or val or test)

    if args.auto and explicit:
        print("[FAIL] use either --auto OR --train/--val/--test-sessions, not both")
        return 2
    if not args.auto and not explicit:
        print(
            "[FAIL] specify --auto or explicit "
            "--train-sessions / --val-sessions / --test-sessions"
        )
        return 2

    if args.auto:
        plan = assign_auto(
            sessions_map, args.train_ratio, args.val_ratio, args.test_ratio
        )
    else:
        plan = assign_explicit(sessions_map, train, val, test)

    # Sufficiency hints
    for fam in LABEL_FAMILIES:
        n_sess = len(sessions_map.get(fam, []))
        if n_sess < 3:
            plan.warnings.append(
                f"{fam}: only {n_sess} session(s) — capture more sessions "
                f"(recommend ≥3) for a real train/val/test split"
            )

    if args.dry_run:
        print("=== Plan (dry-run) ===")
        print(json.dumps(plan.mapping, indent=2))
        for w in plan.warnings:
            print(f"[WARN] {w}")
        print("[OK] dry-run complete; no files written")
        return 0

    manifest = materialize(
        dataset_root,
        captures,
        plan,
        symlink=bool(args.symlink),
        force=bool(args.force),
    )
    print_manifest_summary(manifest)

    if manifest["totals"]["files"] == 0:
        print(
            "[WARN] zero files written — check that crops/ exist for assigned sessions"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
