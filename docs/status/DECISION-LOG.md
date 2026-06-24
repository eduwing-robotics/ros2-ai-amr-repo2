# Decision Log

> **📌 최신 5건은 DECISION-CURRENT.md 참조. 이 파일은 전체 역사 기록입니다.**

## 2026-06-24

### 🗺️ 티원 신규 SLAM 맵 `arena_v3` 저장·검증 PASS + Unity 슬롯 등록

- **결정/결과**: 2026-06-23 잔여 블로커(좌표↔맵 불일치·localize 방향)를 해소하기 위해 티원으로 텔레옵 + SLAM(`slam_toolbox`) 재매핑 → `arena_v3` 맵 저장 완료(10:49). 맵 품질 정량검증 PASS, Unity ControlRoom 슬롯으로 등록까지 완료.
- **연결 상태**: 젠지 `kim@192.168.10.84`(kim-desktop), 티원 `t1@192.168.10.250`(rb) — 둘 다 무선 정상. alias/mDNS 죽어서 SSOT IP로 직접 접속(DHCP drift 정상). 직결 en5(192.168.10.50) 미사용.
- **맵 검증 매트릭스** (`arena_v3.pgm` 41×42px, res 0.05, origin(-0.424446,-1.820601)):
  - 점유(벽) 25.4% / 자유(주행가능) 74.6% / 미지 0%
  - ASCII+PNG 시각확인: 닫힌 방 외곽선 + 내부 자유공간 + 중앙 장애물(충전소 추정) 또렷, **드리프트(벽 겹침/휨) 없음** → ✅ 정상 맵
  - ⚠️ 실제 크기 약 2.05m × 2.1m로 작음 — 경기장 전체인지 일부인지 미확정(주인님 육안 확인 필요).
- **해결 절차** (재현 가능):
  1. 티원 직접 IP ssh(`t1@192.168.10.250`) → `~/arena_v3.pgm/.yaml` 확인(map_saver 산출).
  2. pgm 픽셀 통계 + ASCII + PNG 12배 확대로 품질 판정.
  3. `scp`로 Mac `docs/evidence/maps/arena_v3/` 복사(pgm/yaml/png).
  4. `python3 scripts/pgm_to_map_slot.py docs/evidence/maps/arena_v3/arena_v3.pgm <yaml> arena_v3 "티원 아레나 v3"` → `StreamingAssets/Maps/arena_v3.png+json` 생성.
- **핵심 학습 2건**: ① `MapCatalog.cs`는 `Directory.GetFiles(Maps,"*.json")` **디렉토리 스캔** 방식이라 새 슬롯 자동 인식 — 코드 등록 불필요. 기본맵만 `StaticMapLoader.defaultSlotId="arena"`로 고정(arena_v3는 런타임 선택 또는 PlayerPrefs 기억). ② 저장 맵으로 **이동(goal_pose)** 검증하려면 `slam_toolbox`(라이브 매핑)가 아니라 **Nav2(AMCL+정적맵)** 스택 필요 — 매핑과 주행 스택은 별개.
- **부수 산출물**: `docs/evidence/maps/arena_v3/{arena_v3.pgm,.yaml,.png}`, `unity/ControlRoom/Assets/StreamingAssets/Maps/{arena_v3.png,arena_v3.json}`.
- **다음 진입**: arena_v3 맵에서 ① 로봇 위치 마커(/tf) 표시 ② 좌표설정 goal_pose로 로봇 실이동 검증. 코드는 이미 존재(`RobotPoseSubscriber`/`MapMarkerLayer`/`DispatchPublisher`) → **신규 구현 아닌 검증**. 선행조건=티원 `slam_toolbox` 종료 후 Nav2(AMCL+arena_v3 정적맵) 전환(`urhynix-nav2-waypoint-patrol`).

## 2026-06-23

### 젠지 Nav2 순찰 실측 — 소프트웨어 PASS, 잔여 2건 (2026-06-23)

- **결정**: Nav2 웨이포인트 순찰 소프트웨어 스택(Nav2 FollowWaypoints 액션 + patrol_waypoints_bridge.py + run_waypoints.py)을 젠지 실제 환경에서 검증 완료. 결과: 로봇 부팅, 맵 로드, AMCL localize, FollowWaypoints 액션 발행·수행 전 과정 정상 작동. Unity ControlRoom에 로봇 위치 마커 실시간 표시(맵 270° 회전 정렬) 확인. 모터 동작(제자리 회전) 정상.
- **잔여 2건(블로커)**: ① planner_server GridBased 경로실패 — save map.pgm(57×58, origin -0.734,-2.161)의 자유공간과 웨이포인트 좌표 불일치(점유/미탐색 셀 걸침). 캡처 당시 라이브맵과 저장맵이 다른 상태. ② heading 오류 — --dynamic-start로 기존 AMCL 추정값을 쓸 때 yaw가 180° 틀어져 로봇이 반대 방향 이동 시도. (주의: Unity 270° 회전은 화면 표시 전용·주행 무관)
- **다음 권장 액션**: 현재 공간 새 SLAM 매핑(cartographer) → 그 맵에서 웨이포인트 재캡처(urhynix-teleop-waypoint-capture) → urhynix-nav2-waypoint-patrol로 순찰 재실행. 맵-실제 방향 일치로 planner 경로실패 + heading 오류 동시 해결.
- **영향**: Nav2 웨이포인트 기반 순찰 기능은 로봇·통신·제어·UI 모두 정상. 다음 mapping 및 좌표 정합 후 실제 주행 가능 상태. 스킬 urhynix-nav2-waypoint-patrol에 함정 6건 영구 기록 완료.

## 2026-06-23

### Unity 맵 웨이포인트 에디터(MWE) 구현 + 핵심 설계 결정

- **결정**: 레퍼런스(PyQt UR암 그리드 에디터) 아이디어를 ROS2/Nav2 맥락으로 재설계. 기존 `unity-live-map-twin` Map 레이어 확장(신규 아키텍처 아님).
- **결정**: ROS-TCP-Connector는 ROS2 액션 미지원 → 순찰 실행은 Unity가 `geometry_msgs/PoseArray`를 `/<robotId>/patrol_waypoints`로 발행하고, 로봇측 브리지(`scripts/patrol_waypoints_bridge.py`)가 Nav2 FollowWaypoints 액션으로 수행하는 방식 채택(액션 직접호출 fallback).
- **결정**: 맵 슬롯화 — `StreamingAssets/Maps/<id>.png + <id>.json`(MapConfigData), 런타임 드롭다운으로 저장맵/라이브(SLAM) 전환. 슬롯 추가는 `scripts/pgm_to_map_slot.py` 한 줄. 라이브 `/map`이 오면 우선, 슬롯 직접선택 시 핀 고정.
- **결정**: 로봇 역할 상호교환 — `RobotInfo.role`(표시용)에 더해 `capabilities[]` 추가. 젠지/티원 둘 다 "patrol" 보유 → 활성 로봇(탭 전환=`SelectedRobotId`) 기준으로 순찰/출동 대상이 따라감.
- **결정**: 순찰 경로 영속은 로컬 우선(`persistentDataPath/patrols/<mapId>.json`, 맵별 자동 저장/복원)으로 Wi-Fi 끊겨도 무손실. Supabase 동기화는 신규 `patrol_routes` 테이블(`scripts/sql/patrol_routes.sql`) 적용 후 활성(단계화).
- **영향**: 구현 5 Phase 전부 컴파일 PASS(unityctl, scriptCompilationFailed=false). 잔여: 로봇+Nav2 라이브 세션에서 실주행 검증, Play 시각확인(UI Toolkit 스크린샷 검정 함정으로 자동검증 보류).

---

## 2026-06-23

### 🔄 프로젝트 git 원격 이관 — 기존 repo 폐기 · 새 repo로 단일 초기 커밋 force-push 완료

- **결정**: URHYNIX 프로젝트의 git 원격을 새 GitHub repo로 이관하고 앞으로 모든 push는 이 repo로 진행한다.
- **새 원격(origin)**: `https://github.com/eduwing-robotics/ros2-ai-amr-repo2`
- **기존 원격**: `https://github.com/URHYNIX/URHYNIX.git` (더 이상 사용 안 함, 로컬 백업만 보존)
- **방식**: 기존 git 히스토리를 버리고 새로 init → 단일 초기 커밋으로 force-push 완료. 기존 히스토리는 로컬 `.git.bak.20260623/`에 백업됨(새 repo 검증 후 삭제 예정).
- **경량화 최적화** (.gitignore 보강 완료):
  - `unity-src/` (구버전 Unity, 60M prefab 포함) 제외
  - 모델 가중치: `*.pt`, `*.onnx`, `*.engine`, `*.pth`, `*.weights` 제외
  - 영상 파일: `*.mp4`, `*.mov`, `*.avi`, `*.mkv`, `*.h264`, `*.h265` 제외
  - 루트 참고 PDF: `/*.pdf` 제외
  - evidence 이미지: `docs/evidence/**/*.{png,jpg,jpeg,gif,webp,bmp}` (42개 36M, git에서만 제거·로컬 보존)
- **결과**: 클론 무게 약 **25M**(압축 .git 기준).
- **검증**: Unity ControlRoom 프로젝트는 클론 후 **Unity 6000.3.16f1**로 정상 열림. ProjectSettings/Packages/manifest.json/Assets/.meta 전부 포함. 런타임 DB는 `SupabaseConfig/supabase.json`을 `.example`에서 복사·키 입력 필요.
- **미보류 액션**:
  - 옛 히스토리 백업(`.git.bak.20260623/`) 삭제(새 repo 검증 후)
  - evidence 맵 PNG 필요 시 복원 검토

---

## 2026-06-18

### ✅ demo_logs_rls.sql 적용 완료 + Unity 직접쓰기 경로 end-to-end 검증 PASS (pose_logs TF 추적 과제)

- **결정**: Supabase 프로젝트 `ueupkrxwybuuqxflstvg`는 paused가 아니라 복구되어 LIVE. `demo_logs_rls.sql` 적용 완료(logs 테이블 생성, dispatches event_id nullable + nav_mode/reason 컬럼, anon RLS 정책 10개: 5테이블 × insert/select). Unity Play에서 session_meta + logs 테이블 직접쓰기 PASS, logs 7건 DB 실기록 확인(`DbVerifyConsole.Verify()` + 직조회).
- **미해결 1건**: pose_logs 테이블에 Unity pose가 안 쌓임. 원인은 RobotPoseSubscriber가 /tf map 프레임 못 받은 것(TF 체인/ROS 연결/센서 fake 여부 다음 추적). 첫 pose 자동 기록 로직은 정상이나 데이터 소스 미수신.
- **주의**: anon DELETE 정책이 없어서 anon DELETE는 204 반환해도 실제로 삭제 안 됨(RLS 0행 매칭). 정리는 service_role 권한으로.
- **근거**: `docs/evidence/2026-06-18-unity-supabase-direct-write.md` §4 검증 상태 갱신 완료.

### 🗄️ Unity → Supabase "직접 택배" DB 쓰기 구현 (코드+컴파일 PASS · DB 복구 대기)

- **결정**: 시연 중 ① UI 로그 ② 맵 클릭 좌표 지정→출동 ③ 로봇 이동좌표 추적을 DB에 영속. 연동방식은 **UnityWebRequest+PostgREST anon "직접 택배"** (주인님 선택). supabase-csharp SDK 미채택 — "유니티가 주로 쓰기" + "끊김 없는 시연" + 메모리 룰(가벼운 대안 먼저)에 따른 결정. 조사는 하이쿠 서브에이전트(SDK+Realtime 권고)했으나 가벼운 쪽 채택.
- **개념 정리**: 맵 클릭 명령은 **ROS 길**(`DispatchPublisher`, 기존)이고 DB는 그 클릭을 **기록**만 함. 클릭은 유니티가 일으킨 일이라 Realtime 자동알림 불필요 → 직접 택배가 정답. (멀티화면 실시간 공유 필요 시에만 SDK 재검토)
- **구현 절차**:
  1. SQL `scripts/sql/demo_logs_rls.sql` — `logs` 테이블 신규 + `dispatches.event_id` nullable 완화(+`reason`/`nav_mode`) + `session_meta`/`dispatches`/`events`/`logs` anon RLS. 패턴은 `pose_logs.sql` 복제.
  2. Unity 코드 — `SupabaseSettings`(설정 로드) / `SupabaseClient`(UnityWebRequest REST) / `SupabaseDbService`(이벤트→insert, Hz throttle, 내구성 큐+디스크 버퍼+자동재시도, UUID 클라생성으로 FK 보존) / `PoseLogRepository`(스텁→read 구현) / `DbVerifyConsole`(화면=DB 검증) / `ControlRoomApp` 결선.
  3. 설정 `Resources/SupabaseConfig/supabase.json`(.gitignore) + example 커밋. anon(publishable) 키만, service_role 미반입.
- **결과 매트릭스**:

  | 항목 | 상태 |
  |---|---|
  | Unity 컴파일 | ✅ PASS (`scriptCompilationFailed:false`, 6파일 import 후 CompileScripts 확인) |
  | DB SQL 적용 | ✅ PASS — 2026-06-18 적용 완료 (logs 테이블 + dispatches 컬럼 + anon RLS 10개) |
  | REST 스모크 / Play end-to-end | ✅ PASS — session_meta/logs 직접쓰기 + logs 7건 DB 기록 |

- **핵심 학습 2건**:
  1. **Supabase 무료 티어 자동 paused** — `projects list`엔 보여도 REST 서브도메인이 NXDOMAIN이면 일시정지 상태. Dashboard "Restore project" 필요(CLI 불가).
  2. **unityctl IPC refresh stale 함정** — 에디터 포커스 없으면 `asset refresh`가 "scheduled"만 되고 import 안 됨(.meta 미생성, check는 캐시값). **`osascript -e 'tell application "Unity" to activate'`로 창 활성화 → 자동 import** 우회 성공. (unity-unityctl-ops 보강 후보)
- **부수 산출물**: `scripts/sql/demo_logs_rls.sql`, `unity/.../Database/*.cs`(4종), `App/DbVerifyConsole.cs`, `docs/evidence/2026-06-18-unity-supabase-direct-write.md`, SCHEMA.md(`logs`·dispatches 갱신).
- **다음 진입**: pose_logs /tf map 프레임 추적 (RobotPoseSubscriber 연결/TF 체인 확인).

### ✅ LIVE 검증 완료 — 실토픽 → Unity UI 라이브 표시 (사용자 화면 확인)

- **결정**: Phase A(브리지 배포)·Phase B(토픽 계약)·Phase C(UI 리팩토링) 위에서, 젠지 실센서(PIR/Sound/Temp/Laser)가 Arduino → ROS-TCP-Endpoint(192.168.10.84:10000) → Unity ControlRoom 우측 패널 4카드에 라이브로 표시되는 것을 사용자가 화면에서 육안 확인함.
- **end-to-end 경로**: 젠지 센서(하드웨어) → `arduino_bridge_quad.py`(/sensors/pir·sound·temp·laser) → ROS2 토픽 4종 (root namespace, std_msgs) → ROS-TCP-Endpoint → Unity ROSConnection → 4 Subscriber → 카드.
- **검증 결과**:
  - 온도 (temp): "raw 139~142" 라이브 갱신(1Hz)
  - 사운드 (sound): "swing=N" 수신 확인
  - PIR (인체감지): 화면에서 감지 토글 확인
  - 레이저 (laser): 수신부 미결선이라 토픽 발행되나 UI 비활성
- **해결한 문제 2건**:
  1. **Unity 옛 IP 연결 실패**: `default_robots.json[0].hostAddress`가 DHCP drift로 변경된 IP(192.168.10.87)를 여전히 참조 → 인식 불가. 해결: `default_robots.json` tb3_2 hostAddress를 `kim@192.168.10.84`로 수정 + ControlRoomMain.unity m_RosIPAddress도 동기화. **IP SSOT는 `default_robots.json[0].hostAddress`**이므로 DHCP drift 시 여기를 먼저 갱신.
  2. **PIR 배선 불일치**: PIR이 물리적으로 D4(레이저 핀)에 꽂혀 있음 → 펌웨어가 읽는 D2에 신호 없음. 해결: PIR 신호선을 D4→D2로 물리 이동. 검증: `ros2 topic echo /sensors/pir` → true 확인, 브리지 로그 "PIR motion" 확인.
- **운영 함정 기록**:
  - Arduino DTR 리셋 시 PIR 8초 워밍업 — temp_wire=0은 정상, 워밍업 후 발행 시작
  - PIR/Sound/Laser는 전이형(latching X) → 자동 폴링으로 순간값 누락 가능, 육안 확인이 빠름
- **근거**: `docs/evidence/2026-06-18-quad-bridge-ros2.md` §LIVE 검증.

### ✅ Phase C — Unity UI 4센서 카드 리팩토링 (완료)

- **결정**: Phase A(브리지 배포)·Phase B(토픽 계약 정합) 위에서, Unity UI를 as-built 4센서로 리팩토링해 젠지 실토픽이 우측 패널 카드에 표시되게 함.
- **신규 3파일**: SoundSubscriber.cs (Int32, /sensors/sound, swing + 임계 60), TemperatureSubscriber.cs (Int32, /sensors/temp, raw + timeout 5초), LaserSubscriber.cs (Bool, /sensors/laser, 미결선 비활성).
- **삭제**: LuxSubscriber.cs (+.meta) — 조도/LDR 폐기.
- **변경 6파일**: TopicRegistry.cs(GetLdrRaw 완전삭제), SensorCardListView.cs(4카드 재작성: PIR/sound/temp/laser, 화재 케이스 제거), RightStatusPanel.uxml(5→4행), ControlRoomStyle.uss(.sensor-disabled), FakeSensorData.cs(gas/light 제거→sound/temp 추가), SensorVerifyConsole.cs(4종 정리).
- **Scene**: ControlRoomMain.unity YAML patch — LuxSubscriber_G 제거, Sound/Temp/Laser 3종 GameObject 추가, SceneRoots 4 transform.
- **함정**: 신규 .cs.meta GUID를 unityctl import가 재생성 → Scene m_Script guid 2회 갱신 필요.
- **검증 PASS**: 컴파일(31 assemblies) ✅, GetLdrRaw/LuxSubscriber/ldr/gas/fire 참조 0 ✅, Scene Subscriber×4/fileID무중복/SceneRoots 4 ✅, 라벨ID 일치(UXML/SensorCardListView/SensorVerifyConsole) ✅.
- **미완**: Play 모드 시각 + 젠지 실토픽 LIVE 확인, °C 2점 보정, PIR/사운드 물리 트리거, 레이저 수신부 납땜.
- **근거**: `docs/evidence/2026-06-18-quad-bridge-ros2.md` §Phase C.

### ✅ Phase B — Unity 토픽 계약 정합 (완료)

