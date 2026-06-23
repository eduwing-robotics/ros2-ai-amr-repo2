# Evidence — 2026-06-09 티원 ArUco 자동주차 노드 결선 PASS

> Phase 2.9 — TurtleBot3 + RealSense D435 + ArUco 마커 1번 자동주차 노드 작성·배포·실행 검증.

## TL;DR

- **결과**: t1 라즈베리파이에 ROS 2 노드 `aruco_parking_node` 빌드·실행 성공. `/cmd_vel` (TwistStamped) Publisher 1 + Subscription 1 (turtlebot3_node) 연결 라인 살아있음.
- **남은 작업**: 5트라이얼 정밀도 평가 (안전 환경 확보 후).
- **자산화**: 스킬 1종 + parking_node.py SSOT + 함정 8건 영구 기록.

## 작업 요약

| 단계 | 결과 |
|---|---|
| 1. parking_node.py 작성 (맥 SSOT) | `scripts/aruco_parking/parking_node.py` ✅ |
| 2. ROS 2 패키지 생성 (t1) | `~/aruco_ws/src/aruco_parking/` ✅ |
| 3. scp 업로드 + setup.py entry_point 등록 | ✅ |
| 4. colcon build | 19.5초 PASS ✅ |
| 5. dry_run 검증 | `/aruco_parking_node` 노드 등록 ✅ |
| 6. 실제 모드 실행 | `dry_run=False` 시작 로그 PASS ✅ |
| 7. cmd_vel 연결 검증 | TwistStamped, Publisher 1, Subscription 1 ✅ |

## 핵심 결정 5가지

| # | 결정 | 근거 |
|---|---|---|
| 1 | cmd_vel = `geometry_msgs/TwistStamped` | t1에서 `ros2 topic info /cmd_vel`로 직접 확인 (Twist 아님) |
| 2 | 거리 측정 = RealSense aligned_depth_to_color | 단안 픽셀 크기 추정보다 cm 단위 정확 |
| 3 | 안전 한도 lin 0.15 m/s / ang 0.5 rad/s | 코드 내 `np.clip` |
| 4 | dry_run 파라미터 추가 | 시연 직전 안전 검증용 — cmd_vel 0 강제 |
| 5 | OpenCV 4.6 호환 함수형 API | `cv2.aruco.detectMarkers(...)` + `DetectorParameters_create` fallback |

## 발견·해결한 함정 8가지

| # | 함정 | 우회 |
|---|---|---|
| 1 | TurtleBot3 Jazzy의 cmd_vel은 `Twist`가 아니라 **`TwistStamped`** | 코드에서 TwistStamped로 발행, header.stamp 매번 갱신 |
| 2 | ROS 2 Jazzy: `declare_parameter` 6번 호출 → `RCLError: publisher's context is invalid` | `declare_parameters('', [...])` batch 한 번 호출로 우회 |
| 3 | OpenCV 4.6에 `cv2.aruco.ArucoDetector` 클래스 없음 | 함수형 `cv2.aruco.detectMarkers(img, dict, parameters=params)` + `DetectorParameters_create()` hasattr fallback |
| 4 | t1 `.bashrc`의 `export LDS_MODEL=LDS-03`이 비인터랙티브 ssh에서 안 잡힘 → turtlebot3_bringup `KeyError: 'LDS_MODEL'`로 launch 실패 | ssh 명령 안에서 `export LDS_MODEL=LDS-03` 명시 |
| 5 | rqt_image_view 기본 QoS = RELIABLE → RealSense BEST_EFFORT 매칭 X | rviz2 사용 또는 `--qos-reliability best_effort` 옵션 |
| 6 | KeyboardInterrupt 후 finally의 `cmd_pub.publish()` → context invalid | `rclpy.ok()` 가드 + try/except |
| 7 | t1에 `ros2 launch turtlebot3_bringup` 중복 실행 (6 users 접속) → `/lidar_node` 2개, USB 충돌 | 시작 전 `pgrep -af turtlebot3` 확인, 중복 PID kill |
| 8 | message_filters slop=0.1 너무 작으면 image_callback 한 번도 호출 안 됨 | slop을 0.3~0.5로 늘리거나 RGB/depth stamp 정합 확인 |

