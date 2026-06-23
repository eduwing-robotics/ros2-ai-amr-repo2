# Vision Camera Tech Ref

Pi Camera, Intel RealSense D435, compressed ROS image topics, YOLO/vision work의 빠른 진입점이다.

## Read First

1. `docs/ref/TECH-INDEX.md`
2. `.claude/skills/robot-camera-bringup/SKILL.md`
3. `.claude/skills/unity-camera-panel/SKILL.md` when the target is Unity rendering
4. `docs/status/PROJECT-STATUS.md` Evidence Status camera rows
5. `docs/ref/ARCHITECTURE.md` dual robot role section

## Current Truth

- T1 (`tb3_1`) camera: Intel RealSense D435, not D435i, no IMU.
- Genji (`tb3_2`) camera: Raspberry Pi Camera Module v2, Sony IMX219.
- ROS domain for current dual-robot camera work: `ROS_DOMAIN_ID=210`. (2026-06-15 210으로 통일, cross-discovery PASS)
- T1 custom YOLO studio: `scripts/yolo_training/custom_yolo_studio.py` on Mac, browser UI at `http://127.0.0.1:8766/`.
- T1 low-latency camera bridge: `scripts/yolo_training/t1_compressed_mjpeg_server.py`, default `http://192.168.10.250:8090/preview.jpg`.
- Custom YOLO dataset root: `datasets/custom_object`; training outputs: `runs/custom_object/**/weights/best.pt`.
- Current custom-object cleanup pattern: use ROI burst only when mask/bbox is correct, review with `마스크`/`검수 시작`, delete bad repeated boxes, and save hard-negative background frames with `N 오탐 배경 저장`.
- Unity live topics:
  - `/tb3_2/camera/image_raw/compressed`
  - `/tb3_1/camera/color/image_raw/compressed`
- Unity dual camera live display is verified as of 2026-06-02 (`image-20260602-031954.png`, Confluence `2026.06.02`).
- MVP presentation vision classes: robot, person, important item, fire.
- Fast classifier spike: Google Teachable Machine -> TensorFlow/Keras, classes `empty space`, `box`, `mouse-black/white`, `hand` (Korean labels in Jira: 빈공간, 박스, 마우스(검정/흰색), 손).
- Mac RealSense streaming is not the trusted path; robot/Windows smoke has been validated.
- Latest custom `best.pt` is auto-discovered from `runs/custom_object/*/weights/best.pt`; background false positives should be corrected by adding empty-label hard negatives, not by editing `.pt` directly.

## Verify

- ROS topic hz around 30Hz for camera streams.
- Compressed image transport installed where compressed topics are expected.
- Unity panel renders both camera streams when both robot topics are live.
- Keras classifier emits class + confidence for camera frames before claiming the Teachable Machine spike complete.
- For custom YOLO, verify both positive-object detection and background-only frames. A high mAP on repeated ROI boxes is not enough.
- Before retraining custom YOLO, check duplicate bbox ratios and add `negative_*.jpg` empty-label samples when background false positives appear.
- Evidence file gets updated when camera model, topic, frame rate, or host changes.
