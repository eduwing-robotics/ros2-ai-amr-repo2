---
name: urhynix-aruco-parking-bringup
description: URHYNIX 티원 TurtleBot3 + RealSense D435 ArUco 마커 자동주차 노드 결선 표준. ROS 2 Jazzy + OpenCV 4.6 + TwistStamped cmd_vel 환경에서 검증된 패턴. parking_node.py 골격 + MultiThreadedExecutor + 0.1s heartbeat + Depth latest-cache 패턴 + 상태머신(SEARCH/APPROACH/ALIGN/PARK_DONE) + dry_run 안전 모드 + 10가지 함정표(declare_parameter race, OpenCV ArucoDetector 부재, LDS_MODEL 누락, QoS 매칭, launch 중복, callback stuck, Dynamixel crash 등). 2026-06-09 t1 라즈베리파이 결선 PASS, 시연 GO는 하드웨어 충전 후 다음 세션.
---

# urhynix-aruco-parking-bringup

> 티원 TurtleBot3 Burger + Intel RealSense D435로 ArUco 마커(DICT_4X4_50, ID 1번)를 검출해 자동 주차하는 ROS 2 노드의 **결선 표준**. ROS 2 Jazzy + OpenCV 4.6 환경에서 검증.

## 자산 위치

| 자산 | 경로 |
|---|---|
| 노드 코드 (SSOT) | `scripts/aruco_parking/parking_node.py` |
| 폴더 룰 | `scripts/aruco_parking/CLAUDE.md` |
| t1 배포 경로 | `~/aruco_ws/src/aruco_parking/aruco_parking/parking_node.py` |
| evidence | `docs/evidence/2026-06-09-aruco-parking-bringup.md` |

## 핵심 결정 (2026-06-09)

| 항목 | 결정 | 이유 |
|---|---|---|
| 카메라 | RealSense D435 + depth 정합(`aligned_depth_to_color`) | 단안보다 거리 정확도 10배 ↑ |
| ArUco 사전 | `DICT_4X4_50`, target_id=1 | 마커 1번 인쇄됨 |
| cmd_vel 타입 | `geometry_msgs/TwistStamped` | TurtleBot3 Jazzy 표준 (Twist 아님!) |
| 목표 거리 | 0.25 m | RealSense 최소 depth(~0.2m) 여유 |
| 안전 한도 | lin ≤ 0.15 m/s, ang ≤ 0.5 rad/s | clamp로 코드 안에 박음 |
| 상태머신 | SEARCH / APPROACH / ALIGN / PARK_DONE | dist > 0.4 = APPROACH, > 0.25 = ALIGN, ≤ 0.25 = PARK_DONE |
| dry_run 파라미터 | 기본값 False, 시연 검증 시 `-p dry_run:=true` | cmd_vel 0 발행 — 안전 검증 |

## 표준 결선 흐름 (8단계)

### 1) t1 사전 점검 (USB 디바이스)

```bash
ssh t1@<t1_IP> 'ls /dev/ttyACM* /dev/ttyUSB* && lsusb | grep -iE "realsense|intel|stmicro"'
# 기대: /dev/ttyACM0 (OpenCR), /dev/ttyUSB0 (LiDAR), RealSense D435
```

### 2) RealSense launch (도메인 230)

```bash
ssh t1@<t1_IP> 'nohup bash -c "
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=230
ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true
" > /tmp/realsense.log 2>&1 & disown'
```

### 3) TurtleBot3 bringup (LDS_MODEL 명시 필수)

```bash
ssh t1@<t1_IP> 'nohup bash -c "
source /opt/ros/jazzy/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=230
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-03                              # ⚠️ 비인터랙티브 ssh에서 .bashrc 안 잡힘 — 명시!
ros2 launch turtlebot3_bringup robot.launch.py usb_port:=/dev/ttyACM0
" > /tmp/turtlebot3.log 2>&1 & disown'
```

### 4) 패키지 생성 (t1, 최초 1회만)

```bash
ssh t1@<t1_IP> 'bash -c "
source /opt/ros/jazzy/setup.bash
mkdir -p ~/aruco_ws/src && cd ~/aruco_ws/src
ros2 pkg create --build-type ament_python aruco_parking \
  --dependencies rclpy sensor_msgs geometry_msgs cv_bridge
"'
```

### 5) parking_node.py 업로드 + entry_point 등록

