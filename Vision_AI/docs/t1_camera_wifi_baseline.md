# T1 RealSense → 노트북 YOLO 영상 연결 (튜닝 전 기준선)

**작성 목적:** 반응 속도·해상도 튜닝 전에, **실제로 동작 확인된 설정**을 기록해 둠.
튜닝 후 문제가 생기면 이 문서대로 되돌리면 됨.

**검증 일자:** 2026-06-23
**검증 결과:** 로봇 `~16 fps` JPEG 송신, 노트북 `check_robot_camera.sh` **OK**, YOLO 사람(손·팔) 인식 동작 확인.

---

## 1. 구성 요약

| 항목 | 값 |
|------|-----|
| 로봇 (T1) | `t1@rb`, IP `192.168.10.250` |
| 노트북 | `hc@hp`, IP `192.168.10.64` |
| ROS | Jazzy, `ROS_DOMAIN_ID=210` |
| DDS | **CycloneDDS** (`rmw_cyclonedds_cpp`) — 로봇·노트북 **둘 다** |
| 카메라 | Intel RealSense D435 (USB, Pi 4) |
| 영상 경로 | raw → Pi에서 JPEG 압축 → Wi-Fi → 노트북 YOLO |

### 데이터 흐름 (기준선)

```
[로봇 Pi]
  RealSense D435
    → /tb3_1/camera/color/image_raw          (424×240, 6fps, RGB)
    → jpeg_compressor (quality=75, max 10fps)
    → /tb3_1/camera/color/image_raw/compressed   (JPEG, BEST_EFFORT)

[Wi-Fi / FastDDS — 팀 기본, Cyclone은 USE_CYCLONEDDS=1]

[노트북]
  robot_yolo_viewer.py
    ← /tb3_1/camera/color/image_raw/compressed
    → JPEG 디코딩 → YOLO (museum_fire_smoke.pt + yolov8n 사람)
    → OpenCV 화면
```

> **중요:** 토픽은 `/camera/camera/...` 가 **아님**.
> RealSense `camera_namespace=tb3_1`, `camera_name=camera` → `/tb3_1/camera/color/...`

---

## 2. 해결했던 문제 (원인 → 조치)

| 증상 | 원인 | 조치 |
|------|------|------|
| `VIDIOC_QBUF` / USB 끊김 | Pi USB 절전·전원 | `setup_pi_usb_realsense.sh`, `initial_reset` 끔, ultra 해상도 |
| 토픽은 보이는데 메시지 0 | 로봇 `LAPTOP_IP`가 `250`(자기 자신)으로 잡힘 | `ros_multimachine_env.sh` 로봇 호스트 분기 수정 |
| `rmw_create_node: failed` | CycloneDDS `SocketReceiveBufferSize 10MB` (Pi 미지원) | 해당 Internal 설정 **제거** |
| 로봇에서 jpeg가 안 나옴 | jpeg가 `/camera/camera/...` 구독, RealSense는 `/camera/color/...` 발행 | 토픽 경로 통일 |
| QoS 불일치 | jpeg `BEST_EFFORT` vs 구독 `RELIABLE` | compressed 수신·발행 모두 **BEST_EFFORT** |

---

## 3. 사전 준비 (최초 1회)

### 로봇 (Pi)

```bash
# 패키지
sudo apt install ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-ros2topic

# USB 안정화 (1회 + 재부팅 권장)
cd ~/workspace/robot_project
sudo ./scripts/setup_pi_usb_realsense.sh
sudo reboot
```

### 노트북

```bash
sudo apt install ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-ros2topic
# YOLO: ros_env 또는 scripts/install_laptop_vision_deps.sh
```

### 코드 동기화 (노트북 → 로봇)

```bash
cd ~/workspace/robot_project
export ROBOT_SSH_PASSWORD='...'
./scripts/sync_to_robot.sh
python3 scripts/ssh_t1.py 'cd ~/workspace/robot_project && ./scripts/build_robot_package.sh'
```

---

## 4. 실행 절차 (매번)

### 4-1. 로봇 — 카메라만

```bash
export ROS_DOMAIN_ID=210 LAPTOP_IP=192.168.10.64
cd ~/workspace/robot_project
./scripts/launch_t1_realsense.sh
```

**정상 로그 예시:**

```
[OK] RMW=cyclonedds peers=192.168.10.250,192.168.10.64 static=192.168.10.250;192.168.10.64
[INFO] Request profile: 424x240x6
[INFO] Publish topic: /camera/color/image_raw/compressed (JPEG)
Open profile: ... Width: 424, Height: 240, FPS: 6
RealSense Node Is Up!
JPEG bridge /camera/color/image_raw -> /camera/color/image_raw/compressed
```

`laptop=192.168.10.250` 이면 **잘못된 것** — 카메라를 끄고 `LAPTOP_IP=192.168.10.64` 확인 후 재시작.

### 4-2. 노트북 — 연결 확인

**새 터미널** (반드시 `source` 후):

```bash
cd ~/workspace/robot_project
source scripts/setup_ros_env.sh
bash scripts/check_robot_camera.sh
```

**성공:**

```
── /camera/color/image_raw/compressed ──
Publisher count: 1 (또는 2)
[OK] message received (qos=best_effort)
[OK] Camera stream OK on /camera/color/image_raw/compressed
```

### 4-3. 노트북 — YOLO 화면