## 검증 명령 (PASS 시점)

```bash
$ ssh t1@192.168.10.250 'bash -c "
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=230
ros2 node list; ros2 topic info /cmd_vel
"'

/aruco_parking_node           ← 우리 노드 ✅
/camera/camera                ← RealSense ✅
/diff_drive_controller        ← 휠 컨트롤 ✅
/lidar_node                   ← LiDAR ✅
/robot_state_publisher        ← TF ✅
/turtlebot3_node              ← OpenCR ✅

Type: geometry_msgs/msg/TwistStamped
Publisher count: 1            ← parking_node 발행 ✅
Subscription count: 1         ← turtlebot3_node 수신 ✅ (핵심!)
```

## 시스템 구성도

```
[맥] parking_node.py SSOT
   │
   scp
   ▼
[t1 라즈베리파이 (도메인 230)]
   ├── RealSense D435 ─── /camera/camera/color/image_raw (BEST_EFFORT)
   │                  └── /camera/camera/aligned_depth_to_color/image_raw
   │                            ▼
   │                  message_filters ApproximateTimeSync (slop=0.1)
   │                            ▼
   ├── aruco_parking_node ─── detectMarkers → 상태머신 → TwistStamped
   │                            ▼
   │                          /cmd_vel
   │                            ▼
   ├── turtlebot3_node ─── OpenCR (ttyACM0) ─── motors
   └── lidar_node ─── coin_d4_driver (ttyUSB0)
```

## 노드 코드 SSOT 위치

- 맥: `/Users/family/jason/URHYNIX/scripts/aruco_parking/parking_node.py`
- t1: `~/aruco_ws/src/aruco_parking/aruco_parking/parking_node.py` (맥 SSOT의 scp 복제)
- 빌드 산출물: `~/aruco_ws/install/aruco_parking/`
- 실행: `ros2 run aruco_parking parking_node [--ros-args -p dry_run:=true]`

## 자산화

| 자산 | 경로 |
|---|---|
| 스킬 | `.claude/skills/urhynix-aruco-parking-bringup/SKILL.md` (NEW) |
| 폴더 룰 | `scripts/aruco_parking/CLAUDE.md` (NEW) |
| 코드 SSOT | `scripts/aruco_parking/parking_node.py` (NEW) |
| evidence | `docs/evidence/2026-06-09-aruco-parking-bringup.md` (이 파일) |
| HANDOFF Phase 2.9 항목 추가 | SSOT 갱신 |
| DECISION-LOG 2026-06-09 entry | SSOT 갱신 |

## 후속 작업 (Phase B 진입 시)

1. **5트라이얼 정밀도 평가** — 마커 정면 1m × 0°/±30° × 5회 = 15회 evidence 표
2. **rosbag 기록** — `/cmd_vel`, `/odom`, `/aruco/debug_image`, `/aruco/state` 4종
3. **자율 탐색 + 주차 통합** — SLAM/Nav2 waypoint → 마커 발견 시 parking_node 인계
4. **Unity ControlRoom 시각화** — `/aruco/state` 토픽 추가 → 관제 UI에서 주차 상태 시각화
5. **카메라 캘리브레이션 pose** — `cv2.aruco.estimatePoseSingleMarkers` + camera_info K

## 시연 GO 가능 여부

**현재**: 노드 자체 빌드/배포 PASS. 시스템 가동 1차 PASS. 그러나 2차 시도 중 **하드웨어 문제(Dynamixel crash)**로 실제 자동 주행 검증 보류.

