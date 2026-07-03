---
name: urhynix-t1-nav2-patrol-drive
description: 티원(tb3_1)에서 nav2 순회(FollowWaypoints/NavigateToPose) 풀스택을 네임스페이스로 띄우고, "목표방향 회전→1초정지→이동→도착시360도회전→정지" 시퀀스로 순회지점까지, 또는 N개 웨이포인트를 순서대로 돌고 충전독으로 복귀주차시키는 검증된 절차. "티원 순회 실주행", "순회지점으로 이동시켜", "nav2 순회 스택 띄워", "7웨이포인트 다 돌아", "출발위치로 복귀주차" 요청에 발동. nav2_bringup navigation_launch.py의 내장 /tf 리매핑 충돌, OpenCR 시리얼 크래시, amcl_pose QoS mismatch, `/dev/shm` FastRTPS 잔여물 누적으로 인한 시스템 전체 멈춤(재부팅 필요), 벽 인접 웨이포인트 플래닝 실패 포함. (2026-07-01 단일타겟 3.5cm PASS + 7웨이포인트 인프라 검증, 배터리로 최종 완주 이월)
tags: [ros2, nav2, turtlebot3, namespace, lifecycle, patrol, urhynix]
version: 2
---

# URHYNIX 티원 Nav2 순회 실주행

`urhynix-t1-amcl-saved-map`으로 위치추정까지 끝난 티원(tb3_1)에 nav2 순회 풀스택(controller/planner/bt_navigator/waypoint_follower 등)을 얹어서, 지정 좌표까지 "방향 보고→1초 정지→이동→도착 시 360도 회전→정지" 시퀀스로 실주행시킨다.

## Use When