- **결정**: 젠지(tb3_2) arduino_bridge_quad.py 실제 발행 4토픽(/sensors/pir·sound·temp·laser, root namespace, std_msgs)에 맞춰 Unity 토픽 계약 + SSOT 문서를 as-built로 정합.
- **변경 5파일**: TopicRegistry.cs(GenjiSound/Temp/Laser 상수+getter), default_sensors.json(5→4종, noise→sound, /sensors/*), SensorInfo.cs(주석), CONTRACT.md(핀맵·포맷·이벤트타입 as-built), SCHEMA.md(event_type pir/sound).
- **네임스페이스**: root /sensors/* 통일(브리지 실제). per-robot /tb3_2/sensors/* 미채택(작동 기기 갈아엎기 회피).
- **검증**: default_sensors.json 4항목 JSON 파싱 ✅, TopicRegistry 신규상수 4개 ✅, SSOT topicName 4개 == 젠지 ros2 topic list /sensors/* 4개 완전 일치 ✅.
- **범위 밖(Phase C)**: Unity Subscriber 신규(Sound/Temp/Laser), UXML 5→4칸, SensorCardListView, LuxSubscriber/ldr 실제 삭제.
- **근거**: `docs/evidence/2026-06-18-quad-bridge-ros2.md` §Phase B.

### 🔌 4센서 통합 아두이노 회로 핀맵 확정(as-built PASS) — PIR+레이저+사운드+온도 한 보드

- **결정/결과**: Arduino UNO 1대에 PIR·레이저·사운드·온도(PP-A017) 4종을 통합 결선·업로드·시리얼 검증. **4종 동시 동작 PASS**. 핀맵을 2026-05-27 SSOT에서 변경 확정.
- **확정 핀맵(as-built)**: PIR=**D2**(IN) / 레이저=**D4**(OUT, PIR 연동 점등) / 사운드=**A1**(AO, swing 감지) / 온도 PP-A017=**A0**(AO) / LED=**D7**(옵션). **금지핀: D0/D1(USB 시리얼), D13(SCK)** — 비워둠.
- **핵심 학습 2건**:
  1. **사운드 모듈 DO 불량 → AO swing 우회.** DO가 가변저항 전 구간에서 상시 HIGH(비교기 회로 이상)로 박수 감지 불가 → DO 폐기, **AO(A1)를 짧은 윈도우 min/max(swing)로 읽어 소프트웨어 임계(60)** 로 감지. 무음 swing~2 vs 박수 swing 94~114로 또렷이 갈림. 가변저항 튜닝 불필요.
  2. **D0/D1 금지핀.** 최초 PIR=0·레이저=1 배선 시도 → D0(RX)/D1(TX)는 USB 시리얼 전용이라 업로드·로그 깨짐 → D2/D4로 이동.
- **결과 매트릭스**: PIR(D2) ✅ / 레이저(D4) ✅ / 사운드(A1 AO swing) ✅ / 온도(A0 raw 반응) ✅ (단 ℃ 환산식 미보정 — raw만 검증).
- **부수 산출물**: `sketches/quad_security/quad_security.ino`(통합) + `sketches/sound_a1_debug/`(DO+AO 동시 진단) + `docs/evidence/2026-06-18-quad-sensor-flash.md` + `arduino-flash` 스킬 v4.
- **다음 진입**: ① 온도 PP-A017 실제 °C 2점 캘리브레이션 ② 4센서 통합본 PIR 손흔들기 재캡처(코드 동일, PASS 추정) ③ RPi `arduino_bridge` → ROS2 토픽 연결(`urhynix-sensor-bringup`).

## 2026-06-17

### 🌡️ Arduino 온도센서 트랙 — PP-A017 서미스터로 교체 살림(DS18B20/DHT D8 실패 우회) + 로봇 양대 셧다운

- **증상/결과**: 신규 Arduino UNO에 소형 사운드 모듈(AS0025) + 온도센서 결선 검증. DS18B20·DHT11/22를 D8에 물렸으나 **둘 다 `found:0`/`-127`/NaN으로 통신 실패**(전 핀 스캔에도 1-Wire 디바이스 0건 → D8 핀 또는 센서/풀업 문제로 좁힘). **PP-A017 서미스터 모듈로 교체 → AO→A0 읽기 PASS**(손으로 잡으니 raw 153→116 또렷이 반응). 작업 종료 후 **젠지·티원 양대 로봇 정상 셧다운**.
- **핵심 함정(자산화)**: PP-A017은 이름이 "디지털 온도센서 모듈"이지만 실제는 **서미스터+비교기 아날로그 모듈** — 실제 온도값은 **AO(아날로그)**에서 읽고, DO(디지털)는 임계값 HIGH/LOW 트리거일 뿐. **D13은 내장 LED 때문에 디지털 입력으로 부적합**(DO 핀 배정 회피). 사운드 AS0025는 **DO→D3 배선 정상**(D3 깨끗한 상태값 확인), 박수 무반응은 모듈 위 포텐쇼미터 감도 미보정 → 추후 조정.
- **해결 절차(재현)**: 1. `arduino-cli board list`로 UNO 포트 확인(`/dev/cu.usbmodem11101`). 2. 진단 스케치 컴파일/업로드 후 `stty+cat` 30초 캡처. 3. DS18B20 안 잡힘 → **전 핀 스캔 스케치**로 D2~D13/A0~A5 훑음(0건). 4. DHT 라이브러리로 교체 시도(D8/D7) → NaN. 5. **PP-A017 서미스터로 교체, AO→A0**, analogRead 평균 16샘플 → raw 온도 반응 확인.
- **로봇 셧다운 절차**: mDNS(`.local`) 깨짐 → **ARP + 라즈베리 OUI 매칭**으로 IP 발견. 젠지=**192.168.10.87**(Wi-Fi, OUI `2c:cf:67`, hostname `kim-desktop`, Pi4/Jazzy), 티원=**192.168.10.250**(이더넷, OUI `d8:3a:dd`, hostname `rb`). `ssh … 'echo <pw> | sudo -S shutdown -h now'` → SSH timeout으로 종료 확인.
- **결과 매트릭스**: 온도(PP-A017/A0) ✅ · 사운드(AS0025/D3 배선) ✅(감도보정 대기) · DS18B20/DHT(D8) ❌(보류) · 젠지 셧다운 ✅ · 티원 셧다운 ✅.
- **부수 산출물**: `sketches/dual_sound_temp/`(.ino + `wiring.svg` + `wiring_simple.html` 배선 시각화), `sketches/ds18b20_pinscan/`, `sketches/dht_sound/`, `sketches/thermistor_a0/`.
- **다음 진입**: ① PP-A017 실제 °C 보정(실내온도 1점 + 2점 캘리브레이션) ② 사운드 포텐쇼미터 감도 조정 후 D3 토글 검증 ③ (선택) DS18B20 D8 실패 원인 — 새 센서/풀업/핀 손상 사진 확인.

### 🎨 시나리오 5종 인터랙티브 다이어그램 + 풀 에디터 자산화 (docs/presentation/scenarios/)

- **결정/결과**: 박물관 경비 로봇 시나리오 5종(2026-06-16 확정분)을 **D3+dagre 오프라인 인터랙티브 플로우차트**로 자산화. 발표(P0)·편집(P1/P2) 전부 구현·검증 PASS.
- **산출물 구조**: `docs/presentation/scenarios/` — vendor(d3.v7+dagre 로컬 고정, CDN 의존 0) + 모듈 5종 `engine/{store,render,nav,editor,app}.js` + `data/scenarios.js`. SSOT 원천: Confluence "박물관 경비 로봇 시나리오"(page 14843906 v11).
- **P0 발표/탐색**: 좌우 분기 이동(결정노드 `←` 없음 / `→` 있음, 엣지순서 `[0]`없음/`[1]`있음 + 화면 힌트), 자동재생(속도·반복 키오스크), 활성노드 **줌인 카메라 + 엣지 점 흐름**, 경로강조, 해시 딥링크(`#s3`, `#s3/play`), 위험등급 5색(SAFE→EVACUATE).
- **P1 편집**: 폼으로 노드/엣지/메타 추가·수정·삭제 → **localStorage 자동저장 + 내보내기/가져오기 + 기본값 복원**.
- **P2 드래그**: 노드 드래그 위치 이동(좌표 오버라이드 + 엣지 직선 재계산), Shift+드래그 엣지 연결.
- **결과 매트릭스**: P0 ✅ · P1 ✅ · P2 ✅ · 소넷 독립검증 16항목 ✅ · 콘솔 에러 0. 보고된 "노드추가 throw"는 깨끗한 상태 3중(API·삭제·UI버튼) 재현으로 **오탐 반증**.
- **핵심 학습 2건**: ① 멀티파일 HTML 도구는 `index.html`만 공유하면 외부 스크립트 8개 없어 깨짐 → **inline 단일파일 번들 빌더 필수**. ② `file://`는 원본 파일 직접쓰기 불가(보안) → **localStorage(즉시) + 내보내기 다운로드(레포 영구화) 2단** 패턴(annotate.js와 동일).
- **부수 산출물**: `docs/presentation/scenarios/` 전체 + `build_bundle.py`(→ `scenarios-bundle.html` 427KB 단일파일, 슬랙 업로드용·빈폴더 단독동작 검증) + `docs/presentation/index.html` 상단바 🗺 시나리오 링크.
- **다음 진입**: (선택) 시나리오 문구 다듬기·발표노트 패널·PNG 내보내기, 또는 실제 마우스 드래그 UX 손보기.

## 2026-06-16 — Gen.G 센서 스택 교체 + 자동 충전독 제외 확정 + 시나리오 5종 확정

### 변경 1 — Gen.G(젠지/tb3_2) 센서 스택 교체

- **제거**: LDR(조도 센서), 불꽃(flame) 센서
- **추가**: 온도 센서 모듈, 레이저 송신 모듈, 워터 펌프(릴레이 모듈 + Adafruit 3V 수중 펌프, 화재 대응 모의 분사용 액추에이터)
- **유지**: PIR(인체감지), 소형 사운드 모듈, Pi Camera v2 (IMX219), Arduino Nano/Uno USB 시리얼 센서 보드
- **Gen.G ROS2 연결**: RaspberryPi4 →(USB Serial)→ Arduino Nano/Uno → [PIR · 사운드 · 온도 · 레이저] + 릴레이 → 워터 펌프
- **T1(티원/tb3_1) 유지**: RealSense D435, LDS-03 LiDAR, RaspberryPi4, TurtleBot3 Burger (변경 없음)

### 변경 2 — 자동 충전독 완전 제외 확정

- 완전 자동 충전독(포고핀·무선충전 하드웨어 회로)은 검토 결과 난이도 높아 현 단계 제외 확정
- **대체**: 배터리 잔량 모니터링 + **ArUco 마커 기반 정밀 주차** 후 **수동 충전 연결 요청**(Unity 화면에 요청 표시)
- 정밀 주차 실패 시 "긴급 수동 충전 요청" 표시

### 변경 3 — 발표용 시나리오 5종 확정

**위험등급 5단계: SAFE / WATCH / CHECK / DANGER / EVACUATE**

1. **폐관 후 침입자 감지** — PIR+LiDAR → WATCH → Gen.G 출동 → PIR·카메라 재확인 → DANGER 시 112 신고·차단벽 요청
2. **중요 전시품 분실·이동** — T1 YOLO 기준이미지·Depth 불일치 → WATCH → 재촬영(최대 2회) → CHECK → Gen.G 다각도 확인 → DANGER
3. **화재 의심 즉시 대응** — T1 YOLO 화재 감지 → 즉시 DANGER → Gen.G 출동 → **온도·레이저 센서값 + Pi Camera 재확인** → EVACUATE 시 **워터 펌프 분사** + 119 신고·차단벽 요청
4. **개장 중 전시품 접촉** — T1 YOLO 손 감지 → WATCH → 음성 안내 → CHECK → Gen.G 출동·2차 경고 → DANGER 시 관리자 확인 요청
5. **배터리 부족·임무 인계** — T1 배터리 기준 이하 → Gen.G에 남은 waypoint 인계 → T1 충전소 이동 → **ArUco 정밀 주차 → 수동 충전 연결 요청**(자동 충전독 미구현)

**주의**:
- 신고·차단벽 폐쇄는 실제 자동제어가 아니라 Unity 화면에 "요청 상태"로 표시
- YOLO 인식 MVP 클래스 4종: 로봇·사람·중요품·불

### 근거 및 출처

- Confluence SCRUM 스페이스, 2026-06-16 갱신 정본
  - 기획안(UR HYNIX) v18 /pages/327681
  - 하드웨어 아키텍처 v4 /pages/7536649
  - 소프트웨어 아키텍처 v4 /pages/13729806
  - 디지털 트윈 동작 검증 시나리오 /pages/13860874

### 현재 코드/스킬 드리프트 주의

- **코드 상태**: `unity/` + `scripts/`의 현재 코드는 이전 LDR(조도) 기반으로 작성됨 (LuxSubscriber, arduino_bridge 등)
- **스킬 상태**: `.claude/skills/urhynix-sensor-bringup/` 등은 구 LDR 기준 문서화
- **정합 필요**: 후속 세션에서 센서 하드웨어 교체 후 코드/스킬 토픽명·핀 매핑 갱신 필요

### 변경 4 — 레이저 센서 결선 + PIR 연동 (조도 제거) — Arduino as-built

- **확정 사실 (2026-06-16 검증 PASS)**:
  - **대상**: Mac USB 연결 Arduino UNO (FQBN `arduino:avr:uno`, 포트 `/dev/cu.usbmodem11101`). 향후 Gen.G(tb3_2) 탑재 예정.
  - **변경**: 조도(LDR/A0) **물리 제거**. PIR(D2 OUT) + LED(D2, +220Ω→GND) 유지.
  - **신규**: 레이저 송신 모듈 추가, 데이터핀 **D8**, 5V=브레드보드 레일, GND=공통 그라운드.
  - **동작**: PIR 감지(HIGH) → LED(D2) + 레이저(D8) **동시 ON**, 해제 → 동시 OFF.
  - **새 스케치**: `sketches/pir_laser/pir_laser.ino` (기존 `sketches/pir_led/pir_led.ino`는 참조용 보존).
  - **컴파일**: 7% flash / 9% RAM. arduino-cli 업로드 무에러.
  - **시리얼 검증 PASS**: 9600 배너 `=== PIR + LASER Test ===` → `Ready.` 수신 확인. 로그 포맷: `[MOTION] detected -> LED+LASER ON` / `[CLEAR ] no motion -> LED+LASER OFF`.
- **함정 & 해결**:
  - 레이저를 처음 **D13에 연결**했더니 업로드 `not in sync: resp=0x00 / programmer is not responding` 반복 실패.
  - **원인**: D13은 **SCK 라인** (부트로더 동기화), 액추에이터 부하가 동기화 방해.
  - **해결**: 데이터핀 **D13→D8로 이동** (또는 업로드 중에만 D13 분리). 자동리셋 안 되면 USB 재꽂기/RESET 버튼.
- **산출물**: `.claude/skills/arduino-flash/SKILL.md` v2→v3 갱신 (레이저 D8 + D13/SCK 함정 추가), `docs/ref/CONTRACT.md` §4.1 핀 표 갱신.

---

## 2026-06-15 (후반) — codelab_robot_team_2_5G 무선 통일 + 양 로봇 카메라/센서 cross-host PASS + 망 불안정 경고

### 결정
- **무선 네트워크 최종 통일 SSID: `codelab_robot_team_2_5G`** (5200MHz). 이전 시도: `codelab_5G` → 로봇 범위 밖(신호 0), fallback. 최종 선택: 로봇 기존 연결 SSID로 Mac도 통일. IP: Mac `192.168.10.101`, 젠지 `192.168.10.87`, 티원 `192.168.10.250` (전부 DHCP drift, 다음 세션 mDNS 재확인 필수).
- **`codelab_robot_team_2_5G`는 multicast 정상** — talker/listener 양방향 검증 PASS. 이전 팀 와이파이와 달라(multicast 차단), STATIC_PEERS 우회법 불필요. robot-camera-bringup §F의 우회법은 multicast 차단 망 대비용으로 보존.

### 검증 (PASS)
- **cross-host DDS multicast**: 젠지 talker → 티원 listener "Hello World" 수신 확인 PASS.
- **양 카메라 + 센서 cross-host 결선**:
  - 티원 RealSense D435 `/tb3_1/camera/color/image_raw/compressed` (30Hz, 로컬)
  - 젠지 Pi Camera v2 `/tb3_2/camera/image_raw/compressed` (30Hz, cross-host multicast)
  - 젠지 센서 `/sensors/ldr` (Int32), `/sensors/pir` (Bool) — arduino_bridge.py cross-host 수신 확인
  - 단일 endpoint(티원 port 10000)이 양 로봇 토픽 모두 수집 → Unity forward 완료. RegisterSubscriber 전부 OK.

### 신규 함정 5건 (이번 세션)
1. **젠지 `~/.bashrc` ROS_STATIC_PEERS 잔재** — `export ROS_STATIC_PEERS=192.168.10.70` → cross-host 토픽 불안정. `sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc`로 제거.
2. **`/dev/tb3_arduino` symlink stale** — Arduino realloc `/dev/ttyACM0` → old `/dev/ttyACM1` 여전히. `ln -sf /dev/ttyACM0 /dev/tb3_arduino` 재링크.
3. **RealSense compressed는 lazy republish** — 구독자 없으면 발행 안 함. ros_tcp_endpoint 먼저, Unity 구독, realsense 재시작 순서 필요.
4. **직결(en5) + 무선(en0) 같은 대역 충돌** — asymmetric routing 재발. `ifconfig en5 down` (직결 제거) → 무선 단일화.
5. **Unity 에디터 background throttle** — `unityctl play` 후 포커스 떨어짐 → 로그 정지. "Run In Background" 켜기 또는 Editor 항상 포그라운드 유지.

### 미해결 / 다음 세션 높음 우선
- **`codelab_robot_team_2_5G` 간헐 끊김 심각**: 10회 ping 중 2~3회 100% loss, 회복 1초 내, 빈번 반복 → **시연 신뢰성 낮음**. 임시 우회: 공유기를 로봇 근처로 옮겨 `codelab_5G` 사용 가능한지 확인, 또는 직결(Mac ↔ 젠지 eth0) 복귀 + mDNS 충돌 회피.
- **세션 종료 상태**: 젠지 안전 종료(poweroff) 완료, ping 100% loss 확인. 티원은 망 끊김으로 ssh 셧다운 실패 → **물리 전원 OFF 필요**.
- **다음 진입 5단계**: ① DHCP IP 재확인 ② `/dev/ttyACM*` 재확인 + symlink 갱신 ③ ROS_DOMAIN_ID=210 확인 ④ bringup 실행 ⑤ ros_tcp_endpoint + arduino_bridge.py + Unity 구독 시작.
- **evidence**: `docs/evidence/2026-06-15-wireless-codelab-team-crosshost-camera-sensor.md`

## 2026-06-15 — 무선 통일 + ROS_DOMAIN_ID 210 통일 + Unity 듀얼 로봇 전환 검증

### 결정
- **ROS_DOMAIN_ID 230 → 210 전면 통일.** 젠지(kim-desktop)는 팀원이 이미 210으로 변경한 상태였고, 티원(rb)도 `~/.bashrc` 230→210으로 맞춤. namespace 분리(`/tb3_1`=티원, `/tb3_2`=젠지)는 유지 → "도메인 통일 + namespace 분리"가 정본. SSOT 6개 문서 갱신 완료(ARCHITECTURE/CONTRACT/ROS2-ROBOT/VISION-CAMERA/PROJECT-PLAN + unity Ros/CLAUDE.md).
- **개발 접속을 무선으로 통일** — 직결(Mac en5 ↔ 젠지 eth0)을 제거하고 팀 와이파이(`192.168.10.x`)로 양 로봇 접근.

### 네트워크 (무선 통일 트러블슈팅)
- 팀 와이파이는 **AP isolation 아님** (Mac↔티원 SSH 통과). 이전 세션의 격리망과 다른 망.
- 젠지 무선이 안 닿던 원인 = **asymmetric routing**: 젠지가 eth0(직결)+wlan0 동시 보유 + default route가 eth0로 잡혀, wlan0(.87)로 온 요청의 응답을 직결로 내보냄 → Mac엔 안 옴. **직결 랜선 물리 제거**로 eth0 down → `default via 192.168.10.1 dev wlan0`로 정상화.
- 현재: 젠지=`192.168.10.87`(wlan0), 티원=`192.168.10.250`(wlan0). 둘 다 무선 + 210. (IP는 DHCP drift — [[project_robot_ip_dynamic]])

### 검증 (PASS)
- **cross-discovery PASS**: 양 로봇이 같은 210 도메인에서 `/chatter` 상호 발견 확인 (티원 talker → 젠지·티원 양쪽 topic list에 `/chatter`).
- **Unity 듀얼 로봇 전환 (코드+Scene)**: 카메라·배터리는 두 로봇 Subscriber 배치 + 탭(`tab-tb3_1`/`tab-tb3_2`)→`OnRobotChanged`→즉시 전환 완비(모델 B: 동시 구독 + robotId 필터). cross-host 가시성은 단일 ros_tcp_endpoint(티원)가 210에서 양 로봇 토픽 forward하는 구조에 의존 → 도메인 통일이 전제.

### 역할 분담 (갭 아님 — 설계대로)
- **티원(tb3_1) = RealSense 비전 전용**(role:vision), **젠지(tb3_2) = Pi Camera + 센서 전용**(role:sensor). 조도/PIR/가스는 젠지 단독이 **설계대로**이며 티원엔 물리 센서가 없다. Unity에서 티원 탭 선택 시 센서 카드 `--` 표시가 정상 동작. TopicRegistry `tb3_1` 센서 null도 정상. → "두 로봇 모두 카메라"는 둘 다 OK, "센서"는 젠지 탭에서만(정상).

### 미해결 갭 (다음 작업)
1. **런타임 토픽 0** — 두 로봇 bringup/카메라 노드 미실행. Unity 켜도 데이터 안 옴. 실제 화면 확인은 양 로봇 bringup + 카메라(젠지 Pi Camera / 티원 RealSense) 기동 필요.
2. **ControlRoomApp IP 하드코딩** (`192.168.0.250` fallback + `t1@192.168.10.250`) — IP drift 위반, hostname/mDNS 전환 검토.
3. **젠지 센서 토픽 `/sensors/*` namespace 미분리** — Phase 3에서 `/tb3_2/sensor/*`로 정합 예정.
- evidence: `docs/evidence/2026-06-15-wireless-unify-domain210-unity-dualrobot-check.md`

## 2026-06-10 — Mac MPS + T1 RealSense → YOLOv8n 라이브 PASS + 영상 끊김 정량 진단 + 자산 5종 영구화

### 비전 트랙(Mac 절반) 검증 완료

- **결정**: 박물관 시연 비전 트랙은 **라즈베리(T1)는 영상 publish만, Mac MPS가 YOLO 추론**의 분업 구조를 본선 후보로 채택. 라즈베리에서 YOLO 안 돌림(CPU 한계).
- **결과**:
  - Mac MPS + cv2 + YOLOv8n: **26.0 fps headless / 16~17 fps GUI imshow**
  - 탐지: person 0.89 / keyboard 0.91 / cup 0.86 / tv 0.79 / laptop / mouse / cell phone 등 안정
  - 결과 이미지: `test/realsense_yolo_result.jpg`
- **데이터 경로**: T1 RealSense D435 → `realsense2_camera` (compressed 29Hz 2.17MB/s) → `web_video_server` (port 8080, MJPEG HTTP) → Mac `cv2.VideoCapture(http://...)` → YOLO(mps) → cv2.imshow
- **병렬 다리 3개**: `web_video_server` (8080, cv2/브라우저) + `foxglove_bridge` (8765, Foxglove Studio) + `ros_tcp_endpoint` (10000, Unity). 모두 같은 T1 토픽 별도 TCP 구독.

### 영상 끊김 정량 진단 (8지표) + compressed 전환

- **원인 진단**: raw `/camera/.../image_raw` = 11.27 Hz × 14.24 MB/s = **114 Mbps** → Wi-Fi link rate 65 Mbps의 **1.75배 초과** → publish/transmit 둘 다 못 따라가 끊김 누적.
- **해결**: Foxglove Image 패널 토픽을 `.../image_raw/compressed` (29.22 Hz × 2.17 MB/s = 17 Mbps)로 1줄 변경.
- **효과**:
  - 라즈베리 `realsense_node` CPU **87.5% → ~0%** (-87%p, raw subscribe 없어진 효과)
  - 네트워크 외부 흐름 **14.24 → 2.17 MB/s** (-85%)
  - 발행률 **11.27 → 29.22 Hz** (×2.6)
  - Foxglove 클라이언트 drop/error 0건

### 박제된 자산 (스킬 3종 + 메모리 1종 + 코드 1종 + evidence 1건)

- 🆕 **`.claude/skills/robot-ip-detect-fallback/SKILL.md`** — mDNS 깨졌을 때 ARP 라즈베리 OUI(`d8:3a:dd`/`2c:cf:67`/`dc:a6:32`/`b8:27:eb`/`e4:5f:01`) + `known_hosts` ed25519 host key 매칭으로 신원 추적. 2026-06-10 사례: Wi-Fi 대역 `0.x`→`10.x` 점프, `rb.local` 실패했지만 ed25519 매칭으로 T1=`192.168.10.250` 확정.
- 🆕 **`.claude/skills/robot-camera-stream-diag/SKILL.md`** — 카메라 영상 끊김 6대축 8지표 한 ssh 호출 동시 측정 + raw vs compressed 비교 + 해결 옵션 표. 박물관 시연 dry-run 매 회 첫 검증.
- ✏️ **`.claude/skills/robot-camera-bringup/SKILL.md`** §C/§D/§E + 함정 #19 추가
  - **§C** `ssh -fn` 표준 detach 패턴 (기존 `nohup ... & disown` heredoc 안에서 SSH session 종료 시 로그조차 안 생기는 케이스 회피)
  - **§D** `foxglove_bridge` 통합 (port 8765, Foxglove Studio dmg 클라이언트)
  - **§E** compressed 우선 정책 (Wi-Fi 65Mbps 환경 표준)
  - **함정 #19** `nohup ... & disown` heredoc detach 실패 사례
- ✏️ **메모리 `project_robot_ip_dynamic.md`** — "mDNS 자체가 깨졌을 때 fallback" 한 줄 추가 (다음 세션 자동 로드)
- 🆕 **`test/detect_realsense.py`** — Mac MPS RealSense YOLO. env: `FRAMES` `HEADLESS` `SAVE_LAST` `T1_IP` `T1_PORT` `T1_TOPIC`
- ✏️ **`test/CLAUDE.md`** — Y5 진입 한 줄 추가, Y0~Y4 PASS 마크
- 🆕 **evidence**: `docs/evidence/2026-06-10-mac-yolo-realsense-live.md`

### T1 시스템 변경 (apt install 3종)

- `ros-jazzy-foxglove-bridge` 3.2.6
- `ros-jazzy-realsense2-camera` 4.57.7 (+ msgs, description)
- `ros-jazzy-web-video-server` 3.1.0

### 맞춤 YOLO 캡처-라벨-학습-검수 루프 확정

- **결정**: T1 RealSense 맞춤 물체 인식은 Roboflow 같은 외부 SaaS 없이, 로컬 브라우저 학습실 `scripts/yolo_training/custom_yolo_studio.py`를 우선 정본으로 사용한다. 주소는 `http://127.0.0.1:8766/`.
- **저지연 영상 경로**: T1의 8090 preview 서버(`scripts/yolo_training/t1_compressed_mjpeg_server.py`)를 사용한다. 브라우저는 긴 MJPEG가 아니라 `/preview.jpg` polling으로 원본 실시간을 유지하고, SAM2/GrabCut segmentation은 overlay/검수용으로 분리한다.
- **데이터셋 정본**: `datasets/custom_object/images/{train,val}` + `datasets/custom_object/labels/{train,val}`. 학습 산출물은 `runs/custom_object/<run>/weights/best.pt`.
- **자동 라벨 결정**: ROI 박스를 그대로 저장하지 않고 `ROI crop -> SAM2/rembg/GrabCut mask -> bbox -> YOLO txt` 순서로 좁힌다. 자동연사 기본은 `매핑 성공한 사진만 저장`.
- **검수 결정**: 촬영 목록의 `마스크`, `검수 시작`, `←/→`, `D 삭제`, `Delete/Backspace`, `Esc`를 통해 앱 안에서 빠르게 넘기며 삭제한다. 검수 이미지는 `datasets/custom_object/review_masks` 캐시를 우선 사용한다.
- **오탐 정제 결정**: 배경을 물건으로 감지하는 현상은 `.pt`를 직접 수정하지 않고, `N 오탐 배경 저장`으로 `negative_*.jpg` + 빈 `.txt` hard-negative 샘플을 추가한 뒤 재학습한다.
- **현재 데이터 품질 진단**: 최신 학습 전 데이터에서 반복 bbox가 많았다. 예: 학습 50장 중 35장, 검증 18장 중 13장이 같은 bbox 좌표. 이 경우 높은 mAP라도 실전 배경 오탐을 숨길 수 있으므로, background-only 검증이 필수다.
- **최신 UI 확인**: `http://127.0.0.1:8766/?v=hard-negative-20260610-1806-clean`.
- **근거**: `docs/evidence/2026-06-10-mac-yolo-realsense-live.md`의 `Custom labeling studio`, `Review visibility/cache fix`, `Hard-negative background capture` 섹션.

### Robot safe shutdown 기준 문서화

- **결정**: 실험 종료 시에는 메인 슬라이드 스위치를 먼저 끄지 않고, SSH가 살아 있으면 OS `poweroff`를 먼저 수행한다.
- **표준 순서**:
  1. `tb3-down` 또는 수동 `pkill`로 ROS/카메라/브릿지 프로세스 정리.
  2. `ssh t1@192.168.10.250 'sudo poweroff'` 또는 Genji `ssh urhynix-robot 'sudo poweroff'`.
  3. 10~30초 후 ping 100% loss 확인.
  4. ping loss 확인 후 TurtleBot 메인 슬라이드 스위치 OFF.
  5. LiPo 분리/충전 상태 기록.
- **예외**: SSH frozen, 충돌 위험, 안전 문제는 물리 전원 OFF를 우선할 수 있다. 이 경우 emergency shutdown으로 기록한다.
- **2026-06-10 문서화 시점 상태**: T1 `192.168.10.250`은 ping 2/2 응답 및 8090 status fresh였으므로, 실제 셧다운 완료로 표시하지 않는다. 셧다운 완료 조건은 ping 100% loss다.
- **정본 절차**: `docs/ref/tech/ROS2-ROBOT.md` Safe Shutdown, `docs/status/HANDOFF.md` shutdown note.

### 함정 발견 (이번 세션 4종)

- **#19** `nohup ... & disown` heredoc에서 SSH session 종료 시 같이 죽음 → `ssh -fn` 패턴으로 교체
- **Foxglove inactive-tab 20MB drop** → `defaults write dev.foxglove.studio NSAppSleepDisabled YES` + 재시작 / 또는 cv2 경로 우회
- **mDNS `rb.local` resolve 실패** → ARP OUI + ed25519 매칭 fallback
- **Wi-Fi 대역 점프** (`0.x`→`10.x`) → ssh host key 동일성으로 같은 머신 확인

### 다음 트랙 후보 (이번 세션 종료 시점)

1. 젠지(Pi Camera) 동시 추론 — 이중 카메라 YOLO
2. depth 토픽 결합 — 박스 중심 픽셀 거리 표시
3. Unity ControlRoom 통합 — Mac 추론 결과를 ROS2 `/yolo/detections` 토픽으로 publish
4. realsense 15Hz + depth off 최적화 (박물관 시연 안정성)

### 자세히

`docs/evidence/2026-06-10-mac-yolo-realsense-live.md`

---

## 2026-06-09 — Phase 2.8 — 젠지 Arduino LDR/PIR Unity 결선 + 5종 자산 영구화

### 조도(LDR) + PIR 인체감지 Unity UI 결선

- **결정**: 조도 표시 = `63% · 밝음` (% + 5단계 상태 라벨), PIR = `감지!` / `감지 안 됨` 한글 토글
- **코드 신규**:
  - 🆕 `Assets/Scripts/Ros/LuxSubscriber.cs` (BatterySubscriber 패턴, Inspector `rawMin=30 / rawMax=300` 캘리브레이션 노출)
  - 🆕 `Assets/Scripts/Ros/PirSubscriber.cs` (`std_msgs/Bool` 구독, lastState 추적 + 첫 메시지 로그)
  - 🆕 `Assets/Scripts/App/SensorVerifyConsole.cs` — **영구 검증 자산**. Runtime static class. `Dump()`/`SwitchTo()`/`DumpRos()` 3개. SensorRegistry/Robots 동적 순회로 새 센서 추가 시 dict 1줄로 자동 포함.
  - ✏️ `Assets/Scripts/Ros/TopicRegistry.cs` (GetLdrRaw/GetPirState lookup 추가, 토픽 `/sensors/ldr` `/sensors/pir`)
  - ✏️ `Assets/Scripts/UI/SensorCardListView.cs` (PIR boolean 분기 + light 5단계 라벨 + **OnRobotChanged 캐시 redraw 패치** — 탭 전환 즉시 LastSensorValues에서 끌어와 표시, TelemetryPanelView 패턴과 동일)
  - ✏️ `Assets/Scripts/Data/FakeSensorData.cs` (tb3_2 제외, tb3_1만 fake 유지)
  - ✏️ `Assets/Scenes/ControlRoomMain.unity` 루트에 `LuxSubscriber_G` + `PirSubscriber_G` 2개 GameObject YAML 직접 박음 (Unity Editor 라이선스 핸드셰이크 실패 우회). fileID `7000000001~003` (Lux), `7000000011~013` (Pir).

- **영구 자산화 (스킬 4건)**:
  - 🆕 `.claude/skills/urhynix-sensor-bringup/SKILL.md` — Arduino 센서 결선 표준 (자매 스킬, urhynix-battery-bringup과 1:1 모델)
  - 🆕 `.claude/skills/unity-scene-yaml-patch/SKILL.md` — Editor 라이선스 실패 시 .unity YAML 직접 patch 표준 (fileID 충돌 회피 + SceneRoots 갱신)
  - 🆕 `.claude/skills/urhynix-sensor-verify-console/SKILL.md` — SensorVerifyConsole 호출/확장 패턴
  - ✏️ `.claude/skills/urhynix-battery-bringup/SKILL.md` — 함정 표 #26/#27 추가
    - **함정 #26**: USB `/dev/ttyACM*` 번호 재부팅/재꽂이마다 변동 → udev rule 영구 매핑 (Arduino UNO `2341:0043` → `tb3_arduino`, OpenCR `0483:5740` → `tb3_opencr`)
    - **함정 #27**: `OPENCR_PORT` 환경변수가 `turtlebot3_bringup robot.launch.py`에서 무시됨 → launch argument `usb_port:=/dev/ttyACM1` 사용 (line 40 `LaunchConfiguration('usb_port', default='/dev/ttyACM0')`)

- **검증 결과**:
  - ✅ 조도 UI 표시 PASS (`17% · 매우 어두움` 등 캘리브레이션 후 자연 환산)
  - ✅ PIR UI 표시 PASS (`감지 안 됨` 초기, `감지!` 토글 동작)
  - ✅ LDR/PIR ROS publish PASS (`/sensors/ldr` Int32, `/sensors/pir` Bool)
  - ✅ 젠지 배터리 UI `94.3 %` PASS (오전 작업)
  - ⚠️ **세션 후반 막힘**: Wi-Fi 망 변경 + 도메인 충돌 + 팀원 카메라 작업 후 ROS-TCP-Endpoint가 일관되게 티원 트랙만 forward, 젠지 트랙(배터리/카메라/LDR/PIR) 모두 막힘
    - 진단: 무선 망 multicast 차단으로 DDS multi-host discovery 실패 의심 (티원 ros2 cli도 `Unknown topic '/tb3_1/battery_state'`)
    - 다음 세션 디버그 후보: CycloneDDS unicast peers / Wi-Fi 라우터 IGMP / 팀원 도메인 충돌 분리

- **영향 받은 외부 환경 (참고)**:
  - 양쪽 `.bashrc` ROS_DOMAIN_ID `230` → `210` (팀원과 공유 도메인). **다음 세션 진입 시 도메인 확인 필요**.
  - 젠지 팀원 Pi Camera 작업 중 — 같은 도메인 210에 `/camera_container`, `/image_sub_node` 노드 보임. 우리 camera_node `Killed` (팀원 작업과 충돌 흔적).

- **다음 세션 5분 진입 캡슐**:
  1. 양 로봇 켜기 → `ros2 node list`로 팀원 노드 + 도메인 확인 (충돌 분리)
  2. USB ttyACM 번호 재확인 (`udevadm info`로 Arduino/OpenCR 매핑) → `/dev/tb3_arduino` 심링크 갱신 (함정 #26)
  3. 티원 본체 메인 전원 스위치 ON 확인 (함정 #20)
  4. `turtlebot3_bringup robot.launch.py namespace:=tb3_* usb_port:=/dev/ttyACM<N>` (함정 #27)
  5. `ros_tcp_endpoint` + `arduino_bridge.py` launch
  6. Unity Play → `unityctl exec ... SensorVerifyConsole.Dump()`로 5트랙 종합 검증

- **자세히**: `docs/evidence/2026-06-09-controlroom-sensor-lux-pir-link.md`

## 2026-06-08

### 듀얼 로봇 실 배터리 결선 PASS + 젠지 ROS 2 jazzy 원격 fresh install

- **결과**: `/tb3_1/battery_state` (티원 12.59V→99.5%) + `/tb3_2/battery_state` (젠지 11.73V→59.0%) Unity UI 동시 라이브 표시. 우측 패널 배터리 % + bar 토글 시 즉시 갱신. 사용자 확인 "양쪽 다른 voltage 다른 % 표시 PASS".

- **결정 4건**:
  1. **B안 (실 ROS 배터리 결선) 채택** — 시뮬 FakeSensorData에서 실 `sensor_msgs/BatteryState`로 전환. TurtleBot3 OpenCR 펌웨어가 percentage 필드를 잘못 채움(예: 117%)이라 voltage 선형 변환 채택: LiPo 3S `pct = clamp((voltage-10.5)/2.1)*100`. 만충 12.6V=100%, cutoff 직전 10.5V=0%.
  2. **단일 ros_tcp_endpoint 채택** — 티원에 endpoint 1대 띄우고 양 로봇 토픽 모두 forward. ROS_DOMAIN_ID=230 통일이라 가능. 젠지 endpoint는 미사용(자급 빌드는 함).
  3. **SSOT IP fallback 패턴** — `ControlRoomApp.ConfigureRos`가 `default_robots.json[0].hostAddress`에서 `user@host` 분리 후 IP 사용. mDNS 미작동 시 IP 직결 안전망. SSOT 변경만으로 IP 제어 가능.
  4. **3대 동시 launch 금지 원칙** — TurtleBot3 OpenCR `/dev/ttyACM0`는 1개만 잡음. 다중 launch는 무의미 + 펌웨어 stress. 1대만 launch + 나머지는 subscribe.

- **산출물** (코드 5종):
  - 🆕 `unity/ControlRoom/Assets/Scripts/Ros/TopicRegistry.cs` (`T1BatteryState`, `GenjiBatteryState` 상수 + `GetBatteryState(robotId)`)
  - 🆕 `unity/ControlRoom/Assets/Scripts/Ros/BatterySubscriber.cs` (119줄, voltage 환산 + 끊김 감지 3중: timeout 5초/present=false/voltage<5V/회복 로그)
  - ✏️ `unity/ControlRoom/Assets/Scripts/App/ControlRoomApp.cs` (`DefaultRosIp` 하드코딩 → `default_robots.json[0].hostAddress`에서 IP 추출 + `FallbackRosIp`)
  - ✏️ `unity/ControlRoom/Assets/Scripts/UI/TelemetryPanelView.cs` (`OnRobotChanged` 구독 추가 + `Apply()/Reset()` 헬퍼 분리, 탭 전환 즉시 갱신)
  - ✏️ `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json` (tb3_1 hostAddress `t1@192.168.0.250` → `t1@192.168.10.250`, Wi-Fi 변경 반영)

- **Scene (영구 박힘)**:
  - `BatterySubscriber_T1` GameObject + `BatterySubscriber` 컴포넌트 (robotId=tb3_1, displayLabel=티원)
  - `BatterySubscriber_G` GameObject + `BatterySubscriber` 컴포넌트 (robotId=tb3_2, displayLabel=젠지)
  - `ROSConnection` GameObject + `m_RosIPAddress=192.168.10.250` `m_RosPort=10000`

- **로봇 워크스페이스**:
  - **티원** (rb / 192.168.10.250): `~/turtlebot3_ws/install/ros_tcp_endpoint` 자급 빌드 (Unity-Technologies/ROS-TCP-Endpoint, branch main-ros2)
  - **젠지** (kim-desktop / 192.168.10.87): ROS 2 jazzy 원격 fresh install — ros-jazzy-desktop + ros-jazzy-turtlebot3 + ros-jazzy-turtlebot3-msgs + colcon + rosdep, `~/turtlebot3_ws` clone 3종(turtlebot3, ROS-TCP-Endpoint main-ros2, coin_d4_driver) + `colcon build` 10 packages (3분 57초), `.bashrc` env 박음(TURTLEBOT3_MODEL=burger, LDS_MODEL=LDS-03, OPENCR_PORT=/dev/ttyACM0, ROS_DOMAIN_ID=230)

- **신규 함정 5건 (영구 자산화 #19~#23)**:
  | 번호 | 함정 | 우회 |
  |---|---|---|
  | #19 | TurtleBot3 OpenCR pub `BatteryState.percentage` 필드 117% 같은 무효값 | voltage 선형 변환 사용 (`(v-10.5)/2.1*100`) |
  | #20 | TB3 본체 메인 전원 스위치 OFF — OpenCR는 USB 5V로 살아있지만 Dynamixel 응답 0 → `[TxRxResult] There is no status packet` 후 `process has died, exit code -6` | 본체 메인 스위치 ON 확인 우선 |
  | #21 | 새 OS 사용자 `dialout` 그룹 미가입 → `/dev/ttyACM0` `crw-rw----` 권한 부족 → `Failed to open port` | `sudo usermod -aG dialout <user>` 영구 + `sudo chmod 666 /dev/ttyACM0` 즉시 우회 |
  | #22 | 3대 컴퓨터에서 동시 ssh launch → ttyACM0 선점 경쟁 + 펌웨어 baudrate handshake stress → publisher count 0 깜빡임 | 1대만 launch + 나머지는 subscribe-only |
  | #23 | DHCP Wi-Fi 변경(`192.168.0.x` → `192.168.10.x`) 시 SSOT IP drift, mDNS 일시 캐시 깨짐 | `default_robots.json` IP 갱신 + `dscacheutil -flushcache` + arp sweep으로 MAC 매칭 추적 |

- **다음 진입 후보**:
  - (a) 센서 카드 확장 (`SensorCardListView`에 `OnRobotChanged` 구독 + `/scan` 같은 ROS 토픽 구독)
  - (b) 카메라 namespace 정리 (현 젠지 `/camera/*` → SSOT 약속 `/tb3_2/camera/*`)
  - (c) 끊김 감지 시연 (한쪽 본체 전원 OFF → 5초 후 `⚠️ 배터리 토픽 끊김` 로그 박힘 확인)
  - (d) 가스/소음/조도 Arduino 센서 ROS 토픽화

- **자세히**: `docs/evidence/2026-06-08-controlroom-battery-real-link.md`

## 2026-06-05

### Unity ControlRoom Phase 2.7-dual — 듀얼 카메라 분기 PASS (모델 B, 0ms 즉시 전환) + 함정 #17/#18 영구 자산화

- **결과**: 상단 로봇 탭(티원/젠지) 클릭 시 카메라 패널이 **지연 0ms로 즉시 전환**. 사용자 직접 확인 "딜레이없이 전환잘됨 실시간표시됨". UI Contract Lock 침해 0줄 (UXML/USS 0줄).
- **결정 — 모델 B 채택** (구현 전 측정 기반):

  | 모델 | 전환 지연 | 스피너 | 비용 |
  |---|---|---|---|
  | A 토글 구독 (Subscribe/Unsubscribe) | 80~500ms (Wi-Fi 변동) | 필요 | Pi 1토픽 forward |
  | **B 동시 구독 + display 토글** | **0~33ms (다음 frame)** | 불필요 | Pi 2토픽 (+5~10% CPU), Wi-Fi 6% |

  근거: 학원 Wi-Fi 100Mbps+, Pi 부하 여유 충분, 시연 흐름 끊김 0의 B 압도적. 사용자 결정.

- **산출물 (코드)**:
  - 🆕 `unity/ControlRoom/Assets/Scripts/Ros/TopicRegistry.cs` (16줄, 토픽 SSOT, `Ros/CLAUDE.md` 규칙 준수)
  - ✏️ `Scripts/Ros/CameraStreamSubscriber.cs` 76→81줄 (`robotId` 필드 + 정적 event 시그니처 `(string robotId, Texture2D, float)`, `topicName` 비우면 TopicRegistry lookup)
  - ✏️ `Scripts/UI/CameraPanelView.cs` 43→46줄 (`activeRobotId` 필터링, `OnRobotChanged` 시 hz 초기화)
  - ✏️ `Editor/CameraStreamSetup.cs` 60→80줄 (`SubSpec[]` 배열로 두 GameObject `_Genji`/`_T1` idempotent 생성, 메뉴 `(Dual)`)
  - 변경 0줄: `RobotTabView.cs` (이미 `Button.clicked → SelectRobot → OnRobotChanged + active 토글` 완성) / `ControlRoomState.cs` (이미 `SelectRobot → RaiseRobotChanged` 완성) / `TopBar.uxml` (이미 `tab-tb3_1`/`tab-tb3_2` Button 존재)

- **신규 함정 2종 (스킬화 영구)**:
  1. **#17** Write/외부 에디터로 만든 신규 `.cs`는 Unity `.meta` 미생성 → Asset Pipeline이 무시 → 어셈블리에 새 심볼 누락 → 다른 파일에서 `error CS0103: The name '<Class>' does not exist`. **우회**: `unityctl asset import --project <proj> --path Assets/Scripts/.../<file>.cs --json` (guid 발급 = 정상 import).
  2. **#18** Play 모드 중에는 도메인 리로드 차단 → `unityctl asset refresh` + `RequestScriptCompilation` 호출해도 어셈블리 mtime 옛값. `unityctl exec` 시 옛 코드 실행. **우회 5단계**: `play stop` → settled `Ready` 대기 → `exec RequestScriptCompilation()` → assembly mtime 갱신 확인 → `exec <Method>()` → `play start`.
  3. **공식 통합 — unityctl 자동화 표준 5단계**: 함정 #17 + #18 모두 한 번에 우회. 매 Unity 코드 변경 직후 사용. (자세히 `unity-camera-panel` SKILL 신설 섹션)

- **검증 PASS**:
  - 컴파일 error CS 0건, `Assembly-CSharp.dll`/`Assembly-CSharp-Editor.dll` mtime 11:04:47 갱신
  - 양 토픽 hz cross-host visibility: 젠지에서 `/tb3_2` 30.0Hz + `/tb3_1` 31.0Hz 동시 발행 (티원 endpoint 불필요, 젠지 endpoint 1개로 양쪽 forward)
  - robot port 10000 ESTAB + Send-Q 77KB (영상 흐름 정상)
  - Scene에 두 GameObject(`CameraStreamSubscriber_Genji`/`_T1`) idempotent 박힘
  - Setup batch 로그 "2개 Subscriber 활성 (Dual)"
  - 사용자 시각 확인 — 탭 클릭으로 패널 즉시 전환

- **데이터 흐름 (최종)**:
  ```
  [젠지 Pi Camera 30Hz] → camera_ros → /tb3_2/.../compressed ┐
  [티원 RealSense 30Hz] → realsense2_camera → /tb3_1/.../compressed ┤  ROS_DOMAIN_ID=230
                                                                   ↓
                                            젠지 ros_tcp_endpoint (port 10000, 단일)
                                                                   ↓ TCP Wi-Fi
                                            Unity ROS-TCP-Connector (단일 연결)
                                                                   ↓
                                  ┌──────────────────────────┴──────────────────────────┐
                                  ↓                                                       ↓
                  CameraStreamSubscriber_Genji (robotId="tb3_2")    CameraStreamSubscriber_T1 (robotId="tb3_1")
                                  └──────────────── static event ─────────────────────────┘
                                                                   ↓
                                  CameraPanelView (activeRobotId 필터링, 0ms 토글)
                                                                   ↑
                                  RobotTabView Button.clicked → SelectRobot → OnRobotChanged
  ```

- **스킬 영구 자산화**:
  - `.claude/skills/unity-camera-panel/SKILL.md`: "듀얼 카메라 분기 — 모델 B" 섹션 + "unityctl 자동화 표준 5단계" 섹션 + 함정 #17/#18 + 박물관 시연 매핑 표 T1 토픽 정정 (`/tb3_1/camera/color/...` camera 1번)
  - `.claude/skills/robot-camera-bringup/SKILL.md`: 함정표에 #17 (.meta 미생성) + #18 (Play 중 reload 차단) 추가

- **다음 진입**:
  1. 티원 `sudo loginctl enable-linger t1` 영구화 (현재 `Linger=no` — ssh 끊김 시 realsense2_camera 죽음, 함정 #13 미적용 상태)
  2. Phase 2.8 — Gemma 4 12B 통합 (로그 패널 회색 ⚪ → 녹색 🟢 토글)
  3. (선택) 듀얼 PiP/스플릿 화면 — 백엔드 이미 양쪽 받고 있어 코드 거의 변경 없음
  4. (백로그) `server.py:125` 패치 src/ 영구화 (현재 build/만, colcon build 시 회귀 위험)

- **자세히**: `docs/evidence/2026-06-05-controlroom-dual-camera-toggle.md`

## 2026-06-04

### Unity ControlRoom Phase 2.7 — 젠지 Pi Camera 라이브 결선 PASS + 4종 함정 영구 자산화

- **결과**: ControlRoom 신 프로젝트(Unity 6.3 LTS)에 젠지 `/tb3_2/camera/image_raw/compressed` **30Hz 라이브 RGB 결선 완료**. 사용자 확인 "카메라 화면 잘나옴". 로그 패널에 `🟢 Pi Camera 연결됨` + `⚪ Gemma 4 12B 대기 중` 2줄 표시.
- **산출물**:
  - 🆕 `unity/ControlRoom/Assets/Scripts/Ros/CameraStreamSubscriber.cs` (76줄, namespace `URHYNIX.ControlRoom.Ros`, static event `OnFrameUpdated`)
  - 🆕 `unity/ControlRoom/Assets/Editor/CameraStreamSetup.cs` (60줄, idempotent Scene GameObject 자동 배치)
  - ✏️ `Assets/UI/Parts/CameraAndLogPanel.uxml` 1줄 (`<ui:VisualElement>` → `<ui:Image>`, 시각 변화 0)
  - ✏️ `Assets/Scripts/UI/CameraPanelView.cs` 30→43줄 (기존 라인 0줄 수정, Image 타입 + frame 핸들러 추가만)
  - ✏️ `Assets/Scripts/App/ControlRoomApp.cs` `ConfigureRos()` + Gemma 대기 로그
  - ✏️ `ProjectSettings/ProjectSettings.asset` `scriptingDefineSymbols: Standalone: ROS2`
  - ✏️ robot `~/turtlebot3_ws/build/ros_tcp_endpoint/ros_tcp_endpoint/server.py:125` 패치
  - ✏️ robot `sudo loginctl enable-linger kim` 영구 활성화
- **잡은 함정 4종 (스킬화)**:
  1. **#13** Ubuntu 24.04 `KillUserProcesses=yes` → ssh 끊김 시 백그라운드 노드 죽음 → `sudo loginctl enable-linger <user>` 1회
  2. **#14** Unity 6.3 + ROS-TCP-Connector v0.7.x syscommand JSON `[:-1]`이 valid 끝 char까지 cut → `server.py:125` `.rstrip("\x00").strip()` 패치
  3. **#15** macOS Unity 시동 `setsid+nohup` 즉시 죽음 → **`open -a`** 명령 사용
  4. **#16 ★** Unity 기본 ROS1 모드 → ROS2 endpoint와 CompressedImageMsg binary format 비대칭으로 `OverflowException` → **`ProjectSettings.asset` `scriptingDefineSymbols: Standalone: ROS2`** (또는 GUI: `Edit → Project Settings → Player → Other Settings → Scripting Define Symbols`에 `ROS2` 추가)
- **UI Contract Lock 침해 검사**: UXML 1줄(태그명만 시각 변화 0), USS 0줄, 기존 View C# 라인 0줄 수정. ControlRoomEvents 0줄(Subscriber static event로 우회). → **사실상 침해 없음**.
- **검증 PASS**: 컴파일 31 assemblies + Console 0 errors + robot `RegisterSubscriber OK` + `/tb3_2/camera/image_raw/compressed` 29.9~30.0 Hz + 사용자 시각 검증.
- **데이터 흐름**: Pi Camera → camera_ros (tmux) → /tb3_2/.../compressed → ros_tcp_endpoint (server.py patched) → port 10000 → Unity ROS-TCP-Connector (`#if ROS2` 컴파일 분기) → CameraStreamSubscriber → static event → CameraPanelView → ui:Image.
- **다음 단계**:
  1. `server.py:125` 패치를 `~/turtlebot3_ws/src/`에도 박고 colcon build (현재 build/만 패치, 재빌드 시 덮어쓰일 위험)
  2. 티원(t1) D435 같은 패턴으로 결선 (`loginctl enable-linger t1` + ros_tcp_endpoint)
  3. Phase 2.8 — Gemma 4 12B 통합 (로그 회색 ⚪ → 녹색 🟢 토글)
- **자세히**: `docs/evidence/2026-06-04-controlroom-camera-live-pass.md`
- **스킬 보강**: `.claude/skills/robot-camera-bringup/SKILL.md` 함정 #13~16 + `.claude/skills/unity-camera-panel/SKILL.md` (ROS2 define + UI Toolkit Image element + macOS open -a)

### Unity ControlRoom Phase 2.5 진짜 완료 — EventSystem InputModule 누락 root cause 발견 + UI 상호작용 감사 스킬화

- **증상**: 사용자 "현재 플레이모드이고 눌리는게 아예없음" — Phase 2.5 단계 1~4 시각은 완벽이지만 모든 버튼/토글이 클릭에 0 반응.
- **원인 (root cause)**: `Assets/Editor/ControlRoomSceneSetup.cs:53` EventSystem GameObject 생성 시 `InputSystemUIInputModule` 컴포넌트 누락. 주석에 "자동 모듈 추가" 가정했으나 Unity 6.3 + new InputSystem 1.17.0은 **수동 명시 필수**. InputModule 없으면 UI Toolkit이 마우스 이벤트를 단 1건도 수신 못 함 (시각만 그려지고 클릭 dead).
- **해결 절차** (재현 가능):
  1. `unityctl component add` 로 현재 Scene EventSystem에 `UnityEngine.InputSystem.UI.InputSystemUIInputModule` 추가.
  2. `ControlRoomSceneSetup.cs:54-56` 수정 — `new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule))` 2-인자 패턴.
  3. Scene 저장 + Editor Play 재시작 → 사용자 확인 "잘눌리고있음".
- **부수 작업 — UI 상호작용 감사 자동화 시도** (Phase A 정적 PASS / Phase B 동적 실패):
  - Phase A (Opus 정적): 25개 UI 요소 매트릭스(버튼/토글/탭/카드/팝업) 6 결함 분류(A~F) → **25/25 PASS**, 0 발견사항. `docs/evidence/2026-06-04-ui-interaction-audit.md` 500줄.
  - Phase B (unityctl exec 동적): 5가지 한계 발견 후 포기 — ① `script validate` "Compilation succeeded" 거짓 PASS(실제 CS0079) ② exec --code는 시스템 어셈블리만 검색(Assembly-CSharp 도달 불가) ③ `Button.clicked` 는 event Action → 외부 invoke 컴파일 차단 ④ `Assets/Editor/` 폴더 Play 모드 AppDomain 미로딩 ⑤ `[RuntimeInitializeOnLoadMethod]` 등록 전 컴파일 실패로 미실행.
- **핵심 학습 2건**:
  - Phase A 정적 감사는 Scene config 결함(EventSystem InputModule 누락 등 GameObject 레벨)을 절대 못 잡는다 → 시각 시연 후 사용자가 직접 클릭으로 sanity 1회 필수.
  - Unity 6 + new InputSystem 1.17.0 환경에선 EventSystem에 `InputSystemUIInputModule` 명시 = 비협상 사항. 주석에 "자동" 가정 금지.
- **스킬화**: `.claude/skills/unity-ui-interaction-audit/SKILL.md` 신설(300+줄). Phase A 정적 매트릭스 패턴 + Phase B 한계 5종 + 함정 10건(`script validate` 거짓 PASS / event Action invoke 불가 / Editor 폴더 unreachable / **EventSystem InputModule 누락 0 반응** 등). `.claude/skills/README.md` 인덱스 추가.
- **자기리뷰(Opus) PASS**: 6 검증 항목(SKILL.md 정합성/PLAN.md 갱신/EventSystem fix/Phase A 보고서/스킬 함정표/UI Contract Lock) 전부 PASS, 발견사항 0건, 박물관 시연 GO 판정 유지. `docs/evidence/2026-06-04-self-review.md`.
- **SSOT 패치**: `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md` §3 표 — TopBar=`TopBarView+RobotTabView+PowerButtonView`, 원격 상태 계측=`TelemetryPanelView+SensorCardListView`, 신규 row=`ProtectedTargetView` 보호대상.
- **부수 산출물**: `.claude/skills/unity-ui-interaction-audit/SKILL.md`, `docs/evidence/2026-06-04-{ssot-ui-audit,ui-interaction-audit,self-review}.md`, `unity/ControlRoom/Assets/Editor/ControlRoomSceneSetup.cs` patch, `unity/ControlRoom/Assets/Scenes/ControlRoomMain.unity` (EventSystem 컴포넌트 추가).
- **commit**: bcae8a9(skill+reports) → a213692(EventSystem fix) → 자기리뷰 evidence push 완료.
- **다음 진입**: **Phase 3 데이터 모델/Registry** (POCO 4 `RobotInfo/SensorInfo/RobotFeatureInfo/ProtectedTargetInfo` + Registry 2 `FeatureRegistry/SensorRegistry` + JSON 4 `default_robots/sensors/features.json + office_base_map.json` + loader). **UI Contract Lock 원칙**: UXML/USS/View 0줄 수정. 실 로봇 ROS 연결은 **Phase 5**, 본 Phase 3은 fake지만 config-driven으로 전환.

## 2026-06-02

### Unity ControlRoom Phase 2.5 단계 1~4 완료 + 자기리뷰 PASS — 16 View 100% 활성

- **결정/PASS**: Phase 2.5 (UI Visual Completion) 5단계 중 1~4 완료. 컴파일 PASS, Unity Editor 시각 검증 PASS, 자기리뷰(Opus) PASS. SSOT §3의 14 View + 보너스 2(RobotTabView/PowerButtonView) = **16 View 100% 활성**. fake interaction 깊이 = "알람 popup만" 결정 일관 유지.
- **단계 1 (좌측 4 View, 0.5d PASS)**: MovePanelView / ModePanelView / FeatureToggleListView / WaypointListView 신설 + ScenarioPanelView SRP 리팩토링(Move/Mode 책임 제거) + LeftControlPanel.uxml 더미 5 waypoint + USS `.btn-action.active` 녹색 + `.btn-waypoint*` 스타일.
- **단계 2 (상단바·우측 4 View, 0.5d PASS)**: RobotTabView / PowerButtonView / HardwarePanelView / SensorCardListView 신설 + TopBarView/TelemetryPanelView SRP 리팩토링 + RightStatusPanel.uxml PIR/화재 sensor-row 추가 (총 5종) + USS `.sensor-value.sensor-{ok,warn,danger}` 색상.
- **단계 3 (맵 placeholder 시각 완성, 1d PASS)**: MapPanel.uxml 격자 6선 + waypoint 5(번호) + 보호대상 2(액자A/B) + 로봇 dot 2(티원/젠지) + "박물관 1층" 라벨 + USS 마커 스타일. **함정 학습 2건**: ① UI Toolkit `linear-gradient` 미지원 → 단색 교체 ② 🖼/📍 emoji 폰트 누락 → 컬러 박스/텍스트 교체.
- **단계 4 (카메라/로그 polish + 빈 공간 채움, 0.5d→2d PASS)**: ProtectedTargetView 신설(SSOT 우측 §3 누락분, 보호대상 3개) + 카메라 패널 crosshair + LIVE dot + camera-header. **빈 공간 채움 시행착오 5회** 끝에 **FR5UNITY PendantV3 성공 패턴 발견** (`/Users/family/jason/FR5UNITY/robotapp/Assets/UI/PendantV3/pendant-v3.uss`).
- **FR5UNITY 성공 패턴 이식 — UI Toolkit ScrollView 함정 해소**:
  - ScrollView 부모/자식 모두 `min-height: 0; min-width: 0` 명시 (UI Toolkit flex 함정의 진짜 원인)
  - `.unity-scroll-view__content-container` + `__content-viewport` 내부 element 직접 패치
  - `.unity-scroller--horizontal` 명시 `display: none`
  - 카드 `flex-shrink: 0; min-width: 0; max-width: 100%; overflow: hidden`
  - PanelSettings `m_ScaleMode: 2 → 1` (ConstantPhysicalSize → ScaleWithScreenSize) — letterbox 제거
  - 마지막 카드 `.card-fill { flex-grow: 1 }` + contentContainer `min-height: 100%`로 3단 정렬
- **자기리뷰(Opus) PASS + FIX 1 적용**: alertCount가 로봇 탭 전환 시 reset 안 되는 minor bug → `TopBarView.cs:31` OnRobotChanged 구독 추가 + reset. FIX 2(보호대상 4 시나리오 비대칭) + FIX 3(linear-gradient)는 의도적으로 deferred.
- **placeholder 5건 (Phase 3+ swap 필요)**: 맵 격자/marker, 카메라 RGB feed, 센서 dummy 값, 로그 5초 주기, 배터리 dummy 값.
- **commit**: 17be8ea(단계 1~4 + FR5 패턴) → 다음 commit(FIX 1 + SSOT 3종 갱신).
- **부수 산출물**: `vendor/unityctl-plugin/` 4.3MB 영구화, `.claude/skills/ssot-trio-update/`, `docs/evidence/ui-layout/` 26 PNG.
- **다음 진입**: 단계 5(시나리오 알람 polish — severity별 색상/auto-dismiss/메시지) 또는 Phase 3 직진(데이터 모델 + config 4종 JSON + Registry 자동 UI 생성). Phase 3 진입 시 UI Contract Lock 원칙 (UXML/USS/View 0줄 수정).

### Unity ControlRoom Phase 진행 전략 — 옵션 D (UI Polish First) + Phase 2.5 신설

- **결정**: Phase 3(데이터 모델/Registry) 진입 전에 **Phase 2.5 UI Visual Completion**을 신설해 UI를 contract로 먼저 100% 잠근다. 그 뒤 Phase 3~8은 UXML/USS/View 코드 0줄 수정 원칙으로 안만 채운다. fake interaction 깊이 = **알람 popup만** (시나리오 버튼 클릭 시 알람만 띄움, 센서 spike/로봇 dot animation 등은 안 함, Phase 3 이후 실 데이터로 자연 동작).
- **배경**: SSOT vs 현재 구현 cross-check 결과 View 14개 중 ✅4 / ⚠️3 / ❌7 — UI 자체가 절반 미완성. Map/Robot/Features/Sensors/Ros 5개 폴더는 통째 0%. 옵션 A(SSOT 순차)/B(Map 우선)/C(하이브리드)/D(UI Polish First) 4개 비교 후 D 채택. 이유: 기능 phase에서 UI를 또 바꾸면 두 번 작업 위험 → UI를 contract로 먼저 잠그면 꼬임 방지 + 시각 시연 가성비 최고.
- **Phase 2.5 산출물 (9 View 클래스 + UXML/USS 채움)**:
  - Scripts/UI/MovePanelView, ModePanelView, FeatureToggleListView(정적), WaypointListView, RobotTabView, PowerButtonView, HardwarePanelView, SensorCardListView, ProtectedTargetView
  - UXML 보강: 좌측 순회 지점 더미 5줄, 우측 하드웨어/센서 5종(PIR/화재 추가), MapPanel 격자+dot/waypoint placeholder, TopBar 전원 확인 모달
  - USS 보강: 격자 패턴, marker 스타일, 알람 popup polish
- **5단계 분해 (3~4일)**: ① 좌측 View 4개(0.5일) ② 상단바·우측 View 4개(0.5일) ③ 맵 placeholder 시각 완성(1일) ④ 카메라+로그 polish(0.5일) ⑤ 시나리오 알람 popup(1일).
- **검증 매트릭스 10건**: View 14 전부 ✅, 좌측 토글 시각 반응, 탭 전환 시 우측 갱신, 시나리오 4 알람, 맵 dot/waypoint/보호대상, 카메라 placeholder 자연스러움, 로그 5초 주기 push, 센서 5종, 전원 확인 모달, 30분 demo 녹화 시 "진짜 시연 같음".
- **핵심 학습**: 옵션 B/C(시각 가성비)는 기능 짜다 UI 또 만지는 두 번 작업 위험. 옵션 A(SSOT 순차)는 1주 작업해도 시각 변화 0. **UI를 contract로 먼저 잠그면 둘 다 잡힘**.
- **부수 산출물**: `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md` §13에 Phase 2.5 신설 (Phase 2와 Phase 3 사이).
- **다음 진입**: Phase 2.5 단계 1 — 좌측 패널 View 4개 클래스 작성. 첫 파일: `Scripts/UI/MovePanelView.cs` (URHYNIX.ControlRoom.UI namespace, 순회 시작/정지 버튼 클릭 핸들러 + active 토글).

### 14:30 회의 Jira 최신 반영 — 티원/젠지, ROS_DOMAIN_ID 230, Teachable Machine 분류 스파이크

- **결정/확인**: 14:30 회의록 기준 로봇 별명과 역할을 다시 잠금. **젠지** = Pi Camera + 센서 탑재 로봇, **티원** = 비전 카메라 탑재 로봇. ROS 도메인은 `ROS_DOMAIN_ID=230`으로 통일한다.
- **검증 완료**: Unity에서 두 로봇 카메라 화면 동시 송출을 확인했다. 회의 근거는 Confluence `2026.06.02`(page `6127617`)와 `image-20260602-031954.png`.
- **AI 분류 스파이크**: Google Teachable Machine으로 TensorFlow/Keras 모델을 만들고, 1차 학습 클래스는 `빈공간`, `박스`, `마우스(검정/흰색)`, `손`으로 둔다. 목적은 로봇 카메라 영상에서 빠른 객체 분류 테스트다.
- **기존 비전 범위와의 관계**: 5/29 YOLO/OpenCV MVP 클래스(로봇/사람/중요품/불)는 발표 시나리오용 큰 범위로 유지한다. 6/2 Teachable Machine 클래스는 카메라 입력과 Keras 추론 경로를 빠르게 검증하는 별도 스파이크다.
- **Jira 반영 완료**: `SCRUM-44`, `SCRUM-51`, `SCRUM-54`, `SCRUM-56`, `SCRUM-61`, `SCRUM-62`, `SCRUM-64` 설명에 회의 최신 내용을 추가했다.
- **다음 검증**: 같은 도메인 230에서 `/tb3_1/...`와 `/tb3_2/...` 카메라 토픽이 동시에 보이는지, Keras 모델 추론 결과가 Unity 또는 테스트 로그에 클래스/신뢰도로 찍히는지 확인한다.

### Play UI 미표시 해결 — Scene 파일 m_PanelSettings 직접 GUID 패치 + unityctl screenshot 한계 확인

- **증상**: Play 진입 후 Game View가 Skybox+ground만 표시, UI Toolkit 6패널이 안 보임.
- **원인 1 (본질)**: Scene 파일 `ControlRoomMain.unity:439`의 `m_PanelSettings: {fileID: 0}` — Unity 6.3 LTS UIDocument.panelSettings setter가 직렬화 안 됨. `doc.panelSettings = panel` 호출 후 SaveScene 해도, SerializedObject.FindProperty("m_PanelSettings").objectReferenceValue 박아도 fileID 0으로 남음. sourceAsset(visualTreeAsset)은 정상 직렬화되어 대조됨. (Unity 6.3 버그 의심)
- **해결**: Scene 파일 직접 GUID 박음: `m_PanelSettings: {fileID: 11400000, guid: 22cd8904c7c224cd0a7d5e03ef3240ee, type: 2}` (PanelSettings asset의 mainObjectFileID + meta GUID 사용). Editor가 다음 reload에 그대로 인식.
- **이중 안전망**: `Assets/Scripts/UI/ControlRoomBinder.cs` Awake에 runtime fallback 추가 — `uiDoc.panelSettings == null`이면 `#if UNITY_EDITOR` LoadAssetAtPath로 박음. 다음 Setup 호출에서도 panel 누락되면 자동 복구.
- **원인 2 (부수)**: 본 fix 후에도 `unityctl screenshot capture --view game`이 검은 화면 또는 카메라만 캡처. `ScreenshotHandler.cs:83`이 `camera.Render()`만 호출 → UI Toolkit ScreenSpaceOverlay 미포함.
- **부수 해결**: `vendor/unityctl-plugin/.../ScreenshotHandler.cs:22` 패치 — view=game일 때 `includeOverlayUi` 기본 true. 그러나 `CaptureGameViewWithOverlay`의 `ScreenCapture.CaptureScreenshotAsTexture`가 sync 호출 timing 한계로 빈 frame 반환 (검은 화면). plugin level 본질 해결 어려움.
- **시각 검증 권장**: macOS native `screencapture -x` + `osascript "System Events" "Unity" set frontmost`로 캡처. Unity 활성화 + Game View 영역 캡처 → UI Toolkit overlay 포함 완벽 캡처 PASS. 박물관 시연 좌230(시나리오/모드) + 중앙(맵+카메라+로그) + 우240(배터리/센서) 6패널 모두 렌더링 확인.
- **핵심 학습 추가** (이전 entry 3건 + 2건):
  4. **UIDocument.panelSettings 직렬화 우회는 Scene YAML 직접 패치가 가장 확실**. setter도 SerializedObject도 fail 케이스 있음. GUID + mainObjectFileID(보통 `11400000`) 알면 직접 박기 가능.
  5. **`unityctl screenshot`은 UI Toolkit Overlay 캡처 신뢰 불가** — Native `screencapture` + Unity activate 우회 패턴 권장.
- **부수 산출물**:
  - `vendor/unityctl-plugin/src/Unityctl.Plugin/Editor/Commands/ScreenshotHandler.cs` 1줄 patch (URHYNIX 표시 주석 포함, upstream과 diverge — 다음 vendor 갱신 시 재적용 필요).
  - `Assets/Scripts/UI/ControlRoomBinder.cs:30-43` Awake fallback 블록 추가.
  - `Assets/Scenes/ControlRoomMain.unity:439` m_PanelSettings GUID 박음.
- **다음 진입**: Editor Game View에서 시각 검증 7체크리스트(시계 / 시나리오 버튼 클릭 → 로그+Alert / 2D 3D 토글 / 배터리 변동 / 센서 카드 갱신 / 로그 자동 스크롤 / AlertPopup 모달) 직접 수행.

### unityctl 통합 테스트 10/10 PASS — 5 FAIL 전부 해소 + plugin vendor 영구화 + 핵심 학습 3건

- **결정**: 이전 entry의 5 FAIL(`scene open` 500 / `screenshot` 502 / `exec` 502 / `test` 504 / 휘발성 경로) 모두 해소. unityctl 자동화 baseline → **풀 자동화 가능** 단계 진입.
- **해소 절차** (재현 가능):
  1. **Plugin source 영구화**: `rsync -a --exclude='.git' /tmp/unityctl-repo/ vendor/unityctl-plugin/` (4.3MB, 383 파일). `manifest.json` 경로 변경: `file:/tmp/unityctl-repo/...` → `file:../../../vendor/unityctl-plugin/src/Unityctl.Plugin` (Packages/ 기준 상대경로).
  2. **SceneSetup Camera 추가**: `Assets/Editor/ControlRoomSceneSetup.cs:38` `NewSceneSetup.EmptyScene` → `NewSceneSetup.DefaultGameObjects` 1줄 패치. Scene rootCount 5 → 7 (Main Camera + Directional Light 자동 포함).
  3. **Editor 재시작**: SIGTERM 60258 → nohup 신규 시동 → `osascript activate` (포커스가 IPC Bootstrap 트리거 조건).
  4. **Scene 재생성**: `unityctl exec ExecuteMenuItem("URHYNIX/Setup ControlRoom Scene")` (1차 Play 모드라 NewScene InvalidOperationException → `play stop` 후 2차 PASS).
- **10/10 결과 매트릭스**:
  | Step | 명령 | 결과 |
  |---|---|---|
  | 1 | `doctor` (IPC probe) | ✅ pipe `unityctl_4147f01858f6edf8` 활성 |
  | 2 | `check --type compile` | ✅ 31 assemblies, 0 error |
  | 3 | `scene hierarchy` | ✅ rootCount 7 (MainCamera + DirLight + 5 app GO) |
  | 4 | `screenshot capture --view game` | ✅ 1920×1080 PNG 270KB → `/tmp/controlroom-game-view.png` |
  | 5 | `screenshot capture --view scene` | ✅ 102KB → `/tmp/controlroom-scene-view.png` |
  | 6 | `play start` | ✅ isPlaying=true |
  | 7 | `exec RaiseScenarioTriggered("fire")` ×4 | ✅ 4 시나리오 (fire/intruder/noise/theft) 전부 success=true |
  | 8 | `screenshot capture` (post-scenario) | ✅ Alert popup 포함 화면 캡처 |
  | 9 | `console get-count` | ✅ 5 logs / 7 warnings / 0 errors |
  | 10 | `play stop` + `test --mode edit` | ✅ 3 passed, 0 failed (2.4s) |
- **핵심 학습 3건** (다음 세션 진입 캡슐):
  1. **Editor focus가 IPC Bootstrap 활성화 필수 조건**. `nohup Unity -projectPath ...` 만으로는 IPC pipe 안 뜸. 반드시 `osascript -e 'tell application "Unity" to activate'` 또는 사용자가 직접 Editor 클릭. doctor 메시지 "Editor not focused"가 진짜 단서.
  2. **`exec --code` void method 호출 OK** — 이전 entry의 "void method 거부" 노트는 부정확. `URHYNIX.ControlRoom.App.ControlRoomEvents.RaiseScenarioTriggered("fire")`처럼 직접 호출 가능 (result: null 반환). Roslyn evaluator가 expression-statement 허용.
  3. **`unityctl` plain 출력 Spectre 'Busy' style 버그** — Editor Busy 상태(Play 진입 직후 등)에서 plain CLI 출력이 `StyleParser` exception. **`--json` 옵션 권장** (모든 명령 지원). 그러면 안정적.
- **부수 사실**:
  - Scene 재생성 시 Play 모드면 `EditorSceneManager.NewScene` InvalidOperationException. **반드시 `play stop` 선행**.
  - `vendor/unityctl-plugin/` git 추적 대상 (5MB, `vendor/CLAUDE.md`에 갱신 절차 박음). `.git` 제외해서 read-only 스냅샷 보관.
  - Plugin 컴파일 warning ~30개 (Unity 6.3에서 deprecated API). 동작 무관, 0.2.0 → 신규 버전 시 정리 가능.
- **다음 진입**: 풀 자동화 가능. Phase 3(데이터 모델/Registry 확장) 또는 박물관 시연 7체크리스트 GUI 1차 검증으로 진행.

### unityctl IPC 자동화 도구 도입 + 통합 테스트 10단계 부분 PASS (5/10 PASS, 5 후속 보강)

- **결정**: Unity Editor를 IPC로 원격 조작하는 `unityctl` 0.2.0(`Jason-hub-star/unityctl`, dotnet tool)을 자동 테스트 워크플로의 표준 도구로 채택. ControlRoom 프로젝트에 brigde plugin 설치.
- **설치 절차** (재현 가능):
  1. `dotnet tool install -g unityctl unityctl-mcp` (이미 설치됨)
  2. `git clone --depth 1 https://github.com/Jason-hub-star/unityctl.git /tmp/unityctl-repo`
  3. `unityctl init --project unity/ControlRoom --source /tmp/unityctl-repo/src/Unityctl.Plugin` → `manifest.json`에 `com.unityctl.bridge`(file: 경로) 박힘
  4. `ProjectSettings/UnityctlSettings.asset` 박음: `{"Enabled": true, "InstallSourceKind": "local", "InstalledVersion": "0.2.0"}` — **plugin Bootstrap이 이 파일 + Enabled=true 확인 후에만 IPC server 시작**
  5. Editor 재시작 → `Library/ScriptAssemblies/UnityctlBridge.dll` 생성 + IPC named pipe(`unityctl_4147f01858f6edf8`) 활성
- **10단계 시퀀스 결과** (`/tmp/urhynix-test-suite.sh`):
  | Step | 명령 | 결과 |
  |---|---|---|
  | 1 | `ping` | ✅ PASS (즉시 통과) |
  | 2 | `check --type compile` | ✅ PASS — 31 assemblies, scriptCompilationFailed: false |
  | 3 | `test --mode edit` | ❌ FAIL (504, "Test run failed before execution") |
  | 4 | `scene open ControlRoomMain.unity` | ❌ FAIL (500, log에 scene-open error 기록) |
  | 5 | `play start` | ✅ PASS ("Already in play mode") |
  | 6 | `screenshot capture --view game` | ❌ FAIL (502, "No camera found in the scene") |
  | 7 | `exec --code "RaiseScenarioTriggered(\"fire\");"` × 4 | ❌ FAIL (502, syntax — void method statement 미허용) |
  | 8 | `screenshot capture --view game` | ❌ FAIL (502, 동일) |
  | 9 | `log --last 100` | ✅ PASS — 100 entry 수집 |
  | 10 | `play stop` | ✅ PASS — isPlaying: false |
- **밝혀진 문제 4건과 해결 방향**:
  1. **Scene에 Camera 없음** — `Assets/Editor/ControlRoomSceneSetup.cs`가 `NewSceneSetup.EmptyScene`으로 생성해서 MainCamera + Directional Light 자동 추가 안 됨. UI Toolkit만 쓰면 카메라 불필요하지만 Game View 캡처에 필수. 후속: `NewSceneSetup.DefaultGameObjects` 모드로 바꾸거나 `gameobject create Camera` 추가.
  2. **`exec --code` syntax 제약** — expression 평가 모드라 `Type.Method(args);` statement 거부. 안내 메시지: "For structured calls, prefer `exec invoke`". 그러나 `unityctl --help`에 `exec invoke` 미노출 (0.2.0). 후속: `batch execute --file <C#>` 또는 PlayMode test로 시나리오 트리거 자동화.
  3. **`scene open` 500** — 자세 에러 메시지 없음. ControlRoomMain.unity 자체 OK여도 Editor 상태 또는 plugin 호환성 문제 가능. 후속: 재현 + Editor.log 상세 디버그.
  4. **`test --mode edit` 504** — Test Runner 시작 단계 에러. NUnit asmdef 호환성 또는 unityctl test 호출 방식. 후속: smoke test EditMode 직접 Test Runner 윈도우로 검증.
- **PASS 확보된 baseline**: 컴파일 31 assembly 검증 + Play 모드 진입/종료 + IPC log 100 entry 수집. 즉 Unity Editor를 CLI에서 무대조작 가능한 기초 라인은 살아있음.
- **부수 산출물**:
  - `Assets/Tests/EditMode/URHYNIX.ControlRoom.Tests.EditMode.asmdef` + `SmokeTests.cs` (NUnit Math/String/Float 3 테스트)
  - `Packages/manifest.json` 변경: `"com.unityctl.bridge": "file:/tmp/unityctl-repo/src/Unityctl.Plugin"` 추가 — **주의**: `/tmp/` 휘발성, macOS reboot 시 plugin source 손실 risk. 영구 위치 (`~/.unityctl/plugin/` 또는 vendor commit)로 이전 필요.
  - `/tmp/urhynix-test-suite.sh` 시퀀스 script (재실행 가능)
  - `/tmp/urhynix-test-suite/*.json` 10개 결과 파일

### Unity ControlRoom UI Toolkit skeleton PASS (Phase 2 완료, 19 산출물, batch 컴파일+Scene 생성 검증)

- **결정**: HTML 관제(`robot_control_system.html`) → Unity UI Toolkit 전환의 첫 phase(UI skeleton + fake data) 완료. 박물관 시연 6패널이 Play 모드에서 살아 움직임.
- **레이아웃 A 채택**: 상단바 + 좌 230px(시나리오/모드/순회/특수) + 중앙flex(맵 + 카메라+로그) + 우 240px(배터리/센서/하드웨어). HTML 직접 이식 톤.
- **색상 톤**: 박물관 고품격 밝은 슬레이트 (`#f1f5f9` bg / `#1e293b` text / `#2563eb` accent / `#10b981` ok / `#dc2626` danger / `#f59e0b` warn). USS 변수 10개 SSOT(`ControlRoomTokens.uss`) + C# 상수 1:1(`Design/UiTokens.cs`).
- **만든 파일 19개**:
  - App 3: `ControlRoomApp.cs`, `ControlRoomState.cs`, `ControlRoomEvents.cs`
  - Design 2: `UiTokens.cs`, `IconNames.cs`
  - Data 1: `RobotInfo.cs`
  - Simulation 2: `FakeSensorData.cs`(Perlin/Sin 1.5Hz), `DemoScenarioService.cs`(4 시나리오 트리거)
  - UI Markup 8: `ControlRoomMain.uxml` + Style/Tokens.uss + Parts 5개(TopBar/LeftControl/Map/CameraAndLog/RightStatus)
  - UI Views 7: `ControlRoomBinder.cs` + 7 View(TopBar/Scenario/Map/Camera/Log/Telemetry/AlertPopup)
  - Editor 1: `ControlRoomSceneSetup.cs` (batch Scene 자동 조립)
  - Config 1: `Resources/RobotConfig/default_robots.json` (티원/젠지 메타)
  - Scene 1: `Scenes/ControlRoomMain.unity` + `UI/ControlRoomPanelSettings.asset` (1920×1080 reference)
  - 추가 stub: `Database/SupabaseClient.cs` (PoseLogRepository 의존 해소, Phase 7에서 실 구현)
- **검증**: Unity 6000.3.16f1 batch 2회 (1차 컴파일 에러 2건 → Binder.camera 변수명 + SupabaseClient stub → 2차 PASS). `Assembly-CSharp.dll` 컴파일 PASS, error CS 0건, Scene 저장 PASS, `Exiting batchmode successfully` exit 0.
- **2D/3D 토글 처리**: `MapPanel.uxml`에 2D/3D 버튼 활성, 3D 클릭 시 placeholder + "Phase 6 예정 (URDF Importer)" 라벨. ControlRoomState.MapViewMode 상태 + OnMapViewModeChanged 이벤트.
- **fake data 흐름**: FakeSensorData 1.5Hz tick → ControlRoomEvents 발화 → TelemetryPanelView가 현재 선택 로봇 값만 표시. 배터리 87% ±3% Perlin, 가스/소음 sin, 조도 sin.
- **시나리오 흐름**: ScenarioPanelView 버튼 클릭 → ControlRoomEvents.RaiseScenarioTriggered → DemoScenarioService 수신 → 로그 + 위험 경보 발화 → AlertPopupView 모달 + TopBarView 경보 카운트 증가.
- **다음 진입**: Unity Hub에서 `unity/ControlRoom` Open → `Assets/Scenes/ControlRoomMain.unity` 더블클릭 → Play 모드 → 7 체크리스트 검증 (TopBar 시계, 시나리오 버튼 클릭, 2D/3D 토글, 배터리 변동, 센서 카드 갱신, 로그 자동 스크롤, AlertPopup 모달).
- **남은 단계 (다음 phase)**: Phase 3 데이터 모델/Registry 확장(default_features/sensors/office_base_map.json) → Phase 5 ROS 실제 연결(`CameraPanelView` unity-smoke 재이식) → Phase 6 URDF 3D → Phase 7 Supabase 실 통합.

### `pose_logs` 테이블 Supabase 적용 완료 (CLI `db query --linked`)

- **결정**: `scripts/sql/pose_logs.sql`을 Supabase 프로젝트 `ueupkrxwybuuqxflstvg`에 적용.
- **적용 명령**: `supabase link --project-ref ueupkrxwybuuqxflstvg` → `supabase db query --linked --file scripts/sql/pose_logs.sql --agent=yes` (CLI v2.84.2, env에 박힌 `SUPABASE_ACCESS_TOKEN` + `SUPABASE_PROJECT_REF` 사용).
- **검증** (모두 PASS):
  - 컬럼 9개 — id/session_id/robot_id/ts/x/y/theta/source_topic/nav_mode, NOT NULL/NULL 정합.
  - 인덱스 3개 — `pose_logs_pkey`, `idx_pose_logs_session_robot`, `idx_pose_logs_mode`.
  - RLS 정책 2개 — `anon_insert_pose` (INSERT, anon), `anon_select_pose` (SELECT, anon). UPDATE/DELETE 기본 거부 유지.
  - `select count(*) from public.pose_logs` → 0 rows (정상 빈 상태).
- **부수 효과**: `supabase/.temp/` CLI 캐시 폴더 생성 → 루트 `.gitignore`에 `supabase/.temp/`, `supabase/.branches/` 추가.
- **SCHEMA.md 갱신**: "Current Applied Entities" 섹션에 적용 사실 박음. "Planned Extensions" 표는 참고용으로 유지(컬럼 동일, ✅ 마킹).
- **scripts/sql/CLAUDE.md 갱신**: `pose_logs.sql` 상태 `미실행` → `✅ 2026-06-02 적용 완료`.
- **다음 진입**: 로봇 PC(`scripts/pose_logger.py`)에 `URHYNIX_ROBOT_ID` + `URHYNIX_SESSION_ID` + `SUPABASE_ANON_KEY` env 박고 systemd로 띄우면 실기기 좌표 자동 INSERT 시작.

### 로봇 현재 위치 저장 기능 부품 박음 (`pose_logs` 첫 부품 + Unity/Python/SQL 3측)

- **결정**: SSOT 핵심 목표 "이동 좌표·사진·영상·사운드와 모든 결과가 DB에 기록된다" 중 **이동 좌표** 부품을 폴더 구조에 반영. SCHEMA.md의 SCRUM-23 Planned Extension `pose_logs`를 실 코드 진입점까지 연결.
- **저장 경로**: 로봇 PC가 주 쓰기, Unity는 read 우선. service_role 키 절대 미반입(anon + RLS).
- **추가된 파일**:
  - `unity/ControlRoom/Assets/Scripts/Data/RobotPoseEntry.cs` — pose 1행 POCO, SCHEMA.md 컬럼 1:1.
  - `unity/ControlRoom/Assets/Scripts/Database/PoseLogRepository.cs` — read 우선 + 보조 INSERT 골격(Phase 7 구현).
  - `scripts/pose_logger.py` — 로봇 PC가 `/tb3_*/pose` 구독 → Supabase `pose_logs` INSERT (ROS2 + supabase-py + UTC ISO ts + quaternion→yaw 변환).
  - `scripts/sql/pose_logs.sql` — 테이블 + 인덱스 2종 + RLS 정책 3종(anon INSERT/SELECT, UPDATE/DELETE 기본 거부) migration.
  - `scripts/sql/CLAUDE.md` — migration SQL 운영 규칙 (실행 경로 3종, 검증 흐름, 명명 규칙, 보안).
- **CLAUDE.md 갱신**: `Assets/Scripts/Data/`, `Assets/Scripts/Database/` 두 곳 예정 파일 표에 ✅ 마킹.
- **다음 단계 (적용 전 결정)**:
  - `pose_logs.sql`을 실제 Supabase에 실행할 시점 — 시연 직전 또는 Phase 7 진입 시.
  - 적용 후 `SCHEMA.md` "Planned Extensions" → "Current Applied" 이전.
  - 환경변수 `URHYNIX_ROBOT_ID`, `URHYNIX_SESSION_ID`, `SUPABASE_ANON_KEY`를 `/etc/urhynix.env`에 박는 절차.

### Unity ControlRoom 첫 batch import PASS (Library + .meta 자동 생성)

- **결정**: `unity/ControlRoom/` 프로젝트가 Unity 6000.3.16f1로 첫 batch import 성공. Unity Hub의 Add Project 절차 없이 바로 Open 가능 상태.
- **검증**: `Unity.app -batchmode -quit -nographics -projectPath unity/ControlRoom -logFile /tmp/unity-controlroom-first-open.log` exit code 0 + `Exiting batchmode successfully now!`. License 채널 정상 활성, 어셈블리 에러 0건.
- **산출물**:
  - `Library/` 12개 하위 생성 (BuildInstructions/PackageCache/ScriptAssemblies/ShaderCache/Bee 등)
  - `Assets/**/.meta` 83개 자동 생성 (CLAUDE.md.meta 24개, PNG.meta 26개 포함)
  - `ProjectSettings/ProjectVersion.txt`에 Unity revision hash `a56f230f6470` 자동 박힘
  - Tests 폴더 추가: `Assets/Tests/{EditMode, PlayMode}/` + `CLAUDE.md` (Opus 자기리뷰 caveat #1 해결)
- **무시한 warning**: `Access token is unavailable` (Unity Cloud Analytics 미인증, Personal 사용에 무관), `Curl error 42` (Telemetry 호출 중단, 무관), License 첫 채널 handshake 실패 후 재시도로 success (정상 패턴).
- **다음 진입**: Unity Hub에서 `unity/ControlRoom` Open (Add Project 불필요 — 이미 등록됨). 첫 Open 시 Library 재생성 없이 즉시 열림.

### Unity ControlRoom 신규 프로젝트 분리 + Unity 6.3 LTS (6000.3.16f1) 채택

- **결정**: HTML 관제(`robot_control_system.html` 2727줄)를 Unity C# 관제로 전환하기 위해 **`unity/ControlRoom/`** 신규 Unity 프로젝트를 만들고 **Unity 6.3 LTS (6000.3.16f1)**를 사용한다.
- **버전 선택 근거**:
  - Unity 6.3 LTS는 2025-12 출시, **2027-12까지 지원** (Unity 6.0 LTS는 2026-10 EOL).
  - 박물관 시연 이후에도 장기 안정. unity-smoke(6000.0.64f1)는 카메라 검증용 자료실로 보존.
  - URDF Importer는 Unity 6 계열에서 호환성 미검증이라 Phase 6 진입 전 별도 smoke 필요 — fallback: community fork(gkjohnson urdf-loaders) 또는 사전 변환된 prefab.
- **폴더 구조**: `URHYNIX/unity/ControlRoom/` (Unity 프로젝트 루트). 기존 `unity-smoke/`(카메라 검증 PASS, 자료실로 보존), `unity-src/`(PNG 시트만 채워진 빈 껍데기, Art는 신규로 이관)는 그대로 둔다.
- **scaffold 완료**: ProjectSettings = unity-smoke 복사, manifest.json = ROS-TCP-Connector v0.7.0 + Universal RP 17.0.4 + UI Toolkit (`com.unity.modules.uielements`) 베이스, ProjectVersion.txt = `6000.3.16f1`, .gitignore = Unity 표준 + Supabase 키 차단, PNG 26개 이관(`Assets/Art/IconsPng/`).
- **다음 진입**: 주인님이 Unity Hub에서 **6000.3.16f1 설치 → Add Project → `unity/ControlRoom` 선택** → 첫 Open 시 Library/ 자동 재생성(5~10분) → URDF Importer smoke 1건 결정.

### Supabase 연동 URL + write path 정책 확정

- **결정**: Unity ControlRoom의 Supabase 진입점을 **`https://ueupkrxwybuuqxflstvg.supabase.co`** 로 박는다.
- **write path 정책 (시뮬은 최대한 실기기 기반)**:
  - 로봇 PC(젠지/티원 Python ROS2 노드) = **주 쓰기 주체**. anon key + RLS 정책으로 events/dispatches/pose_logs INSERT.
  - Unity ControlRoom = **read + 제한 INSERT만**. `dispatches`(출동 명령), `session_meta` 등 사람 액션만 쓰기. service_role 키 **절대 미반입**.
  - 민감 작업(전원 종료, RLS 우회) = Supabase **Edge Function** 호출만.
- **키 보관**: anon key는 `Assets/Resources/SupabaseConfig.local.asset` (`.gitignore` 차단). template 파일 `SupabaseConfig.template.asset`만 커밋.
- **SDK**: `supabase-csharp` + `kamyker/supabase-unity` git URL (또는 NuGetForUnity), UniTask 필수.
- **dual naming**: DB `robot_id`는 `tb3_1`/`tb3_2` 그대로. 사람 UI 표기는 티원/젠지 별명.

### ROS_DOMAIN_ID 230 통일 (티원 기준에 젠지 맞춤)

- **결정**: 두 로봇의 `ROS_DOMAIN_ID`를 **230**으로 통일한다.
- **배경**: 티원(`t1@192.168.0.250`)이 이미 230으로 작동 중. 젠지(`urhynix-robot`)는 신규 SD 부트스트랩 시 30으로 초기화돼있어 같은 도메인이 아니면 두 로봇 토픽이 서로 안 보임 → 박물관 시연 시 dispatcher/협업 불가.
- **드리프트 발견**: SSOT에서 56(정본 설계 CONTRACT.md), 30(신규 SD HANDOFF/evidence), 230(티원 실제) 3개 값이 섞여있었음. 230으로 일괄 통일.
- **변경 작업**:
  - 젠지 `~/.bashrc`: `export ROS_DOMAIN_ID=30` → `export ROS_DOMAIN_ID=230` (`sed` 1줄)
  - 검증: `ssh urhynix-robot 'source ~/.bashrc && echo $ROS_DOMAIN_ID'` → `230` ✅
  - 백업 파일: `~/.bashrc.bak-YYYYMMDD-HHMMSS` 자동 생성
- **SSOT 정정 (5파일)**:
  - `docs/ref/CONTRACT.md` 정본 설계 (56 → 230) + 2026-06-02 정정 사유 박음
  - `docs/status/HANDOFF.md` 환경 자동 source 라인 (30 → 230)
  - `docs/status/DECISION-LOG.md` 신규 SD 부트스트랩 결정 본문 (30 → 230)
  - `docs/evidence/2026-06-01-new-sd-128gb-ros2-jazzy-bootstrap.md` 부트스트랩 표 (30 → 230)
  - `docs/instructor-report/index.html` 발표 자료 (56 → 230)
- **건드리지 않음**: 이전 evidence (`2026-05-27-live-turtlebot...`, `2026-05-29-mac-docker-slam...`, `maps/desk_static_v1/eval.md`) — 16GB SD 시점 역사 기록. `MAC-DOCKER-ROS2-PLAYBOOK.md` 5곳 — Mac Docker 트랙은 5/29에 부적합 결론났으므로 deprecated, 별도 정리 시 일괄 변경.
- **230 안전 범위 caveat**: ROS2 공식 0~232 안에 있지만 Linux 권장 0~101 (multicast port 7400 + 250*domain_id가 system reserved 영역과 가까움). 동료가 이미 230으로 작동 검증했고 codelab_5G WiFi에서 충돌 없으니 박물관 시연 한정으로 사용. 후속 프로젝트는 0~101 권장.
- **다음 검증** (다음 세션 또는 두 로봇 동시 켤 때):
  - 양쪽 `ros2 topic list`에서 `/tb3_1/...` + `/tb3_2/...` 모두 보이는지
  - Unity ROS-TCP-Endpoint도 같은 도메인 환경 확인 (TCP 자체는 도메인 무관이지만 robot 내부 ros_tcp_endpoint 노드는 도메인 영향 받음)

### 로봇 작명 + 호스트 매핑 확정 (티원 / 젠지)

- **결정**: 두 로봇에 e스포츠 팀 별명을 부여한다. ROS namespace는 `tb3_1`/`tb3_2` 그대로 유지하고, 사람 문서/UI/회의록에서 별명을 사용한다 (dual naming).
- **매핑**:
  - **tb3_1 = 티원** (비전 중심) — 카메라: **Intel RealSense D435** (3층 정면 부착) — 호스트: **`t1@192.168.0.250`** (hostname `rb`) — 사용자명 `t1` = 티원 일치
  - **tb3_2 = 젠지** (센서 중심) — 카메라: **Raspberry Pi Camera Module v2 (Sony IMX219, 8MP)** + Arduino 4종 (PIR/LDR/소리/불꽃) — 호스트: **`urhynix-robot`** (kim@192.168.0.82)
- **근거**: 2026-06-01 회의(Confluence 5111810)에서 "로봇1=비전, 로봇2=센서" 분담 결정. 회의 결정 + 사용자명 + 작업 영역 매핑이 모두 일치(D435는 t1@.250에서, IMX219는 urhynix-robot에서 검증됨).
- **dual naming 원칙**:
  - ROS topic: `/tb3_1/...`, `/tb3_2/...` 영문 + 표준 (한글 unicode 토픽 미사용)
  - DB `robot_id`: `tb3_1`, `tb3_2`
  - 사람 문서/Unity UI/회의록/PR 제목: **티원** / **젠지** 별명 사용 권장
  - 양쪽 표기 모두 SSOT에 명시
- **SSOT 반영 위치**: `docs/ref/ARCHITECTURE.md` (듀얼 로봇 역할 + 외부 시스템 표), `docs/ref/PROJECT-PLAN.md` (2대 로봇 역할 분리), `docs/status/PROJECT-STATUS.md` (한 줄 상태), `docs/status/HANDOFF.md` (Last updated).
- **잔여 액션**:
  - JIRA-MAP의 SCRUM-19/25 본문에 카메라 매핑 정확화 (`/tb3_1/camera/*` D435 vs `/tb3_2/camera/*` IMX219)
  - Unity 패널의 로봇 전환 토글 라벨을 "티원/젠지"로
  - 다음 회의에서 카메라 부착 이전 일정 확정 (D435가 어제 임시 검증 머신 = t1@.250 그대로 영구라면 이전 불필요. 다른 머신이면 이전 일정 잡기)
- **영향 없음**: ROS namespace `tb3_1`/`tb3_2`는 그대로라 코드/Unity/DB 변경 없음. 사람 표기만 별명 추가.

## 2026-06-01

### RealSense D435 Windows streaming PASS (pyrealsense2) 추가 확인

- **검증 결과**: Windows workstation에서 RealSense D435가 OS 장치 인식뿐 아니라 `pyrealsense2` RGB-D streaming pipeline까지 PASS. RGB/Depth 장치가 Windows PnP에서 `OK`로 보였고, Python pipeline에서 depth/color `640x480` frame 수신을 확인했다.
- **장치 정보**: `Intel RealSense D435`, Serial `254522075185`, Product ID `0B07`, Firmware `5.17.0.10`.
- **프레임 결과**: `depth 640x480`, `color 640x480`, center depth sample `0.159 m`.
- **해석**: 기존 Mac evidence의 streaming BLOCKED 결론은 macOS Tahoe + Homebrew librealsense 조합에 한정한다. 카메라 하드웨어 자체와 Windows SDK 경로는 정상이다.
- **프로젝트 결정 유지**: 실제 로봇/ROS2 통합은 Pi4 + `realsense2_camera` 경로를 계속 우선한다. Windows는 빠른 RGB-D bench test host로 사용할 수 있다.
- **근거 evidence**: `docs/evidence/2026-06-01-realsense-d435-windows-pyrealsense2-smoke.md`

### Pi Camera 모델 확정 (Module v2 / Sony IMX219) + Ubuntu 24.04 ports repo 미제공 → 소스 빌드 결정

- 변경 목적: 2026-06-01 SCRUM 회의록(Confluence page `5111810`)의 역할 분담/부착 계획을 SSOT에 명시한다.
- **모델 확정**: 신규 128GB SD 부트스트랩 후 첫 진단에서 Raspberry Pi Camera Module v2 (Sony IMX219, 8MP, 3280×2464 최대 해상도) 확정. 근거: `lsmod`에 `imx219` 로드, `i2c-10` address `0x10` 응답, `/dev/video0` = `unicam-image` (CSI MMIO `fe801000.csi`).
- **하드웨어 상태**: 100% 정상 (CSI controller + `bcm2835_unicam` + `bcm2835_isp` + `bcm2835_codec` 전부 로드). 케이블/sensor 응답 정상.
- **차단 원인**: Ubuntu 24.04 LTS for Raspberry Pi ports repo는 `rpicam-apps`/`libcamera-apps` **미제공**. `apt install` 시 "패키지를 찾을 수 없습니다". Ubuntu는 upstream libcamera만 포함하고 Pi ISP/IPA는 Raspberry Pi fork에만 존재.
- **결정**: libcamera Pi fork(`github.com/raspberrypi/libcamera`) + rpicam-apps(`github.com/raspberrypi/rpicam-apps`) **소스 빌드 진행** (30~60분, Pi4 풀로드). 한 번 빌드 후 영구 사용. W2 진입 전 박물관 시연 풀 기능 확보.
- **HANDOFF 잔여 액션 #4 갱신**: 기존 "Pi 카메라 동작 검증 3분"에서 "Module v2 (IMX219) user-space 풀 빌드 30~60분"으로 정정. 검증 자체는 이미 통과 (하드웨어 정상).
- **외부 근거**:
  - [rpicam-apps#388 — Libcamera-apps not available for Ubuntu](https://github.com/raspberrypi/rpicam-apps/issues/388)
  - [Sepideh Shamsizadeh — IMX219 on Ubuntu 24.04 LTS 가이드](https://medium.com/@sepideh.92sh/setup-and-troubleshooting-of-raspberry-pi-camera-module-v2-1-imx219-on-ubuntu-24-04-lts-fb518f4576c0)
  - [Hackaday — Bringing Up IMX219 on Pi 5 with Ubuntu 24.04](https://hackaday.io/project/203704-gesturebot/log/242459)
- **D435와의 역할 분담**: IMX219 = 일반 RGB 영상(라이브 스트림 + YOLO 4종 인식 + 녹화 MP4/rosbag). D435 = Depth + RGB(3D 매핑, 가벽 detection). 박물관 시연에서 **두 카메라 동시 사용**.
- **빌드 완료 (16:36)**: libcamera Pi fork v0.7.1+rpt20260429 + rpicam-apps v1.12.0 6분만에 빌드 PASS. capabilities `egl:1 qt:1 drm:1 libav:0`. 캡처 검증도 통과: `rpicam-still` 1920×1080 JPG 283KB + `rpicam-vid` 1280×720@30Hz × 5초 H.264 2.9MB.
- **잡은 함정 3건** (Ubuntu 24.04 특이): ① ports repo에 rpicam-apps 없음 → 소스 빌드. ② `libepoxy-dev` deps 누락 (preview/meson.build:32) → apt 추가. ③ libavcodec 60.31.x가 rpicam-apps master 요구 API보다 오래됨 → `-Denable_libav=disabled` 우회 (mp4 인코딩은 별도 ffmpeg).
- **재사용 가능 스크립트**: `scripts/build-picamera.sh` — sudo keeper 50s + setsid + 함정 3건 모두 반영. 다음 SD 또는 협업자 머신에서 한 줄(`nohup bash build-picamera.sh > picam-build.log 2>&1 &`)로 30~60분 안에 동일 빌드 가능.
- **근거 evidence**: `docs/evidence/2026-06-01-rpi-camera-imx219-source-build.md` (산출물: JPG 283KB + H.264 2.8MB 동봉)

### 로봇 1/2 역할 분리 + 카메라/센서 부착 계획 (회의록 기반, 계획/진행 중)

- 변경 목적: 2026-06-01 회의록에서 합의된 2대 로봇 역할 분리를 SSOT에 고정한다.
- **운영 모델(초안)**:
  - `tb3_1`(로봇 1) = **비전 중심**: RealSense `D435`를 전면(3층 정면) 부착해 RGB-D 기반 인식/매핑을 담당.
  - `tb3_2`(로봇 2) = **센서/확인 중심**: Arduino 센서 스택 + Pi Camera(IMX219) 부착로 이벤트/확인(영상) 담당.
- **상태**: 부착은 “예정/진행 중”. 실제 장착 완료/ROS 토픽 레벨 검증은 evidence로 별도 업데이트 필요.

### Unity 관제 UI v1 상호작용/버튼 요구사항 (회의록 기반, 계획/정의 중)

- 변경 목적: 2026-06-01 회의록의 UI 기능 정의를 “현재 구현”이 아니라 “정의/계획”으로 분리 기록한다.
- **결정/정의(요약)**:
  - 맵 클릭 상호작용: 우클릭=좌표 생성/삭제, 좌클릭=화면 스크롤(좌우).
  - 좌표 상태/속성: 충전 위치/특정 좌표/이름 지정, 순회 번호 및 경로·방향 편집(모달에서 드래그앤드랍 순서 조정).
  - 차단 지역: 자유 변형 가능한 영역 스케치.
  - 모드: 수동(teleop) / 자동(순회 시작, 확인 팝업), 스캔 모드(좌표마다 360° 1회전), 가속 모드(속도 프리셋).
  - 로봇 상태 패널: 배터리 + (가스/소리/화재/조도 등) 센서 수치 표시.
  - UI 정리: “화재 발생 이미지 매칭 UI”는 삭제하고 “조도 센서 상태”를 우선 추가, 위험 상태 시 알람 팝업.

### RealSense 카메라 모델 D435 확정 (D435i 아님) + Mac SDK streaming 차단 → Pi4 이전 결정

- **모델 확정**: 주인님 손에 있는 카메라는 `Intel RealSense D435` (Product ID `0B07`, Serial `254522075185`, Asic Serial `350423023342`, FW `5.15.1.55`). `Imu Type: IMU_Unknown` 으로 D435i가 아닌 D435 확정. 그동안 SSOT의 "D435i 도입 후보" 표기는 모두 D435로 정정 대상.
- **Mac 검증 결과**: `sudo /opt/homebrew/bin/rs-enumerate-devices` verbose는 PASS (Depth/RGB/IR 모든 stream profile 노출). 그러나 `rs-hello-realsense`에서 `Frame didn't arrive within 15000` + `Dispatcher: mutex lock failed: Invalid argument` 로 실제 streaming은 차단.
- **차단 원인 (3중 호환 이슈)**:
  1. macOS Monterey+ 이후 librealsense는 sudo 필수 (해결됨)
  2. brew formula 2.58.1은 `-DHWM_OVER_XU=false`, `-DFORCE_RSUSB_BACKEND=true` 빌드 옵션 누락 → 알려진 timeout 버그
  3. macOS Tahoe(26.3.1)은 librealsense 공식 미지원 + Apple Silicon adhoc 서명에 IOUSBHost entitlement 부재
- **결정**: macOS source 재빌드(1~2시간, 성공률 ~40%)는 시도하지 않는다. Pi4 이전(30분, 95%)으로 진행. **근거**: 어차피 ROS2 Jazzy는 macOS 미지원 → 박물관 매핑은 Pi4가 정답. URHYNIX 시연 흐름(카메라=Pi4 직결 → ROS topic 발행 → Unity(Mac) 구독)에서 카메라가 Mac에 꽂혀있을 일 자체가 없음.
- **박물관 매핑 계획 영향**:
  - VIO (Visual-Inertial Odometry) 폐기 → odom 보정은 LDS-03 + wheel odom으로
  - RTAB-Map RGB-D SLAM, 가벽 detection (낮은 가벽 depth로 잡기), 액자 YOLO+depth 위치 식별, Pi 카메라 자리 흡수, Unity 3D mesh import — 모두 그대로 살아있음
  - 전체 계획의 95% 유지, IMU 의존 부분만 빠짐
- **잔여 액션**:
  1. 카메라 케이블 → Pi4 USB 3.0 직결 (사람 작업, 1분)
  2. `ssh urhynix-robot` + `sudo apt install ros-jazzy-realsense2-camera` (5분)
  3. `ros2 launch realsense2_camera rs_launch.py` + 토픽 30Hz hz 검증 (5분)
- **근거 evidence**: `docs/evidence/2026-06-01-realsense-d435-mac-sdk-smoke.md` (Phase별 결과, 명령 로그, 외부 이슈 트래커 6건 인용)

## 2026-05-29

### 🎉 SLAM end-to-end 첫 검증 PASS — Robot 직접 cartographer + Unity 임포트

- 결정: SLAM은 Mac VM/Docker 우회 시도 모두 실패 후 **로봇 자체에서 cartographer 실행**하기로. multicast 모드(ROS_DISCOVERY_SERVER 미사용)로 통일.
- 산출물: `docs/evidence/maps/desk_static_v1/{.pgm, .yaml, .png, eval.md}` — 5.90m × 5.40m 책상 환경 정적 매핑. Unity Plane scale `(0.5900, 1, 0.5400)` 자동 계산.
- 검증: `/scan` 10Hz + `/map` 1.0Hz + map_saver_cli 정상 + scp + PIL pgm→png + tb3-map-to-unity 한 줄.
- 영향: 경기장 출동 시 같은 흐름 (`tb3-up → tb3-slam → tb3-teleop → tb3-slam-save → tb3-fetch-map → tb3-map-to-unity`)을 25분 주행에 적용. Mac Docker/VM은 본 사례에 불필요로 확인.

### Mac Docker로 외부 SLAM 실행 (라즈베리파이 디스크 회피)

- 결정: cartographer/nav2/map-server를 라즈베리파이가 아니라 Mac Docker 컨테이너에서 실행한다. 로봇은 bringup만 담당.
- 이유: 라즈베리파이 SD 15GB가 96%+ 사용 중이라 apt install이 dpkg hang을 일으킴. 4/4 패키지 commit은 끝났지만 ldconfig trigger가 디스크 0으로 hang. 또한 RPi 4 (4GB RAM)에서 cartographer 동시 실행 시 메모리 부담 큼.
- 영향: 
  - 호스트 종속 (Mac/Ubuntu) — 동료가 Ubuntu라면 native 가능, Mac은 Docker Desktop 4.34+ 호스트 네트워크 필요.
  - 새 자산: `docs/ref/MAC-DOCKER-ROS2-PLAYBOOK.md` + `scripts/tb3.sh`의 `tb3-docker-*` 8 helpers.
  - 이미지: `robotis/turtlebot3:jazzy-pc-latest` (5GB) — cartographer + nav2 + map-server 사전 설치.

### 라즈베리파이 dpkg hang 복구 + 워크스페이스 클린 재빌드

- 결정: dpkg hang (4/4 commit 완료 + trigger 단계 hang) 발견 후 reboot으로 회복. `~/turtlebot3_ws/install/build` 삭제 → `colcon build --symlink-install --parallel-workers 1 --executor sequential` 클린 재빌드.
- 이유: 처음 디스크 정리 시 `~/turtlebot3_ws/build`를 같이 지웠는데 그 안에 install/setup.bash hook 일부가 있어서 launch가 깨짐. sequential 빌드로 메모리 부담 최소화 (8 패키지 6분 17초).
- 영향: bringup 정상 publish (`/scan /odom /tf /battery_state` 등 13 토픽). 다음 세션부터 build/ 절대 지우지 말 것.

### macOS Docker host networking — inbound UDP 미라우팅 미해결

- 사실 확인: Docker Desktop 4.34+ host networking은 outbound는 작동(컨테이너에서 LAN ping OK)이지만 **inbound UDP가 컨테이너 프로세스로 라우팅되지 않음**. `lsof -nP -iUDP:11811` 결과 `com.docker`가 IPv6 dual-stack으로 listen하지만 Fast DDS Discovery Server에 robot 접속 메시지 0건.
- 영향: Mac 컨테이너에서 robot `/scan` topic discovery 실패. 다음 세션 디버깅 출발점: (1) Cyclone DDS XML로 strict unicast peer, (2) `osrf/ros:jazzy-desktop` 다른 base 이미지 시도, (3) 동료 Ubuntu native (multicast 정상) fallback.

### 경기장 진입 + 라이브 SLAM 사이클 검증 (arena_v1)

- 결정: 어제 책상 매핑에서 검증된 흐름(`tb3-up → tb3-slam → save → fetch → map-to-unity`)을 경기장에 그대로 적용해 1차 매핑 산출물 `arena_v1`을 생성. Mac Docker 우회는 시도조차 안 함 (어제 결정대로 robot 직접 cartographer + multicast 모드).
- 근거: `/scan` 10.04Hz + `/map` 1.000Hz 안정. 158×151 px @ 0.05 m/px = 7.90×7.55m. robot/local evidence/Unity Assets 3곳 저장 OK. SSH key 인증 무대화형 통과. ARENA-DEPLOYMENT-CHECKLIST 첫 10단계 절차 작동 검증.
- 영향: `docs/evidence/maps/arena_v1/{pgm,yaml,png,eval.md}` 신규 + `unity-smoke/Assets/Maps/arena_v1.{png,yaml}` 임포트 자동. 어제 결정 "robot 직접 cartographer가 정답"이 경기장 환경에서 재검증됨.

### DHCP IP 변경 대응 — `.138` → `.33` + Unity scene 일시 패치

- 결정: 경기장 Wi-Fi에서 robot이 DHCP로 `192.168.0.33`을 받음. `scripts/tb3.sh`의 `TB3_ROBOT_IP_HINT='192.168.0.138'`는 유지(tb3-ip가 MAC sweep으로 자동 발견). Unity 측 `unity-smoke/Assets/Scenes/SampleScene.unity:151` + `unity-smoke/Assets/Scripts/RosSmokeDashboard.cs:10`의 `rosIP`를 `.138 → .33`으로 임시 패치 + Mac `known_hosts`에서 `.138` 엔트리 정리.
- 근거: ARP MAC 매칭으로 진짜 robot IP가 `.33`으로 검증됨 (`.138`은 다른 기기가 응답해 SSH refused + host key 충돌). Unity Inspector 수동 입력은 시간 낭비라 코드/Scene 직접 수정으로 자동화.
- 영향:
  - 다음 세션 DHCP가 또 바뀌면 같은 패치 반복 필요 (Scene + Script 두 곳).
  - 잔여 결정: helper에 `tb3-unity-set-ip <ip>` 신설 후보 (Scene + Script 일괄 패치 → `tb3-ip` 결과 자동 주입). 미실행.
  - HANDOFF "Unity rosIP 매 세션 수동" 이슈에 패치 절차 추가 + git status에 두 파일 변경 잡힘 (commit 시점에 임시방편임 명시).

### 회전만 매핑의 한계 인식 + 하이브리드 패턴 표준화

- 결정: 경기장 중앙에서 회전만 5~6바퀴 매핑한 결과 가벽이 LDS-03 반경 3.5m 안에 부분적으로만 들어옴을 확인. **다음 매핑(arena_v2)부터 하이브리드 (회전 + 작은 stop & rotate 이동) 패턴을 표준**으로 한다. arena_v1은 회전만 매핑의 비교 evidence로 영구 보존.
- 근거: arena_v1 픽셀 통계 = occupied 1.9% / free 98.1% / **unknown 0.0%**. unknown 0은 회전 5바퀴라 모든 방향 관측 완료이지만 외곽이 둥글게 끊기고 가벽 연결선 없음 = 가벽 일부가 LiDAR 반경 밖. PNG 시각 검증 결과 박물관 보호 영역 시각화로는 부적합.
- 하이브리드 표준 절차 (다음 매핑 채택):
  1. 출발점에서 360° 1바퀴 (각속도 0.2 rad/s)
  2. 천천히 1m 직진 (선속 0.10 m/s)
  3. 360° 1바퀴
  4. (2)~(3) 반복 3~4 stop으로 가벽 전체 도달
  5. 출발점 복귀 후 360° 한 번 더 → 루프 클로저 강제
  6. 총 ~5분 예상
- 영향:
  - `docs/ref/ARENA-DEPLOYMENT-CHECKLIST.md` §"현장 도착 후 첫 10분" 8단계 매핑 주행을 하이브리드로 갱신 (잔여 작업).
  - HANDOFF Top 1을 "arena_v2 하이브리드 매핑 OR W2 SCRUM-10 진입" 분기 결정으로 갱신.
  - 발표 시연용 maps는 arena_v2 후보. arena_v1은 발표 자료에 "회전만의 한계" 비교 슬라이드용 활용 가능.

### 매핑 실패 진단 정정 — "회전 한계"가 아니라 "가벽 높이 < LiDAR 스캔 평면" (회의록 기반)

- 결정: 위의 "회전만 매핑의 한계" 진단을 **정정한다**. 실제 원인은 **경기장 가벽 높이가 TurtleBot3 Burger의 LDS-03 LiDAR 스캔 평면(약 192mm 지상고)보다 낮아서 LiDAR가 가벽 상단을 over-shoot한 것**. 회전 횟수·반경과는 무관.
- 근거: 2026-05-29 Confluence 회의록 (page `3932161`) 김주영 발언 직접 인용: *"png파일 얻었지만 라이다높이보다 가벽이낮아서 벽 매핑실패. 하지만 좌표값읽기 성공"*. arena_v1 픽셀 통계의 occupied 1.9% / unknown 0%는 같은 증상이지만 원인은 **평면(거리)이 아니라 수직(높이)**.
- 영향:
  - **하이브리드 매핑 권장 폐기** — 가벽 높이가 부족하면 회전을 더 해도 stop & rotate를 추가해도 해결 안 됨.
  - `arena_v1/eval.md` Verdict + Recommendation 재정정 (하이브리드 권장 제거).
  - `HANDOFF.md` Top 1 분기 재정의: "가벽 높이 측정 + 보강" 우선, 보강 후 hybrid 매핑.
  - `.claude/skills/map-quality-eval/eval.py` classify() 로직에 **수직 차원 가능성** 추가.
  - 다음 매핑 전 사람이 줄자로 가벽 실측 높이를 eval.md에 기록.
- 잠재 해법 (다음 매핑 전 결정 분기):
  - (A) 가벽을 200mm 이상으로 물리적 보강 (테이프·종이·박스)
  - (B) LiDAR를 더 낮게 마운트 (Burger 구조상 어려움, 비추천)
  - (C) 카메라 vision 기반 가벽 인식으로 보완 (임현찬 YOLO 라인 활용)
  - (D) 가벽을 obstacle이 아닌 **"보호 영역 경계 마커"**로 정의 변경 (Unity 디지털 트윈 + DB 좌표만 사용, Nav2 cost map 미반영)
- 잠금: arena_v1의 **"좌표값 읽기 성공"**(odom·TF·map 좌표 1:1)은 그대로 유효. 시각 텍스처용 PNG만 한계.

### Pi 카메라 토픽 검증 + YOLO/OpenCV 환경 통과 + MVP 4 클래스 잠금 (임현찬)

- 결정: Raspberry Pi 카메라 ROS 토픽 3종(`/camera/image_raw`, `/camera/camera_info`, `/camera/image_raw/compressed`)을 30Hz 정상 publish로 검증 완료. MP4 + ROS bag 동시 녹화 스크립트(`/home/pi/camera_recordings/scripts/record_bag_mp4.sh`)를 표준 녹화 도구로 채택. 노트북 Ubuntu에 YOLO/OpenCV 환경 + `yolo11n.pt` 기본 모델 + 실시간 카메라 스트림 인식 통과. **MVP 학습 클래스 4종 잠금: 로봇 · 사람 · 중요품 · 불**.
- 근거: 2026-05-29 Confluence 회의록 (page `3932161`) 임현찬 진척 보고 직접 인용.
- 영향:
  - `docs/ref/PRD.md` 카메라 인식 범위에 4 클래스 명시.
  - `docs/ref/ARCHITECTURE.md` Vision 파이프라인에 MP4/bag 분리 (MP4 = 즉시 확인, bag = 재처리) 추가.
  - `docs/ref/CONTRACT.md`에 카메라 토픽 3종 + 30Hz 명시.
  - `docs/ref/JIRA-MAP.md` SCRUM-19/20에 진척 반영.
  - 다음 작업: 자체 데이터셋 촬영 + 라벨링 + 커스텀 YOLO 학습 (W2 후반).
- 잠금: 기본 `yolo11n.pt`로는 박물관 도메인(액자·중요품) 인식 한계 — 발표 시연 전에 커스텀 학습 필수.

## 2026-05-26

### 로봇팔 제거 버전으로 MVP 진행

- 결정: FR5 로봇팔, 픽앤플레이스, 장애물 물리 제거는 이번 버전에서 제외한다.
- 이유: 7~8주 일정 안에서는 TurtleBot3 자율주행, Unity 관제, 카메라 인식, DB 기록에 집중하는 편이 성공 가능성이 높다.
- 영향: 발표 주제는 협동로봇 전체 시스템보다 "Unity Digital Twin 기반 자율주행 장애물 인식 관제"에 가까워진다.

### 카메라가 있는 상태 기준으로 작업 재분리

- 결정: 카메라가 있다고 가정하고 Jira에 카메라 설치, ROS pose 동기화, 데이터셋, 실시간 인식, Unity 표시, DB 저장, QA 카드를 추가한다.
- 이유: 카메라가 있는 경우 Vision 작업이 단순 샘플 이미지 테스트보다 훨씬 커진다.
- 영향: 김선일, 임현찬, 김주영, 박태진 모두에게 카메라 관련 작업이 나뉘었다.

### Unity는 관제와 시각화 중심

- 결정: 실제 로봇 안전 판단과 주행 제어의 진실값은 ROS/TurtleBot3 쪽에 둔다.
- 이유: Unity는 시각화와 관제 UI에는 강하지만, 실제 로봇 제어의 안전 기준으로 삼기에는 위험하다.
- 영향: Unity는 map, pose, path, camera result, DB summary를 보여주는 역할을 맡는다.

## 2026-05-27

### 단일 TurtleBot 비교 데모 → 다중 경비 로봇 디지털 트윈 전환

- 결정: 발표 시나리오를 "LiDAR only vs Camera+Vision 비교 데모"에서 "다중 TurtleBot 디지털 트윈 경비 로봇 (tb3_1 순찰/감지 + tb3_2 출동/확인)"로 전면 전환한다.
- 근거: Confluence 1540099 "브레인스토밍: 다중 경비 로봇 디지털 트윈 마인드맵" (2026-05-27)에서 팀 합의. 기존 비교 데모는 발표 임팩트와 데이터셋 가치가 떨어진다는 판단.
- 영향:
  - SSOT 8종(`PRD`, `PROJECT-PLAN`, `PROJECT-STATUS`, `ARCHITECTURE`, `CONTRACT`, `SCHEMA`, `JIRA-MAP`, `STACK-PROFILES`) 전면 재작성.
  - 토픽 네임스페이스: `/turtlebot/*` → `/tb3_1/*`, `/tb3_2/*`, `/security/*`.
  - DB 테이블 재정의: `drive_log`/`detection_log` → `events`/`dispatches`/`camera_captures`/`session_meta`.
  - Jira SCRUM-8~25 티켓 제목·담당자·Sprint 재배치 (ID 유지).
- 새 역할 매트릭스 (5 모듈 × 4명):
  - 백엔드 DB / ROS-TCP 라벨링 / AI: 김주영, 김선일
  - 아두이노 (메인 보드/통신): 박태진, 임현찬, 김주영
  - 유니티 관제UI · ROS-TCP 통신 · 영상 라이브 스트리밍: 김선일, 박태진
  - 아두이노 센서: 김주영, 임현찬, 박태진
  - 터틀봇 LiDAR · 카메라 · SLAM · 네비게이션: 임현찬, 김선일
- 보존: ARCHITECTURE의 "ROS=진실값, Unity=시각화" 원칙은 유지. `GIT-WORKFLOW.md`, `DECISION-LOG.md` 양식 유지.
- 발표 한 줄(MVP): tb3_1이 야간 순찰 중 센서 이벤트를 감지하면 Unity 관제 화면에 위치·이벤트가 표시되고, tb3_2가 감지 지점으로 출동해 카메라로 확인하며, 모든 이벤트와 대응 결과를 DB에 기록한다.

### 발표 제목·범위·센서 인터페이스 정리

- 결정: 표시 제목은 `디지털트윈경비로봇`으로 통일하고, 모바일/태블릿 앱 DT는 이번 범위에서 제거한다.
- 역할: M4(아두이노 센서)에 박태진을 추가해 김주영·임현찬·박태진 3인 담당으로 둔다.
- 보류: 아두이노 센서를 TurtleBot에 붙이는 방식은 아직 확정하지 않는다. S1에서 Arduino 보드→Raspberry Pi USB serial, OpenCR GPIO/ADC, Raspberry Pi GPIO/I2C/UART 후보를 비교한다.

### 센서 연결·적층 구조 확정

- 결정: 센서 4종(PIR/조도/소리/불꽃)은 **별도 Arduino Uno R3 + 브레드보드 → 라즈베리파이 USB serial** 경로로 통일한다. OpenCR 직접 연결과 RPi GPIO 직접 연결 후보는 폐기.
- 이유:
  - 팀이 보유한 **아두이노 기본 키트**(Uno R3 + 브레드보드 + 점퍼선 + LDR + 저항)로 즉시 시작 가능.
  - 주행 펌웨어(OpenCR core)를 건드리지 않아 SLAM/Nav2 안정성 보존.
  - 아날로그 센서 3종(조도·소리·불꽃)을 ADC 외부 IC 없이 처리 가능.
  - 분리된 시스템이라 디버깅이 쉬움 (`/dev/ttyACM0` 시리얼만 확인하면 됨).
- 적층 구조 (위→아래):
  1. **LDS LiDAR (최상단, 절대 양보 X)** — 360° 시야 보존
  2. **Arduino + 브레드보드 + 센서 4종 (NEW 층)** — M3 스페이서 30~40mm로 추가
  3. Raspberry Pi (기존)
  4. OpenCR (기존)
  5. 배터리/모터 (베이스)
- 시리얼 포맷: `EVT,<type>,<severity>,<unix_ts>\n` 예) `EVT,pir,3,1716800000\n`
- 핀 할당 (Arduino Uno R3):
  - PIR → D2 (디지털)
  - 조도 (LDR + 10kΩ 분압) → A0 (아날로그)
  - 소리 (KY-038 D-out) → D3
  - 불꽃 (D-out) → D4
  - 모의 입력 버튼 (화재) → D5
- 영향:
  - `PRD.md` 리스크 표에서 "센서 연결 방식 미확정" 행 제거 → "센서 노이즈" 행만 유지.
  - `ARCHITECTURE.md`에 적층 다이어그램과 핀 매핑 추가.
  - `CONTRACT.md §4` 후보 비교 표 → 확정 표.
  - `PROJECT-STATUS.md` 미확정 항목에서 제거.

### 병렬 작업 우선 — Sprint 앞에 매트릭스 추가

- 결정: 한 사람이 한 모듈에서 직렬로 작업하는 동안 다른 사람들은 다른 모듈에서 동시 진행이 가능하다는 점을 명시한다. `PROJECT-PLAN.md` 앞부분에 **주차×모듈 병렬 매트릭스**와 **의존성 그래프** 섹션을 추가한다.
- 이유: 7주는 빠듯하므로 직렬 대기 시간을 최소화해야 한다. 모듈 간 인터페이스(CONTRACT.md)만 합의해두면 각 모듈은 독립적으로 진행 가능.
- 핵심 병렬 라인 (S1 1주차 동시 시작 가능):
  - 김주영·김선일 → SCRUM-14 (DB 스키마 초안, M1)
  - 김선일·박태진 → SCRUM-9 (Unity UI 초안, M3)
  - 박태진·임현찬 → SCRUM-16 (실내 트랙 환경, 공통)
  - 김주영·임현찬·박태진 → 아두이노 키트 점검 + 핀 배선 도면 (M2/M4 준비)
- 직렬 병목: SCRUM-8 합의 (1일) → SCRUM-10 (SLAM은 SCRUM-16 뒤) → SCRUM-12 (출동은 SCRUM-13 뒤).

### 하드웨어 최종 확정 — TurtleBot3 Burger + Arduino Uno + OpenCR 5V 분기

- 결정:
  - 로봇 모델: **TurtleBot3 Burger** 확정
  - MCU: **Arduino Uno R3** 확정 (ESP32 검토했으나 키트 보유 우선)
  - 적층: **한 단 추가 없음**. 라즈베리파이 위치를 한쪽으로 치우치게 재배치하고 반대편 빈 공간(약 50×130mm)에 미니 브레드보드 + Arduino를 양면테이프로 부착
  - 전원: **OpenCR 5V 핀 → Arduino 5V 핀 점퍼 2줄(5V + GND)**. AA 배터리 4개 소켓은 추가하지 않는다 (6V로 Uno DC 잭 7V 최저 미달, 무게/관리 부담)
  - 통신: USB Type-B 케이블로 Arduino ↔ 라즈베리파이 (데이터 전용, USB 5V는 Uno 내부 P-MOSFET이 자동 선택)
- 이유:
  - AA 4개(6V)는 Uno DC 잭에 모자라고 5V 핀 직결이면 OpenCR 5V 분기와 동일 효과 → 배터리 추가 이득 없음
  - OpenCR 5V 출력 마진(약 1A 한계, 현재 LDS 400mA + 자체 100mA + Arduino 150mA = 650mA)이 충분
  - 메인 LiPo 배터리 영향은 시연 10분 기준 ~5분 단축 정도 (사실상 무영향)
- 영향:
  - `PRD.md` 하드웨어 구성 표 갱신 (Arduino 전원 = OpenCR 5V 점퍼)
  - `ARCHITECTURE.md` 적층 다이어그램 단순화 (별도 층 X, 라즈베리파이 옆 부착)
  - `CONTRACT.md §4` 시리얼 배선 표 갱신
- 주의: Arduino 전원은 반드시 **5V 핀**에 (Vin 아님). OpenCR과 Arduino GND 공통 연결.

### Day-1 작업 분담 (2026-05-27 즉시 시작)

- 결정: SCRUM-8 합의는 끝났다고 보고, 각자 오늘부터 모듈 안에서 즉시 가능한 검증 작업을 시작한다.
- 팀 분담:
  - **김주영 + 임현찬**: **라즈베리파이 Pi Camera 스트림 + DB 테스트** (SCRUM-19 일부 + SCRUM-14 일부)
  - **박태진**: **Arduino + PIR(인체 감지) 센서값 → DB 연결 테스트** (SCRUM-13 + SCRUM-14 일부)
  - **김선일**: **Unity 관제 UI 기능 정의 문서화** (SCRUM-9 + SCRUM-22 기능 명세 초안)
- 이유: 인터페이스(`CONTRACT.md`)가 잠긴 상태라 각자 모듈에서 독립 검증 가능. Day-1에 PIR → 시리얼 → DB로 데이터 한 줄이 통하면 S1 끝까지의 자신감이 생긴다.
- 산출물 (오늘 끝):
  - 김주영·임현찬: Pi Camera 토픽 확인 영상 + `events` 테이블에 sample insert 1건
  - 박태진: Arduino 스케치(PIR + 시리얼) + DB insert까지 통한 로그
  - 김선일: Unity UI 기능 목록 1장 (운영 대시보드·이벤트 패널·카메라 패널·모드 토글)

## 2026-05-28

### Arduino 플래시 파이프라인 자동화 + `arduino-flash` 스킬 등록

- 결정: 아두이노 GUI IDE 의존을 줄이고 **`arduino-cli` 기반 컴파일·업로드·시리얼 검증 파이프라인**을 URHYNIX 표준으로 채택한다. 동일 흐름을 재사용하기 위해 `.claude/skills/arduino-flash/SKILL.md`로 스킬화한다.
- 근거:
  - 2026-05-28 PIR(HW-740) + LED 한 줄 검증을 GUI 없이 `brew install arduino-cli` → `core install arduino:avr` → `compile` → `upload` → 시리얼 raw 캡처 30초로 성공적으로 마쳤다.
  - 센서 4종(PIR/조도/소리/불꽃) 동일 보드(Arduino UNO R3)에 반복 플래시될 예정이므로, 동일 절차를 4번 반복하는 대신 스킬로 묶어 첫 회부터 표준화한다.
  - `arduino-cli monitor`가 비-TTY 환경에서 즉시 종료되는 함정도 `stty + cat` 우회로 잡았으므로 AI 비대화형 검증까지 포함해 자산화한다.
- 영향:
  - `.claude/skills/arduino-flash/SKILL.md` 신설 (이번 커밋).
  - `.claude/skills/README.md`에 Embedded / Hardware Skills 표 + Rule of Thumb 1줄 추가.
  - `docs/status/PROJECT-STATUS.md` Evidence Status에 "PIR 플래시 (cli) 통과" 행 추가.
  - `docs/status/HANDOFF.md` 자산 표에 스킬 + 스케치 폴더 추가.
  - 향후 조도·소리·불꽃 센서 작업 시 본 스킬 1개로 일관 진행.
- 주의 (핀 매핑 정렬):
  - 2026-05-28 검증 코드는 **PIR=D7 / LED=D2**로 작성됐다. 그러나 2026-05-27 결정의 **SSOT 핀 매핑은 PIR=D2** (소리=D3, 불꽃=D4, 모의=D5, 조도=A0).
  - LED를 사용하는 디버그 코드는 다음 단계에서 **PIR=D2 / LED=D8(또는 D11)**로 재정렬해야 SSOT와 일치한다. 본 결정은 정렬 의무를 잠그는 의도이며, 다음 박태진 작업분에서 반영한다.

### Day-1 PIR 단계 진행 (Arduino 측 완료, DB 연결 단계 잔여)

- 결정: 박태진 Day-1 작업 중 **Arduino + PIR + 시리얼 로그까지의 절반**은 2026-05-28 시점에 검증 완료로 본다. 남은 절반 **시리얼 → 라즈베리파이 → `events` insert**는 다음 세션 첫 5분 액션으로 유지한다.
- 근거: `/Users/family/jason/URHYNIX/sketches/pir_led/pir_led.ino` 업로드 후 시리얼에서 `[MOTION] detected -> LED ON` / `[CLEAR ] no motion -> LED OFF` 패턴이 안정적으로 출력됨을 확인.
- 영향:
  - `HANDOFF.md` Top 1 액션을 "PIR → DB insert 단계 연결"로 좁힘.
  - `PROJECT-STATUS.md` Day-1 진행 표에서 박태진 행에 "Arduino+PIR 통과(2026-05-28) / DB 단계 잔여" 메모.

### LDR(조도) 센서 추가 + A0 SSOT 정렬 검증

- 결정: PIR 회로 위에 **LDR + 10kΩ 분압회로**를 추가하고, 신호 핀을 **A0 (SSOT 일치)**로 확정한다. 시리얼 라벨 포맷은 `[LDR] A0=<0-1023> (dark|dim|bright|very bright)`로 표준화한다.
- 근거:
  - 2026-05-28 1차 시도는 임시로 A1에 꽂아 검증 → 값 25↔211 진동으로 빛 변화 추종 확인.
  - 2026-05-28 2차로 **A0로 재배선 + 코드 정렬 + 재플래시 + 30초 시리얼 재캡처** 모두 통과. 라벨이 `[LDR] A0=...`로 갱신되고 29↔214 진동 + PIR 모션 동시 발생 시 충돌 없음을 확인.
  - SSOT(2026-05-27 결정)의 `A0 = 조도(LDR + 10kΩ 분압)`와 일치하므로 별도 SSOT 변경 불필요. 본 결정은 **실측 정렬 완료를 잠그는 기록**.
- 영향:
  - `sketches/pir_led/pir_led.ino`가 PIR(D7) + LED(D2) + LDR(A0) 3-기능 베이스 스케치가 됨. 남은 센서(소리/불꽃) 추가 시 본 파일을 분기해 재사용.
  - `arduino-flash` 스킬에 LDR 분압회로 배선 패턴 + 라벨 포맷을 자산화 (version 2).
  - `PROJECT-STATUS.md` Evidence Status에 "LDR A0 정렬 검증" 행 추가.
  - `HANDOFF.md` 자산 표·상태 표에 LDR 정렬 완료 반영, Top 1 잔여는 여전히 **PIR=D7→D2 정렬 + 시리얼→DB insert**.
- 잔여 정렬: PIR=D7(코드) ↔ D2(SSOT) 불일치만 남음. LED는 SSOT에 액추에이터로만 명시되어 있어 D2 사용은 SSOT와 충돌하나, **PIR을 D2로 옮기는 시점에 LED를 D8 또는 D11로 이동**해 함께 해소한다.

### 라즈베리파이 ↔ Arduino USB 시리얼 안정 식별 (2026-05-28 후속)

- 결정: Arduino UNO USB serial을 라즈베리파이에서 **`/dev/tb3_arduino` 안정 심볼릭 링크**로 영구 식별한다. udev rule + 사용자 그룹을 한 번에 잠근다.
- 근거:
  - 2026-05-28 라즈베리파이(`kim@192.168.0.138`) 점검에서 `/dev/ttyACM0` = OpenCR (vendor 0483), `/dev/ttyACM1` = Arduino UNO (vendor 2341, model 0043) 분리 확인.
  - `pyserial 3.5` 사전 설치 확인. bringup tmux 살아있는 상태에서 동시 점검 가능.
  - 기본 udev에서 `/dev/ttyACM1` 권한이 `crw-rw----` + `dialout` 그룹 멤버가 비어있어 `kim` 사용자 접근 불가 (`Permission denied`).
- 적용 사항:
  - `sudo usermod -aG dialout kim` — `kim` 사용자 영구 그룹 가입 (`id`에서 `20(dialout)` 확인 완료).
  - `/etc/udev/rules.d/99-urhynix-arduino.rules` 작성: `SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", MODE="0666", SYMLINK+="tb3_arduino"`. `udevadm control --reload && udevadm trigger`까지 적용.
  - 결과: `/dev/tb3_arduino -> ttyACM1` 자동 생성, 모드 `crw-rw-rw-`. USB 재연결 시에도 룰이 모드+심링크 자동 복구.
- 영향:
  - 라즈베리파이에서 Arduino를 읽는 모든 코드는 **`/dev/tb3_arduino`** 사용 (USB 순서 바뀌어도 안전).
  - 8초 시리얼 캡처에서 `[MOTION] detected -> LED ON`, `[LDR] A0=190 (dark)` 등 표준 라벨 정상 수신 확인 (워밍업 직후 첫 2줄은 버퍼 잔재로 라인 잘림 — readline 정상 동작 후 라벨 깔끔).
  - `CONTRACT.md §4` 시리얼 배선 표에 `/dev/tb3_arduino` 권장 경로 반영 예정 (다음 작업).

### DB 선정 보류 — Day-1 "한 줄 insert" 사전 차단 (2026-05-28)

- 결정: `events` 테이블이 들어갈 데이터베이스를 **이번 세션에서는 선정하지 않는다**. 다음 세션의 첫 행동으로 격상한다.
- 근거:
  - Supabase MCP `list_projects` 결과 URHYNIX 전용 프로젝트가 **없음** (현재 ACTIVE는 `vibe` 1개로 무관, `TailLog`/`mungmungfit`는 INACTIVE이며 별개 프로젝트).
  - `SCHEMA.md`의 `db/migrations/2026-05-27_init_security.sql` 파일도 미작성 상태 → 테이블 DDL 자체가 존재하지 않음.
  - 그래서 박태진 Day-1 잔여 액션 "시리얼→`events` insert"가 **DB 선정**과 **마이그레이션** 두 단계로 사전 차단됨.
- 결정 보류 옵션 3가지 (다음 세션에서 김주영 결정):
  1. **신규 Supabase 프로젝트 `urhynix`** (`ap-northeast-2`, 무료 tier active 2개 한도 내 가능) — 격리·SSOT 정확 일치, 생성 ~2-3분
  2. **기존 `vibe` 프로젝트에 `urhynix` 스키마 추가** — 즉시 가능/비용 0, 다른 프로젝트와 혼재
  3. **라즈베리파이 로컬 Postgres 14+** — 완전 격리/오프라인 가능, Unity·원격 접근 어려움
- 차단 영향:
  - `HANDOFF.md` Top 1이 "PIR → DB insert" → **(0) DB 선정 → (1) `session_meta`+`events` 마이그레이션 → (2) 시리얼→insert 파이썬 스크립트** 3단계로 확장.
  - 박태진 Day-1 작업은 DB 선정 결정까지 **대기**. 단, Arduino 측 잔여 (PIR 핀 D7→D2 정렬)는 독립 진행 가능.
  - `SCHEMA.md` 상단·Open Questions에 "DB 미선정 (Day-1 차단)" 명시.
  - `arduino-flash` 스킬 마지막에 "RPi→DB 단계는 DB 선정 후 별 스킬" 노트 추가.
- 잠금: 본 결정은 "DB 미선정"을 **명시적으로 잠그는 결정**. 다음 세션에서 옵션 1/2/3 중 하나로 전환되는 즉시 새 DECISION 항목으로 갱신.

### DB 선정 완료 — 신규 Supabase `ueupkrxwybuuqxflstvg` (옵션 B + 트위스트) (2026-05-28)

- 결정: URHYNIX `events`/`session_meta`/`dispatches`/`camera_captures` 4테이블은 **신규 Supabase 프로젝트 `ueupkrxwybuuqxflstvg`** (region ap-northeast-1 Tokyo, org `uisuqsaynxoedcsuikqc`)에 잠근다. 기존 시도(`oucgzkbqrzbwxxffmmqt` mungmungfit)는 **egress quota 초과**로 외부 REST가 HTTP 402로 차단되어 폐기.
- 근거:
  - 2026-05-28 외부 진단: `https://ueupkrxwybuuqxflstvg.supabase.co/rest/v1/` HTTP 401 `No API key found` = endpoint 살아있음 + quota 깨끗.
  - Supabase access token `sbp_…` 으로 `supabase projects list` 통과 → org 권한 확인.
  - Management API SQL endpoint `POST https://api.supabase.com/v1/projects/{ref}/database/query`로 마이그레이션 적용 성공 (HTTP 201, 4 테이블 + seed 1건 확인).
- 외부 REST insert 통로:
  - **publishable key** (`sb_publishable_bB5OpwyxD3-9o41kgcSY8g_tDgiCARM`) → RLS auto-on 상태에서 INSERT `HTTP 401 code 42501 RLS violation` (정상 보안).
  - **service_role legacy JWT** → INSERT `HTTP 201` 정상 (RLS 우회). 새 row `c8c389b9-a5ee-4054-87fa-0203454a5d11` 확인.
- 영향:
  - `db/migrations/2026-05-27_init_security.sql` 헤더의 대상 ref를 신규 프로젝트로 갱신.
  - `scripts/arduino_bridge.py` default `SUPABASE_URL`을 `https://ueupkrxwybuuqxflstvg.supabase.co`로 갱신. `SUPABASE_KEY`는 RPi `/etc/urhynix.env`에만 service_role 값으로 주입 (commit 금지).
  - `SCHEMA.md` 상단 "저장소 미선정" 경고 해소.
  - `PROJECT-STATUS.md` Evidence Status에 DB 선정 행 추가.
  - `HANDOFF.md` Top 1을 (1) RPi env 작성 → (2) tb3-up → (3) tb3-bridge → (4) PIR row insert 검증 4단계로 재정렬.
- 키 운영 룰 (2026-05-28 잠금):
  - **service_role legacy JWT** = secret. RPi `/etc/urhynix.env`에만, 절대 repo·HTML 보드·Slack에 박지 않음.
  - **publishable key** = 안전 공개 가능. 단 RLS ON 상태라 외부 anon 접근은 의미 없음 (정책 추가 시 효력).
  - **access token `sbp_…`** = 일회용 작업 토큰. 2026-05-28 작업 후 https://supabase.com/dashboard/account/tokens 에서 revoke 권장.
- RLS 정책: 현재 4테이블 모두 RLS ON · 정책 0개. service_role만 R/W 가능. 추후 시연 dashboard용 SELECT policy는 별도 결정.

### LDR(조도) 이벤트 트리거 규칙 — edge-trigger + 히스테리시스 (2026-05-28)

- 결정: `arduino_bridge.py`가 LDR 시리얼 라인 (`[LDR] A0=<v>`)을 받을 때 **A0 < 200 으로 처음 진입**하는 순간 한 번만 `events` 테이블에 `event_type='dark', severity=1` 로 insert. **A0 >= 250 으로 복귀**하면 내부 state reset(insert 없음). 같은 어두움 상태 안에선 중복 insert 없음.
- 근거:
  - Arduino 스케치 임계값: `<200 dark / <600 dim / <900 bright / else very bright` (PIR+LDR 스케치).
  - LDR은 2초 주기로 시리얼 발행 → 어두운 상태가 계속되면 매 2초마다 row 1건 → 시연 30분이면 ~900 row → DB가 dark로 가득 차고 신호 노이즈 비율 악화.
  - edge-trigger(진입 1회만) + 히스테리시스(`enter=200`, `exit=250`)로 chatter 방지.
  - severity: PIR(=3, 침입)보다 낮은 `1`로 잠금 (어두움 = 야간 모드 진입 신호 정도의 중요도).
- 트리거 흐름:
  ```
  A0=190 (dark) → dark_state=False → insert event_type='dark' → dark_state=True
  A0=180 (dark) → dark_state=True → insert 안 함 (중복 방지)
  A0=260 (dim)  → A0>=250 + dark_state=True → state=False (insert 없음)
  A0=190 (dark) → dark_state=False → insert event_type='dark' → dark_state=True
  ```
- 영향:
  - `scripts/arduino_bridge.py`에 `LDR_DARK_ENTER=200`, `LDR_DARK_EXIT=250`, `self._dark_state` 추가.
  - `scripts/aliases.sh`에 `sb-by-type` / `sb-dark` / `sb-pir` 신규 alias 3개. 시연 시 이벤트 타입별 통계 한 줄.
  - `SCHEMA.md`의 `event_type` enum은 이미 `dark/pir/noise/fire`를 포함하므로 변경 없음.
  - `raw_payload`에 `label="dark"`, `ldr=<A0 raw>`, `ts_unix`, `have_odom` 저장 → 후속 분석에서 어두운 정도(A0 값) 복원 가능.
- 잔여: 시연 시 darkening 속도(LDR 직접 가림)에 따라 `LDR_DARK_ENTER=200`이 너무 민감하거나 둔할 수 있음 → 실측 후 임계값 미세조정. 임계값은 코드 상단 상수 두 줄만 변경.

### SSH 공개키 인증 채택 — expect+비번 의존 영구 제거 (2026-05-28)

- 결정: Mac/Linux 머신의 ed25519 공개키를 로봇 `kim@192.168.0.138`의 `~/.ssh/authorized_keys`에 등록한다. 이후 모든 SSH/SCP 호출이 비번 prompt 없이 즉시 통과하며, expect의 password 처리 의존을 거의 0으로 줄인다.
- 근거:
  - 2026-05-28 사용자 실측에서 `tb3-go` 흐름이 expect heredoc + send 자동 입력으로 처리되긴 했으나, 화면에 password prompt가 일부 노출되고 사용자가 무의식적으로 키 입력을 추가하면 zsh 명령 라인으로 흘러나가 `command not found: 1234` 같은 부작용 발생.
  - 더 근본적으로 일부 셸 상태에서 `$TB3_PASSWORD`가 빈 값으로 expect에 expand되어 자동 입력 실패 → `Connection refused` 연쇄.
  - 공개키 인증은 (a) 비번 prompt 자체가 발생하지 않음 (b) `BatchMode=yes`로 비대화형 호출 가능 (c) 키 분실 시 robot 쪽 authorized_keys만 정리하면 회수 가능.
- 적용:
  - Mac: `ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519` (이미 있으면 재사용) + `ssh-copy-id -i ~/.ssh/id_ed25519.pub kim@192.168.0.138`.
  - 검증: `ssh -o BatchMode=yes kim@192.168.0.138 hostname` → `kim-desktop` 무대화형 응답.
  - 헬퍼: `scripts/tb3.sh`에 `tb3-key-setup` 함수 신설 — 키 생성/검사 + ssh-copy-id + 검증을 한 줄로.
- 영향:
  - `tb3-go` / `tb3-restart` / `tb3-bridge` / `tb3-down` / `tb3-poweroff` / `tb3-arduino` / `tb3-logs` 모두 password 무관하게 동작.
  - `~/.tb3rc`의 `TB3_PASSWORD`는 (a) 비상시 expect fallback (b) `tb3-key-setup` 첫 ssh-copy-id 호출 용도로만 의미.
  - 협업자 (Ubuntu) 첫 setup 단계에 `tb3-key-setup` 한 줄 추가.
  - `HANDOFF.md` Top 1을 (1) 메인 스위치 ON → (2) `tb3-go` → (3) `tb3-unity` → (4) PIR/LDR → `sb-tail` 검증 4단계로 단순화. SSH key 미등록 머신만 (0) `tb3-key-setup` 한 번 선행.
- 보안:
  - 키는 passphrase 없이 생성됨 — 개인 머신 전제. 공용 PC에선 passphrase 사용 권장 + `ssh-agent`에 일시 add.
  - 키 회수: 로봇에서 `sed -i '/<MAC public key fingerprint>/d' ~/.ssh/authorized_keys`.

### 박물관/미술관 액자 보호 컨셉 + 미디어/좌표 저장 요구 반영 (2026-05-28)

- 결정: 디지털트윈경비로봇의 발표 컨셉을 **박물관/미술관 액자형 중요물품 보호**로 구체화한다. 사진이 붙은 액자형 타깃을 카메라가 보호 대상으로 인식하고, 외부자 판단은 PIR 단독이 아니라 **PIR + LiDAR 변화 + pose log** 조합으로 남긴다.
- 이유:
  - "무엇을 지키는 로봇인가"가 분명해져 발표 시나리오가 직관적이다.
  - 화재 의심 이벤트에서 액자/중요물품 주변 카메라 확인, 영상 클립, 대응 좌표 로그를 함께 보여주면 DB/AI/Unity/로봇 파트가 하나의 체인으로 설명된다.
  - 조도 센서가 어두움을 감지했을 때 LiDAR를 물리적으로 새로 켜는 구조가 아니라, 저속 순찰·스캔/pose 로그 저장 빈도 증가·확인 이벤트 강화로 "LiDAR 강화 모드"를 표현하는 편이 TurtleBot 구조와 맞다.
- 영향:
  - `PRD.md`: MVP/성공 기준/데이터 수집 전략/리스크에 액자형 중요물품, 좌표·사진·영상·사운드 저장 요구 추가.
  - `ARCHITECTURE.md`: `protected_assets`, `pose_logs`, `media_artifacts`, 박물관/미술관 보호 컨셉, LiDAR 강화 모드 원칙 추가.
  - `SCHEMA.md`/`CONTRACT.md`: 현재 실제 DB 4테이블과 분리해 `pose_logs`, `media_artifacts`, `protected_assets`, `protected_asset_id`, `asset_seen`/`asset_missing` 확장 예정 계약 추가.
  - `PROJECT-PLAN.md`/`JIRA-MAP.md`: SCRUM-9/14/15/16/21/23 제목과 Sprint 작업을 보호 컨셉에 맞게 확장.
- 잔여:
  - 현재 Supabase에는 초기 4테이블이 적용되어 있다. `pose_logs`/`media_artifacts`/`protected_assets` 실제 마이그레이션은 SCRUM-23에서 별도 SQL로 적용한다.
  - 카메라 인식 1차 구현은 AprilTag/QR/고대비 프레임 같은 보조 표식을 우선 후보로 둔다.
  - 2026-05-28 REST 실조회 확인: `session_meta`, `events`, `dispatches`, `camera_captures`는 HTTP 200. `pose_logs`, `media_artifacts`, `protected_assets`는 HTTP 404(PGRST205)로 현재 미존재.

### 매일 18:00 Confluence 회의록 기반 SSOT 자동화 예약 (2026-05-28)

- 결정: Codex automation `urhynix-daily-ssot-sync-from-confluence`를 매일 18:00(KST) 실행하도록 생성한다.
- 이유: 당일 Confluence 회의록의 결정/완료/블로커/다음 액션을 로컬 SSOT와 외부 Confluence/Jira에 반복 반영해야 하며, 사람이 매번 놓치기 쉽다.
- 실행 기준:
  - 작업 디렉터리: `/Users/family/jason/URHYNIX`
  - 로컬 SSOT를 먼저 읽고 갱신한다.
  - 실제 검증된 현재 상태와 예정안을 분리한다. DB/Jira 상태가 언급되면 가능한 범위에서 실조회 후 current로 승격한다.
  - SSOT 변경이 보드에 영향을 주면 `python3 docs/whiteboards/build_bundle.py`를 실행하고 HTML 파싱 검증을 수행한다.
  - Confluence/Jira는 회의록에서 명확히 영향받은 항목만 갱신한다.
- 주의: 외부 문서 전체 덮어쓰기는 필요할 때만 수행하고, 기본은 검증된 변경만 반영한다.

### 신규 128GB SD + Ubuntu 24.04.4 + ROS2 Jazzy 풀 부트스트랩 (2026-06-01)

- 결정: 라즈베리파이4의 기존 16GB SD를 128GB로 교체하고, Mac에서 직접 `dd` + cloud-init 사전설정 박는 방식으로 새 부팅 환경을 잠근다. ROS2 Jazzy + turtlebot3 메타 + ld08_driver + ros_tcp_endpoint까지 한 세션에 풀 셋업.
- 이유:
  - 기존 SD가 디스크 1.1GB(94%) 빡빡해서 colcon build/패키지 추가가 위험. 128GB로 여유 확보.
  - Raspberry Pi Imager GUI는 매번 수동 클릭이 필요하지만, cloud-init `user-data`/`network-config`/`meta-data` 3개 파일을 `system-boot` 파티션 루트에 두면 Pi용 `preinstalled-server-arm64+raspi.img.xz`가 자동 인식한다. 재현성과 자동화에 더 좋다.
  - Opus 자기리뷰가 "NoCloud datasource_list 명시 필요 / cloud/ 서브디렉토리 필요"라고 했지만, 실제 검증에서는 둘 다 불필요했다. Ubuntu Pi 이미지의 cloud-init은 system-boot 파티션 루트의 user-data를 자동으로 NoCloud datasource로 인식한다 (`status: done` `DataSourceNoCloud [seed=/dev/mmcblk0p1]`).
- 잠금 사항:
  - 이미지: `ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz` (SHA256 `790652fa...0d37`)
  - 사용자: `kim` / 비번 `1234` (학원 LAN 한정, 발표 후 변경 권장)
  - hostname: `urhynix-robot`, timezone `Asia/Seoul`, locale `ko_KR.UTF-8`
  - SSH 키 인증 자동 (Mac `~/.ssh/id_ed25519` 등록), `ssh_pwauth: true` (helper 호환)
  - 네트워크: 유선 eth0 DHCP. 학원이 `192.168.0.x` ↔ `192.168.10.x` 라우팅을 해줘서 robot이 `192.168.10.59`에 있어도 Mac에서 직접 SSH/ping 가능. 단 mDNS multicast는 라우터 못 건너 `.local` 미작동 → Mac `~/.ssh/config` 별칭 `urhynix-robot` 으로 우회.
  - ROS2 Jazzy + `ros-jazzy-turtlebot3` 메타(2.3.6) + cartographer + nav2-bringup + hls-lfcd-lds-driver + dynamixel-sdk + rmw-cyclonedds-cpp 모두 apt
  - src 빌드: `ld08_driver` (jazzy 브랜치, LDS-03 LiDAR) + `ros_tcp_endpoint` (main-ros2 0.7.0, Unity 통신)
  - `~/.bashrc`에 ros-jazzy setup + ws setup + TURTLEBOT3_MODEL=burger + LDS_MODEL=LDS-03 + OPENCR_PORT=/dev/ttyACM0 + ROS_DOMAIN_ID=230 자동 source (초기 30 → 2026-06-02에 230으로 통일, 티원과 일치)
  - udev rules `/dev/tb3_arduino` (Arduino UNO 2341:0043, 2a03:0043) + `/dev/tb3_opencr` (STM 0483:5740) 안정 심볼링크
  - `/etc/urhynix.env` 템플릿 (640 root:kim, SUPABASE_KEY 자리는 `PASTE_SERVICE_ROLE_JWT_HERE` 로 비워둠 — 발표 직전 주인님이 채움)
- 잔여:
  - 다음 세션 첫 5분에 `/etc/urhynix.env` SUPABASE_KEY 주입 (service_role JWT, 절대 commit 금지)
  - OpenCR firmware 재플래시, Arduino UNO PIR/LDR 스케치 재플래시 (D2 핀 SSOT 정렬)
  - Pi 카메라 동작 검증 (`libcamera-hello -t 0`)
  - bringup `/scan` `/odom` topic 검증 (LiPo ON 필요)
  - 그 다음에 가벽 보강(옵션 A) + arena_v2 매핑
- 근거: `docs/evidence/2026-06-01-new-sd-128gb-ros2-jazzy-bootstrap.md`

### IP-drift zero-touch 화 — Unity rosIP + helper mDNS hostname 기반화 (2026-06-01 오후)

- 결정: DHCP IP가 바뀔 때마다 Unity Scene/Script/helper의 hardcoded IP를 patch하던 매 세션 첫 5분 표준 작업(`ip-drift-resync` 스킬 호출)을 mDNS hostname 기반화로 zero-touch 한다.
- 이유: 신규 SD 부트스트랩 후 robot이 학원 Wi-Fi(codelab_5G)에 영구 연결됐고 avahi-daemon이 `urhynix-robot.local`을 publish. Mac과 robot이 같은 192.168.0.x 서브넷에 있으므로 mDNS multicast 작동. 모든 진입점에 hostname을 박으면 IP 변경에 무관.
- 잠금 사항:
  - `unity-smoke/Assets/Scenes/SampleScene.unity:151` rosIP=`urhynix-robot.local`
  - `unity-smoke/Assets/Scripts/RosSmokeDashboard.cs:10` 기본값=`urhynix-robot.local`
  - `scripts/tb3.sh`에 `export TB3_HOSTNAME='urhynix-robot'` 추가 + `tb3-ip()` 맨 앞에 mDNS 우선 시도 (`ping <hostname>.local`에서 IP 추출, 실패 시 기존 ARP sweep으로 fallback)
  - Mac `~/.ssh/config` `Host urhynix-robot` 별명 → `HostName urhynix-robot.local`
- 효과: IP 바뀌어도 `ssh urhynix-robot` / `tb3-ip` / Unity 모두 자동 follow. `ip-drift-resync` 스킬은 호출 거의 불필요 (다른 망 가거나 mDNS 죽었을 때만 안전망으로 남음).
- 검증: 랜선 분리 + 재기동 후 무선 단독 PASS (eth0 IP 비어있는 상태로 wlan0=192.168.0.82만으로 ssh + ros2 진입 OK).
- 근거: `docs/evidence/2026-06-01-new-sd-128gb-ros2-jazzy-bootstrap.md` §"IP-drift zero-touch 화"

### 티원 TurtleBot3 + RealSense D435 ArUco 마커 자동주차 노드 결선 PASS (2026-06-09)

- 결정: 티원(`t1@192.168.0.250`)에서 RealSense D435 카메라로 ArUco 마커 ID 1번을 감지하고 자동 주차(자율 접근·정렬·停止)하는 ROS2 노드를 결선한다.
- 표준 결정 5가지:
  1. **cmd_vel = `geometry_msgs/TwistStamped`** (Twist 아님) — TurtleBot3 Jazzy 표준, `ros2 topic info /cmd_vel`로 확인.
  2. **거리 측정 = RealSense `aligned_depth_to_color`** — 단안 픽셀 크기 추정보다 cm 단위 정확도 높음.
  3. **dry_run 파라미터 추가** (기본 False) — 안전 검증 모드, cmd_vel을 0으로 강제해 모션 차단.
  4. **OpenCV 4.6 호환 함수형 API** (`cv2.aruco.detectMarkers(...) + DetectorParameters_create()`) — ArucoDetector 클래스 미존재.
  5. **sensorId=ID 1번 우선** — A4 가득 인쇄 마커, ~12cm 표준.
- 발견·해결한 함정 8가지 (영구 자산화):
  1. cmd_vel = TwistStamped (TB3 Jazzy)
  2. declare_parameter 6번 호출 → context race → declare_parameters batch 사용
  3. OpenCV 4.6에 ArucoDetector 클래스 없음 → 함수형 API 사용
  4. LDS_MODEL 비인터랙티브 ssh에서 안 잡힘 → 명시적 export
  5. rqt_image_view QoS RELIABLE vs RealSense BEST_EFFORT → rviz2 또는 옵션 조정
  6. finally의 cmd_pub.publish race → rclpy.ok() 가드
  7. turtlebot3_bringup 중복 launch → 노드 이름 충돌
  8. message_filters slop=0.1 너무 작음 → 0.3~0.5 권장
- 새 자산 4종:
  - 스킬: `.claude/skills/urhynix-aruco-parking-bringup/SKILL.md` (NEW)
  - 노드 SSOT: `scripts/aruco_parking/parking_node.py` (NEW, 맥 측 소스)
  - t1 배포: `~/aruco_ws/src/aruco_parking/aruco_parking/parking_node.py` (scp 복제)
  - 폴더 룰: `scripts/aruco_parking/CLAUDE.md` (NEW)
  - evidence: `docs/evidence/2026-06-09-aruco-parking-bringup.md` (NEW)
- 기술 스택:
  - 카메라: RealSense D435 (Serial 254522075185, FW 5.17.0.10)
  - 마커: ArUco DICT_4X4_50, ID 1번
  - 목표 거리: 0.25m (마커까지 접근 후 停止)
  - 상태머신: SEARCH (마커 찾기) → APPROACH (정면 접근) → ALIGN (정렬) → PARK_DONE (停止)
  - 안전 한도: lin velocity 0.15 m/s, ang velocity 0.5 rad/s (np.clip 내부)
- 검증:
  - colcon build PASS (19.5s)
  - 노드 실행: `ros2 run aruco_parking parking_node`
  - `/cmd_vel` Publisher 1 (parking_node) + Subscription 1 (turtlebot3_node) — 연결 라인 확인
  - `/cmd_vel_input` (subscribe) + `/cmd_vel_output` (publish) 토픽 라우팅 OK
- 잠금: 다음 세션 첫 5분은 **5트라이얼 정밀도 평가** (안전 환경 확보 후). 평가 완료 시 시연 GO 조건 확정.
- 근거: `docs/evidence/2026-06-09-aruco-parking-bringup.md`

### 코드 구조 보강 + 2차 시도 하드웨어 문제 발견 — Dynamixel crash + callback stuck (2026-06-09 2차 시도)

- 결정: parking_node.py를 MultiThreadedExecutor + ReentrantCallbackGroup + heartbeat timer(0.1초) + try/except callback wrapper + Depth latest-cache 패턴으로 강화하고, 발견된 함정 #9, #10을 영구 자산화한다.
- 코드 구조 4가지 변경:
  1. **MultiThreadedExecutor 채택** — SingleThreadedExecutor에서 image_callback 실행 중 다음 메시지 처리 지연 → 첫 callback 1회 호출 후 cmd_vel hz 0, debug_image hz 0 멈춤 현상 해결.
  2. **ReentrantCallbackGroup** — callback 내부에서 publisher 호출 시 deadlock 방지.
  3. **0.1초 heartbeat timer** — callback 멈춰도 cmd_vel 정지 신호(0, 0, 0) 발행 보장 → 로봇이 최대 0.1초 후 자동 정지.
  4. **Depth latest-cache 패턴** — message_filters.ApproximateTimeSynchronizer의 slop 0.1/0.5 조정으로도 RealSense RGB/Depth 동기화 매칭 안정성 부족 → RGB 콜백 후 매 프레임마다 latest depth frame으로 거리 측정 (stamp 매칭 폐기).
- 발견한 추가 함정 2가지 (총 8 → 10으로 확장):
  - **함정 #9**: Dynamixel SDK 통신 실패 → turtlebot3_ros crash
    - 증상: turtlebot3.log에 `[DynamixelSDKWrapper]: Failed to read[[TxRxResult] There is no status packet!]` 반복 후 `*** stack smashing detected ***: terminated` 발생, process exit code -6.
    - 원인: LiPo 배터리 부족 / OpenCR↔Dynamixel 통신 끊김 / 케이블 불량. 소프트웨어 원인 아님 (parking_node와 무관).
    - 우회: 배터리 충전, OpenCR 리셋 버튼, 휠 모터 케이블 재연결, 전원 OFF/ON.
  - **함정 #10**: image_callback 단일 호출 후 멈춤 (SingleThreadedExecutor)
    - 증상: 첫 callback 1회 호출 후 cmd_vel hz 0, debug_image hz 0.
    - 원인: SingleThreadedExecutor + 무거운 callback (cv_bridge 변환)이 다음 메시지 처리 못 따라감.
    - 우회: MultiThreadedExecutor + ReentrantCallbackGroup + 0.1s heartbeat + try/except로 callback 안전화.
- 다음 세션 진입 조건 (시연 GO 해제):
  1. LiPo 배터리 충전 완료 (>11.5V)
  2. OpenCR 리셋 버튼 1회 누름
  3. Dynamixel 휠 모터 케이블 재연결
  4. t1 전원 OFF → ON
  5. turtlebot3_bringup launch 후 `[DynamixelSDKWrapper] Failed to read` 에러 없는지 확인
  6. parking_node 실행 → 5트라이얼 정밀도 평가
- 영향:
  - `scripts/aruco_parking/parking_node.py` = SSOT 자체 (MultiThreadedExecutor + 패턴 코드로 이미 갱신).
  - `.claude/skills/urhynix-aruco-parking-bringup/SKILL.md` 함정 #9, #10 추가 (기존 함정 8→10으로 확장).
  - `docs/evidence/2026-06-09-aruco-parking-bringup.md`에 오늘 2차 시도 결과 추가 (하드웨어 crash 진단 + 우회책 명기).
  - PROJECT-STATUS.md 한 줄 상태: "Phase 2.9 시연 GO 보류 (하드웨어 점검 필요)".
  - HANDOFF.md 다음 세션 진입: "①배터리 충전 확인 → ②OpenCR 리셋 → ③turtlebot3_bringup 검증 → ④parking_node 5트라이얼".
- 잠금: 다음 세션 첫 5분은 하드웨어 점검(배터리·OpenCR·케이블) → 정상 부팅 검증 → 5트라이얼 정밀도. 시演 GO는 이 후.
- 근거: `docs/evidence/2026-06-09-aruco-parking-bringup.md` (2차 시도 결과 섹션)

### 3차 시도: 시연 PASS 확정 + 배터리 트렌드 측정 + 동료 인계 완료 (2026-06-09 오후)

- 결정: 배터리 충전 후 parking_node를 재실행하고, 사용자가 직접 시연 중 자동주차 동작을 확인한다. 완료 후 우리 parking_node는 종료하고 turtlebot3_bringup + RealSense를 nohup으로 유지해 동료에게 인계한다.
- 조건:
  - 배터리 부팅 직후: 11.54V / 57.77% (멀티미터 측정)
  - parking_node 실행: MultiThreadedExecutor + ReentrantCallbackGroup + 0.1s heartbeat + try/except + Depth latest-cache 패턴 적용 (2차 시도 코드 그대로)
  - 사용자 시연: 자동주차 동작(마커 감지 → 접근 → 정렬 → 停止) **PASS 확인**
  - 시연 후 배터리: 11.43V / 51.66% → 감소량 0.11V, 6.11% (약 1회 시연당 -6%)
- 자산:
  - 배터리 트렌드 표:
    | 시점 | voltage | percentage |
    |---|---|---|
    | 부팅 직후 | 11.54 V | 57.77% |
    | 시연 후 | 11.43 V | 51.66% |
    | 감소 | -0.11 V | -6.11% |
  - 추가 자산: XQuartz 설치 완료 (`brew install --cask xquartz` + SUDO_ASKPASS helper 우회 패턴)
  - 경로: `/Applications/Utilities/XQuartz.app` + `/opt/X11/bin/Xquartz`
  - **주의**: 로그아웃/재로그인 필요 → 다음 세션 진입 시 `ssh -Y t1@192.168.10.250 + ros2 run rqt_image_view rqt_image_view`로 맥에서 RealSense 영상 직접 확인 가능
- 동료 인계:
  - 우리 ssh 연결 자동 종료 (매 명령마다 새 세션)
  - 동료가 본인 PC에서 `source /opt/ros/jazzy/setup.bash + export ROS_DOMAIN_ID=230 + python3 aruco_real_test1.py` 3줄로 진입 가능
  - 우리 parking_node 종료 완료, turtlebot3_bringup + RealSense nohup으로 유지(동료 재사용)
  - 동료 코드 권장 수정 2가지:
    1. `cv2.namedWindow` 제거 (DISPLAY 환경 의존, SSH 환경에서 불필요)
    2. `np.clip` 안전 클램프 추가 (velocity bounds 명시)
- 다음 세션 진입 조건:
  1. 배터리 풀충전 (>12.4V 권장)
  2. t1 부팅 후 `/battery_state` voltage 확인
  3. XQuartz 재로그인 후 `ssh -Y` 가능 (선택)
  4. parking_node 실행 → 5트라이얼 정밀도 평가 (마커 정면 1m × ±30° 각도, 5회 중 3회 이상 0.25m 이내 停止 성공)
  5. rosbag 4종 기록 (/cmd_vel, /odom, /aruco/debug_image, /aruco/state)
- 영향:
  - 시演 GO 조건 **확정** — Phase 2.9 완료
  - 배터리 관리: 11.0V 도달 시 즉시 정지 + 충전 권장
  - 다음 단계: 5트라이얼 정량 평가 → 다중 마커 통합 (티원 D435) → 박물관 시나리오 통합
- 근거: `docs/evidence/2026-06-09-aruco-parking-bringup.md` (3차 시도 결과 섹션 추가)
