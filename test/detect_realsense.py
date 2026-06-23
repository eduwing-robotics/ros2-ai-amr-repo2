"""
detect_realsense.py — T1 RealSense D435 라이브 영상 + YOLOv8n 추론 (Y5)

입력: T1(192.168.10.250) web_video_server MJPEG HTTP 스트림
출력: cv2.imshow 라이브 윈도우 (박스 오버레이) + 콘솔 탐지 로그 (1초당 1회)
실행: source .venv/bin/activate && python detect_realsense.py
종료: 'q' 키 또는 Ctrl+C

전제: T1에서 realsense2_camera + web_video_server 둘 다 살아 있어야 함.
검증: curl http://192.168.10.250:8080/ → 토픽 목록 나오면 OK.
"""
import os
import sys
import time
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

T1_IP = os.environ.get("T1_IP", "192.168.10.250")
PORT = int(os.environ.get("T1_PORT", "8080"))
TOPIC = os.environ.get("T1_TOPIC", "/camera/camera/color/image_raw")
URL = f"http://{T1_IP}:{PORT}/stream?topic={TOPIC}&type=mjpeg"

MAX_FRAMES = int(os.environ.get("FRAMES", "0"))  # 0=무한, >0=N 프레임 후 종료
HEADLESS = os.environ.get("HEADLESS", "0") == "1"  # 1=imshow 안 띄움 (검증용)
SAVE_LAST = os.environ.get("SAVE_LAST", "")  # 경로 지정 시 마지막 프레임 저장

device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"[device] {device}")
print(f"[url] {URL}")

model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(URL)
if not cap.isOpened():
    print(f"[error] 스트림 열기 실패: {URL}")
    print("  T1에 web_video_server가 살아 있는지 확인:")
    print(f"  curl http://{T1_IP}:{PORT}/")
    sys.exit(1)

print("[stream] 연결 OK, 'q'로 종료")
last_log = 0.0
frame_count = 0
t0 = time.time()

while True:
    ok, frame = cap.read()
    if not ok:
        print("[warn] 프레임 읽기 실패, 재시도...")
        time.sleep(0.2)
        continue

    results = model(frame, device=device, verbose=False)
    annotated = results[0].plot()

    frame_count += 1
    elapsed = time.time() - t0
    fps = frame_count / elapsed if elapsed > 0 else 0.0
    cv2.putText(annotated, f"FPS {fps:.1f}  device={device}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    if not HEADLESS:
        cv2.imshow("T1 RealSense + YOLOv8n", annotated)

    now = time.time()
    if now - last_log >= 1.0:
        boxes = results[0].boxes
        labels = [model.names[int(b.cls[0])] for b in boxes]
        confs = [float(b.conf[0]) for b in boxes]
        summary = ", ".join(f"{l}({c:.2f})" for l, c in zip(labels, confs)) or "(none)"
        print(f"[{fps:.1f}fps] {summary}", flush=True)
        last_log = now

    if MAX_FRAMES and frame_count >= MAX_FRAMES:
        if SAVE_LAST:
            cv2.imwrite(SAVE_LAST, annotated)
            print(f"[save] {SAVE_LAST}", flush=True)
        break

    if not HEADLESS and (cv2.waitKey(1) & 0xFF == ord("q")):
        break

cap.release()
if not HEADLESS:
    cv2.destroyAllWindows()
print(f"[done] 총 {frame_count} 프레임, 평균 {fps:.1f} fps")
