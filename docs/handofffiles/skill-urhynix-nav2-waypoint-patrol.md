---
name: urhynix-nav2-waypoint-patrol
description: TurtleBot3 + Nav2로 저장 웨이포인트 경로를 실주행시키는 표준 — bringup → Nav2(localize-before-costmap) → nav2_simple_commander 실행. 라즈베리/데스크탑 어디서 돌리든 동일. Nav2 bringup abort(costmap tf 타임아웃)·simple_commander 무한대기·SUBNET discovery·pkill 자기-kill·플래너 경로실패 진단 등 함정 7종. Unity 디지털트윈 관찰 연동. 2026-06-23 젠지 검증.
user_invocable: true
tags: [ros2, nav2, turtlebot3, waypoint, patrol, urhynix]
version: 1
---

# URHYNIX Nav2 Waypoint Patrol

저장된 웨이포인트(YAML)를 TurtleBot3가 Nav2로 순서 주행하게 하는 표준 + 이 과정에서 반복해서 물리는 함정 모음. `urhynix-teleop-waypoint-capture`로 만든 경로를 실행하는 단계.

## Use When

- 캡처/생성한 순찰 경로를 실제 로봇으로 돌릴 때
- "순찰시작 눌렀는데 안 움직임 / 카운터만 올라감 / Nav2가 안 뜸"을 디버깅할 때
- Unity ControlRoom으로 로봇 순찰을 실시간 관찰할 때

## 전체 흐름 (전부 같은 로봇 PC, 도메인210/RMW fastrtps/SUBNET)

```bash
# 공통 export (매 터미널)
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET TURTLEBOT3_MODEL=burger

# ① bringup
ros2 launch turtlebot3_bringup robot.launch.py
# ② Nav2 + AMCL (웨이포인트와 같은 맵!) — 띄우자마자 초기위치 연속발행(아래 함정#1)
ros2 launch turtlebot3_navigation2 navigation2.launch.py map:=/home/kim/maps/<그맵>.yaml
# ③ 순찰 실행 (로봇을 START에 놓고)
python3 -u run_waypoints.py waypoints_*.yaml
```

자산: `run_waypoints.py`(=`.claude/skills/urhynix-teleop-waypoint-capture/run_waypoints.py`), 토픽기반은 `scripts/patrol_waypoints_bridge.py`, 맵 슬롯 변환 `scripts/pgm_to_map_slot.py`.

## 함정표 (하드원, 2026-06-23 젠지)

| # | 증상 | 원인 | 회피 |
|---|---|---|---|
| 1 | Nav2 떴는데 planner_server/bt_navigator `inactive`, nav2.log에 "Failed to activate global_costmap ... transform map does not exist" → "Aborting bringup" | **로봇 localize 전에 Nav2 autostart** → global_costmap이 map→base_link tf 없어서 활성 타임아웃 | 런치 **직후 /initialpose를 ~30초 연속 발행**해서 amcl이 costmap 활성 전에 localize되게. (또는 amcl param `set_initial_pose:true`) |
| 2 | `run_waypoints`가 "Waiting for amcl_pose to be received"에서 무한대기 | nav2_simple_commander가 /amcl_pose QoS로 _waitForInitialPose 멈춤(localize는 됐는데) | `nav.initial_pose_received = True` 직접 세팅(tf map→base_footprint로 localize 외부확인). run_waypoints.py에 적용됨 |
| 3 | "amcl/get_state service not available, waiting..." 무한 | 프로세스마다 `ROS_AUTOMATIC_DISCOVERY_RANGE` 불일치 → 서비스 디스커버리 실패 | **모든 프로세스에 SUBNET 통일** (run_waypoints 런치에도 빠뜨리지 말 것) |
| 4 | ssh로 `pkill -f run_waypoints.py` 했더니 세션 끊김(exit 255)/출력 없음 | pkill 패턴이 **자기 ssh 명령줄**(그 문자열 포함)까지 매칭→자살 | 괄호트릭 `pkill -9 -f "[r]un_waypoints"` + **kill과 launch를 다른 ssh 호출로 분리**(launch엔 그 문자열이 있으므로) |
| 5 | 로그에 시작 INFO만, 내 print 안 보임 | nohup 리다이렉트 시 python stdout 블록버퍼링 | `python3 -u`로 실행 |
| 6 | 수동 `ros2 lifecycle set ... activate` 했더니 controller/bt가 `finalized`(죽음) | lifecycle_manager의 bond와 충돌 | 수동 activate 금지 → **Nav2 통째 재시작**(함정#1 방식으로) |
| 7 | 로봇 안 움직이는데 웨이포인트 카운터만 올라감 | 각 NavigateToPose가 abort→FollowWaypoints가 다음으로 skip | 아래 진단표로 abort 원인 규명 |

## 안 움직일 때 진단표

| 로그/관측 | 의미 | 조치 |
|---|---|---|
| `planner_server: Failed to create plan ... tolerance` | 목표 좌표가 그 맵의 **점유/미탐색 셀** = 맵↔좌표 불일치 | 좌표를 **현재 맵에서 새로** 캡처/생성, 또는 좌표 딴 맵으로 구동 |
| `behavior_server: spin failed - Exceeded time allowance` + `/odom` 정지 | 바퀴 안 돎 = 모터/전원 | 본체 메인스위치·배터리·OpenCR 확인 |
| `/odom`은 변하는데 위치 안 맞음 | localize 틀어짐 | START 정확 배치 + /initialpose 재발행 |

## Unity 디지털트윈 관찰 (선택, 비침습)

- 로봇/도메인210에 `ros_tcp_endpoint`(포트10000, `ROS_IP:=0.0.0.0`) 1개 띄우면 Unity가 /map·/tf 수신 → ▲마커 실시간.
- Unity ROS IP는 `Resources/RosConfig/ros_endpoint.json`(endpointIp)로 지정(없으면 선택로봇 hostAddress). shell 편집 가능.
- **arena 맵 표시 회전은 270°** (`StreamingAssets/Maps/arena.json` displayRotationDeg=270, 2026-06-23 정렬 검증). 다른 맵은 ⟲⟳로 맞춰 PlayerPrefs 영속.
- endpoint는 ROS2 액션 미지원 → 토픽기반 순찰은 `patrol_waypoints_bridge.py`([[urhynix-teleop-waypoint-capture]] 참조).

## 검증 (2026-06-23 젠지)

- Nav2 풀스택 active(amcl/planner/controller/bt) + localize(START) + FollowWaypoints 액션 수락 + Unity ▲마커 표시(270° 정렬) — **소프트웨어 전 과정 PASS**.
- 잔여: 캡처 좌표가 저장 map.pgm 자유공간과 불일치(planner 경로실패) → 현재 맵에서 좌표 재캡처 필요. 모터는 정상(제자리 회전 확인).

관련: [[urhynix-teleop-waypoint-capture]] · [[map-pgm-waypoint-autogen]] · [[ros2-noninvasive-pose-tap]] · [[live-map-pull-from-domain]] · [[unity-live-map-twin]] · [[ip-drift-resync]]
