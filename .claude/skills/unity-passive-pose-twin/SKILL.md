---
name: unity-passive-pose-twin
description: 다른 컴퓨터가 라이다/Nav2/SLAM/AMCL로 로봇을 운영 중일 때, 그 운영을 0으로 방해하면서 옆에서 "구독만" 해서 로봇 위치를 우리 Unity ControlRoom 맵에 마커로 띄우는 패시브 디지털트윈 절차. 남의 ros_tcp_endpoint 포트·시리얼·도메인 토픽을 안 뺏는 브리지 배치, 멀티로봇 per-robot /tb3_X/pose, 네임스페이스 tf 함정, 비침습 teardown까지. ros2-noninvasive-pose-tap(읽기 절반)의 Unity 브리지 짝.
user_invocable: true
tags: [ros2, unity, noninvasive, urhynix, digitaltwin]
version: 1
---

# Unity 패시브 Pose 트윈 (옆에서 구독만)

다른 PC(또는 로봇 자체)가 bringup + localize로 도메인 210을 한창 쓰는 중에, **그 운영을 안 건드리고** 로봇 위치만 우리 Unity 맵에 띄운다. 오늘(2026-06-25) 우리가 시리얼·포트·도메인을 점유해 옆 데스크탑 접속을 막은 사고의 정답 패턴.

## 핵심 원리 — 무엇이 안전하고 무엇이 충돌하나

ROS2 DDS는 pub/sub다. **구독자는 발행자를 절대 방해 못 한다** → 위치를 "듣는" 건 항상 안전(상세: [[ros2-noninvasive-pose-tap]]). 충돌하는 **희소 자원은 딱 3개뿐**:

1. **하드웨어 시리얼**(OpenCR `/dev/ttyACM*`, 라이다 `/dev/ttyUSB*`) — bringup 띄운 쪽만 점유. **우리는 bringup을 절대 안 한다.**
2. **`ros_tcp_endpoint`의 TCP 포트**(기본 10000) — 호스트:포트당 리스너 1개. 남이 쓰는 포트를 뺏으면 남의 Unity가 끊긴다.
3. **우리가 publish하는 토픽 *이름*** — 남이 이미 내는 토픽명으로 publish하면 충돌. 우리는 **남이 안 내는 새 토픽**(`/tb3_X/pose`)만 만든다(구독은 무제한 안전).

→ 패시브 트윈 = **bringup 0 + 남의 endpoint 포트 안 뺏기 + 새 pose 토픽만 추가**.

## Use When

- "다른 컴퓨터가 작업 중인데 옆에서 구독만 해서 Unity에 로봇 띄우고 싶다"
- 팀 시연/관전용 트윈을 운영 중인 매핑·내비를 안 건드리고 띄울 때
- 우리가 직접 로봇을 점유하면 안 되는 상황(공유 로봇)

## 브리지 호스트 선택 (Unity는 네이티브 ROS 노드가 아님 → endpoint 필수)

Unity(ROS-TCP-Connector)는 `ros_tcp_endpoint` 하나에 붙어야 ROS를 본다. 그 endpoint를 **어디에 띄우냐**가 비침습의 전부다. 침습 적은 순서:

| 브리지 호스트 | 침습도 | 비고 |
|---|---|---|
| **별도 리눅스 박스**(로봇·작업PC 아님, 같은 서브넷) | 0 (최선) | 로봇·남의 PC 무관. SUBNET discovery로 토픽 다 봄 |
| **로봇 한 대**(작업 PC가 endpoint를 *자기 PC*에 띄운 경우) | 낮음 | endpoint는 **구독만** → 라이다/OpenCR **안 건드림**. 단 그 로봇 :10000을 우리가 점유 |
| Mac | 불가 | ROS 미설치 |

> ⚠️ 이 프로젝트 `ros_endpoint.json`은 `endpointIp`만 있고 포트는 ROS-TCP-Connector 기본 **10000 고정**. 따라서 **브리지 호스트는 :10000이 비어 있어야** 한다 = 남의 endpoint 호스트와 달라야 한다.

## 절차

