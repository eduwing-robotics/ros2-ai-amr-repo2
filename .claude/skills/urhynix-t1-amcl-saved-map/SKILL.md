---
name: urhynix-t1-amcl-saved-map
description: 티원(tb3_1)을 저장맵(arena_v*)으로 self-host AMCL 위치추정해 Unity ControlRoom에 정확한 마커로 띄우는 검증된 엔드투엔드. 젠지가 다른 도메인/네임스페이스로 별도 운영 중이어도 0 충돌(도메인 분리 + ns 격리). "티원 amcl", "티원 위치추정", "저장맵 amcl 띄워", "티원 유니티 마커 정확히", "충전독 초기포즈", "로봇 맵상 위치 정확히 구독", "맵 교체 후 초기포즈", "충전소 물리 이동", "로봇 손으로 옮김/옮겼음(재시딩)" 요청에 발동. map_server+amcl 수동 lifecycle, 라이브 /map override pin 함정, 글로벌+회전 수렴, 충전독 초기포즈 박아 무-teleop 업그레이드, **맵 교체 시 옛 dock좌표 무효화 대응 패턴**까지. (2026-07-03 arena_shared 재캡처 맵교체 PASS, 2026-07-01 최초 arena_shared PASS, 도메인 2 재확정, 순회 nav2 스택 설치 완료)
---

# URHYNIX 티원 AMCL — 저장맵 위치추정 → Unity 마커

티원(tb3_1)을 **저장된 2D 맵(arena_v5 등)** 위에 라이다 AMCL로 위치추정해서, Unity ControlRoom 맵에 **실제 위치에 정확히** 마커로 띄운다. 젠지가 옆에서 라이브 SLAM(cartographer) 중이어도 안 건드린다(ns 격리).

## 핵심 원리 — 맵≠위치

저장맵은 고정 파일. 로봇은 전원 껐다 켜거나 들었다 놓으면 **odom이 (0,0)으로 리셋** → 자기가 맵 어디인지 모름. `map→odom` tf를 만들어주는 게 **AMCL**(라이다 스캔 ↔ 저장맵 매칭). odom만이면 "켠 자리 기준 상대좌표"라 맵 밖/엉뚱.

전제: 저장맵이 **현재 물리공간과 일치**해야 AMCL이 맞음(벽 바뀌면 어긋남 = map5 0.9m 블로커의 근본원인). 정확하려면 정확한 재SLAM.

## 상수 (2026-07-01 갱신 — 도메인 재확정: 2가 맞음)
- 도메인 `ROS_DOMAIN_ID=2`(티원 전용, 젠지와 분리 운영), `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`. **2026-07-01 세션에서 210↔2 두 번 왕복 후 실측 확정**: `/proc/<pid>/environ`으로 살아있는 bringup·map_server·amcl 5개 프로세스 전부 확인한 결과가 진실 — `unity/ControlRoom/Assets/Scripts/Ros/CLAUDE.md`의 "210 통일"(2026-06-15)은 이후 도메인 재분리로 stale해진 문서였음. `_robot_bringup_ns.sh`/`_robot_amcl_ns.sh`/`_pose_ep_up.sh`는 하위호환 기본값 210을 유지하되 **티원 호출 시 항상 domain 인자에 2를 명시**할 것.
- 티원 ns=`tb3_1`. scan=`/tb3_1/scan`(frame `tb3_1/base_scan` — bringup_ns가 이미 교정, scan_frame_fix는 frame_id 교정 자체는 불필요해도 **시계skew 대응으로 계속 씀**, 아래 절차 참조), odom=`/tb3_1/odom`(20Hz), cmd_vel=`/tb3_1/cmd_vel`(**TwistStamped**)
- 티원 접속 `t1@192.168.20.101`(WiFi)/`t1@192.168.10.51`(랜선), pw 123, ssh alias `t1/tiwon/rb` — **DHCP drift** + AP isolation(WiFi SSH 불가, 랜선직결). `default_robots.json`의 tb3_1 hostAddress도 2026-07-01에 이 WiFi IP로 동기화됨.
- nav2_amcl·nav2_map_server 설치됨(1.3.12). **nav2_lifecycle_manager는 ABI 깨짐**([[urhynix-t1-nav2-lifecycle-abi]]). `nav2_bt_navigator`/`nav2_waypoint_follower`/`nav2_navigation2`/`nav2_bringup`/`turtlebot3_navigation2` **2026-07-01 apt로 설치 완료** — 순회(FollowWaypoints) 풀스택 확보, 단 아직 순회 자체는 미검증(다음 세션 진입점).
- SSOT 2D 맵은 `arena_shared`(2026-07-01부로 `arena_v5` 폐기, [[urhynix-arena-slot-no-hardcode]]) — 아래 예시의 `arena_v5`는 과거 세션 흔적이니 실행 시 `arena_shared`로 치환.