```bash
source scripts/setup_ros_env.sh
./scripts/launch_robot_test.sh run
```

---

## 5. 진단 명령

### 로봇에서 (로컬 스트림 확인)

```bash
source ~/workspace/robot_project/scripts/setup_ros_env.sh
ros2 topic hz /camera/color/image_raw/compressed
# 기대: average rate 약 10~16
```

### 노트북에서

```bash
source scripts/setup_ros_env.sh
ros2 topic hz /camera/color/image_raw/compressed
bash scripts/check_robot_camera.sh
```

### 로봇 USB / RealSense

```bash
./scripts/diagnose_realsense_usb.sh
sudo ./scripts/reset_realsense_usb.sh   # 끊김 시
```

---

## 6. 기준선 파라미터 (튜닝 전 값)

### 로봇 `launch_t1_realsense.sh` 기본

| 변수 | 기본값 |
|------|--------|
| `CAMERA_QUALITY` | Pi에서 `ultra` |
| `COLOR_PROFILE` | `424x240x6` |
| `JPEG_STREAM` | `1` |
| `JPEG_QUALITY` | `75` |
| `JPEG_MAX_FPS` | `10` |
| `REALSENSE_USB_RESET` | `1` (시작 전 USB reset) |

### `museum_patrol_system/config/realsense_wifi.yaml`

- RGB only: depth/infra/gyro/accel OFF
- `rgb_camera.color_profile: '424x240x6'`
- `initial_reset: false`

### 노트북 `launch_robot_test.sh run` → `robot_yolo_viewer.py`

| 항목 | 값 |
|------|-----|
| 토픽 | `/tb3_1/camera/color/image_raw/compressed` |
| `--infer-fps` | `10` |
| `--display-fps` | `12` |
| `--imgsz` | `640` |
| `--upscale-min-width` | `640` (424px 입력 시 내부 960px 업스케일) |
| 사람 모델 | `yolov8n.pt` (companion) |

### DDS (`scripts/ros_multimachine_env.sh`)

- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
- `ROS_STATIC_PEERS="${ROBOT_IP};${LAPTOP_IP}"`
- Cyclone 설정 파일: `~/workspace/robot_project/.cyclonedds_peers.xml`
- `AllowMulticast=true`, explicit peers 250 + 64
- **없음:** `SocketReceiveBufferSize min="10MB"` (Pi에서 도메인 생성 실패 유발)

---

## 7. 관련 파일 (기준선 스냅샷)

| 파일 | 역할 |
|------|------|
| `scripts/launch_t1_realsense.sh` | 로봇 카메라 launch |
| `scripts/setup_ros_env.sh` | ROS + multimachine env |
| `scripts/ros_multimachine_env.sh` | CycloneDDS / LAPTOP_IP |
| `scripts/check_robot_camera.sh` | 노트북 연결 테스트 |
| `scripts/launch_robot_test.sh` | YOLO 뷰어 실행 |
| `museum_patrol_system/launch/realsense_compressed.launch.py` | RealSense + jpeg |
| `museum_patrol_system/launch/realsense_only.launch.py` | JPEG 끈 raw fallback |
| `museum_patrol_system/museum_patrol_nodes/jpeg_camera_compressor_node.py` | JPEG 브리지 |
| `scripts/robot_yolo_viewer.py` | 노트북 단일 프로세스 YOLO |
| `scripts/setup_pi_usb_realsense.sh` | Pi USB 1회 튜닝 |
| `scripts/reset_realsense_usb.sh` | USB 리셋 |

---

## 8. 알려진 경고 (무시 가능)

- `ros_env not found` (로봇) — YOLO 안 돌리므로 무시
- `ROS_LOCALHOST_ONLY is deprecated` — Jazzy 안내 메시지
- `Publisher count: 2` on compressed — image_transport + jpeg 중복 광고 가능, **수신은 정상**

---

## 9. 튜닝 전 되돌리기 체크리스트

튜닝 후 안 되면:

1. **git** 으로 기준선 커밋/브랜치로 checkout (또는 `sync_to_robot.sh` 로 노트북 코드 재배포)
2. 로봇: `./scripts/build_robot_package.sh`
3. 환경 변수만 기준선으로:
   ```bash
   export ROS_DOMAIN_ID=210 LAPTOP_IP=192.168.10.64
   unset CAMERA_QUALITY JPEG_MAX_FPS JPEG_QUALITY   # 기본값 사용
   ```
4. 로봇·노트북 **카메라/YOLO 프로세스 모두 종료** 후 §4 순서대로 재실행
5. `bash scripts/check_robot_camera.sh` 가 OK 인지 확인 후 YOLO 실행

### 빠른 성공 기준 (3줄)

```bash
# 로봇
export ROS_DOMAIN_ID=210 LAPTOP_IP=192.168.10.64 && ./scripts/launch_t1_realsense.sh

# 노트북
source scripts/setup_ros_env.sh && bash scripts/check_robot_camera.sh && ./scripts/launch_robot_test.sh run
```

---

## 10. 정리 원칙

- 현재 기준선은 `launch_t1_realsense.sh` + `launch_robot_test.sh run` 경로만 유지
- 예전 분리 실행용 YOLO launch / viewer 스크립트는 삭제함
- 튜닝은 이 기준선이 다시 확인된 뒤 별도로 진행
