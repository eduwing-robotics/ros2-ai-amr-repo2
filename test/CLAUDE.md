# /test — Mac 로컬 YOLOv8 / OpenCV 실습 스크래치

> 본 폴더는 PDF 강의자료(`13. OpenCV & ArUco`, `15. YOLOv8 Object Detection`)를
> Mac (Apple M5, arm64) 환경에서 단계별로 재현하기 위한 **로컬 실습 스크래치**다.
> 박물관 시연 본선(`unity/ControlRoom`, robot side)에 박지 않는다.

## 실행 환경

- 칩셋: Apple M5 (arm64), MPS 가속
- Python: 3.13.12 (`/opt/homebrew/bin/python3.13`)
- venv: `.venv/` (이 폴더 안)
- 디스크: 3.9GB 여유 → 추론 only, 학습 금지

## 폴더 룰

1. **새 파일 = 최상단 1~5줄 헤더 주석**으로 의도/입력/출력/실행법 명시
2. **NVIDIA 전용 코드 제거**: `torch.backends.cudnn.enabled`, `cuda.matmul.allow_tf32` → Mac MPS로 치환
3. `cv2.imshow`는 Mac 로컬이라 native 윈도우 정상 — 그대로 사용
4. 모델 가중치(`*.pt`)는 `git` 추적 X (자동 다운로드)
5. 결과 이미지(`*_result.jpg`)는 검증 후 정리

## 진행 phase

- Y0: 폴더 + CLAUDE.md + venv ✅
- Y1: ultralytics + torch + MPS 확인 ✅
- Y2: bus.jpg / zidane.jpg 다운로드 ✅
- Y3: detect_basic.py → bus 탐지 PASS ✅
- Y4: zidane 확장 검증 ✅
- Y5: **`detect_realsense.py`** — T1 RealSense → Mac YOLO 라이브 ← **현재**

## Y5 진입 한 줄

전제: T1에서 `realsense2_camera` + `web_video_server` 살아 있어야 함.

```bash
# T1 측 (한 번만)
ssh -fn t1@192.168.10.250 "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && exec ros2 run web_video_server web_video_server --ros-args -p port:=8080 -p address:=0.0.0.0' > /tmp/local-wvs.log 2>&1"

# Mac 측
source .venv/bin/activate && python detect_realsense.py
```

기본 URL: `http://192.168.10.250:8080/stream?topic=/camera/camera/color/image_raw&type=mjpeg`
환경변수로 override: `T1_IP`, `T1_PORT`, `T1_TOPIC`
