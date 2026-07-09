---
name: urhynix-genji-nav2-drive
description: 젠지(tb3_2)를 단일 비-ns AMCL+Nav2 스택으로 한방 기동(nav_up.sh)해 Unity 좌표주행시키는 검증 절차. "젠지 켜서 주행", "젠지 좌표주행", "젠지 순찰", "젠지 연결 확인" 요청에 발동. bridge --nav-ns 분기, initialpose 반올림 쿼터니언 조용한 거부(malformed), 옆에 주차된 로봇 블롭으로 AMCL 회전수렴 발산, lifecycle_manager 부분 활성화, endpointRobotId stale TextAsset, 전역 tf 폴백 유령 마커 함정 포함. (2026-07-08 0.8m 오차 4.1cm PASS)
tags: [ros2, nav2, turtlebot3, amcl, genji, unity, urhynix]
version: 1
---

# URHYNIX 젠지 Nav2 좌표주행 (비-ns 단일 스택)

티원(ns+수동 lifecycle)과 **정반대 구조**: 젠지는 표준 `nav2_bringup bringup_launch.py`(비-ns, lifecycle_manager autostart) 하나로 다 올라간다. 2026-06-25 최초 PASS([[urhynix-genji-nav2-driving-bringup]] 메모리, 버그 7종), 2026-07-08 arena_shared 재검증 PASS + 함정 8종 추가 — 이 스킬이 정본.

## 상수 (2026-07-08)