## 절차 (검증된 7단계)

1. **도메인 감지** — 티원 self-bringup: `ssh t1 'bash ~/_robot_bringup_ns.sh tb3_1'`(자체 데몬화, ssh 끊겨도 생존). `/tb3_1/scan`·`/odom` 뜨는지 폴링. **전원 ON ≠ bringup** — 이 한 줄을 꼭 돌려야 토픽이 뜸.
2. **맵 scp** — `scp docs/evidence/maps/<id>/<id>.pgm`(+`.yaml`) → `t1:~/maps/<id>/`(파일당 1회). yaml `image:`가 실제 pgm명인지 확인.
3. **map_server+AMCL (ns, 수동 lifecycle)** — `scripts/_t1_amcl_ns.sh`(scp→run). `/map`을 `/tb3_1/map`으로 격리(젠지 cartographer `/map` non-ns와 충돌 회피), frame=공용 `map`, odom=`tb3_1/odom`, base=`tb3_1/base_footprint`. lifecycle_manager 대신 **`ros2 lifecycle set configure`→`activate` 수동**. 둘 다 `active [3]`이면 OK.
4. **scan frame 교정** — 보통 **불필요**(bringup_ns가 `tb3_1/base_scan`로 이미 냄). amcl.log에 "no laser" 뜨면 `scripts/scan_frame_fix.py`.
5. **초기포즈 + 수렴** — 좌표 알면 `/tb3_1/initialpose` 직접 발행이 최선. 모르면 **글로벌**: `ros2 service call /reinitialize_global_localization std_srvs/srv/Empty {}` → `python3 ~/drive_rotate.py /tb3_1/cmd_vel 0.4 26`(제자리 회전, 병진0=벽충돌X) → `/request_nomotion_update` 몇 회. 공분산(x분산)이 떨어지면 수렴. 회전만은 ±0.25m가 한계 → **병진(teleop)** 추가하면 더 조여짐.
6. **pose republisher + endpoint** — `python3 ~/robot_pose_publisher.py --robot tb3_1 --root map --target tb3_1/base_footprint`(tf→`/tb3_1/pose`) + `ros2 run ros_tcp_endpoint default_server_endpoint -p ROS_IP:=$(hostname -I|cut -d' ' -f1) -p ROS_TCP_PORT:=10000`(turtlebot3_ws overlay). Unity `ros_endpoint.json` → endpoint 호스트(.250)로.
7. **Unity 마커 육안 검증(성역)** — Stop→Play 재연결. ⚠️ **드롭다운서 저장맵 슬롯 명시 선택(pin)** 안 하면 라이브 /map이 덮음(아래 함정). 마커가 실제 위치(충전독)에 맞는지 + 로봇 움직임 따라오는지 확인.

