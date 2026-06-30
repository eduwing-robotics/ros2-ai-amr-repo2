---
name: urhynix-t1-amcl-saved-map
description: 티원(tb3_1)을 저장맵(arena_v*)으로 self-host AMCL 위치추정해 Unity ControlRoom에 정확한 마커로 띄우는 검증된 엔드투엔드. 젠지가 같은 도메인210에서 라이브 cartographer SLAM 중이어도 네임스페이스 격리로 0 충돌. "티원 amcl", "티원 위치추정", "저장맵 amcl 띄워", "티원 유니티 마커 정확히", "충전독 초기포즈", "로봇 맵상 위치 정확히 구독" 요청에 발동. map_server+amcl 수동 lifecycle, 라이브 /map override pin 함정, 글로벌+회전 수렴, 충전독 초기포즈 박아 무-teleop 업그레이드까지. (2026-06-26 부분 PASS)
---

# URHYNIX 티원 AMCL — 저장맵 위치추정 → Unity 마커

티원(tb3_1)을 **저장된 2D 맵(arena_v5 등)** 위에 라이다 AMCL로 위치추정해서, Unity ControlRoom 맵에 **실제 위치에 정확히** 마커로 띄운다. 젠지가 옆에서 라이브 SLAM(cartographer) 중이어도 안 건드린다(ns 격리).

## 핵심 원리 — 맵≠위치

저장맵은 고정 파일. 로봇은 전원 껐다 켜거나 들었다 놓으면 **odom이 (0,0)으로 리셋** → 자기가 맵 어디인지 모름. `map→odom` tf를 만들어주는 게 **AMCL**(라이다 스캔 ↔ 저장맵 매칭). odom만이면 "켠 자리 기준 상대좌표"라 맵 밖/엉뚱.

전제: 저장맵이 **현재 물리공간과 일치**해야 AMCL이 맞음(벽 바뀌면 어긋남 = map5 0.9m 블로커의 근본원인). 정확하려면 정확한 재SLAM.

## 상수 (2026-06-26 실측)
- 도메인 `ROS_DOMAIN_ID=210`, `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`, `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`
- 티원 ns=`tb3_1`. scan=`/tb3_1/scan`(frame `tb3_1/base_scan` — bringup_ns가 이미 교정, scan_frame_fix **불필요**), odom=`/tb3_1/odom`(20Hz), cmd_vel=`/tb3_1/cmd_vel`(**TwistStamped**)
- 티원 접속 `t1@192.168.10.250`(pw 123, ssh alias `t1/tiwon/rb`) — **DHCP drift**, 도메인 토픽으로 찾을 것
- nav2_amcl·nav2_map_server 설치됨(1.3.12). **nav2_lifecycle_manager는 ABI 깨짐**([[urhynix-t1-nav2-lifecycle-abi]])

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

## 무-teleop 업그레이드 (충전독 초기포즈 박기)

충전독은 **항상 같은 자리** → 한 번 좌표를 확정해 `_t1_amcl_ns.sh`에 `-p set_initial_pose:=true -p initial_pose.x:=<X> -p initial_pose.y:=<Y> -p initial_pose.yaw:=<YAW>`로 박으면, 이후 **부팅→bringup→amcl 한 줄 = 충전독에 즉시 정확**. 글로벌·회전·teleop 영영 불필요. (좌표 확정은 teleop으로 병진 한 번 줘서 공분산 ±0.05m로 조인 뒤 amcl_pose 값을 사용.)

## 재사용 스크립트
- `scripts/_robot_bringup_ns.sh` — ns bringup(tb3_1/tb3_2) [[urhynix-multirobot-domain-collision]]
- `scripts/_t1_amcl_ns.sh` — 티원 ns map_server+amcl, 수동 lifecycle, /map 격리 ★본 스킬 핵심
- `scripts/robot_pose_publisher.py` — tf map→base_footprint → /tb3_1/pose
- `scripts/drive_rotate.py` — 제자리 회전(amcl 수렴, TwistStamped 매틱 stamp)
- `scripts/teleop_stamped.py` — 수동 주행(병진 수렴·대화형, 사용자 직접)

## 검증 (2026-06-26 — 부분 PASS)
bringup→arena_v5 map_server+amcl active→글로벌+회전 수렴(≈x0.9,y−0.94,yaw−141°, 공분산 0.38→0.064=±0.25m)→/tb3_1/pose 발행→endpoint(.250)→**Unity 마커 충전독에 표시(위치 대략 맞음)**. 라이브맵 override 버그 발견·pin으로 해결. **남은 일**: ① teleop 병진으로 ±0.05m 조임 ② 그 좌표를 _t1_amcl_ns.sh에 초기포즈로 박아 무-teleop화 ③ 마커 트래킹 정밀 검증.

## 관련
[[urhynix-t1-nav2-lifecycle-abi]](amcl만·lifecycle 우회) · [[unity-passive-pose-twin]](남이 운영·구독만 변형) · [[unity-livemap-overrides-static-slot]](핵심 함정) · [[saved-map-to-unity-slot]](맵 슬롯 등록) · [[urhynix-arena-slot-no-hardcode]] · [[pkill-f-self-kill-ssh]]
