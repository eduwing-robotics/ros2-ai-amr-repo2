"""
detect_basic.py — YOLOv8n 단일 이미지 객체 탐지 (PDF #15 §2 Mac 패치판)

입력: bus.jpg, zidane.jpg (같은 폴더)
출력: bus_result.jpg, zidane_result.jpg + 콘솔 탐지 로그
실행: source .venv/bin/activate && python detect_basic.py

PDF 원본 대비 패치:
- NVIDIA 전용 2줄 제거 (torch.backends.cudnn.enabled, cuda.matmul.allow_tf32)
- Apple Silicon MPS 사용 (device='mps')
- imshow 대신 imwrite 우선 (Mac 로컬이라 imshow도 가능하지만 자동 검증 위해 파일 저장)
"""
import sys
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

# Mac: MPS 가속, 없으면 CPU
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"[device] {device}")

# 1. YOLOv8n 모델 로드 (최초 1회 6MB 자동 다운로드)
model = YOLO("yolov8n.pt")

# 2. 이미지 객체 탐지
images = ["bus.jpg", "zidane.jpg"]
for img_name in images:
    if not Path(img_name).exists():
        print(f"[skip] {img_name} 없음")
        continue

    print(f"\n=== {img_name} 추론 ===")
    results = model(img_name, device=device, verbose=False)

    # 3. 탐지된 객체 정보 출력
    for result in results:
        boxes = result.boxes
        print(f"  탐지 {len(boxes)}건:")
        for box in boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])
            print(f"    - {class_name} (신뢰도 {confidence:.2f})")

        # 4. 결과 이미지 저장
        out_name = img_name.replace(".jpg", "_result.jpg")
        result.save(out_name)
        print(f"  → 저장: {out_name}")

print("\n[done] 전체 추론 완료")