## 함정표 (전부 2026-06-26 실측)
| 증상 | 원인 | 해결 |
|---|---|---|
| 마커가 맵 **밖**으로 튀어나감 | pin 없으면 **라이브 /map(젠지 cartographer)이 저장맵을 덮음** → viewport 메타가 젠지맵 origin/크기로 바뀜 → 티원 좌표를 엉뚱한 좌표계로 픽셀변환 | Unity 드롭다운서 **저장맵 슬롯 선택(pin)** → `pinnedSlot` 설정 → 라이브 override 차단([[unity-livemap-overrides-static-slot]]) |
| amcl "set the initial pose" 무한 | 초기포즈 미발행 | Step 5(글로벌 or /initialpose) |
| lifecycle_manager 죽음(diagnostic_updater) | ABI 충돌 | 수동 `configure`→`activate` |
| `/map` 발행자 2개 | 젠지 cartographer와 토픽명 충돌 | map_server `topic_name:=/tb3_1/map` ns 격리 |
| scan "earlier than transform cache" | 크로스호스트 amcl 시계skew | **각 로봇 self-host AMCL**(티원 amcl은 티원에서) |
| ssh exit 255, 일부만 죽음 | teardown 패턴이 ssh 명령줄 노출 → pgrep이 셸 매칭 → self-kill | **PID로만 kill**(패턴+kill 같은 줄 금지), 또는 스크립트 파일 내부([[pkill-f-self-kill-ssh]]) |
| 전원 ON인데 `/tb3_1` 없음 | bringup 미실행 | `bash ~/_robot_bringup_ns.sh tb3_1` 꼭 |
| 맵 교체 후 옛 dock 좌표로 시딩했더니 Unity 마커가 실제 위치와 다름 | SLAM 재캡처마다 맵 `origin`이 달라짐(이전 캡처와 무관) — 옛 좌표는 옛 원점 기준이라 새 맵에선 무의미 | "맵 교체 시 초기포즈 재확보 절차"(아래) — 사용자 클릭 ground truth + 위치고정/방향탐색 패턴 |
| 글로벌 로컬라이제이션(회전) 반복해도 공분산은 작은데 매번 다른 위치로 수렴 | 좁고 대칭적인 방이라 위치+방향을 동시 탐색하면 벽 대칭에 낚여 로컬 최적점(그럴싸하지만 틀림)에 안착 | 위치는 먼저 사용자 ground truth로 고정(covariance 작게), 방향만 느슨하게 열어서 회전 — 탐색 차원을 1개로 줄이면 급격히 안정화 |
| initialpose를 발행해도 pose가 안 바뀜 — **에러 없이 무시된 것처럼 보임** (2026-07-08 젠지, 3회 연속 헛시딩) | ①반올림 쿼터니언(예: z=0.146,w=0.989)이 정규화 검사 실패 → amcl "**initialpose message is malformed. Rejecting**"으로 조용히 거부(로그에만) ②수락돼도 amcl_pose/tf는 다음 스캔 업데이트까지 latched 옛값 | ①쿼터니언은 `math.sin/cos(y/2)` 정밀값으로만 ②수락 판정은 amcl 로그 "**Setting pose: x y yaw**"가 유일한 ground truth ③반영 확인은 `/request_nomotion_update` 1회 후 pose 토픽 |
| 타이트 시딩 후 회전 수렴시켰더니 오히려 0.3~0.55m 이탈 (2026-07-08 젠지) | **옆에 주차된 다른 로봇 = 맵에 없는 큰 블롭**이 근거리 스캔 매칭을 오염 → 회전할수록 파티클이 가짜 위치로 끌려감 | 옆에 미등록 장애물/로봇이 있으면 **회전 수렴 포기** — 위치는 사용자 클릭, 방향은 물리 정렬로 확정 후 타이트 시딩만(pos 0.01/yaw 0.06). 주행 시작하면 블롭에서 멀어지며 자연 수렴 |

## 무-teleop 업그레이드 (충전독 초기포즈 박기) — 2026-07-03 arena_shared(재캡처)로 갱신

충전독은 **항상 같은 물리적 자리**지만, 맵을 다시 캡처하면(SLAM 원점이 매번 다름) **좌표는 매번 바뀐다**. 현재값(2026-07-03 arena_shared 기준): **x=0.038, y=1.405, yaw=0.293(rad, ≈16.8°)** — 아래 "맵 교체 시" 패턴으로 재확보함. 옛 값(x=0.05,y=0.028,yaw=0.0)은 2026-07-01 캡처본 전용이라 이번 재캡처 이후 무효. `_robot_amcl_ns.sh tb3_1 <map.yaml> 0.038 1.405 0.293 2`로 재현 가능(마지막 인자가 domain=2).