- `urhynix-t1-amcl-saved-map`으로 AMCL/pose/endpoint까지는 떠 있고, 이제 실제로 목표 좌표까지 로봇을 보내야 할 때
- "순회지점으로 실주행", "nav2 순회 스택 첫 기동", "회전-정지-이동-도착회전" 시퀀스가 필요할 때
- costmap이 "frame does not exist"로 영구 activate 실패할 때 (아래 함정#1)

## 전제조건

1. `urhynix-t1-amcl-saved-map` 절차로 bringup+map_server+amcl+pose_publisher+endpoint까지 이미 `active`/발행 중이어야 한다 (도메인 `ROS_DOMAIN_ID=2`, ns `tb3_1`).
2. `/tb3_1/amcl_pose`가 방 범위 안의 sane한 값을 내는지 먼저 확인(`ros2 topic echo --once`) — 이게 확인 안 되면 이 스킬을 시작하지 않는다.

## 절차 (검증된 순서)

1. **params 패치 생성**(최초 1회 또는 `burger.yaml` 원본이 바뀐 경우만) — 로봇에서 `python3 patch_nav_params_ns.py` → `/home/t1/nav2_tb3_1_params.yaml` 생성. 이미 있으면 재생성 불필요(디스크에 영속, 재부팅에도 살아남음).
2. **launch 파일 재배포**(★매 재부팅마다 필요) — `/tmp` 사본은 재부팅으로 사라지므로 로컬 리포에서 매번 scp:
   ```bash
   scp scripts/nav_ns_launch.py t1@<ip>:/home/t1/nav_ns_launch.py
   ```
3. **nav2 스택 기동**(백그라운드 필수 — 이 프로세스들은 장기 상주라 foreground로 띄우면 ssh 세션이 안 끊겨야 함):
   ```bash
   ssh t1@<ip> "unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH LD_LIBRARY_PATH PYTHONPATH ROS_PACKAGE_PATH
   source /opt/ros/jazzy/setup.bash
   export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
   setsid nohup ros2 launch /home/t1/nav_ns_launch.py > /tmp/nav_tb3_1.log 2>&1 </dev/null &"
   ```
4. **수동 lifecycle configure→activate** (lifecycle_manager는 ABI 깨짐 — [[urhynix-t1-nav2-lifecycle-abi]] 우회 그대로): 8개 노드 순서 `controller_server smoother_server planner_server behavior_server bt_navigator waypoint_follower velocity_smoother collision_monitor` — 전부 `configure` 먼저 돌리고, 그 다음 전부 `activate`.
5. **액션서버 확인** — `ros2 action list | grep tb3_1`에 `navigate_to_pose`/`follow_waypoints`/`spin` 등이 떠야 함.
6. **실주행 스크립트 배포+실행** — `scp scripts/patrol_test_seq.py t1:/home/t1/` → **foreground**로 실행(백그라운드 금지, 아래 안전 캐비어트 참고):
   ```bash
   ssh t1@<ip> "... python3 -u patrol_test_seq.py 2>&1 | tee /tmp/patrol_run.log"
   ```
   좌표는 스크립트 상단 `TARGET_X/TARGET_Y` — Unity 저장 순찰경로(`~/Library/Application Support/DefaultCompany/turtlebot/patrols/<mapId>.json`)에서 가져온다.

## 시퀀스 동작 (사용자 확정 스펙, 2026-07-01 실주행 PASS)

1. 현재 amcl_pose에서 목표까지 방위각 계산 → 그 방향으로 제자리 `Spin`(회전)
2. 1초 정지
3. `NavigateToPose`로 목표까지 이동
4. 도착 후 제자리 360도 `Spin`
5. 정지 (Spin 종료 시 속도 자동 0)

실측 PASS(2026-07-01, arena_shared 순회지점1 x=0.121,y=-1.211): 목표 대비 도착 오차 **3.5cm**, 4단계 전부 `STATUS_SUCCEEDED(4)`.

## N웨이포인트 순회 + 충전독 복귀주차 (`scripts/patrol_multi_waypoint.py`)

단일 타겟 시퀀스를 일반화: 각 레그마다 `회전→1초정지→NavigateToPose→1초정지`를 반복하고(다음 레그의 회전이 곧 "도착 후 방향전환"), 마지막에 **충전독 고정좌표(DOCK_X/Y/YAW, AMCL 시딩값과 동일)로 한 번 더 NavigateToPose**해서 주차한다 — 실제로 왔던 경로를 역추적(`ComputePathToPose`+`FollowPath`)하지 않고 충전독을 "그냥 마지막 웨이포인트"로 취급하는 방식(그 편이 훨씬 검증된 안전한 패턴이라 채택, [[urhynix-dual-multi-endpoint-amcl]]류 역추적은 AMCL 발산과 얽혀 보류).

- `wait_pose()`는 **매 레그 후 `self.cur`를 비우지 않는다** — 로봇이 이미 목표 허용오차 안이면 AMCL이 새 메시지를 안 낼 수 있어(update_min_d/a 미달) 강제로 None을 만들면 정상 도착도 "무응답"으로 오판함(아래 함정#10).
- 웨이포인트 좌표는 벽에서 최소 클리어런스(기본 0.25m)를 확보하도록 `scripts/patrol_safe_clearance.py`로 사전 검증/보정할 것(아래 함정#9) — Unity에서 클릭으로 찍은 좌표를 그대로 쓰면 벽 인접 지점에서 플래닝이 실패한다.

## Keepout Zone(보호대상 진입금지) — [[urhynix-t1-nav2-keepout-filter]]

보호대상 주변 반경을 nav2 Costmap Filter(KeepoutFilter)로 하드 회피시키는 절차는 별도 스킬로 분리. 이 스킬과 독립적으로 켜고 끌 수 있으며, 2026-07-01 세션에서 **AMCL 멈춤/실패의 원인이 아님이 명확히 반증됨**(필터 제거 후에도 동일 증상 재현 — 아래 함정#8).

## 함정표 (2026-07-01 실측, #1~7은 최초 검증분, #8~11은 같은 날 후속 세션 추가)

| # | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | costmap/controller/planner가 **영구** `inactive`, 로그에 `Invalid frame ID "..." passed to canTransform ... frame does not exist`(⚠️ "extrapolation"류 타이밍 에러와 다른 종류 — 그 프레임을 그 노드가 애초에 한 번도 못 본 것) | `nav2_bringup/navigation_launch.py`가 `remappings=[('/tf','tf'),('/tf_static','tf_static')]`를 내장 — `PushRosNamespace('tb3_1')`와 결합되면 nav2 tf 리스너가 `/tb3_1/tf`로 격리됨. 그런데 이 프로젝트는 bringup/amcl이 공유(비-ns) `/tf`를 씀(map 프레임이 여러 로봇 간 공유돼야 함) | stock `navigation_launch.py` 쓰지 말고 `scripts/nav_ns_launch.py`(각 `Node()`를 직접 나열, tf `remappings=[]`)로 대체 |
| 2 | 가동 중 `turtlebot3_ros`가 `*** stack smashing detected ***`로 죽음(직전 `DynamixelSDKWrapper: Failed to read[[TxRxResult]...]` 반복) | OpenCR 시리얼 통신 신뢰성 이슈(근본원인 미규명, 장시간 세션 리스크로만 인지) | `_robot_bringup_ns.sh` 재기동 → odom이 (0,0)으로 리셋되므로 **`/tb3_1/initialpose` 재시딩 필수**(아래 #4) |
| 3 | `patrol_test_seq.py` 첫 구독 콜백에서 터무니없는 pose(예: x=-2931, y=14806) 수신 → 회전각 오계산 → `Spin` 즉시 ABORTED | `/tb3_1/amcl_pose` 퍼블리셔 QoS가 `TRANSIENT_LOCAL`인데 rclpy 구독자 기본값은 `VOLATILE` → durability mismatch. **단 이게 유일한 원인은 아님** — QoS 수정 후에도 `ros2 topic echo`(QoS 자동매칭 CLI)로 동일 garbage가 재현된 사례 있음(2026-07-01 충전독 복귀 시도), `amcl.log`에 `Message Filter dropping message ... queue is full`(스캔 처리 백로그) 동반 — AMCL 자체가 발산할 수 있음(근본원인 미규명, 이월) | 구독 QoS를 `TRANSIENT_LOCAL`로 명시 맞춤 + **좌표 sanity-check(±5m 벗어나면 즉시 abort)**를 방어선으로 항상 유지(QoS 고쳐도 이 가드는 계속 필요). garbage 재현 시 `amcl.log`의 큐 오버플로 여부부터 확인 |
| 4 | 재부팅/로봇 재배치 후 AMCL을 "믿고" 재시딩했더니 실제 위치와 어긋나서 이상 주행 | **AMCL 재시딩은 "로봇이 그 좌표에 물리적으로 있다"는 선언** — 실제 위치와 다르면 위험. 특히 사람이 손으로 로봇을 옮긴 직후엔 이전 AMCL 추정치가 완전히 stale | 재시딩 전 **반드시 로봇이 지금 물리적으로 어디 있는지 확인**(충전독 복귀=실제 주행 vs 사람이 손으로 옮김 둘 다 가능 — 방식이 다르면 시딩 좌표/방식도 달라짐). 애매하면 사용자에게 직접 물어본다 |
| 5 | `python3 -u patrol_test_seq.py`를 foreground로 돌리다 ssh/툴콜이 중간에 끊김 → 로봇이 "멈춘 것처럼" 보임 | ssh 세션이 끊기면 로컬 클라이언트(`patrol_test_seq.py`)는 SIGHUP으로 죽지만, **nav2 자체(controller_server 등)는 별도 장기 프로세스라 계속 goal을 수행**할 수 있음 — 클라이언트 kill이 즉각적인 로봇 정지를 보장하지 않음 | 진짜 멈췄는지는 `ros2 topic echo /tb3_1/cmd_vel --once`(무응답=정지) + `amcl_pose`/`odom`으로 실제 위치 확인. 확실히 멈추려면 client kill이 아니라 `NavigateToPose` goal cancel 또는 `/tb3_1/cmd_vel` 직접 0 발행 |
| 6 | ssh 명령이 배너 교환 중 타임아웃(`Connection timed out during banner exchange`) | 로봇 wifi(`codelab_robot_team_2_5G`)가 간헐적으로 끊김(알려진 이슈, [[urhynix-wifi-codelab-status]]) | 몇 초 후 재시도하면 대부분 복구 — 반복 재시도 루프로 흡수 |
| 7 | 재부팅 직후 SSH가 몇 분간 안 열림(ping은 되거나 안 되거나 함) | 정상 부팅 시간(ROS 서비스 기동 포함, 보통 1~3분) | `for` 루프로 10초 간격 폴링. 3분 넘게 안 열리면 그때 재부팅 재시도 고려 |
| 8 | (긴 세션에서) `amcl_pose`/TF가 **완전히 멈춤**(같은 값만 재방송), `NavigateToPose`가 120초 타임아웃(`status=NONE`), 심지어 새 `ros2` CLI가 `rcl_init 실패`로 죽음 | **로봇 시스템 리소스 고갈** — 하루 동안 `pkill`로 프로세스를 수십 번 강제종료하면 FastRTPS 공유메모리(`/dev/shm`) 잔여물이 청소 안 되고 누적(실측 152개 파일)돼 새 DDS participant discovery를 방해함. keepout filter 추가가 원인이라 의심했으나 **필터 제거 후에도 동일 재현돼 반증됨** | `/dev/shm` 파일 개수 확인(`ls /dev/shm | wc -l`, 정상은 재부팅 직후 1~5개) → 많으면 **로봇 전체 재부팅**(`sudo reboot`)이 유일한 확실한 해결책(프로세스 재기동만으론 `/dev/shm` 잔여물이 안 지워짐). 재부팅 직후 `/dev/shm` 1개로 clean, 동일 시퀀스 즉시 clean PASS로 재현 성공 |
| 9 | `ssh ... "... & disown; sleep N; pgrep ..."`처럼 **백그라운드 기동+sleep+상태확인을 한 ssh 호출에 합치면** 종종 exit 143/255로 멈추거나 타임아웃 | setsid로 완전히 분리해도 같은 ssh 세션 안에서 sleep까지 물고 있으면 채널이 걸리는 경우가 있음(정확한 내부 메커니즘 미규명) | **launch(fire-and-forget)와 상태확인을 별도 ssh 호출 2개로 분리**: `ssh "... & disown; echo FIRED"` 먼저, 로컬에서 `sleep N` 한 뒤 `ssh "pgrep ..."`으로 별도 확인. 이 세션에서 100% 안정적으로 재현 |
| 10 | `patrol_multi_waypoint.py`가 특정 레그에서만 `실패 — 중단`(`amcl_pose` 자체는 sane함) | 도착 시점에 로봇이 이미 목표 허용오차(기본 0.25~0.5m) 안이면 AMCL이 새 pose를 안 낼 수 있는데(움직임이 `update_min_d/a` 미달), 스크립트가 매 레그 후 `self.cur=None`으로 강제 리셋하고 5초 안에 "새" 메시지가 안 오면 무조건 실패 처리하던 버그 | `wait_pose()`에서 `self.cur`를 비우지 않고 마지막 값을 유지한 채로 짧게만 spin — "최근값 유효"로 취급. sanity(±5m) 체크는 그대로 유지 |
| 11 | 웨이포인트로 `NavigateToPose`가 `status=6`(ABORTED), 로그에 `worldToMap failed`(픽셀좌표가 맵 크기 밖)+`Failed to create plan with tolerance` | 목표 좌표 자체는 맵 안이고 점유(occupied)도 아니지만 **벽에서 너무 가까움**(당시 costmap `inflation_radius`=0.5m, `robot_radius`=0.1m — 실측 0.14m 이격은 걸러짐). 플래너의 tolerance 탐색이 목표 주변을 훑다가 맵 경계 밖 픽셀까지 스캔하면서 나는 부수적 에러라 "맵 밖"으로 오진하기 쉬움(직접 겪음, 정정 필요) | `scripts/patrol_safe_clearance.py`로 전체 웨이포인트를 사전에 검사·보정(거리변환 기반, 벽 최소 클리어런스 + 웨이포인트 간 최소간격 동시 만족하는 가장 가까운 안전지점으로 이동). **로봇의 현재 위치 자체**가 벽에 너무 가까우면(실측 0.04m) `Spin`(제자리 회전)조차 즉시 ABORTED — 그럴 땐 자동 명령 대신 사용자가 직접 로봇을 벽에서 떼어내야 함. **2026-07-03**: 근본 원인이 소형 아레나(1.9×1.9m) 대비 `inflation_radius`가 과대했던 것으로 추가 규명(하이쿠 조사 — TB3 표준 예시는 robot_radius 대비 ~3.2배 비율, 0.5m는 방 바닥의 25%+를 위험지대화) → `patch_nav_params_ns.py`에서 `inflation_radius`를 0.35m로 하향 패치(양쪽 costmap). 다음 브링업부터 적용, 실주행 재검증 필요 |

## 재사용 스크립트

- `scripts/patch_nav_params_ns.py` — `turtlebot3_navigation2/burger.yaml`(비-ns 기본값)을 tb3_1 프레임/스캔토픽에 맞게 패치 → `/home/t1/nav2_tb3_1_params.yaml`. `inflation_radius`도 0.35m로 하향 패치(양쪽 costmap, 2026-07-03, 함정#11 참고)
- `scripts/nav_ns_launch.py` — controller/planner/bt_navigator 등 8노드를 tf 리매핑 없이 직접 기동(함정#1 수정판, 매 재부팅마다 재배포 필요)
- `scripts/_restart_nav_ns.sh` — nav2 노드만 pkill 후 재기동(bringup/amcl은 안 건드림)
- `scripts/patrol_test_seq.py` — 회전→1초정지→이동→도착시360도회전 시퀀스, `TARGET_X/TARGET_Y` 상단에서 좌표 지정, QoS 수정+안전가드 반영됨
- `scripts/patrol_multi_waypoint.py` — N웨이포인트 순회 + 충전독 복귀주차. `WAYPOINTS` 리스트 + `DOCK_X/Y/YAW` 상단에서 지정, `wait_pose()` 버그 수정 반영(함정#10)
- `scripts/patrol_safe_clearance.py` — 웨이포인트가 벽 안전여유 안쪽이면 거리변환으로 가장 가까운 안전지점으로 보정(함정#11). `python3 patrol_safe_clearance.py <patrol.json> <out.json> [clearance_m=0.25] [sep_m=0.2]`

## 검증 (2026-07-01)

**단일타겟**: bringup(도메인2)→AMCL 재시딩(충전독, 사람이 직접 배치 확인 후)→nav2 8노드 configure+activate→`patrol_test_seq.py` foreground 실행→**전 4단계 `STATUS_SUCCEEDED`, 목표 대비 3.5cm 오차로 도착, Unity 마커 실시간 반영 확인(육안 PASS)**.

**7웨이포인트**: 같은 날 후속 세션에서 `/dev/shm` 시스템 정체(함정#8, 재부팅으로 해결) + 웨이포인트 벽 인접 플래닝 실패(함정#11, `patrol_safe_clearance.py`로 해결) + `wait_pose()` 버그(함정#10, 수정) 순서로 규명·수정 — 재부팅 후 단일타겟 재현 PASS로 시스템 안정성 확인, 7웨이포인트 중 1번 레그 clean PASS까지 확인. **배터리로 최종 완주는 다음 세션 이월** — 재개 시 AMCL 충전독 재시딩부터 `patrol_multi_waypoint.py` 재실행.

## 관련

[[urhynix-t1-amcl-saved-map]](선행 단계 — AMCL/pose/endpoint) · [[urhynix-t1-nav2-lifecycle-abi]](lifecycle 우회 원본) · [[urhynix-multirobot-domain-collision]](도메인/ns 배경) · [[urhynix-wifi-codelab-status]](wifi 불안정 배경) · [[urhynix-t1-nav2-keepout-filter]](보호대상 진입금지, 독립 기능) · `urhynix-nav2-waypoint-patrol`(젠지의 non-ns/nav2_simple_commander 방식 — 티원과는 다른 스택)