- 접속: `kim@192.168.20.7`(DHCP drift 주의), ssh alias `genzi`, sudo pw 1234
- **도메인 210, 비-ns**: 토픽 `/scan /odom /cmd_vel /amcl_pose /initialpose`, 액션 `/navigate_to_pose`. Unity 계약 토픽만 `/tb3_2/{pose,goal_pose,patrol_waypoints}`(릴레이/브리지가 변환)
- 맵: `~/maps/arena_shared/arena_shared.yaml` (nav_up.sh가 scp)
- 티원과 도메인 분리(티원=2)라 동시 기동해도 DDS 충돌 없음. 단 **물리적으로 옆에 있으면 AMCL 함정**(아래 #4)

## 절차

1. **한방 기동**: `bash scripts/nav_up.sh kim@<현IP> <ix> <iy> <iyaw_deg>` — 스크립트4종+맵 scp → bringup → nav2 → 초기포즈 → pose릴레이 → bridge → endpoint(:10000)까지. 초기포즈를 모르면 placeholder(0 0 0)로 올리고 아래 5번으로.
2. **lifecycle 전수 검증(★autostart를 믿지 말 것, 함정#1)**: `ros2 lifecycle get`으로 8노드 확인 → `inactive`면 수동 `activate`. bt_navigator/planner/collision_monitor가 자주 안 올라옴.
3. **Unity 전환**: `ros_endpoint.json` `endpointRobotId: tb3_2` → **`unityctl exec 'UnityEditor.AssetDatabase.Refresh()'` 필수**(함정#5) → Play 재시작 → **UI 로봇 선택을 젠지로**(함정#6·#7).
4. **초기포즈 확보** — 젠지 전용 주의: 티원이 옆에 주차돼 있으면 **회전 수렴 금지**(함정#4). 사용자에게 위치(맵 클릭/근처 웨이포인트 기준)와 방향(물리 정렬)을 확정받아 **타이트 시딩**(pos cov 0.01, yaw cov 0.06) → nomotion 1회 → `/tb3_2/pose`로 반영 확인.
5. **주행**: 우클릭 출동(`/tb3_2/goal_pose`) 또는 순찰(`/tb3_2/patrol_waypoints`). 첫 goal은 **0.25m보다 멀리**(함정#8).

## 함정표 (2026-07-08 실측, 번호는 이날 발견 순)

| # | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | goal 즉시 거부 "Action server is inactive. Rejecting" | lifecycle_manager autostart가 **일부만 활성화**(bt_navigator/planner/collision_monitor inactive로 방치) — bridge의 wait_for_server는 서버 존재만 보고 active는 안 봄 | 기동 후 8노드 `ros2 lifecycle get` 전수 확인 → inactive는 수동 activate. collision_monitor inactive면 cmd_vel 관문이 막혀 goal 수락돼도 안 움직임 |
| 2 | bridge가 "Nav2 액션서버 대기..."에서 영원히 멈춤 | `patrol_waypoints_bridge.py`가 티원용 `BasicNavigator(namespace=robot)` 기본값 → 비-ns 스택의 `/navigate_to_pose`와 불일치 | **`--nav-ns ''` 인자**(2026-07-08 신설) — Unity 계약 토픽은 `/tb3_2/*` 유지, nav 스택 쪽만 비-ns. `_robot_nav_up.sh`에 반영됨 |
| 3 | initialpose를 발행해도 pose가 꿈쩍 안 함 — **에러 없이 조용히 무시된 것처럼 보임** | ①반올림 쿼터니언(z=0.146,w=0.989)이 정규화 검사 실패 → amcl이 "**Received initialpose message is malformed. Rejecting**"으로 거부(로그에만 남음) ②수락돼도 amcl_pose/tf는 다음 스캔 업데이트까지 옛값(latched) | ①쿼터니언은 반드시 `python3 -c "import math;y=<yaw>;print(repr(math.sin(y/2)),repr(math.cos(y/2)))"` 정밀값 ②수락 판정은 **amcl 로그 "Setting pose: x y yaw"가 유일한 ground truth** ③반영은 `/request_nomotion_update` 1회 후 `/tb3_2/pose`로 확인 |
| 4 | 타이트 시딩+회전 수렴을 해도 매번 0.3~0.55m 엉뚱한 곳으로 이탈 | **바로 옆에 주차된 다른 로봇(티원)이 맵에 없는 블롭** → 라이다 스캔 매칭을 오염 → 회전할수록 파티클이 "맵이 스캔을 더 잘 설명하는" 가짜 위치로 끌려감 (좁은 대칭방 함정의 변종) | 옆에 로봇/미등록 장애물이 있으면 **회전 수렴 자체를 포기** — 위치는 사용자 확정(클릭/웨이포인트 기준), 방향은 물리 정렬("티원과 같은 방향으로 돌려놔 주세요")로 확정한 뒤 타이트 시딩만. 주행 시작하면 블롭에서 멀어지며 자연 수렴 |
| 5 | `ros_endpoint.json` 고쳐도 Unity가 옛 로봇 IP로 접속 | Play 재시작만으론 부족 — **에디터 밖에서 고친 TextAsset은 AssetDatabase.Refresh 전까지 임포트 캐시가 stale** | `unityctl play stop` → `exec 'UnityEditor.AssetDatabase.Refresh()'` → `play start`. 검증은 Editor.log `[ControlRoomApp] ROS IP set: <ip>` |
| 6 | Unity Stop→Play 후 명령이 티원으로 감 | `SelectedRobotId`가 tb3_1로 리셋(06-25 버그#5 재확인) | 명령 전 UI에서 젠지 선택. endpoint 로그 `RegisterPublisher(/tb3_X/...)`로 확인 |
| 7 | **꺼진 티원 마커가 맵에 나타나 젠지를 따라다님**(유령) | `MapMarkerLayer.cs`의 전역 /tf 폴백 — 비-ns 젠지 스택의 전역 tf가 "선택 로봇"(리셋된 tb3_1) 마커에 얹힘. 한 번 set된 마커는 선택을 바꿔도 마지막 위치에 얼어붙음 | 로봇 선택을 젠지로(폴백 중단) + 굳은 유령은 Play 재시작으로 제거. 근본 수정(오프라인 로봇 폴백 차단)은 TODO |
| 8 | 0.3m 거리 goal이 1초 만에 "성공" — 가짜 성공 | 젠지는 **스톡 params**라 `xy_goal_tolerance 0.25`(티원의 0.15 튜닝은 티원 yaml 전용) | 검증 주행은 0.25m보다 충분히 먼 goal로. 정밀도 필요하면 티원처럼 params 패치(별도 작업) |
| 9 | ssh로 robot 셸에서 `ros2 lifecycle get /collision_monitor`가 빈 응답 | CLI 간헐 타임아웃(비-ns 데몬 캐시/부하) | 재시도 1회. 상태 판정 자체는 set activate의 성공 여부로도 가능 |

## 재사용 스크립트

- `scripts/nav_up.sh` — Mac 오케스트레이터 (2026-07-08: arena_shared+현IP+MAP 인자 갱신)
- `scripts/_robot_nav_up.sh` — 로봇측 한방 기동 (bridge `--nav-ns ''` 반영)
- `scripts/patrol_waypoints_bridge.py` — 티원/젠지 겸용 (`--nav-ns`로 분기, PolygonStop 존 토글+90s 타임아웃 내장)
- `scripts/drive_rotate.py` — 제자리 회전 (함정#4 상황에선 쓰지 말 것)

## 검증 (2026-07-08 PASS)

부팅→nav_up.sh(도메인210)→lifecycle 수동 보정(bt_navigator/planner/collision_monitor)→endpointRobotId=tb3_2+Refresh+Play 재시작→초기포즈(사용자 확정 0.10,1.11,0.293 타이트 시딩, amcl "Setting pose" 수락 확인)→`/tb3_2/goal_pose` (0.157,0.317) 발행→**13초 주행, 도착 (0.188,0.344) 오차 4.1cm, 존 토글 해제→복원 왕복 정상**. 배터리 95.5%.

## 관련

[[urhynix-genji-nav2-driving-bringup]](2026-06-25 원본 버그 7종 — 본 스킬이 승계) · [[urhynix-t1-nav2-patrol-drive]](티원 ns 스택 — 구조 반대임에 주의) · [[urhynix-t1-amcl-saved-map]](AMCL 공통 함정) · [[ip-drift-resync]](endpointRobotId) · [[unity-livemap-overrides-static-slot]]