```bash
# 맥 → t1 scp
scp scripts/aruco_parking/parking_node.py t1@<t1_IP>:~/aruco_ws/src/aruco_parking/aruco_parking/

# setup.py entry_points 추가 (Python 한방)
ssh t1@<t1_IP> 'python3 -c "
p=\"/home/t1/aruco_ws/src/aruco_parking/setup.py\"
s=open(p).read()
if \"parking_node\" not in s:
    s=s.replace(\"\\x27console_scripts\\x27: [\", \"\\x27console_scripts\\x27: [\\n            \\x27parking_node = aruco_parking.parking_node:main\\x27,\")
    open(p, \"w\").write(s)
"'
```

### 6) colcon build

```bash
ssh t1@<t1_IP> 'bash -c "
source /opt/ros/jazzy/setup.bash
cd ~/aruco_ws
colcon build --packages-select aruco_parking --symlink-install
"'
```

`--symlink-install` → Python 코드만 수정하면 rebuild 불필요.

### 7) dry_run 검증 (실제 모드 전 안전 검증)

```bash
ssh t1@<t1_IP> 'nohup bash -c "
source /opt/ros/jazzy/setup.bash
source ~/aruco_ws/install/setup.bash
export ROS_DOMAIN_ID=230
ros2 run aruco_parking parking_node --ros-args -p dry_run:=true
" > /tmp/parking.log 2>&1 & disown'

# 5초 후 검증
sleep 5
ssh t1@<t1_IP> 'bash -c "
source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=230
ros2 node list                                                  # /aruco_parking_node 보여야 함
ros2 topic info /cmd_vel                                        # Publisher 1, Subscription 1
ros2 topic info /aruco/debug_image                              # Publisher 1
"'
```

### 8) 실제 모드 실행

```bash
ssh t1@<t1_IP> 'nohup bash -c "
source /opt/ros/jazzy/setup.bash
source ~/aruco_ws/install/setup.bash
export ROS_DOMAIN_ID=230
ros2 run aruco_parking parking_node                              # dry_run 인자 없음 = False
" > /tmp/parking_real.log 2>&1 & disown'
```

⚠️ 실제 모드는 **사람이 옆에서 비상정지 명령어 클립보드 대기** + 마커 정면 1m + 통로 장애물 0개.

## 비상정지 명령

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {stamp: now}, twist: {linear: {x: 0.0}, angular: {z: 0.0}}}"
```

## 디버그 영상 확인

우분투/맥에서:

```bash
ros2 run rqt_image_view rqt_image_view
# 드롭다운 → /aruco/debug_image
# 화면에 STATE/dist/x_err/cmd 박힌 오버레이 영상
```

## 코드 골격 (핵심만)

```python
class ArucoParkingNode(Node):
    def __init__(self):
        super().__init__('aruco_parking_node')

        # ⚠️ Jazzy context-race 회피: declare_parameter 여러 번 X, batch O
        self.declare_parameters('', [
            ('target_id', 1),
            ('target_distance', 0.25),
            ('cmd_vel_topic', '/cmd_vel'),
            ('rgb_topic',   '/camera/camera/color/image_raw'),
            ('depth_topic', '/camera/camera/aligned_depth_to_color/image_raw'),
            ('dry_run', False),
        ])

        # ⚠️ RealSense는 BEST_EFFORT QoS
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=5)
        rgb_sub   = message_filters.Subscriber(self, Image, rgb_topic,   qos_profile=qos)
        depth_sub = message_filters.Subscriber(self, Image, depth_topic, qos_profile=qos)
        self.sync = message_filters.ApproximateTimeSynchronizer(
            [rgb_sub, depth_sub], queue_size=5, slop=0.1)
        self.sync.registerCallback(self.image_callback)

        # ⚠️ cmd_vel = TwistStamped (TB3 Jazzy)
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)

        # ⚠️ OpenCV 4.6 호환 — ArucoDetector 클래스 없음
        self.aruco_dict   = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters_create() \
            if hasattr(cv2.aruco, 'DetectorParameters_create') \
            else cv2.aruco.DetectorParameters()

    def image_callback(self, rgb_msg, depth_msg):
        # 함수형 detectMarkers (4.6 API)
        corners, ids, _ = cv2.aruco.detectMarkers(rgb, self.aruco_dict, parameters=self.aruco_params)

        # 마커 중심 픽셀 → depth 직접 읽기 → 실제 거리(m)
        cx, cy = int(corner[:,0].mean()), int(corner[:,1].mean())
        patch = depth[cy-1:cy+2, cx-1:cx+2]
        valid = patch[patch > 0]
        distance = float(np.median(valid)) / 1000.0   # mm → m

        # 상태 전이 + P 제어 + 클램프
        ...
        self.cmd_pub.publish(self.make_cmd(lin_x, ang_z))

    def make_cmd(self, lin_x=0.0, ang_z=0.0):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        if self.dry_run:
            lin_x, ang_z = 0.0, 0.0
        msg.twist.linear.x  = float(lin_x)
        msg.twist.angular.z = float(ang_z)
        return msg