## 물리 재배치(hand-move) 표준 루프 — 2026-07-09 도출, 같은 세션 3회 반복으로 검증

사용자가 로봇을 **손으로 충전독에 다시 놓고** 주행을 재시작하는 반복 패턴. 스택 재기동 없이 3단계로 끝난다(bringup/amcl/nav2 전부 살아있는 상태 전제).

1. **들어올리기 전 정지 보장** — 손으로 드는 순간 goal이 살아있으면 바퀴가 허공에서 돌고(함정#5: 클라이언트 kill로는 nav2가 안 멈춤), 내려놓는 순간 옛 goal로 달려간다:
   ```bash
   # cmd_vel이 조용하면 이미 대기 — 이 단계 통째 스킵 가능
   ros2 lifecycle set /tb3_1/waypoint_follower deactivate && ros2 lifecycle set /tb3_1/bt_navigator deactivate
   ros2 lifecycle set /tb3_1/bt_navigator activate && ros2 lifecycle set /tb3_1/waypoint_follower activate   # goal만 죽고 스택은 유지
   ```
2. **사용자가 평소 주차 방향 그대로 독에 배치** (yaw까지 시딩값과 일치해야 함) → 배치 완료 신호 대기. **재시딩 전에 순찰 시작 금지** — 손으로 옮긴 직후의 AMCL은 완전히 stale(함정#4).
3. **재시딩+검증 한 줄** — `ssh t1 'bash ~/_dock_reseed.sh'` (원본 `scripts/_dock_reseed.sh`, 기본값이 티원 독). 정밀 쿼터니언 발행→nomotion→**"Setting pose <방금 좌표>" 수락로그**+amcl_pose 에코까지 출력. 수락로그의 좌표가 방금 값이 아니면 latched 옛값 착시이므로 재발행.

로봇이 **자기 힘으로 주행해 간 자리**라면 이 루프 자체가 불필요 — AMCL이 유효하니 그냥 다음 goal을 보내면 된다(재시딩은 손으로 옮겼을 때만).

## 맵 교체 시 초기포즈 재확보 절차 (재사용 패턴, 2026-07-03 도출)

**전제**: SLAM을 다시 떠서 맵을 교체하면 `origin`(yaml)이 이전 캡처와 다르다 → **옛 dock 좌표를 새 맵에 그대로 쓰면 안 됨**(원점이 달라 위치가 완전히 틀어짐, 공분산은 작게 나와도 그럴싸하게 틀린 값일 수 있음 — 직접 겪음). 아래 순서로 매번 재확보한다.

1. **글로벌 로컬라이제이션(위치+방향 동시 탐색)을 먼저 시도하지 않는다** — 좁고 대칭적인 방(이 프로젝트 아레나 1.9×1.9m)에서는 회전만으론 위치 자체가 벽 대칭 때문에 헷갈려서 엉뚱한 자리로 수렴하기 쉽다(2026-07-03 실측: `/reinitialize_global_localization`+26초 회전 2회 반복해도 계속 다른 엉뚱한 위치로 수렴, 공분산은 매번 작아 보여서 착시 유발).
2. **사용자에게 실제 물리 위치를 Unity 클릭으로 찍어달라 요청** — "웨이포인트 추가"로 로봇이 서있는 그 자리를 새 맵 위에 정확히 클릭해달라고 부탁(사용자가 방을 직접 보고 있으니 가장 신뢰도 높은 ground truth). `~/Library/Application Support/DefaultCompany/turtlebot/patrols/<mapId>.json`의 새 포인트 `x,y`를 읽는다. ⚠️ 이 좌표가 "로봇이 서있는 자리"인지 "로봇이 바라보는 방향의 앞쪽 지점"인지 반드시 재확인(둘 다 나올 수 있는 응답이라 헷갈리기 쉬움).
3. **위치는 타이트, 방향은 느슨하게 시딩** — `/<ns>/initialpose`에 covariance를 `x/y=0.01`(±10cm), `yaw=8.0`(사실상 전방향 미지)로 발행. 위치를 사용자 ground truth로 이미 고정했으니 파티클필터가 위치까지 같이 탐색할 필요가 없어 훨씬 안정적으로 수렴한다.
4. **짧게 제자리 회전**(`drive_rotate.py <cmd_vel_topic> 0.4 15` 정도, 26초씩 두 번 돌 필요 없음 — 위치가 이미 고정이라 짧아도 충분) → `amcl_pose` 공분산 재확인. yaw 분산이 급격히 줄면(9.x → 0.1 이하) 진짜 수렴, 안 줄면 2번부터 재시도.
5. **사용자에게 Unity 마커 육안 대조 요청**(성역 — 숫자만 믿지 말 것). 방향까지 맞다는 확인을 받아야 끝.
6. **(선택) 원래 정지 방향으로 물리 복원** — 회전 명령을 여러 번 썼다면(테스트 반복 등) 총 회전각(`wz × 총시간`, mod 360°)을 계산해 반대 방향으로 등가 회전을 한 번 더 명령하면 로봇이 원래 쉬고 있던 물리 방향으로 되돌아온다(AMCL 좌표값 자체가 아니라 "로봇이 실제로 어느 쪽을 보고 쉬고 있었는가"를 사용자가 신경 쓰는 경우에만 필요).
7. **`patrol_multi_waypoint.py`의 `DOCK_X/DOCK_Y/DOCK_YAW`를 최종 수렴값으로 갱신** — 다음 세션 무-teleop 시딩과 순회 복귀주차 목표 둘 다 이 상수를 쓴다.

**⚠️ 초기포즈 yaw 확정 시 함정 — Unity 2D 맵뷰의 화면회전(PlayerPrefs, 0°가 아닐 수 있음)과 절대 섞지 말 것.**
`MapPanelView`의 회전 버튼(`Viewport.AddRotation`)이 지도 전체(배경+마커)를 화면상 회전시켜서(`PlayerPrefs["urhynix.map.displayRotationDeg"]`에 영속), 회전이 0°가 아닌 상태에서 "화면에서 보이는 방향"으로 yaw를 역산하면 **실제 AMCL 물리 yaw가 화면회전만큼 틀어진 값**으로 심어진다(화면은 우연히 맞아 보이지만 Nav2/순회가 실제로는 엉뚱한 방향으로 출발함). **반드시 맵뷰 회전을 0°로 리셋한 뒤** "실물 로봇이 향한 방향"을 확인해 yaw를 심을 것. 2.5D뷰(`Map25DRobotMarkerLayer.cs`)는 이 화면회전을 아예 안 타고 순수 ROS-frame yaw(0=+X 동쪽, 90°=+Y 북쪽)로 그리므로, 2D(회전=0°)와 2.5D 두 뷰가 같은 방향을 보이면 물리 yaw가 진짜 맞다는 교차검증이 된다.

## 맵-현실 정합 검증 + 스캔매칭 정밀 재시딩 (2026-07-08 신설, 젠지 98.5% PASS)

"맵의 벽/장애물이 현실과 진짜 일치하나?" 또는 "마커가 어긋난 게 맵 탓인가 위치추정 탓인가"를 분리 판정:

1. **캡처**: 로봇에서 rclpy로 tf `map→<scan frame>` + `/scan` 1장을 JSON 덤프(sensor QoS 필수). 필드: x,y,yaw,amin,ainc,rmin,rmax,ranges.
2. **렌더+판정**: `python3 scripts/scan_vs_map_check.py <scan.json> <out.png> --fit` — 스캔점을 맵에 오버레이(빨강=일치/주황=불일치, 10cm 게이트) + (dx,dy,dyaw) 그리드 탐색.
3. **해석**: baseline 낮은데 fit이 높으면(예: 45.6%→98.7%) **맵은 맞고 위치추정이 어긋난 것** → fit이 출력한 corrected pose로 `/initialpose` 타이트 재시딩(스캔매칭 ground truth라 사용자 클릭보다 정밀). fit도 낮으면 맵≠현실 → 재SLAM 검토.
4. **주의**: 옆에 주차된 다른 로봇 등 맵에 없는 실물은 정당한 주황(불일치)으로 나옴 — 일치율 판정에서 그 방향 섹터는 감안.

## 재사용 스크립트
- `scripts/_robot_bringup_ns.sh` — ns bringup(tb3_1/tb3_2), domain 인자 파라미터화(3번째 인자, 기본 210 — 티원은 반드시 2 명시) [[urhynix-multirobot-domain-collision]]
- `scripts/_robot_amcl_ns.sh` — ns map_server+amcl, 수동 lifecycle, /map 격리, **domain 인자 추가(6번째, 기본 210 — 티원은 반드시 2 명시)** ★본 스킬 핵심, 2026-07-01부로 이게 정본(`_t1_amcl_ns.sh`는 레거시)
- `scripts/_pose_ep_up.sh` — pose republisher+endpoint, domain 인자 추가(3번째, 기본 210 — 티원은 반드시 2 명시)
- `scripts/robot_pose_publisher.py` / `scripts/scan_frame_fix.py` — **로봇 홈 디렉토리 사본이 0바이트로 비어있을 수 있음**(2026-07-01 실측: 원인 불명, 이전 세션에서 truncate됨) — 실행 전 `ssh t1 'wc -l ~/robot_pose_publisher.py ~/scan_frame_fix.py'`로 0줄이면 로컬 `scripts/`에서 재scp
- `scripts/drive_rotate.py` — 제자리 회전(글로벌 로컬라이제이션 경로에서만 필요, 좌표를 아는 충전독은 불필요)
- `scripts/teleop_stamped.py` — 수동 주행(병진 수렴·대화형, 사용자 직접)

## 검증 (2026-07-01 — arena_shared PASS)
bringup(domain2)→arena_shared map_server+amcl active→`/tb3_1/initialpose` 직접 시드(0.05,0.028,yaw=0)→즉시 수렴→robot_pose_publisher(재scp 필요했음)+endpoint(192.168.20.101:10000, `default_robots.json` hostAddress 동기화)→**Unity 2D 마커 충전독 위치·방향 정확히 표시(육안 확정 PASS)**. nav2 순회 풀스택(bt_navigator/waypoint_follower/controller/turtlebot3_navigation2)도 이 세션에서 apt 설치 완료. **순회 실주행은 2026-07-01에 PASS**(3.5cm 오차) — 절차는 [[urhynix-t1-nav2-patrol-drive]] 참조.

## 검증 (2026-07-03 — 맵 교체 후 재확보 PASS)
arena_shared를 재캡처본(`arena_shared2`)으로 전량 교체([[saved-map-to-unity-slot]] 절차 + 로봇측 map_server 경로 재배포) 후, 옛 dock 좌표(0.05,0.028,0)로 시딩했더니 Unity 마커가 실제 위치와 다름(사용자 육안 확인) → 글로벌 로컬라이제이션 2회 반복도 매번 다른 위치로 수렴(좁은 대칭 방 함정) → 위 "맵 교체 시 초기포즈 재확보 절차"로 전환: 사용자가 Unity에 실제 위치 클릭(-0.104,1.556) → 위치고정(var 0.01)+방향느슨(var 8.0) 시딩 → 16초 회전 → 공분산 yaw 9.85→0.088로 급수렴 → 사용자 육안 방향 일치 확인 **PASS**. 최종 확정 dock: x=0.038, y=1.405, yaw=0.293. `patrol_multi_waypoint.py` DOCK_X/Y/YAW 갱신 완료, WAYPOINTS(7개)는 옛 맵 기준이라 재계산 전까지 미사용 상태로 이월.

## 관련
[[urhynix-t1-nav2-lifecycle-abi]](amcl만·lifecycle 우회) · [[urhynix-t1-nav2-patrol-drive]](후속 단계 — nav2 순회 실주행) · [[unity-passive-pose-twin]](남이 운영·구독만 변형) · [[unity-livemap-overrides-static-slot]](핵심 함정) · [[saved-map-to-unity-slot]](맵 슬롯 등록) · [[urhynix-arena-slot-no-hardcode]] · [[pkill-f-self-kill-ssh]]
