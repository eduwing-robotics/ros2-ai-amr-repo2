#!/usr/bin/env python3
"""웹캠 + YOLO + OpenCV 뷰어 (단일 프로세스 — 끊김 최소, 노트북 테스트용)."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

import cv2

try:
    import torch
    from ultralytics import YOLO
    from museum_patrol_nodes.detection_filters import DetectionFilter, FilterConfig, RawBox
    from museum_patrol_nodes.yolo_model_utils import (
        PERSON_CLASS_IDS_COCO,
        extract_person_boxes,
        load_companion_person_model,
        model_has_person,
    )
except ImportError:
    print('[ERROR] source scripts/setup_ros_env.sh 후 실행', file=sys.stderr)
    raise


TARGET = frozenset({'fire', 'smoke', 'person'})
COLORS = {'fire': (0, 0, 255), 'smoke': (128, 128, 128), 'person': (255, 128, 0)}
LABELS = {'fire': 'FIRE', 'smoke': 'SMOKE', 'person': 'PERSON'}
OVERLAY_HOLD_SEC = 1.5


def parse_args() -> argparse.Namespace:
    ws = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description='Webcam YOLO preview (single process)')
    p.add_argument('--device-index', type=int, default=0)
    p.add_argument('--model', type=Path, default=ws / 'models' / 'museum_fire_smoke.pt')
    p.add_argument('--person-model', default='yolov8n.pt')
    p.add_argument('--conf', type=float, default=0.25, help='Fire confidence floor (model NMS)')
    p.add_argument('--smoke-conf', type=float, default=0.45, help='Smoke min confidence')
    p.add_argument('--person-conf', type=float, default=0.40, help='Person min confidence')
    p.add_argument('--imgsz', type=int, default=640)
    p.add_argument('--infer-fps', type=float, default=12.0)
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=480)
    return p.parse_args()


def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f'웹캠 {index} 열기 실패 — WEBCAM_DEVICE=1 시도')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def draw_boxes(frame, boxes, detected: set[str]) -> None:
    for x1, y1, x2, y2, label, conf, color in boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f'{label} {conf:.2f}'
        ty = y1 - 8 if y1 > 22 else min(y2 - 4, frame.shape[0] - 4)
        cv2.putText(frame, text, (x1, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
    hud = f'YOLO | {", ".join(sorted(detected)).upper()}' if detected else 'YOLO | monitoring (fire/smoke/person)'
    cv2.putText(frame, hud, (8, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2, cv2.LINE_AA)


def main() -> int:
    args = parse_args()
    if not args.model.is_file():
        print(f'[ERROR] Model not found: {args.model}', file=sys.stderr)
        return 1

    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    print(f'[INFO] Model: {args.model}')
    print(f'[INFO] Device: {device}, conf={args.conf}, imgsz={args.imgsz}')

    model = YOLO(str(args.model))
    model_names = {idx: name.lower() for idx, name in model.names.items()}
    person_model = None
    person_model_names: dict[int, str] = {}
    if args.person_model and not model_has_person(model_names):
        loaded = load_companion_person_model(args.person_model)
        if loaded is not None:
            person_model, person_model_names = loaded
    main_classes = ('fire', 'smoke') if person_model else ('fire', 'smoke', 'person')
    det_filter = DetectionFilter(
        FilterConfig(
            fire_confidence=args.conf,
            smoke_confidence=args.smoke_conf,
            person_confidence=args.person_conf,
        )
    )
    model_conf = det_filter.model_conf_floor()
    print(f'[INFO] Classes: {list(model.names.values())}')
    if person_model is not None:
        print(f'[INFO] Person model: {args.person_model}')
    print(f'[INFO] Filter: fire>={args.conf}, smoke>={args.smoke_conf}, '
          f'confirm smoke={det_filter.config.smoke_confirm_frames} frames')

    # GPU 워밍업
    import numpy as np
    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    model(dummy, imgsz=args.imgsz, device=device, conf=model_conf, verbose=False)
    if person_model is not None:
        person_model(
            dummy,
            imgsz=args.imgsz,
            device=device,
            conf=args.person_conf,
            classes=PERSON_CLASS_IDS_COCO,
            verbose=False,
        )

    cap = open_camera(args.device_index, args.width, args.height)
    frame_lock = threading.Lock()
    latest_frame = {'img': None}
    overlay = {'boxes': [], 'detected': set(), 'until': 0.0}
    overlay_lock = threading.Lock()
    stop = threading.Event()

    def capture_loop() -> None:
        while not stop.is_set():
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with frame_lock:
                latest_frame['img'] = frame

    def infer_loop() -> None:
        period = 1.0 / max(args.infer_fps, 1.0)
        while not stop.is_set():
            t0 = time.monotonic()
            with frame_lock:
                img = latest_frame['img']
            if img is None:
                time.sleep(0.05)
                continue
            infer_img = img.copy()
            try:
                results = model(
                    infer_img,
                    imgsz=args.imgsz,
                    device=device,
                    conf=model_conf,
                    verbose=False,
                )
            except Exception as exc:
                print(f'[WARN] inference: {exc}')
                continue

            raw_boxes: list[RawBox] = []
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    cls = model_names.get(int(box.cls[0]), '?')
                    if cls not in main_classes:
                        continue
                    x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                    raw_boxes.append(
                        RawBox(cls=cls, conf=float(box.conf[0]), x1=x1, y1=y1, x2=x2, y2=y2)
                    )

            if person_model is not None:
                person_results = person_model(
                    infer_img,
                    imgsz=args.imgsz,
                    device=device,
                    conf=args.person_conf,
                    classes=PERSON_CLASS_IDS_COCO,
                    verbose=False,
                )
                raw_boxes.extend(extract_person_boxes(person_results, person_model_names))

            filtered, detected = det_filter.apply(infer_img, raw_boxes)
            parsed = []
            for box in filtered:
                color = COLORS.get(box.cls, (0, 255, 0))
                parsed.append(
                    (box.x1, box.y1, box.x2, box.y2,
                     LABELS.get(box.cls, box.cls.upper()), box.conf, color)
                )

            with overlay_lock:
                if parsed:
                    overlay['boxes'] = parsed
                    overlay['detected'] = detected
                    overlay['until'] = time.monotonic() + OVERLAY_HOLD_SEC
                    names = ','.join(sorted(detected))
                    print(f'[DETECT] {names} (max conf {max(b[5] for b in parsed):.2f})')
                elif time.monotonic() > overlay['until']:
                    overlay['boxes'] = []
                    overlay['detected'] = set()

            elapsed = time.monotonic() - t0
            sleep_for = period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    threading.Thread(target=capture_loop, daemon=True).start()
    threading.Thread(target=infer_loop, daemon=True).start()

    win = 'Webcam YOLO Preview (Q=quit)'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 960, 540)
    print('[INFO] 카메라 앞에 서 보세요 (사람) 또는 라이터 불꽃 (화재). Q=종료')

    while not stop.is_set():
        with frame_lock:
            frame = latest_frame['img']
        if frame is None:
            cv2.waitKey(10)
            continue
        display = frame.copy()
        with overlay_lock:
            boxes = list(overlay['boxes'])
            detected = set(overlay['detected'])
        draw_boxes(display, boxes, detected)
        cv2.imshow(win, display)
        if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
            break

    stop.set()
    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