def main():
    rclpy.init()
    node = ArucoParkingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # ⚠️ 종료 시 publish race 회피 — rclpy.ok() 가드
        try:
            if rclpy.ok():
                node.cmd_pub.publish(node.make_cmd(0.0, 0.0))
        except Exception:
            pass
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()
```

## 함정표 (10가지 — 모두 2026-06-09 발견·해결)

| # | 함정 | 증상 | 우회 |
|---|---|---|---|
| 1 | **cmd_vel = TwistStamped** (Twist 아님) | `ros2 topic pub` 시 타입 mismatch. 코드도 안 보냄 | `ros2 topic info /cmd_vel`로 타입 사전 확인. TurtleBot3 Jazzy 표준 = TwistStamped |
| 2 | **declare_parameter 여러 번 호출 → context race** | `RCLError: publisher's context is invalid` (init 직후) | `declare_parameters('', [...])` batch 한 번에 |
| 3 | **OpenCV 4.6 — `cv2.aruco.ArucoDetector` 없음** | `AttributeError: module 'cv2.aruco' has no attribute 'ArucoDetector'` | 함수형 API `cv2.aruco.detectMarkers(img, dict, parameters=params)` + `DetectorParameters_create()` fallback |
| 4 | **LDS_MODEL 환경변수가 비인터랙티브 ssh에서 안 잡힘** | `KeyError: 'LDS_MODEL'`로 turtlebot3_bringup launch 즉시 실패 | ssh 명령 안에서 `export LDS_MODEL=LDS-03` 명시. `.bashrc`는 비인터랙티브 셸에서 source 안 됨 |
| 5 | **rqt_image_view 기본 QoS = RELIABLE → RealSense BEST_EFFORT 매칭 X** | rqt 화면 회색, 토픽은 보이는데 영상 안 옴 | rviz2 사용(자동 매칭) 또는 `--qos-reliability best_effort` 옵션. 또는 `ros2 run image_tools showimage` |
| 6 | **finally block의 cmd_pub.publish() race** | KeyboardInterrupt 직후 `context is invalid` | `rclpy.ok()` 가드 + try/except로 감싸기 |
| 7 | **`ros2 launch turtlebot3_bringup` 중복** | 노드 이름 충돌 워닝 (`/lidar_node` 2개), USB 자원 경쟁 | 시작 전 `pgrep -af turtlebot3` 확인. 발견 시 PID kill. 6 users 접속 시 자주 발생 |
| 8 | **message_filters.ApproximateTimeSynchronizer 매칭 불안정** | image_callback이 한 번도 안 불리거나 1회 후 멈춤 (parking 로그에 시작 한 줄만) | slop 0.5도 부족할 수 있음 — **ApproximateTimeSynchronizer 폐기**, RGB-콜백 + Depth latest-cache 패턴으로 전환 |
| 9 | **Dynamixel SDK 통신 실패 → turtlebot3_ros crash** (하드웨어) | turtlebot3.log에 `[DynamixelSDKWrapper]: Failed to read[[TxRxResult] There is no status packet!]` 반복 → `*** stack smashing detected ***: terminated`, exit code -6 | **소프트웨어 원인 아님**. LiPo 배터리 충전(>11.5V), OpenCR 리셋 버튼, 휠 모터 케이블 재연결, 전원 OFF/ON |
| 10 | **SingleThreadedExecutor + 무거운 callback → callback stuck** | image_callback 첫 호출 1회 후 cmd_vel hz 0 / debug_image hz 0 | **`MultiThreadedExecutor` + `ReentrantCallbackGroup` + `0.1s heartbeat timer` + try/except callback** 패턴 채택 |

## 검증 시퀀스 (PASS 기준)

### 매 결선 시 5분 점검