전제: 작업 측이 localize까지 해서 `map→base_footprint` tf 또는 `/tb3_X/pose`를 이미 도메인에 내고 있다.

### Step 0 — 비침습 read로 발행원 확인 (아직 아무것도 안 띄움)

```bash
# pose가 토픽으로 나오나?  (남이 robot_pose_publisher를 이미 돌리는 경우)
ssh -o ControlMaster=no <robot> 'source /opt/ros/jazzy/setup.bash; \
  export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; \
  ros2 topic list | grep -E "/tb3_._/pose|/tf"; timeout 5 ros2 topic hz /tb3_1/pose'
# 안 나오면 위치는 tf에 있다 → 프레임 이름 확인(ns면 tb3_1/base_footprint)
#   timeout 4 ros2 topic echo /tf | grep -E "frame_id|child_frame_id" | sort -u
```

### Step A — (남이 이미 `/tb3_X/pose`를 냄) Unity만 붙이면 끝

브리지 호스트에서 **우리 endpoint만** 기동:

```bash
ssh <bridge_host> 'source /opt/ros/jazzy/setup.bash; source $HOME/turtlebot3_ws/install/setup.bash; \
  export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; \
  setsid nohup ros2 run ros_tcp_endpoint default_server_endpoint \
    --ros-args -p ROS_IP:=$(hostname -I | cut -d" " -f1) -p ROS_TCP_PORT:=10000 \
    > /tmp/passive_endpoint.log 2>&1 </dev/null &'
```

### Step B — (남이 `/tf`만 냄) tf→pose 리퍼블리셔를 *우리가* 추가

`scripts/robot_pose_publisher.py`는 tf(map→base_footprint)를 **새 토픽** `/tb3_X/pose`로 발행 = 구독(/tf)+신규 publish라 **비침습**. 브리지 호스트에서 로봇 수만큼:

```bash
# 프레임 이름을 Step 0에서 본 그대로 맞춘다. ns 로봇이면:
python3 scripts/robot_pose_publisher.py --robot tb3_1 --root map --target tb3_1/base_footprint
python3 scripts/robot_pose_publisher.py --robot tb3_2 --root map --target tb3_2/base_footprint
# (단일 로봇 비-ns면 --root map --target base_footprint, 또는 Unity의 /tf fallback(RobotPoseSubscriber)로 republisher 생략 가능)
```
그 다음 Step A의 endpoint 기동. (localize가 전혀 없어 tf조차 없으면 트윈 불가 — 이땐 `scripts/odom_to_pose.py`로 odom-only 표시가 한계. 단 이건 남이 localize 안 하는 상황이라 "패시브"가 아님.)

### Step C — 우리 Unity를 브리지로 지정

`unity/ControlRoom/Assets/Resources/RosConfig/ros_endpoint.json` → `"endpointIp": "<bridge_host_ip>"`. Unity Play → `RobotPoseFeed`가 `default_robots.json`의 `poseTopic`(`/tb3_1/pose`,`/tb3_2/pose`)을 구독해 마커 표시. 색은 `markerColor`(티원 `#34D98C`/젠지 `#4DA3FF`).

## 검증 (비침습 증명이 핵심)

1. Unity 콘솔에 `[RobotPoseFeed] subscribed → /tb3_X/pose` + 마커가 맵에 뜬다.
2. **남의 운영이 멀쩡한가** = 비침습 증거: 우리 트윈 켜기 전/후로 작업 측 `/scan`·`/odom`·Nav2 action hz가 **안 떨어진다**. 떨어지면 우리가 어딘가 publish/노드 충돌한 것.
3. 충돌 점검: `ros2 node list`에 우리가 의도한 노드(endpoint, robot_pose_publisher)만 추가됐고 bringup류는 우리 것이 없다.

## 끝나면 — 비침습 teardown (남의 bringup은 절대 안 죽인다)

우리가 추가한 것(endpoint + robot_pose_publisher)**만** 종료. 남의 turtlebot3/coin_d4/Nav2는 손대지 않는다.

