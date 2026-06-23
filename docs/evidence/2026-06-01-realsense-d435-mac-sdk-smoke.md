# RealSense D435 — Mac SDK smoke (2026-06-01)

> 2026-06-01 추가 확인: 같은 D435는 Windows workstation에서 `pyrealsense2==2.58.1.10581` streaming smoke를 PASS했다. Depth/Color `640x480` frame 수신과 center depth sample `0.159 m` 확인. 따라서 이 문서의 BLOCKED 결론은 macOS Tahoe + Homebrew librealsense 경로에 한정한다. Windows evidence: `docs/evidence/2026-06-01-realsense-d435-windows-pyrealsense2-smoke.md`

> 주인님 손에 있는 RealSense 카메라가 D435i가 아니라 **D435**로 확정. Mac에서 SDK enumeration까지는 통과했지만 macOS Tahoe(26) + brew formula 호환성 문제로 **실제 streaming은 차단**. 박물관 매핑(arena_v2_3d) 진입은 라즈베리파이4로 이전하기로 결정한 근거.

## 환경

| 항목 | 값 |
|---|---|
| Mac | MacBook Air, Apple Silicon (arm64) |
| macOS | 26.3.1 (Build 25D2128, **Tahoe**) |
| Homebrew | 5.1.14 (`/opt/homebrew`) |
| Python | 3.14.3 |
| librealsense | 2.58.1 (brew formula, adhoc 서명) |
| USB 포트 | MacBook Air USB-C, USB 3.2 SuperSpeed 5 Gb/s |

## 카메라 확정 정보 (sudo rs-enumerate-devices verbose 기준)

```
Name                : Intel RealSense D435
Serial Number       : 254522075185
Asic Serial Number  : 350423023342
Firmware Version    : 5.15.1.55
Physical Port       : 0-2-4
Advanced Mode       : YES
Product Id          : 0B07
Product Line        : D400
Camera Locked       : YES
Usb Type Descriptor : 3.2
Imu Type            : IMU_Unknown
Connection Type     : USB
```

### 모델 분류 — D435i가 아닌 D435

| 모델 | IMU | RGB | Depth | URHYNIX 영향 |
|---|---|---|---|---|
| ~~D435i (가정)~~ | ✅ BMI055 | ✅ | ✅ | VIO 가능 |
| **D435 (실제)** | ❌ `IMU_Unknown` | ✅ | ✅ | VIO 불가, RGB-D SLAM은 그대로 |

**근거**: `Imu Type: IMU_Unknown` + Product ID `0B07` = D435 (D435i는 Product ID `0B3A`).

### 노출된 Stream Profile

**Stereo Module (Depth + IR)**:
- Depth: `1280×720@30Hz`, `848×480@90Hz`, `640×480@90Hz`, `256×144@300Hz`
- Infrared 1/2: `1280×800@25Hz`, `848×480@90Hz`, `848×100@300Hz`

**RGB Camera**:
- `1920×1080@30Hz`, `1280×720@30Hz`, `848×480@60Hz`, `640×480@60Hz`

→ **박물관 매핑(arena_v2_3d) + 액자 YOLO 인식에 필요한 모든 스트림이 디바이스 레벨에서 작동 가능**. Mac에서 막힌 건 streaming pipeline, 카메라 자체는 정상.

## Phase별 진행 결과

| Phase | 결과 | 비고 |
|---|---|---|
| **0. USB 인식** | ✅ PASS | `ioreg`로 vendor 0x8086, USB SuperSpeed 5 Gb/s 확인 |
| **1. SDK enumeration** | ✅ PASS (sudo 필요) | Device info + Stream profile 전체 노출 |
| **2. Viewer GUI** | ⏭️ SKIPPED | brew formula에 `realsense-viewer` 미포함 (`rs-pointcloud`/`rs-capture`로 대체 가능했지만 streaming 막힘) |
| **3. On-chip calibration** | ⏭️ SKIPPED | streaming 차단으로 진입 불가 |
| **4. 줄자 정확도** | 🟥 BLOCKED | `rs-hello-realsense` Frame timeout |
| **5. 박물관 시나리오** | 🟥 BLOCKED | streaming 차단 |
| **6. Python SDK** | ⏭️ SKIPPED | Python 3.14.3 → pyrealsense2 휠 미호환 가능성 + streaming 차단으로 의미 없음 |
| **7. ROS2 통합** | ❌ NOT APPLICABLE | macOS는 ROS2 Jazzy 공식 미지원 |