```bash
# 1) USB 디바이스
ssh t1 'ls /dev/ttyACM* /dev/ttyUSB*'
# 기대: /dev/ttyACM0, /dev/ttyUSB0 둘 다 있음

# 2) 노드 5종 살아있나
ssh t1 'source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=230; ros2 node list'
# 기대: /aruco_parking_node, /camera/camera, /diff_drive_controller, /lidar_node,
#        /robot_state_publisher, /turtlebot3_node (6개)

# 3) cmd_vel 연결
ssh t1 'source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=230; ros2 topic info /cmd_vel'
# 기대: Type=TwistStamped, Publisher=1 (parking), Subscription=1 (turtlebot3_node)

# 4) 디버그 영상
ros2 run rqt_image_view rqt_image_view   # /aruco/debug_image 선택
# 기대: 마커 시야 → 노란 원 + STATE/dist/x_err 오버레이
```

### PASS 기준 표

| 항목 | 기대 |
|---|---|
| t1 USB 디바이스 | `/dev/ttyACM0` + `/dev/ttyUSB0` 둘 다 |
| `/aruco_parking_node` | 존재 + `ArUco Parking 시작` 로그 |
| `/cmd_vel` 타입 | `TwistStamped` |
| `/cmd_vel` Publisher | 1 (parking_node) |
| `/cmd_vel` Subscription | 1 (turtlebot3_node) — **이 줄이 핵심**: 0이면 다 무용 |
| `/aruco/debug_image` | Publisher 1, hz > 5 |
| 마커 정면 1m 시야 | `STATE: APPROACH` + `dist: ~1.00m` |
| 목표 거리 도달 | `STATE: PARK_DONE` + cmd_vel 0 |
| 마커 시야 밖 | `STATE: SEARCH (no marker)` + cmd_vel 0 |

## 안전 시연 시나리오 표준 (5트라이얼)

| # | 시작 위치 | 기대 결과 |
|---|---|---|
| A.1 | 마커 정면 1.0m, 각도 0° | PARK_DONE @ 0.22~0.28m, 각도 ±5° 이내 |
| A.2 | 같은 시작점 반복 | 시도 A.1과 동일 결과 (재현성) |
| B.1 | 정면 1.0m, 각도 +30°(좌측) | 회전 정렬 후 APPROACH → PARK_DONE |
| B.2 | 정면 1.0m, 각도 -30°(우측) | 좌우 대칭 |
| C.1 | 마커 시야 밖에서 시작 | SEARCH 유지, cmd_vel 0 (안전) |

→ 5회 시도 평가 시 evidence 표 기록: 시작 거리/각도 + 최종 거리/각도 + 도달 시간 + PASS/FAIL.

## 관련 자산

- 자매 스킬 — `urhynix-battery-bringup` (배터리 트랙 결선 패턴 모티브)
- 자매 스킬 — `urhynix-sensor-bringup` (LDR/PIR 결선과 동일한 nohup+ssh+export 패턴)
- 자매 스킬 — `urhynix-sensor-verify-console` (검증 자산화 패턴)
- 자매 스킬 — `ip-drift-resync` (t1 IP 변동 대응)
- 자매 스킬 — `slam-nav2-arena-survey` (자율 탐색 + 주차 통합 시 — Phase B 진입)
- evidence — `docs/evidence/2026-06-09-aruco-parking-bringup.md`
- SSOT — `docs/status/HANDOFF.md` (Phase 2.9)
- 코드 SSOT — `scripts/aruco_parking/parking_node.py`

## 후속 작업 (Phase 2.9 → 3 진입 시)

| 후속 | 트리거 | 액션 |
|---|---|---|
| 5트라이얼 정밀도 평가 | 안전 환경 확보 | evidence 표 + 영상 rosbag 기록 |
| 자율 탐색 + 주차 통합 (Phase B) | Phase A PASS 후 | SLAM/Nav2 waypoint → 마커 발견 시 parking_node로 인계. `slam-nav2-arena-survey` 스킬 결합 |
| 마커 ID별 의미 분리 | 시연 시나리오 확장 | ID 0 = 충전소, ID 1 = 대기소, ID 2 = 비상정지 등 dict로 분기 |
| Unity ControlRoom 시각화 | 관제 UI 통합 | parking_node 상태(`/aruco/state`) 토픽 추가 발행 → Unity Subscriber |
| 카메라 캘리브레이션 기반 pose | depth 부족 시 보강 | `cv2.aruco.estimatePoseSingleMarkers` + `camera_info` K 매트릭스 |