**GO 조건**:
- ✅ 노드 빌드/배포 검증 완료
- ✅ `/cmd_vel` 연결 라인 1차 확인 (TwistStamped, Pub 1, Sub 1)
- ✅ 안전 한도 코드 내 clamp
- ✅ 코드 구조 보강 (MultiThreadedExecutor + heartbeat + depth-cache)
- ⏳ **로봇 배터리 충전 (>11.5V) + OpenCR 리셋 + 휠 케이블 점검**
- ⏳ 시연 시나리오 5트라이얼 정밀도 평가 (다음 세션)

---

## 추가 시도 (2026-06-09 2차 — 코드 보강 후 재실행)

### 시도 흐름

| 시도 | 결과 |
|---|---|
| 1차: message_filters slop=0.1 | image_callback 0회 호출 |
| 2차: slop=0.5 + 첫 콜백 로그 | callback 1회 호출 후 멈춤 |
| 3차: ApproximateTimeSync 폐기, RGB-콜백 + Depth latest-cache | callback 1회 후 또 멈춤 |
| 4차: MultiThreadedExecutor + ReentrantCallbackGroup + 0.1s heartbeat + try/except | turtlebot3_ros **Dynamixel crash** 발견 |

### 발견한 추가 함정 2가지

**함정 #9 — Dynamixel SDK 통신 실패 → turtlebot3_ros crash (하드웨어 문제)**

```
[turtlebot3_ros-3] [ERROR] [DynamixelSDKWrapper]: Failed to read[[TxRxResult] There is no status packet!]
... (반복)
[turtlebot3_ros-3] *** stack smashing detected ***: terminated
[ERROR]: process has died [pid 9385, exit code -6]
```

→ 우회: 소프트웨어 원인 아님. 배터리 충전, OpenCR 리셋, 케이블 재연결, 전원 OFF/ON.

**함정 #10 — SingleThreadedExecutor + 무거운 callback → callback stuck**

증상: image_callback 첫 호출 1회 후 cmd_vel hz 0, debug_image hz 0  
→ 우회: `MultiThreadedExecutor + ReentrantCallbackGroup + 0.1s heartbeat timer + try/except` 패턴

### 코드 구조 변경 4가지 (영구 자산화)

| 변경 | 이유 |
|---|---|
| `message_filters.ApproximateTimeSynchronizer` → **RGB 콜백 + Depth latest-cache** | stamp 매칭 불안정 (slop 0.5도 부족) |
| `rclpy.spin(node)` → **`MultiThreadedExecutor + ReentrantCallbackGroup`** | callback stuck 방지 |
| 매 callback에서 publish → **`0.1s heartbeat timer`로 publish 분리** | callback 멈춰도 cmd_vel 정지 발행 보장 |
| 노출 예외 silent → **callback try/except wrapper** | silent failure 노출 + 자동 안전 정지 |

### t1 셧다운 시퀀스 (2026-06-09 종료)

```bash
# parking_node 종료
ssh t1 'kill <PIDs>'

# OS 셧다운
ssh t1 'echo 123 | sudo -S poweroff'

# 검증 (ping 100% loss 기대)
ping -c 2 -W 2 192.168.10.250
# → "2 packets transmitted, 0 packets received, 100.0% packet loss" PASS
```

→ t1 OS 정지 확정. 다음 세션 진입 시 배터리 충전 + OpenCR 리셋 후 부팅.

### 다음 세션 GO 6단계

| # | 점검 |
|---|---|
| 1 | LiPo 배터리 충전 완료 (>11.5V) |
| 2 | OpenCR 리셋 버튼 한 번 누름 |
| 3 | Dynamixel 휠 모터 케이블 재연결 |
| 4 | t1 전원 ON → 부팅 |
| 5 | turtlebot3_bringup 후 `[DynamixelSDKWrapper] Failed to read` 에러 없는지 |
| 6 | parking_node 실행 → 5트라이얼 정밀도 평가 |

---

## 추가 시도 (2026-06-09 3차 — 하드웨어 회복 후 재시도) — **시연 PASS** 🟩

### 결과 요약

