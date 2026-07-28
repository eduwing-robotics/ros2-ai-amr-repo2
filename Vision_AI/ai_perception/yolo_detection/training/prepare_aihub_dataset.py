#!/usr/bin/env python3
"""Prepare AI-Hub fire/smoke YOLO dataset for museum patrol training.

AI-Hub dataset (화재영상 2D):
  https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71472

Expected after unzip (flexible layout detection):
  - JPG/PNG images with matching .txt YOLO labels in parallel folders
  - AI-Hub class IDs: 0=불꽃(fire), 1=연기(smoke)

Usage:
  python3 ai_perception/yolo_detection/training/prepare_aihub_dataset.py \\
    --source ~/Downloads/aihub_fire_dataset \\
    --output ~/workspace/robot_project/datasets/museum_fire/processed \\
    --val-ratio 0.1 \\
    --indoor-only

Optional COCO person samples for 3-class model:
  --add-coco-person --coco-person-count 2000
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp'}
AIHUB_CLASS_MAP = {
    0: 0,  # 불꽃 → fire
    1: 1,  # 연기 → smoke
}


def aihub_label_path(image_path: Path) -> Path:
    """Map AI-Hub 71472 image path to TXT label path."""
    path_str = str(image_path)
    if '01.원천데이터' in path_str:
        label_str = path_str.replace('01.원천데이터', '02.라벨링데이터')
        img = Path(label_str)
        # .../Smoke/실외-주간-연기/0021/0021_F0001.jpg
        # → .../Smoke/실외-주간-연기/TXT/0021/0021_F0001.txt
        return img.parent.parent / 'TXT' / img.parent.name / f'{img.stem}.txt'
    return image_path.with_suffix('.txt')


def find_labeled_pairs(source: Path, indoor_only: bool) -> List[Tuple[Path, Path]]:
    pairs: List[Tuple[Path, Path]] = []
    images = [
        p for p in source.rglob('*')
        if p.suffix.lower() in IMAGE_EXTS and p.is_file()
    ]

    for image_path in images:
        if indoor_only:
            lowered = str(image_path).lower()
            if '실내' not in lowered and 'indoor' not in lowered:
                continue

        label_path = aihub_label_path(image_path)
        if label_path.exists():
            pairs.append((image_path, label_path))

    return pairs


def remap_label_file(src_label: Path, dst_label: Path, person_class_id: int = 2) -> bool:
    lines_out: List[str] = []
    for line in src_label.read_text(encoding='utf-8', errors='ignore').splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        try:
            cls = int(float(parts[0]))
        except ValueError:
            continue
        if cls not in AIHUB_CLASS_MAP:
            continue
        parts[0] = str(AIHUB_CLASS_MAP[cls])
        lines_out.append(' '.join(parts))

    if not lines_out:
        return False

    dst_label.parent.mkdir(parents=True, exist_ok=True)
    dst_label.write_text('\n'.join(lines_out) + '\n', encoding='utf-8')
    return True


def copy_split(
    pairs: List[Tuple[Path, Path]],
    output: Path,
    val_ratio: float,
    seed: int,
) -> Dict[str, int]:
    random.seed(seed)
    shuffled = pairs[:]
    random.shuffle(shuffled)
    val_count = max(1, int(len(shuffled) * val_ratio))
    val_set = set(id(p) for p in shuffled[:val_count])

    stats = {'train': 0, 'val': 0, 'skipped': 0}

    for pair in shuffled:
        image_path, label_path = pair
        split = 'val' if id(pair) in val_set else 'train'
        dst_image = output / 'images' / split / image_path.name
        dst_label = output / 'labels' / split / f'{image_path.stem}.txt'

        if not remap_label_file(label_path, dst_label):
            stats['skipped'] += 1
            continue

        dst_image.parent.mkdir(parents=True, exist_ok=True)
        if dst_image.exists():
            dst_image.unlink()
        shutil.copy2(image_path, dst_image)
        stats[split] += 1

    return stats


def add_coco_person_samples(output: Path, count: int, seed: int) -> int:
    """Download COCO val2017 person crops via ultralytics helper if available."""
    try:
        from ultralytics.data.utils import autosplit
        from ultralytics.utils.downloads import download
    except ImportError:
        print('[WARN] ultralytics not installed — skip COCO person augmentation', file=sys.stderr)
        return 0

    coco_dir = output.parent / 'coco_person_cache'
    coco_dir.mkdir(parents=True, exist_ok=True)
    # ultralytics can auto-fetch small sample; keep lightweight
    print(f'[INFO] COCO person augmentation requested ({count} samples) — manual step:')
    print('       Place person-labeled images under datasets/coco_person/ and re-run with')
    print('       --coco-person-dir PATH (future). Skipping automatic download in v1.')
    return 0


def write_data_yaml(output: Path, yaml_template: Path) -> Path:
    data_yaml = output / 'data.yaml'
    rel_root = output.resolve()
    content = yaml_template.read_text(encoding='utf-8')
    content = content.replace('../datasets/museum_fire/processed', str(rel_root))
    data_yaml.write_text(content, encoding='utf-8')
    return data_yaml


def main() -> int:
    parser = argparse.ArgumentParser(description='Prepare AI-Hub fire dataset for YOLO training')
    parser.add_argument('--source', required=True, help='Unzipped AI-Hub dataset root')
    parser.add_argument(
        '--output',
        default='datasets/museum_fire/processed',
        help='Processed YOLO dataset output directory',
    )
    parser.add_argument('--val-ratio', type=float, default=0.1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--indoor-only', action='store_true', help='Keep indoor fire scenes only')
    parser.add_argument('--add-coco-person', action='store_true')
    parser.add_argument('--coco-person-count', type=int, default=2000)
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    yaml_template = Path(__file__).resolve().parent / 'museum_fire.yaml'

    if not source.exists():
        print(f'[ERROR] Source not found: {source}', file=sys.stderr)
        return 1

    print(f'[INFO] Scanning {source} ...')
    pairs = find_labeled_pairs(source, indoor_only=args.indoor_only)
    if not pairs:
        print('[ERROR] No image/label pairs found. Check --source path.', file=sys.stderr)
        print('        AI-Hub zip must be extracted first from https://www.aihub.or.kr/', file=sys.stderr)
        return 1

    print(f'[INFO] Found {len(pairs)} labeled image pairs')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    stats = copy_split(pairs, output, args.val_ratio, args.seed)
    print(f'[INFO] Split — train: {stats["train"]}, val: {stats["val"]}, skipped: {stats["skipped"]}')

    if args.add_coco_person:
        added = add_coco_person_samples(output, args.coco_person_count, args.seed)
        print(f'[INFO] COCO person samples added: {added}')

    data_yaml = write_data_yaml(output, yaml_template)
    print(f'[INFO] Wrote {data_yaml}')
    print('[OK] Dataset ready. Next: ./scripts/train_yolo.sh')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