```bash
# self-kill 함정([[pkill-f-self-kill-ssh]]): 패턴은 bracket, kill과 verify를 분리, 같은 줄에 비-bracket 키워드 0개
ssh <bridge_host> 'for p in "[r]obot_pose_publisher" "[d]efault_server_endpoint" "[o]dom_to_pose"; do pkill -9 -f "$p"; done; echo KILLED'
# 별도 호출로 확인
ssh <bridge_host> 'pgrep -af "robot_pose_publisher|default_server_endpoint" | grep -v pgrep || echo CLEAN'
```

## 함정표

| 함정 | 증상 | 회피 |
|---|---|---|
| 남의 endpoint 포트 강탈 | 남의 Unity가 끊김 | 브리지 호스트는 :10000 비어 있는 곳(남의 endpoint 호스트 ≠ 우리 것) |
| ns tf 프레임 불일치 | `robot_pose_publisher`가 `tf 대기 중` 무한 | Step 0에서 실제 frame_id 확인 후 `--target tb3_X/base_footprint`로 맞춤 (2026-06-25 듀얼서 발생) |
| 비대화 ssh 미소싱 | `ros2: command not found` | `source /opt/ros/jazzy/setup.bash; source ~/turtlebot3_ws/install/setup.bash` 명시 |
| 도메인/RMW 불일치 | 토픽 안 보임 | `ROS_DOMAIN_ID=210` + `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` + `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` |
| teardown self-kill | exit 255, 일부만 죽음 | bracket 패턴 + kill/verify 분리 ([[pkill-f-self-kill-ssh]]) |
| 로봇을 브리지로 쓰며 bringup도 우리가 함 | 시리얼 점유 = 침습 | endpoint/republisher는 구독만 OK, **bringup은 절대 우리가 안 함** |

## Outputs

- 우리 Unity에 로봇 마커 1~N개 + 작업 측 hz 무변동(비침습 증명) 1건.

## 실전 검증 (2026-06-25 — Case B end-to-end PASS)

옆 데스크탑이 **티원 비-ns bringup(로봇)** + **원격 Nav2/AMCL/rviz(GUI PC)**를 돌리는 실제 상황에서 검증:
- Step 0 read: `/tf`·`/amcl_pose`·`/map`은 있고 `/tb3_X/pose` **없음**, `ros_tcp_endpoint` 아무도 안 띄움(노드목록에 UnityEndpoint 부재) → **티원 :10000 빈 포트** 확인. tf `map→base_footprint` 해석됨(전역 비-ns 프레임).
- Step B: 티원에서 `robot_pose_publisher.py --robot tb3_1 --root map --target base_footprint`(비-ns) → `/tb3_1/pose` 라이브 발행(AMCL 위치 그대로 x0.338/y-0.083).
- Step A: 티원 :10000에 우리 endpoint. Mac→포트 도달 OK.
- 비침습 증명: 우리 켜기 전/후 옆 `/scan` **10.017Hz 무변동**. 우리가 추가한 노드는 republisher+endpoint 2개뿐, bringup·serial 0 점유.
- 교훈: 보통 **아무도 ros_tcp_endpoint를 안 띄우므로 로봇 :10000이 비어 브리지로 쓰기 쉽다**. 단일 비-ns 로봇이면 `--target base_footprint`(ns 접두사 없이).

## 관련

[[ros2-noninvasive-pose-tap]](읽기 절반·왜 안전한가) · [[unity-live-map-twin]](맵 렌더+goal_pose 능동 트윈) · [[urhynix-dual-fullstack-unity]](우리가 직접 듀얼 운영할 때) · [[urhynix-ros-domain-diagnose]](도메인 엉킴 진단) · 스크립트: `scripts/robot_pose_publisher.py`(tf→pose), `scripts/odom_to_pose.py`(odom-only 폴백).

## 한줄정리

구독은 공짜·무해, 충돌은 시리얼·endpoint포트·토픽이름 3개뿐 → bringup 안 하고 :10000 빈 브리지 호스트에 우리 endpoint(+필요시 tf→/tb3_X/pose 리퍼블리셔)만 띄워 우리 Unity를 거기로 붙이면, 남의 운영 0 방해로 로봇 위치가 우리 맵에 뜬다.
