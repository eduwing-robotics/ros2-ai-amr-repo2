#!/usr/bin/env python3
"""Train museum patrol YOLO model (fire + smoke + person)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> int:
    parser = argparse.ArgumentParser(description='Train museum patrol YOLO model')
    parser.add_argument(
        '--data',
        default='datasets/museum_fire/processed/data.yaml',
        help='Dataset data.yaml path',
    )
    parser.add_argument('--model', default='yolov8n.pt', help='Base pretrained weights')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--device', default='cpu', help='cpu | 0 | cuda device id')
    parser.add_argument('--project', default='runs/museum_fire')
    parser.add_argument('--name', default='train')
    parser.add_argument(
        '--export-model',
        default='ai_perception/yolo_detection/models/museum_fire_smoke.pt',
        help='Copy best weights here after training',
    )
    args = parser.parse_args()

    data_path = Path(args.data).expanduser().resolve()
    if not data_path.exists():
        print(f'[ERROR] data.yaml not found: {data_path}')
        print('Run: python3 ai_perception/yolo_detection/training/prepare_aihub_dataset.py --source <AIHUB_DIR>')
        return 1

    model = YOLO(args.model)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=10,
        save=True,
        plots=True,
    )

    best = Path(results.save_dir) / 'weights' / 'best.pt'
    export_path = Path(args.export_model).expanduser().resolve()
    export_path.parent.mkdir(parents=True, exist_ok=True)
    if best.exists():
        export_path.write_bytes(best.read_bytes())
        print(f'[OK] Exported best weights → {export_path}')
    else:
        print(f'[WARN] best.pt not found under {results.save_dir}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