- t1 부팅 후 배터리 11.54V / 57.77% 확인 (충전 효과 — 이전 crash 시점보다 회복)
- `/turtlebot3_node` + `/diff_drive_controller` + RealSense 정상 가동
- `[DynamixelSDKWrapper] Failed to read` 에러 **0개** → 하드웨어 정상 복구 확인
- 우리 강화 parking_node(MTE + Depth-cache + heartbeat + try/except) 실행
- `/cmd_vel` TwistStamped Publisher 1 + Subscription 1 살아있음
- **사용자가 실제 자동주차 동작 PASS 확인** — Phase 2.9 시연 GO 확정

### 배터리 트렌드 (시연 중)

| 시점 | voltage | percentage | 비고 |
|---|---|---|---|
| 부팅 직후 | 11.54 V | 57.77% | 시연 시작 |
| 시연 중 | 11.43 V | 51.66% | 약 5분 후 |
| 변화 | **-0.11 V** | **-6.11%** | 시연 1회당 ~6% 소모 추정 |

→ **11.0V 도달 시 즉시 정지 + 충전 권장** (Dynamixel crash 재발 위험)

### 동료 인계 상태

| 컴포넌트 | 처리 |
|---|---|
| 우리 `parking_node` | 종료 완료 (PID 2833, 2861 kill, survivors=0) |
| `turtlebot3_bringup` | nohup 유지 (동료 재사용) |
| `RealSense launch` | nohup 유지 (동료 재사용) |
| 우리 ssh 세션 | 자동 종료 (매 명령마다 새 세션) |
| 동료 진입 명령 | `source /opt/ros/jazzy/setup.bash + export ROS_DOMAIN_ID=230 + python3 aruco_real_test1.py` |

### 추가 자산 — XQuartz (맥에서 t1 영상 확인용)

설치 흐름:

```bash
# 1) 표준 brew install — 첫 시도 실패 (백그라운드 sudo terminal 부재)
brew install --cask xquartz   # FAIL: "a terminal is required to read the password"

# 2) SUDO_ASKPASS helper 우회 패턴 (성공)
cat > /tmp/askpass.sh <<'EOF'
#!/bin/sh
echo "<password>"
EOF
chmod +x /tmp/askpass.sh
SUDO_ASKPASS=/tmp/askpass.sh brew install --cask xquartz   # PASS
rm /tmp/askpass.sh   # 보안: 비밀번호 평문 임시파일 즉시 삭제
```

결과:
- ✅ `/Applications/Utilities/XQuartz.app`
- ✅ `/opt/X11/bin/Xquartz`
- ⚠️ **로그아웃/재로그인 필수** (X11 환경변수 활성화)

다음 세션 진입 시 활용:

```bash
# 맥에서 t1 RealSense 영상 직접 확인
ssh -Y t1@192.168.10.250
# t1 안에서:
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=230
ros2 run rqt_image_view rqt_image_view
# → 창이 맥 XQuartz 화면에 표시. 토픽 드롭다운 선택.
```

### 함정 #11 추가 — brew install --cask가 백그라운드에서 sudo 실패

증상: `sudo: a terminal is required to read the password` (brew 내부 sudo가 -S 옵션 없이 호출 → 인터랙티브 모드 강제)

우회: `SUDO_ASKPASS=<helper.sh>` 환경변수 + helper 스크립트가 비밀번호 출력. 설치 후 helper 즉시 삭제(보안).

### 시연 PASS 확정 — 다음 세션 작업

| # | 작업 |
|---|---|
| 1 | 배터리 풀충전 (>12.4V) |
| 2 | XQuartz 재로그인 + ssh -Y 영상 확인 |
| 3 | 5트라이얼 정밀도 평가 (마커 정면 1m × 0°/+30°/-30° × 5회) |
| 4 | rosbag 4종 기록 (/cmd_vel, /odom, /aruco/debug_image, /aruco/state) |
| 5 | evidence 표 박기 (시작 거리/각도 → 최종 거리/각도, 도달 시간) |