## 막힌 원인 — 3중 호환 이슈

### 1) macOS Monterey+ sudo 요구 (해결됨)

```
01/06 14:19:00 ERROR failed to claim usb interface: 0, error: RS2_USB_STATUS_ACCESS
```

- 첫 시도 (비-sudo): `RS2_USB_STATUS_ACCESS` interface 0 점유 실패
- 원인: macOS는 모든 UVC USB 카메라를 OS 레벨 CoreMediaIO/VDC.plugin 드라이버로 점유 (lsof 결과: `ControlCenter`, `avconferenced`, `Slack`, `Chrome`가 잡고 있음)
- 해결: `sudo` 실행으로 통과 → enumeration까지 가능

### 2) brew formula의 빌드 옵션 누락 (streaming 차단 원인)

```
01/06 14:30:30 ERROR Frame didn't arrive within 15000
01/06 14:30:30 ERROR Dispatcher exception caught: mutex lock failed: Invalid argument
```

- `rs-hello-realsense` 15초 동안 단 1프레임도 못 받음
- 원인: brew formula 2.58.1은 `-DHWM_OVER_XU=false` 누락 + Apple Silicon 권장 `-DFORCE_RSUSB_BACKEND=true` 미적용
- 동일 증상 다수 보고: [librealsense#12931](https://github.com/IntelRealSense/librealsense/issues/12931), [#14648](https://github.com/realsenseai/librealsense/issues/14648), [#14302](https://github.com/realsenseai/librealsense/issues/14302), [#14325](https://github.com/realsenseai/librealsense/issues/14325)
- brew 코드서명: `Signature=adhoc`, `TeamIdentifier=not set` → macOS 26의 강화된 IOUSBHost 정책에서 entitlement 부족

### 3) macOS Tahoe(26.3.1) 공식 미지원

- Intel RealSense 공식 macOS 지원: Big Sur/Monterey 시점에 universal binary 제공 이후 적극 업데이트 없음
- M3/M4 Sonoma(14)/Sequoia(15)에서도 동일 `mutex lock failed: Invalid argument` 보고 다수
- **Tahoe(26)은 위 두 OS보다 더 신상** → 호환 보장 X

## 결정 — 박물관 매핑 진입은 Pi4로

### Mac에서 시도하지 않을 것

| 옵션 | 시간 | 성공률 | 사후 ROS2 가능 | 결론 |
|---|---|---|---|---|
| brew --build-from-source + 올바른 flag | 30~60분 | ~40% (Tahoe 신상) | ❌ Mac은 ROS2 미지원 | 시간 대비 무가치 |
| LightBuzz 가이드 source build | 1~2시간 | ~50% | ❌ | 동일 |

### 채택 — Pi4 이전 (95% 확실)

Pi4는 이미 ROS2 Jazzy 풀 스택 부트스트랩 완료 (`docs/evidence/2026-06-01-new-sd-128gb-ros2-jazzy-bootstrap.md`). Linux는 RealSense 1급 지원 플랫폼.

다음 명령으로 진행:

```bash
ssh urhynix-robot
sudo apt install -y ros-jazzy-realsense2-camera ros-jazzy-realsense2-description ros-jazzy-librealsense2*

ros2 launch realsense2_camera rs_launch.py \
  align_depth.enable:=true pointcloud.enable:=true

# 토픽 hz 검증
ros2 topic list | grep camera
ros2 topic hz /camera/camera/color/image_raw         # 통과 기준 30Hz
ros2 topic hz /camera/camera/depth/image_rect_raw    # 통과 기준 30Hz
```

## URHYNIX 박물관 매핑 계획에 미치는 영향

| 항목 | 변화 |
|---|---|
| 가벽 매핑 실패 해결 | ✅ 그대로 (Depth로 낮은 가벽 detect) |
| VIO (Visual-Inertial Odometry) | ❌ 폐기 (IMU 없음) |
| Odom 보정 | LDS-03 + wheel odom만 사용 (기존과 동일) |
| RTAB-Map RGB-D SLAM | ✅ 그대로 가능 |
| 박물관 액자 YOLO + Depth 위치 | ✅ 그대로 가능 |
| Pi 카메라 자리 흡수 | ✅ 그대로 (D435 RGB stream으로 대체) |
| Unity 3D 디지털 트윈 (mesh) | ✅ 그대로 (RTAB-Map mesh export) |
| W2 매핑 일정 영향 | 미미 (Pi4 setup 30분만 추가) |

**전체 박물관 매핑 계획의 95% 살아있음**. IMU 의존 부분(VIO drift 보정)만 빠지고 기존 LDS-03 odom으로 대체.

## 잔여 액션

1. **카메라 케이블을 Pi4 USB 3.0 포트로 이전** (사람 작업, 1분)
2. **`ssh urhynix-robot` + ros-jazzy-realsense2-camera 설치** (자동 가능, 5분)
3. **`ros2 launch realsense2_camera rs_launch.py` + 토픽 30Hz hz 검증** (자동, 5분)
4. (선택) 펌웨어 5.15.1.55 → 5.16.x 업데이트 — Pi4에서 `rs-fw-update`로 가능
5. W2: RTAB-Map smoke + arena_v2_3d 매핑

## 3번째 검증 — `rs-depth` 동일 차단 (2026-06-01 14:33경)

```
$ sudo /opt/homebrew/bin/rs-depth 2>&1 | head -20
There are 1 connected RealSense devices.

Using device 0, an Intel RealSense D435
    Serial number: 254522075185
    Firmware version: 5.15.1.55

rs_error was raised when calling rs2_get_option(options:0x78f09c780, option_id:28):
    failed to set power state
```

- ✅ Enumeration 통과 (3번 일관 — Serial/FW 매번 같은 값)
- ❌ Option 28 (sensor preset) 설정 시점에서 `failed to set power state` — `rs-hello-realsense`의 frame timeout과 **동일 backend 차단**
- 다른 해상도(rs-depth는 848×480) 사용해도 동일 → backend 단의 USB power state 제어 자체가 막혀있음
- **결론**: brew formula의 알려진 빌드 버그가 모든 streaming 데모에 일관되게 적용. macOS source 재빌드 또는 Pi4 이전 외 우회 없음.

## 재현 명령 (Mac에서 다시 시도하고 싶을 때)

```bash
# Phase 0
system_profiler SPUSBDataType | grep -A 10 -i RealSense
ioreg -p IOUSB -l -w 0 | grep -B 2 -A 4 "8086\|RealSense"

# Phase 1 (sudo 필요)
sudo /opt/homebrew/bin/rs-enumerate-devices -s
sudo /opt/homebrew/bin/rs-enumerate-devices         # verbose

# Phase 4 (현 상태에선 timeout — 3종 모두 동일)
sudo /opt/homebrew/bin/rs-hello-realsense           # Frame didn't arrive within 15000
sudo /opt/homebrew/bin/rs-depth                     # failed to set power state
sudo /opt/homebrew/bin/rs-distance                  # (예상 동일)
```

## 외부 근거

- [librealsense#12931 Frame didn't arrive within 5000 on macOS](https://github.com/IntelRealSense/librealsense/issues/12931)
- [librealsense#14648 D435i viewer inconsistent on Mac M2](https://github.com/realsenseai/librealsense/issues/14648)
- [librealsense#14302 Persistent segfaults on Apple Silicon M2](https://github.com/realsenseai/librealsense/issues/14302)
- [librealsense#14325 D435 not working on M4 Sequoia 15.6](https://github.com/realsenseai/librealsense/issues/14325)
- [librealsense#11815 librealsense needs sudo on macOS Monterey/Ventura](https://github.com/IntelRealSense/librealsense/issues/11815)
- [Build RealSense for macOS Monterey | LightBuzz](https://lightbuzz.com/realsense-macos/)
- [librealsense — Homebrew Formulae](https://formulae.brew.sh/formula/librealsense)

## 한줄정리

D435 카메라는 USB 3.2로 정상 인식되고 Depth/RGB/IR 모든 스트림이 SDK에 노출되지만, **macOS Tahoe(26) + brew librealsense 빌드 옵션 누락 + IOUSBHost entitlement 부재** 3중 호환성 이슈로 Mac에서 streaming은 불가. Mac source 재빌드에 시간 갈아넣어도 결국 ROS2가 Mac 미지원이라 Pi4로 옮겨야 하므로 **즉시 Pi4 이전이 정답**. 박물관 매핑 계획은 IMU 의존 부분(VIO)만 폐기되고 95% 그대로 살아있음.
