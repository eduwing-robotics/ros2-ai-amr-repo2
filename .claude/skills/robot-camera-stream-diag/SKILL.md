---
name: robot-camera-stream-diag
description: URHYNIX 로봇 카메라(Pi Camera v2 / RealSense D435) 영상이 끊길 때 hz/bw/CPU/Wi-Fi/USB/foxglove 6대축 8지표를 한 ssh 호출로 동시 측정하고 raw vs compressed 비교 + 해결 옵션 표를 자동 출력하는 진단 스킬. 박물관 시연 dry-run 매번 첫 검증으로 사용. 2026-06-10 T1 RealSense + foxglove_bridge 끊김(라즈베리 11Hz publish + Wi-Fi 65Mbps 대역 초과) 사례에서 도출.
user_invocable: true
tags: [diagnostics, camera, foxglove, wifi, ros2, urhynix]
trigger: "Foxglove/Unity/ros2 화면에서 카메라 영상이 끊기거나 지연이 보일 때, 어디가 병목인지 정량 측정이 필요할 때"
version: 1
---

# Robot Camera Stream Diag (영상 끊김 6대축 정량 진단)

## 언제 쓰나

- Foxglove Studio Image 패널이 뚝뚝 끊김
- Unity 카메라 패널 hz가 낮음
- 박물관 시연 dry-run 직전 카메라 트랙 마지막 검증
- `realsense2_camera_node` / `camera_ros` CPU 한 코어 풀 의심
- Wi-Fi 대역 부족 의심 (대역폭 vs link rate 비교)

## 한 줄 실행 (T1 예시)

```bash
ssh t1@<T1_IP> 'bash -c "
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=230

echo \"[1] raw image hz/bw (10s)\"
timeout 10 ros2 topic hz /camera/camera/color/image_raw 2>&1 | tail -2
timeout 10 ros2 topic bw /camera/camera/color/image_raw 2>&1 | tail -1

echo \"[2] compressed image hz/bw (10s)\"
timeout 10 ros2 topic hz /camera/camera/color/image_raw/compressed 2>&1 | tail -2
timeout 10 ros2 topic bw /camera/camera/color/image_raw/compressed 2>&1 | tail -1

echo \"[3] T1 CPU 상위 (top)\"
top -bn 1 | grep -E \"realsens|foxglov|camera_ros|turtleb\" | head -5

echo \"[4] load average\"
uptime

echo \"[5] Wi-Fi RSSI/link rate\"
iwconfig wlan0 2>/dev/null | grep -E \"Link Quality|Signal level|Bit Rate|ESSID\"

echo \"[6] D435 USB 속도\"
lsusb -t | grep -B1 -A0 -iE \"realsense|8086\"

echo \"[7] foxglove_bridge 클라이언트/드롭 로그\"
tail -20 /tmp/local-fx.log 2>/dev/null | grep -iE \"drop|client|backpressure|warning|error\" | head -5

echo \"[8] 토픽 sub 수 (누가 raw 받는지)\"
ros2 topic info /camera/camera/color/image_raw 2>&1 | head -4
ros2 topic info /camera/camera/color/image_raw/compressed 2>&1 | head -4
"'
```

> 젠지(Pi Camera)는 토픽 prefix를 `/tb3_2/camera/...`로 바꿔서 동일.

## 6대축 8지표 — 무엇을 보나

| 축 | 지표 | 임계 | 의심 |
|---|---|---|---|
| **A. publish 능력** | raw hz | < 25Hz @ 30 설정 | 라즈베리 CPU 한계, 카메라 드라이버 |
| **B. 페이로드** | raw bw | > Wi-Fi link rate × 0.7 | 압축 필수 |
| **C. 압축 효율** | compressed bw / raw bw | < 0.2 | JPEG 정상 |
| **D. 노드 부하** | `realsense` / `camera_ros` CPU | > 80% 1코어 | 해상도/FPS 낮춰야 |
| **E. 시스템 부하** | load avg | > 코어 수 | turtlebot3_bringup 등 동거 노드 검토 |
| **F. 무선 환경** | Wi-Fi link rate, RSSI | < raw bw, RSSI < -65dBm | AP 거리/주파수 변경 |
| **G. USB 대역** | `lsusb -t` 5000M | 480M (USB2)면 D435 FPS↓ | USB3 포트로 이동 |
| **H. 다리** | foxglove_bridge drop/backpressure | drop 메시지 발견 | send_buffer 늘림 / 토픽 줄임 |

## 해결 옵션 표 (raw vs compressed)

| 시나리오 | 권장 |
|---|---|
| 화면만 보기 (Foxglove) | **compressed 토픽 구독** ← 99% 케이스 정답 |
| YOLO/OpenCV 처리 | compressed → Mac에서 `cv2.imdecode()` 디코드 후 추론 |
| Depth 필요 | depth는 raw만 의미있음 (압축 손실 큼), 해상도 ↓ |
| 라즈베리 CPU 더 절약 | realsense relaunch with `enable_depth:=false`, `pointcloud.enable:=false` |
| Wi-Fi 대역 자체 부족 | 라우터 AC/AX 교체, 또는 5GHz 채널 변경 |

## 실제 사례 2026-06-10 (T1 RealSense)

진단 전:
- raw hz **11.27** (목표 30) ❌
- raw bw **14.24 MB/s = 114 Mbps**
- Wi-Fi link rate **65 Mbps** ← 절대 못 보냄 (1.75배 초과)
- realsense CPU **87.5%** (한 코어 풀)
- load avg **3.45** (4코어 한계)
- Wi-Fi RSSI **-46 dBm** (우수, 거리 문제 X)

해결: Foxglove Image 패널 Topic을 `.../compressed`로 1줄 변경.

진단 후:
- compressed hz **29.22** ✅
- compressed bw **2.17 MB/s = 17 Mbps** (Wi-Fi 26%만 사용)
- realsense CPU **~0%** (top 표에서 사라짐)
- foxglove_bridge CPU 43.8 → 53.3% (디코드/forward 부하 약간 ↑)

**raw 토픽 자체는 라즈베리 내부에서 계속 발행되지만 외부로 안 나감** (Foxglove가 compressed만 sub) → CPU 절감 메커니즘은 publisher의 rate limiter라기보다 subscriber 부재로 인한 publish path 단축화로 추정.

## robot-camera-bringup / robot-ip-detect-fallback과의 관계

- `robot-ip-detect-fallback` → IP 잡기
- `robot-camera-bringup` → 카메라 노드 launch + Unity bridge
- **이 스킬 → launch 후 끊김 정량 확인 + 압축/해상도 정책 결정**

## 한 줄 요약

raw publish hz / raw bw / Wi-Fi link rate / 노드 CPU 4개만 봐도 카메라 끊김 원인의 95%는 잡힌다. 정답은 거의 항상 "compressed 토픽 구독으로 전환".
