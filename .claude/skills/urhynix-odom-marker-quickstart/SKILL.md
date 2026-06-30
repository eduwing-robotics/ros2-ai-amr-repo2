---
name: urhynix-odom-marker-quickstart
description: 두 TurtleBot(티원 tb3_1 / 젠지 tb3_2)의 위치를 Unity ControlRoom 맵에 빠르게 띄우는 odom-only 한방 기동. AMCL·map_server·scan정합 없이 bringup + odom_to_pose + endpoint만으로 마커 2개를 충전소에 표시한다. "위치만 대강 표시", "마커 띄워줘", "재기동", "구독모드", "충전소에 로봇 표시"일 때. 정밀 절대위치/Nav2 자율주행이 필요하면 AMCL 경로로 격상.
user_invocable: true
tags: [urhynix, ros2, unity, odom, marker]
---

# URHYNIX odom-only 듀얼 마커 한방 기동

AMCL의 무거운 부수비용(시계 skew·lifecycle ABI·scan frame·초기포즈) 없이, **위치 표시**만 빠르게 하는 경로. 2026-06-25 도출·검증.

## 언제 쓰나 / 안 쓰나

- **쓴다**: 데모/관제에서 "로봇이 맵 어디 있나·움직이나"만 보면 될 때. 재기동 시 빠른 복구.
- **안 쓴다(AMCL로 격상)**: 주행 중에도 절대위치가 정확해야 하거나, **Nav2 자율순찰**(경로계획·추종)이 필요할 때 → AMCL 필수. (AMCL 함정/우회는 아래 [[관련]].)

## ★ 대전제 — 충전소 도킹 후 bringup

odom-only는 **마커 = 오프셋 + bringup 이후 이동량**. bringup 순간 odom 원점이 정해지므로:
- **두 로봇을 충전소에 도킹한 상태에서** 기동해야 마커가 충전소에서 정확히 시작.
- 딴 데서 bringup하면 어긋남. 주행하면 천천히 드리프트 → **다시 도킹하면 리셋**.

## 한방 기동

```bash
# 1) 두 로봇 전원 ON + 충전소 도킹 확인 (ping UP)
# 2) Mac에서:
bash scripts/dual_marker_up.sh            # IP drift 시: bash scripts/dual_marker_up.sh t1@<ip> kim@<ip>
# 3) Unity Stop→Play  (ros_endpoint.json = 젠지 IP)
```

`dual_marker_up.sh`가 하는 일: `odom_to_pose.py`+`_robot_up.sh` scp → 티원(tb3_1, 왼쪽 +y) · 젠지(tb3_2, 오른쪽 −y, +endpoint) 기동. 리부팅으로 `/tmp`가 비어도 매번 재배포하므로 안전.

## 좌표·색 (검증된 상수)

- 충전소 ≈ map **(0,0)** (Unity에서 충전소 클릭→`/tb3_1/goal_pose`로 확인된 값).
- **맵 x축 = 화면 세로, y축 = 화면 가로(+y=왼쪽)**. 가로로 나란히 놓으려면 **y로** 벌린다.
- 티원 `(0, +0.1)` 왼쪽 / 젠지 `(0, −0.1)` 오른쪽. (반대로 보이면 부호 swap.)
- 마커색(`default_robots.json`): 티원 🟢`#34D98C` / 젠지 🔵`#4DA3FF`.

## 함정표 (이 세션에서 도출)

| 함정 | 증상 | 회피 |
|---|---|---|
| pkill self-kill | exit 255, 일부만 죽음 | 패턴 bracket + **kill/launch(=odom_to_pose.py 등 키워드 포함)를 같은 ssh 줄에 두지 말 것**. `_robot_up.sh`는 파일이라 cmdline에 키워드 없어 안전 ([[pkill-f-self-kill-ssh]]) |
| 마커 세로로 겹침 | 두 마커가 위아래로 | 맵 x축이 화면 세로 → **y축으로** 벌린다 |
| /tf fallback 유령 마커 | 안 띄운 로봇이 추가로 뜸 | **ns(tb3_1/tb3_2) bringup** → 글로벌 `base_footprint` 없어 `RobotPoseSubscriber`가 못 잡음 |
| 마커가 충전소 아닌 데 | 위치 어긋남 | bringup 전 **도킹** 필수. 오프셋은 충전소 좌표 |
| `/tmp` 스크립트 소실 | 리부팅 후 "No such file" | `dual_marker_up.sh`가 매번 재 scp |
| IP drift | ssh 안 됨 | 인자로 IP 덮어쓰기, [[project_robot_ip_dynamic]]·robot-ip-detect-fallback |

## Verify

```bash
# 양 로봇 pose가 오프셋 위치로 발행 + endpoint 포트
ssh kim@<genji> 'source /opt/ros/jazzy/setup.bash; source ~/turtlebot3_ws/install/setup.bash; \
  export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; \
  ros2 topic echo /tb3_1/pose --once; ros2 topic echo /tb3_2/pose --once'
nc -z <genji_ip> 10000   # endpoint
```
- 티원 ≈(0,0.1)·젠지 ≈(0,−0.1) 발행, 포트 OPEN.
- Unity: 충전소에 왼쪽 초록(티원)·오른쪽 파랑(젠지) 2마커. 로봇 굴리면 따라 움직임.

## 종료

```bash
# 우리 프로세스만 (전원 유지) — kill/verify 분리
ssh <host> 'for p in "[o]dom_to_pose" "[r]obot.launch" "[t]urtlebot3_ros" "[c]oin_d4" "[d]efault_server_endpoint"; do pkill -9 -f "$p"; done; echo KILLED'
# 전원까지: [[urhynix-robot-shutdown]] / echo <pw>|sudo -S shutdown -h now (젠지 1234/티원 123)
```

## 관련

- 격상(정밀/Nav2): AMCL 경로 — `scripts/scan_frame_fix.py`(ns scan frame 교정), 수동 lifecycle 우회(티원 nav2 lifecycle_manager ABI 깨짐→`ros2 lifecycle set`), 크로스호스트 amcl은 시계 skew로 깨지니 **각 로봇 자기 호스트에서 amcl**. ([[urhynix-dual-fullstack-unity]], [[ros2-noninvasive-pose-tap]], [[unity-passive-pose-twin]])
- 스크립트: `scripts/dual_marker_up.sh`, `scripts/_robot_up.sh`, `scripts/odom_to_pose.py`.

## 한줄정리

충전소 도킹 후 `dual_marker_up.sh` 한 방 → bringup+odom_to_pose+endpoint로 AMCL 없이 티원(초록,왼)·젠지(파랑,오) 마커가 충전소에 뜬다. odom-only라 도킹 전제·주행 드리프트가 한계, 정밀/Nav2는 AMCL로 격상.
