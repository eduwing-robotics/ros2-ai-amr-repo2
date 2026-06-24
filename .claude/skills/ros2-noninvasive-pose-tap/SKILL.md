---
name: ros2-noninvasive-pose-tap
description: 다른 PC가 라이다/Nav2/Cartographer로 ROS2 도메인을 점유 중일 때, 그 그래프에 방해(publish·노드기동) 없이 subscriber로 로봇 현재 위치(map→base_footprint)만 읽어오는 비침습 read 표준. ROS_DOMAIN_ID 빈값 함정·SUBNET discovery·ssh ControlMaster=no·비대화 셸 소싱까지. URHYNIX 젠지/티원 듀얼. 2026-06-23 티원 검증.
user_invocable: true
tags: [ros2, tf2, noninvasive, urhynix, network]
version: 1
---

# ROS2 Non-invasive Pose Tap

다른 컴퓨터가 라이다/Nav2/SLAM으로 ROS2 도메인을 한창 점유 중일 때, **그 운영을 방해하지 않고** 로봇의 현재 위치만 읽어오는 표준 절차.

## 핵심 원리 (왜 안전한가)

- ROS2 DDS는 **pub/sub** 구조다. **구독자(subscriber)는 발행자(publisher)에 영향을 줄 수 없다.** 토픽/tf를 "듣기"만 하면 라이다·Nav2·Cartographer에 **0의 방해**.
- 비용은 discovery 트래픽 + 수신 대역폭(미미) + 약간의 CPU뿐.
- **절대 금지(=간섭):** 새 노드(SLAM/Nav2/bringup) 기동, 토픽 publish, `/initialpose`·`/goal_pose` 쓰기, 파라미터 변경. 읽기만 한다.

## Use When

- 팀원/다른 PC가 ROS2를 쓰는 중에 로봇 pose만 빼와야 할 때
- 로봇 좌표를 DB·Unity·로그로 흘려보내되 운영 중인 매핑/내비를 안 건드려야 할 때
- pose를 캡처해 웨이포인트를 만들 때 ([[urhynix-teleop-waypoint-capture]]의 읽기 엔진)

## One-Liner — 현재 pose 1회 (map→base_footprint)

```bash
ssh -o ConnectTimeout=8 -o BatchMode=yes -o ControlMaster=no t1@<ROBOT_IP> \
 'source /opt/ros/jazzy/setup.bash; \
  export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; \
  timeout 6 ros2 run tf2_ros tf2_echo map base_footprint'
```

출력의 `Translation: [x, y, z]` + `RPY (radian) [..,..,yaw]`가 지도 기준 로봇 위치다.

> IP는 DHCP로 바뀐다([[project_robot_ip_dynamic]]). ssh alias(`genzi`/`t1`)나 [[ip-drift-resync]]로 먼저 맞춘다. (2026-06-23 기준 `t1` alias는 죽은 `rb.local`을 봐서 `t1@192.168.10.250` 직결 필요 — alias 갱신 권장.)

## 함정표

| 함정 | 증상 | 회피 |
|---|---|---|
| 빈 도메인 | `ros2 topic list` 텅 빔 | 비대화 ssh는 `~/.bashrc`를 안 읽음 → `ROS_DOMAIN_ID` 직접 export (URHYNIX=210) |
| RMW 불일치 | 토픽/노드 안 보임 | `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` 양쪽 통일 |
| discovery 범위 | 다른 호스트 노드만 안 보임 | `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` |
| ssh 멀티플렉스 잔류 | 2번째 호출 hang | `-o ControlMaster=no` |
| pose 토픽 부재 | `/amcl_pose` 못 찾음 | 위치는 **토픽이 아니라 tf** — `tf2_echo map base_footprint` (또는 `base_link`)가 정답 |
| 소싱 누락 | `ros2: command not found` | `source /opt/ros/jazzy/setup.bash` 먼저 |

## 검증

- `tf2_echo`가 1초 간격으로 Translation/RPY를 출력하면 OK.
- 동시에 팀원 라이다/Nav2 토픽 hz가 떨어지지 않는지 확인(완전 무관해야 정상 = 비침습 증명).

관련: [[urhynix-teleop-waypoint-capture]] · [[live-map-pull-from-domain]] · [[ip-drift-resync]]
