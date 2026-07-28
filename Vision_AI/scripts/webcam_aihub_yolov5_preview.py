#!/usr/bin/env python3
"""AI-Hub YOLOv5 (fire/smoke) — 노트북 웹캠 테스트 (PyTorch 2.6+ 호환)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

SCRIPT_DIR = Path(__file__).resolve().parent
WS_DIR = SCRIPT_DIR.parent
AIHUB_ROOT = Path(os.environ.get('AIHUB_ROOT', Path.home() / 'Downloads/ai/AI 모델_1-018-058-001'))
YOLOV5_DIR = AIHUB_ROOT / '1.AI모델 소스코드/yolov5'
WEIGHTS = AIHUB_ROOT / '2.학습모델파일/best_fire_yolov5s_results.pt'

if not YOLOV5_DIR.is_dir():
    sys.exit(f'[ERROR] YOLOv5 not found: {YOLOV5_DIR}')
if not WEIGHTS.is_file():
    sys.exit(f'[ERROR] Weights not found: {WEIGHTS}')

sys.path.insert(0, str(YOLOV5_DIR))
sys.path.insert(0, str(WS_DIR / 'museum_patrol_system'))

import torch

_orig_torch_load = torch.load


def _torch_load_compat(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _orig_torch_load(*args, **kwargs)


torch.load = _torch_load_compat  # type: ignore[assignment]

import cv2
from models.common import DetectMultiBackend
from museum_patrol_nodes.detection_filters import DetectionFilter, FilterConfig, RawBox
from utils.augmentations import letterbox
from utils.general import non_max_suppression, scale_boxes
from utils.torch_utils import select_device

BOX_COLORS = {'fire': (0, 0, 255), 'smoke': (128, 128, 128)}
BOX_LABELS = {'fire': 'FIRE', 'smoke': 'SMOKE'}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='AI-Hub YOLOv5 webcam test')
    p.add_argument('--device-index', type=int, default=0)
    p.add_argument('--fire-conf', type=float, default=0.38, help='Display fire if >= this')
    p.add_argument('--smoke-conf', type=float, default=0.18, help='Display smoke if >= this')
    p.add_argument('--model-conf', type=float, default=0.12, help='YOLO raw NMS floor')
    p.add_argument('--no-filter', action='store_true', help='Raw YOLO only (no post-filter)')
    p.add_argument('--imgsz', type=int, default=416)
    p.add_argument('--device', default='0', help='cuda device or cpu')
    return p.parse_args()


def _normalize_name(name: str) -> str:
    n = name.lower().strip()
    if n in ('fire', 'flame', '불꽃'):
        return 'fire'
    if n in ('smoke', '연기'):
        return 'smoke'
    return n


def _draw_boxes(frame, boxes: list[RawBox], detected: set[str]) -> None:
    for box in boxes:
        color = BOX_COLORS.get(box.cls, (0, 255, 0))
        label = BOX_LABELS.get(box.cls, box.cls.upper())
        cv2.rectangle(frame, (box.x1, box.y1), (box.x2, box.y2), color, 2)
        text = f'{label} {box.conf:.2f}'
        ty = box.y1 - 8 if box.y1 > 22 else min(box.y2 - 4, frame.shape[0] - 4)
        cv2.putText(frame, text, (box.x1, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    hud = (
        f'AI-Hub | {", ".join(sorted(detected)).upper()}'
        if detected
        else 'AI-Hub | monitoring (fire/smoke)'
    )
    cv2.putText(frame, hud, (8, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 2, cv2.LINE_AA)


def main() -> int:
    args = parse_args()
    device = select_device(args.device)
    model = DetectMultiBackend(str(WEIGHTS), device=device)
    stride, names = model.stride, model.names
    name_map = {i: _normalize_name(str(n)) for i, n in names.items()}
    imgsz = args.imgsz
    model.warmup(imgsz=(1, 3, imgsz, imgsz))

    det_filter = DetectionFilter(
        FilterConfig(
            fire_confidence=args.fire_conf,
            smoke_confidence=args.smoke_conf,
            model_inference_confidence=args.model_conf,
            fire_confirm_frames=2,
            smoke_confirm_frames=1,
        )
    )
    nms_conf = det_filter.model_conf_floor()

    cap = cv2.VideoCapture(args.device_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.device_index)
    if not cap.isOpened():
        print('[ERROR] Webcam open failed', file=sys.stderr)
        return 1

    print(f'[INFO] AI-Hub YOLOv5 — classes: {names}')
    print(f'[INFO] Weights: {WEIGHTS}')
    print(
        f'[INFO] fire>={args.fire_conf} smoke>={args.smoke_conf} '
        f'nms>={nms_conf} imgsz={imgsz} filter={"off" if args.no_filter else "on"}'
    )
    print('[INFO] Q to quit')

    win = 'AI-Hub YOLOv5 (Q=quit)'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        im = letterbox(frame, imgsz, stride=stride, auto=True)[0]
        im = im.transpose((2, 0, 1))[::-1]
        im_t = torch.from_numpy(im.copy()).to(device)
        im_t = im_t.float() / 255.0
        if len(im_t.shape) == 3:
            im_t = im_t[None]

        pred = model(im_t)
        pred = non_max_suppression(pred, nms_conf, 0.45, max_det=100)

        raw_boxes: list[RawBox] = []
        for det in pred:
            if len(det):
                det[:, :4] = scale_boxes(im_t.shape[2:], det[:, :4], frame.shape).round()
                for *xyxy, conf, cls in reversed(det):
                    cls_name = name_map.get(int(cls), str(int(cls)))
                    if cls_name not in ('fire', 'smoke'):
                        continue
                    x1, y1, x2, y2 = (int(v) for v in xyxy)
                    raw_boxes.append(RawBox(cls_name, float(conf), x1, y1, x2, y2))

        if args.no_filter:
            visible, detected = raw_boxes, {b.cls for b in raw_boxes}
        else:
            visible, detected = det_filter.apply(frame, raw_boxes)

        out = frame.copy()
        _draw_boxes(out, visible, detected)
        cv2.imshow(win, out)
        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
