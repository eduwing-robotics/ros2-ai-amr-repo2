# Project Status

Last updated: 2026-06-18 — **✅ demo_logs_rls.sql 적용 완료 + Unity 직접쓰기 경로 end-to-end 검증 PASS**: Supabase `ueupkrxwybuuqxflstvg` 복구되어 LIVE. logs 테이블 생성, dispatches event_id nullable + nav_mode/reason, anon RLS 10개 적용 완료. Unity Play에서 session_meta + logs 테이블 직접쓰기 PASS, logs 7건 DB 실기록(`DbVerifyConsole` 검증). **미해결**: pose_logs는 RobotPoseSubscriber /tf map 프레임 미수신(다음 세션 TF 추적 과제). 자세히: `DECISION-LOG.md` 2026-06-18 최상단. 이전(2026-06-18): 4센서 통합 아두이노 핀맵 확정 PASS(PIR D2·레이저 D4·사운드 A1 AO·온도 A0). **이전(2026-06-10)**: Mac MPS + T1 RealSense → YOLOv8n 라이브 PASS(26 fps).

## 2026-06-02 Addendum

- **14:30 회의 Jira 최신 반영 완료**. 젠지=Pi Camera+센서, 티원=비전 카메라로 표기 통일했고 `ROS_DOMAIN_ID=230`, Unity 듀얼 카메라 동시송출 검증, Google Teachable Machine + TensorFlow/Keras 객체 분류 스파이크(빈공간/박스/마우스 검정·흰색/손)를 Jira `SCRUM-44`, `SCRUM-51`, `SCRUM-54`, `SCRUM-56`, `SCRUM-61`, `SCRUM-62`, `SCRUM-64`에 반영했다.
- **Jira 관리자용 7개 스크럼 재구성 완료**. 이전 열린 SCRUM 카드와 이전 주차 에픽은 완료 처리했고, 새 관리자 에픽 `SCRUM-39`~`SCRUM-45`와 하위 작업 `SCRUM-46`~`SCRUM-66`으로 재생성했다. 스크럼 1/2와 해당 하위 작업 6개는 완료, 스크럼 3~7 에픽 5개 + 하위 작업 15개는 해야 할 일. JQL 검증: `project = SCRUM AND statusCategory != Done ORDER BY key ASC` 결과 20건.
- **Jira 카드 가독성 정리 완료**. `SCRUM-39`~`SCRUM-72`의 제목과 설명을 `스크럼 1`~`스크럼 7` 순서의 쉬운 한글 문장으로 바꿨다. 예: `[스크럼 3] 로봇 주행과 센서 연결`, `[스크럼 5] 데이터 저장과 출동 흐름 연결`. 실제 Jira Sprint 객체 이름 변경은 현재 도구로는 불가하므로 Jira Backlog 화면에서 해당 Sprint의 `Edit sprint`로 직접 수정한다.
- **기술별 ref 라우팅 추가** (`docs/ref/TECH-INDEX.md`, `docs/ref/tech/*.md`). Unity/ROS2/Arduino/DB/카메라/하네스 작업 시 전체 ref를 넓게 읽기 전에 해당 기술 ref 1개로 빠르게 진입하도록 `AGENTS.md`, `CLAUDE.md`, `.claude/skills/README.md`, `task-intake-router`를 동기화했다. Unity 작업 기본 경로는 `docs/ref/tech/UNITY.md` → `unity/ControlRoom/README.md` → `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md`.
- **Unity ControlRoom 신규 프로젝트 scaffold 완료** (`unity/ControlRoom/`). Unity 6.3 LTS (6000.3.16f1) 채택, 2027-12까지 LTS 지원.
- 폴더: `Assets/{Scenes,Scripts,UI,Art/IconsPng,Resources,Robots/{UrdfSource,ImportedPrefabs},Editor}` + `Packages/manifest.json` + `ProjectSettings/` (unity-smoke 베이스 복사) + `.gitignore` (Unity 표준 + Supabase 키 차단).
- PNG 26개 이관 (`Assets/Art/IconsPng/`: Common/Robot/Sensor/Target/Generated/GeneratedRaw 6 카테고리).
- **폴더 트리 + CLAUDE.md 28개 박음** (`Assets/Scripts/` 11개 하위 + `UI/Parts/` + `IconsPng/` 6 카테고리 + `Tests/{EditMode,PlayMode}/` 등). 각 CLAUDE.md = 그 폴더가 무엇을 담는지 + 명명 규칙 + 주의사항.
- **신규 파일/폴더 룰 영구 메모리 박음**: 폴더는 CLAUDE.md, 파일은 최상단 1~5줄 헤더 주석. 앞으로 모든 신규 파일 생성에 자동 적용.
- Supabase URL **확정**: `https://ueupkrxwybuuqxflstvg.supabase.co`. write path = 로봇 PC anon+RLS 주 쓰기 / Unity read+dispatch만 / service_role 키 미반입.
- **`pose_logs` 테이블 Supabase 적용 완료** (2026-06-02 밤, CLI `db query --linked`). 컬럼 9개 + 인덱스 3개 + RLS 정책 2개 검증 PASS, count=0. 이로써 SCRUM-23 Planned Extension 중 첫 테이블이 Current Applied로 이전됨. 자세히: `docs/status/DECISION-LOG.md` 2026-06-02 최상단.
- **로봇 좌표 저장 부품 박음**: `pose_logs`의 Unity/Python/SQL 3측 진입점 작성. `unity/ControlRoom/Assets/Scripts/Data/RobotPoseEntry.cs` + `Database/PoseLogRepository.cs` + `scripts/pose_logger.py` + `scripts/sql/pose_logs.sql` + `scripts/sql/CLAUDE.md`. 다음 진입: 로봇 PC에 env 박고 `pose_logger.py`를 systemd로 띄우기.
- **Unity 6000.3.16f1 첫 batch import PASS**: `Library/` 12개 하위 생성, `Assets/**/.meta` 83개 자동 생성 (CLAUDE.md.meta 24 + PNG.meta 26 + 그 외), 어셈블리 에러 0건, `Exiting batchmode successfully` + exit 0. Unity Hub에서 Add Project 불필요 — 이미 등록 상태, `unity/ControlRoom` Open 하면 즉시 열림.
- 다음 진입: Unity Hub에서 `unity/ControlRoom` Open → URDF Importer Unity 6 호환성 smoke → UI Toolkit skeleton (UXML/USS/Binder) 시작.
- 자세히: `docs/status/DECISION-LOG.md` 2026-06-02 최상단 2건.

## 2026-06-01 Addendum

- Robot2(`t1@192.168.0.250`, hostname `rb`)에서 Intel RealSense D435 ROS2 smoke PASS. Ubuntu 24.04.4 + ROS2 Jazzy + `realsense2_camera`로 color/depth/aligned depth 토픽이 모두 약 30Hz로 발행됨.
- Robot2 장치 정보: Serial `254522075185`, Product ID `0B07`, Firmware `5.17.0.10`, USB 3.2, ROS launch profile depth `848x480x30`, color `640x480x30`.
- Robot2에서 일반 사용자 접근을 위해 `t1`을 `video,plugdev` 그룹에 추가함. 이후 `rs-enumerate-devices -s`가 sudo 없이 PASS.
- Evidence: `docs/evidence/2026-06-01-robot2-realsense-d435-ros2-smoke.md`
- Windows workstation에서 Intel RealSense D435 streaming smoke PASS. `pyrealsense2==2.58.1.10581`로 depth/color `640x480` frame 수신 확인.
- 장치 정보: Serial `254522075185`, Product ID `0B07`, Firmware `5.17.0.10`, center depth sample `0.159 m`.
- 기존 Mac evidence의 streaming BLOCKED 결론은 macOS Tahoe + Homebrew librealsense 조합에 한정. 카메라 하드웨어와 Windows SDK path는 정상.
- 로봇 실기 통합 결정은 계속 Pi4 + ROS2 `realsense2_camera` 우선. Windows는 bench smoke host로 사용 가능.
- Evidence: `docs/evidence/2026-06-01-realsense-d435-windows-pyrealsense2-smoke.md`

## 한 줄 상태

**Phase 2.9 시연 PASS 확정 — 5트라이얼 정량 평가 다음 세션**: 배터리 11.54V(57.77%)로 부팅 후 parking_node(MultiThreadedExecutor+heartbeat+depth-cache) 가동. 사용자 시연 → 자동주차 동작 PASS 확인. 배터리 감소 -6% (1회 시연당). 동료에게 t1 인계 완료. **다음: 배터리 풀충전(>12.4V) + t1 부팅 검증 + 5트라이얼 정밀도 평가(마커 정면 1m, ±30° 각도, 3회 이상 停止 성공) + rosbag 4종 기록.**

## 현재 방향

- 팀명: UR HYNIX
- 프로젝트 제목: 디지털트윈경비로봇
- 핵심 목표: tb3_1이 박물관/미술관 전시 구역을 순찰하며 액자형 사진 타깃과 센서 이벤트를 감지하면 Unity 관제 화면에 표시되고, tb3_2가 출동해 카메라로 확인하며, 이동 좌표·사진·영상·사운드와 모든 결과가 DB에 기록된다.
- 시나리오 5종: ①폐관 침입자(PIR+LiDAR) ②중요전시품 분실·이동(YOLO) ③화재 의심(온도·레이저 재확인→EVACUATE 워터펌프 분사) ④개장 중 접촉(YOLO 손) ⑤배터리 부족·임무 인계(ArUco 정밀주차→수동 충전 요청). 위험등급 SAFE/WATCH/CHECK/DANGER/EVACUATE. [정본 v18 2026-06-16 — HW/코드 미반영]
- 포함 범위: SLAM/Nav2, 다중 로봇 이벤트 응답, 아두이노 센서 4종(PIR·온도·소리·레이저+워터펌프), Pi Camera, Unity 관제 UI, ROS-TCP, 영상 라이브 스트리밍, DB 기록, 이동 좌표 로그, 미디어 메타데이터 저장, AI 보조 분류, 액자형 중요물품 인식. [정본 v18: LDR·불꽃→온도·레이저·워터펌프]
- 제외 범위: FR5 로봇팔, 실시간 사람 추적, 실제 화재 테스트, 완전 자동 보안 시스템
- **하드웨어 확정**: 별도 Arduino Uno R3 + 미니 브레드보드 → Raspberry Pi USB serial. **별도 층 추가 없음** — Burger 상판 빈 공간(라즈베리파이 반대편)에 양면테이프로 부착. 전원은 OpenCR 5V 핀 → Arduino 5V 핀 점퍼 2줄.
- **병렬 작업 매트릭스**: `docs/ref/PROJECT-PLAN.md` 앞부분에 주차×모듈 표와 S1 1주차 4팀 동시 시작 가이드 추가됨.
- **오늘 추가 요구 반영 (2026-05-28)**: 박물관/미술관 컨셉, 액자형 사진 타깃 보호, 조도 기반 LiDAR 강화 모드, 외부자 PIR+LiDAR 판단을 SSOT에 반영. `pose_logs`/`media_artifacts`/`protected_assets`는 실제 DB 미적용 상태의 SCRUM-23 확장 예정안으로 분리.
- **오늘 회의록 반영 (2026-05-29)**:
  - SLAM: 책상 환경에서 SLAM end-to-end 테스트 성공(스킬화). 경기장에서 SLAM+Unity 좌표값 정렬도 **성공**(PNG 확보)했으나, **LiDAR 높이보다 낮은 가벽** 때문에 벽 매핑이 실패(블로커) — 트랙/가벽 조건 재검토 필요.
  - 사용자 요구사항: Confluence `사용자 요구사항 정의서(3112961)` 수정 보완(세부 diff는 미확인, 회의록 언급 근거).
  - 카메라: RPi 카메라 토픽(`/camera/image_raw`, `/camera/camera_info`, `/camera/image_raw/compressed`) 정상 + `/camera/image_raw` ~30Hz 확인.
  - 녹화: MP4 + ROS bag 동시 저장 스크립트 `/home/pi/camera_recordings/scripts/record_bag_mp4.sh` 구성(영상 즉시 확인용 MP4, 재처리용 rosbag 분리).
  - 비전: 노트북 Ubuntu에서 YOLO/OpenCV 환경 구성 + `yolo11n.pt`로 녹화 영상/실시간 스트림 인식 화면 확인 완료. 프로젝트 전용은 커스텀 학습 필요(예정: 로봇/사람/중요품/불 중심 클래스).

## 현재 Jira 기준

- 에픽: `SCRUM-7` (박물관/미술관 액자 보호형 디지털트윈경비로봇으로 본문 갱신 완료)
- 관리자 스크럼 에픽: `SCRUM-39`~`SCRUM-45` (`스크럼 1`~`스크럼 7`). 스크럼 1/2는 완료, 스크럼 3~7은 해야 할 일.
- 스크럼 1/2 완료 하위 카드: `SCRUM-46`~`SCRUM-51` (팀명 정하기, 사용자 요구사항 정리하기, 프로젝트 주제 정하기, 기능 요구사항 정리하기, Unity 화면 초안 만들기, 비전 자료 조사하기)
- 실제 Sprint 1/2 수동 이동용 새 카드: `SCRUM-67`~`SCRUM-72` (Backlog에서 사용자가 만든 Sprint 1/2로 드래그한 뒤 완료 처리)
- 스크럼 3~7 실행 하위 카드: `SCRUM-52`~`SCRUM-66` (로봇 주행과 센서 연결, Unity 관리자 화면, 데이터 저장과 출동 흐름, AI 비전 리허설, 최종 발표 준비)
- 실행 상세 카드: `SCRUM-8`~`SCRUM-25`. 전체 매핑 표는 `docs/ref/JIRA-MAP.md` 참조

## 외부 SSOT 인덱스 (모든 진입점 한곳에)

| 시스템 | 페이지 | 역할 |
|---|---|---|
| Confluence | [기획안 (UR HYNIX) v12](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/327681) | **외부 정본 SSOT** |
| Confluence | [역할 분배 보드](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1605636) | 5×4 매트릭스 + PNG 2장 |
| Confluence | [2026-05-27 회의록](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1048633) | Day-1 작업 분담 |
| Confluence | [2026/05/29 회의록](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/3932161) | SLAM 테스트 성공 + 경기장 Unity 좌표 정렬 예정 |
| Confluence | [브레인스토밍 마인드맵](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1540099) | 방향 전환 근거 |
| Confluence | [기능 요구사항 정의서 v5](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/2555905) | 액자 보호 기능 요구사항 + 현재/예정 DB 분리 |
| Jira | [SCRUM-7 에픽](https://jason1127.atlassian.net/browse/SCRUM-7) · [보드](https://jason1127.atlassian.net/jira/software/projects/SCRUM/boards/1) | 18 카드 부모 |
| Slack | 채널 `C0B5Q43A27R` (⚠️ 봇 초대 필요) | 팀 소통 |
| GitHub | [URHYNIX/URHYNIX](https://github.com/URHYNIX/URHYNIX) | 코드 정본 |
| 로컬 보드 | `docs/dev-plan-bundle.html` | 단일 HTML 7페이지 |

## 역할 매트릭스 (5 모듈 × 4명)

| 모듈 | 담당자 |
|---|---|
| 백엔드 DB / ROS-TCP 라벨링 / AI (M1) | 김주영, 김선일 |
| 아두이노 메인 보드·통신 (M2) | 박태진, 임현찬, 김주영 |
| 유니티 관제UI · ROS-TCP 통신 · 영상 라이브 스트리밍 (M3) | 김선일, 박태진 |
| 아두이노 센서 (M4) | 김주영, 임현찬, 박태진 |
| 터틀봇 — LiDAR · 카메라 · SLAM · 네비게이션 (M5) | 임현찬, 김선일 |

| 담당자 | 맡은 모듈 수 | 주요 라인 |
|---|---|---|
| 김주영 | 3 (M1·M2·M4) | AI · 백엔드 · 임베디드 데이터 라인 |
| 김선일 | 3 (M1·M3·M5) | 통신 · 관제 · 로봇 통합 라인 |
| 박태진 | 3 (M2·M3·M4) | 하드웨어 ↔ 클라이언트 ↔ 센서 라인 |
| 임현찬 | 3 (M2·M4·M5) | 임베디드 · 로봇 라인 |

## 현재 마일스톤

- **M0 (완료, 2026-05-27)**: SSOT 전환 + 역할 매트릭스 확정 + Confluence 1605636(역할 분배 보드) 발행
- **M1 (진행 예정, Sprint 1 종료 시점)**: tb3_1 순찰 + Unity pose 표시 + DB 스키마 초안 + 보호 대상/미디어 확장 계획
- **M2 (Sprint 2 종료)**: 센서 1종 이벤트 → Unity 마커
- **M3 (Sprint 3 종료)**: tb3_2 출동 시뮬 + 카메라 확인 + DB 저장 전체 흐름 + 좌표/미디어/보호 대상 저장 확장
- **M4 (Sprint 4 종료, 발표)**: 박물관/미술관 액자 보호 컨셉으로 시나리오 4종 시연 + 발표 지표 표

## Day-1 작업 (2026-05-27 즉시 시작 · 확정) — 2026-06-09 Phase 2.9 진행 중

| 팀 | 인원 | 작업 | 관련 SCRUM | 오늘 산출물 |
|---|---|---|---|---|
| **Pi+DB팀** | 김주영, 임현찬 | Raspberry Pi Pi Camera 스트림 확인 + DB 연결 테스트 | SCRUM-19, SCRUM-14 | 카메라 토픽 확인 영상, `events` sample insert 1건 |
| **PIR+DB팀** | 박태진 | Arduino + PIR(인체 감지) 센서값 시리얼 → DB insert 한 줄 통과 | SCRUM-13, SCRUM-14 | Arduino 스케치 + DB insert 로그 / **2026-05-28: Arduino+PIR+시리얼+RPi `/dev/tb3_arduino` 식별까지 통과. DB 단계는 ⚠️ DB 미선정으로 사전 차단 (DECISION-LOG "DB 선정 보류" 참조)** |
| **Unity 문서팀** | 김선일 | Unity 관제 UI에 들어갈 기능 정의 문서화 (운영 대시보드/이벤트 패널/카메라 패널/모드 토글) | SCRUM-9, SCRUM-22 | UI 기능 명세 1장 |

→ Day-1 끝에 PIR → 시리얼 → DB가 한 줄로 통하면 S1 끝까지 자신감 확보.

## 다음 액션 (Phase 2.9 GO 조건 해제까지)

1. **①배터리 충전 (>11.5V)** + **②OpenCR 리셋** + **③케이블 재연결** + **④t1 부팅 검증** (turtlebot3_bringup Dynamixel crash 없는지 확인)
2. **⑤parking_node 5트라이얼 정밀도 평가** (안전 환경에서 0.25m 목표 거리까지 진입 성공률 3회 이상/5회)
3. 시연 GO 조건 해제 후 — 티원 + 젠지 듀얼 ArUco 마커 감지 통합
4. 박물관 시나리오 통합 시연 (액자 타깃 + ArUco 마커 주차 + 이벤트 연쇄)
5. 그 외 잔여 센서(소리/불꽃) + 분류 모델 통합

## Handoff Capsule

**Capsule timestamp**: 2026-05-27 (Day-1 종료 직후) · **Session closer**: 김주영

### Next entrypoint
- **`docs/status/HANDOFF.md`** — 1페이지 진입 캡슐 (5분 내 컨텍스트 + Top 1 액션 + Day-2 진입 흐름)

### Read first (3개 순서)
1. `docs/status/HANDOFF.md` ← **1순위, 이것만 읽으면 출발 가능**
2. `docs/status/PROJECT-STATUS.md` (이 파일 — 역할 매트릭스 + Day-1 작업 + 외부 SSOT 인덱스)
3. `docs/status/DECISION-LOG.md` 가장 아래 5건 (오늘까지 결정 변천)

### Current phase
- Sprint 1 / W1 Day-1 진행 중 (오늘 시작, 종료 검증 대기)
- 3팀 동시 진행: Pi+DB(김주영·임현찬) · PIR+DB(박태진) · Unity 문서(김선일)

### Blockers
- **팀 Slack 채널 봇 권한 부족**: 채널 `C0B5Q43A27R`에 Claude 봇 멤버 초대 필요. 그때까지 결정 공지는 본인 DM으로만 발송 가능.
  - 안전한 다음 행동: 본인 DM으로 받은 메시지를 수동으로 팀 채널에 복붙해 공유.
- ~~DB 미선정~~ → ✅ **해소 (2026-05-28)**: Supabase `ueupkrxwybuuqxflstvg` 잠금, 마이그레이션 적용 완료. DECISION-LOG "DB 선정 완료".
- **로봇 전원 OFF (2026-05-28)** — 라즈베리파이 셧다운 + LiDAR 정지를 위해 메인 스위치 OFF 상태. end-to-end PIR→insert 테스트는 로봇 부팅 후 진행. 절차: 메인 스위치 ON → 30s 부팅 → `tb3-up && tb3-bridge` → PIR 손 흔들기 → `events` row +1 확인.
- **RPi `/etc/urhynix.env` 미작성 (2026-05-28)** — 로봇 부팅 후 한 번만 작성 필요 (`SUPABASE_URL`, `SUPABASE_KEY=service_role JWT`). 자세한 내용: HANDOFF Top 1.
- 그 외 미해결 결정: **none** (방향·하드웨어·역할·Day-1 분담·정합성은 모두 잠금)

### Unfinished decisions
- **none** (다음 세션이 직면할 결정은 Day-1 결과에 따라 분기만 있음)

### First verify (다음 세션이 첫 5분에 돌릴 명령)
```bash
# 1. 진행 상태 빠른 점검
git status
ls -lh docs/dev-plan-bundle.html  # 465KB여야 정상

# 2. 정합성 잔재 0건 확인 (활성 문서)
grep -rn '/turtlebot/\|LiDAR only vs\|expansion plate\|Arduino 층은 LiDAR' docs/ref docs/status docs/dev-plan*.html 2>/dev/null | grep -v 'DECISION-LOG\|build_bundle'

# 3. Day-1 통합 검증 (Top 1 액션)
#    박태진의 Arduino PIR 이벤트가 events 테이블에 한 줄 저장됐는지
#    psql -c "SELECT id, robot_id, event_type, severity, ts FROM events ORDER BY ts DESC LIMIT 5;"
#    (또는 Supabase 대시보드 events 테이블)
```

### Files changed this session (요약)
- SSOT 9개 + HTML 8개 + 번들 + 신규 스킬 2개(`ssot-board-sync`, `decision-broadcast`) + HANDOFF.md 신설 + CLAUDE.md 압축 + Confluence 4페이지 갱신 + Jira 24건 갱신.
- 자세한 변경 이력: `docs/status/DECISION-LOG.md` (오늘 결정 5건 포함)

### Next branch / commit context
- 현재 브랜치: `main` (직접 commit 금지, PR로만)
- 작업자 본인 브랜치 권장: `juyoung`
- 미커밋 파일: PROJECT-STATUS / HANDOFF / CLAUDE.md / 그 외 오늘 변경 SSOT

---

## Evidence Status

| 검증 항목 | 상태 | 비고 (2026-05-29) |
|---|---|---|
| Git 추적 PNG 제거 | ✅ | 2026-06-01 `git ls-files '*.png'` 기준 383개 PNG를 `git rm`으로 제거. 완료 검증은 동일 명령 0건으로 확인 |
| 옛 방향/제거 범위 본문 잔재 grep | ✅ | 활성 문서에서 제거 대상 키워드와 이전 제목 잔재 없음. DECISION-LOG의 전환 기록만 예외 |
| `tb3_1`/`tb3_2` 일관 사용 grep | ✅ | 10개 파일에서 등장 (SSOT 8 + DECISION-LOG + dev-plan.html) |
| 역할 매트릭스 일치 (STATUS / JIRA-MAP / dev-plan.html) | ✅ | M4 = 김주영·임현찬·박태진으로 동기화 |
| 센서 연결 방식 상태 | ✅ | Arduino Uno R3 → Raspberry Pi USB serial, OpenCR 5V 전원 분기로 확정 |
| dev-plan*.html 파싱 OK | ✅ | `python3 html.parser`로 8개 HTML 통과 — 브라우저 로드는 사용자가 최종 확인 |
| dev-plan-bundle.html 브라우저 로드 | ⚠️ | Codex Browser의 `file://` URL 정책 차단으로 미실행. 파서 검증으로 대체 |
| Jira 관리자용 7개 스프린트 에픽 + 하위 작업 | ✅ | 2026-06-02 저녁 이전 열린 SCRUM 카드 완료 처리 후 새 구조 생성. 에픽 `SCRUM-39`~`SCRUM-45`, 하위 작업 `SCRUM-46`~`SCRUM-66`. Sprint 1/2 완료 전환 확인. JQL `project = SCRUM AND statusCategory != Done ORDER BY key ASC` 검증: 20건(Sprint 3~7 에픽 5 + 하위 작업 15) |
| TurtleBot3 live ROS2 bringup | ✅ | `192.168.0.138` / MAC `2c:cf:67:47:38:03` 검증. `/dev/ttyACM0`, `/scan`, `/odom`, `/battery_state`, `/tf` 확인. `/scan` 약 10Hz |
| RViz visual route | ✅ | Robot `DISPLAY=:2`, TigerVNC `5902`, RViz 실행 확인. Mac Screen Sharing 경로는 `vnc://192.168.0.138:5902` |
| ROS-TCP → Unity smoke | ✅ | ROS-TCP-Endpoint `main-ros2` 빌드, `10000` listen, Unity mini project subscriber 등록 확인 (`/scan`, `/odom`, `/battery_state`, `/tf`) |
| SLAM end-to-end 1차 PASS | ✅ | 2026-05-29 책상 환경에서 Robot cartographer 실행 → map save → Unity 임포트까지 검증 PASS. 다음: 경기장 실환경에서 SLAM+Unity 좌표 정렬(plane scale/원점) 재검증 |
| RPi 카메라 토픽/프레임레이트 확인 | ✅ | 2026-05-29 `/camera/image_raw` ~30Hz + `/camera/camera_info` + `/camera/image_raw/compressed` 정상(회의록 3932161 근거). 녹화 스크립트 `/home/pi/camera_recordings/scripts/record_bag_mp4.sh` 구성 |
| 경기장 벽 매핑 실패 원인 기록 | ⚠️ | 2026-05-29 PNG 확보/좌표 정렬은 성공했으나, LiDAR 높이보다 낮은 가벽으로 벽 매핑 실패(회의록 3932161). 트랙/가벽 조건 변경 또는 매핑 전략 보완 필요 |
| TurtleBot helper aliases | ⚠️ | Mac helper는 `/Users/family/.zshrc` 반영 완료. Robot helper installer는 `/tmp/install_tb3_helpers.py` 복사 후 SSH timeout으로 원격 실행 미검증 |
| Arduino PIR 플래시 (cli 자동화) | ✅ | 2026-05-28 `arduino-cli` 1.5.0 + AVR core 1.8.8로 `sketches/pir_led/`를 `/dev/cu.usbmodem1101`(Arduino UNO)에 업로드, 시리얼 raw 캡처 30초에서 MOTION/CLEAR 로그 확인. 핀: 코드는 PIR=D7·LED=D2, SSOT는 PIR=D2 → 다음 작업분에서 정렬 |
| `arduino-flash` 스킬 등록 | ✅ | `.claude/skills/arduino-flash/SKILL.md` + README Embedded/Hardware 표 추가. 센서 4종 반복 플래시 표준화 |
| LDR(조도) 센서 A0 정렬 검증 | ✅ | 2026-05-28 LDR + 10kΩ 분압회로를 SSOT 일치 핀(A0)으로 재배선·재플래시·재캡처. 시리얼 `[LDR] A0=29~214` 진동으로 빛 변화 추종 + PIR 모션 동시 동작 충돌 없음 확인. 잔여: PIR=D7→D2 정렬 |
| RPi USB serial 식별 + 권한 영구화 | ✅ | 2026-05-28 `/dev/ttyACM0`=OpenCR · `/dev/ttyACM1`=Arduino UNO(vendor 2341) 분리 확인. `usermod -aG dialout kim` + `/etc/udev/rules.d/99-urhynix-arduino.rules` (MODE=0666, SYMLINK `tb3_arduino`) 적용. 8초 캡처에서 `[MOTION] detected -> LED ON`, `[LDR] A0=...` 정상 수신. |
| DB 선정 + 마이그레이션 적용 | ✅ | 2026-05-28 신규 Supabase 프로젝트 `ueupkrxwybuuqxflstvg` (ap-northeast-1) 선정. Management API SQL endpoint로 `db/migrations/2026-05-27_init_security.sql` 적용 (4테이블 + seed). service_role JWT INSERT 정상(row `c8c389b9-...`). publishable key는 RLS 차단(정상 보안). 이전 mungmungfit 시도는 egress quota 초과로 폐기. |
| 실제 DB 구조 재확인 + 보호 컨셉 SSOT 정정 | ✅ | 2026-05-28 Supabase REST service_role 조회: `session_meta`/`events`/`dispatches`/`camera_captures` HTTP 200, `pose_logs`/`media_artifacts`/`protected_assets` HTTP 404(PGRST205). 따라서 좌표·사진·영상·사운드·액자 보호 테이블은 현재 구조가 아니라 SCRUM-23 확장 예정안으로 SCHEMA/CONTRACT/STATUS/HANDOFF/HTML에 분리 표기. `python3 docs/whiteboards/build_bundle.py` 재빌드 + 8개 dev-plan HTML 파싱 OK. |
| Jira/Confluence 보호 컨셉 반영 | ✅ | 2026-05-28 Jira `SCRUM-7/9/14/15/16/21/23` 갱신. Confluence `기획안 (UR HYNIX)` page 327681 v12 갱신 + `기능 요구사항 정의서` page 2555905 v5 갱신 + `2026/05/28` draft 2883585 갱신. 폴더 parent 직접 생성은 Atlassian tool의 spaceId/parentId 해석 문제로 실패하여 정본 페이지 갱신으로 대체. |
| Confluence 회의록 기반 SSOT 자동화 예약 | ✅ | 2026-05-28 Codex automation `urhynix-daily-ssot-sync-from-confluence` 생성. 매일 18:00에 `/Users/family/jason/URHYNIX`에서 당일 Confluence 회의록을 찾아 로컬 SSOT 우선 갱신, 현재/예정 상태 분리, dev-plan 번들 재빌드, Confluence/Jira 반영 리포트 생성. |
| TurtleBot ↔ Unity ROS-TCP 재기동 (`turtlebot` 프로젝트) | ✅ | 2026-05-28 새 Unity 프로젝트 `/Users/family/jason/turtlebot`에 ROS-TCP-Connector v0.7.0 + smoke 자산 설치. RegisterSubscriber 4/4(`/scan`·`/odom`·`/battery_state`·`/tf`) + ESTAB 2 세션 확인. Mac IP `192.168.0.67`(DHCP 변경), 로봇 IP `192.168.0.138` 유지. |
| Mac → Robot SSH 공개키 인증 | ✅ | 2026-05-28 `ssh-keygen ed25519` + `ssh-copy-id kim@192.168.0.138` 완료. `ssh -o BatchMode=yes kim@... hostname` → `kim-desktop` 무대화형 응답. 이후 모든 tb3-* 명령이 비번 prompt 없이 동작. `scripts/tb3.sh`에 `tb3-key-setup` 헬퍼 추가 (협업자 머신용). |
| Arduino → DB 자동 insert (PIR + LDR) | ✅ | 2026-05-28 robot `arduino_bridge` tmux에서 PIR `[MOTION]` → events insert (severity=3) + LDR A0<200 edge-trigger → event_type='dark' (severity=1) 검증. 누적 `events` 45+ row. `sb-by-type` 결과 `pir 44 / dark 1`. |
| 경기장 SLAM v1 (회전만 5바퀴) | 🟡 | 2026-05-29 18:14 경기장 중앙에서 회전만 5~6바퀴 매핑 → `arena_v1` 산출. 158×151 @ 0.05m/px = **7.90×7.55m**, origin [-3.767,-3.939]. robot `~/maps/` + 로컬 `docs/evidence/maps/arena_v1/` + Unity `Assets/Maps/` 3곳 저장 OK. 픽셀: occupied 1.9% / free 98.1% / unknown 0.0%. 가벽이 LiDAR 반경 3.5m 일부 외 → 발표용 임팩트 약, `arena_v2` 하이브리드 재매핑 후보. eval.md 참조. |
| DHCP IP 변경 대응 (.138 → .33) | 🟡 | 2026-05-29 경기장 Wi-Fi에서 robot DHCP `.33` 할당. Unity `SampleScene.unity:151` + `RosSmokeDashboard.cs:10` rosIP 일시 patch (.138→.33). known_hosts에서 .138 제거. tb3-ip는 MAC sweep으로 자동 발견하므로 helper 코드는 미변경. 다음 세션 출발 시 IP 재검증 + 같은 패치 반복 필요 가능. |
| 매핑 실패 진단 정정 (회의록 5/29 기반) | 🟥 | 2026-05-29 Confluence 회의록 page `3932161` 김주영 발언으로 확인: arena_v1 가벽 매핑 실패의 **진짜 원인은 "라이다 높이 > 가벽 높이" (수직 차원)**, 회전 한계가 아님. 하이브리드 매핑 권장 폐기. DECISION-LOG/eval.md/HANDOFF/map-quality-eval 스킬 정정 완료. **다음 매핑 전 가벽 실측 높이 측정 + 192mm 이상 보강 또는 vision/마커 fallback 결정 필요**. |
| Pi 카메라 + YOLO 환경 + MVP 4 클래스 잠금 (회의록 5/29 기반) | ✅ | 2026-05-29 임현찬 진척: Pi 카메라 토픽 3종 30Hz 정상 + MP4/rosbag 동시 녹화 스크립트 + 노트북 YOLO/OpenCV 실시간 인식 통과. **MVP 학습 클래스 4종 잠금: 로봇·사람·중요품·불**. 2026-06-02 Teachable Machine 스파이크와 별도 범위로 유지. |
| 신규 128GB SD + Ubuntu 24.04.4 + ROS2 Jazzy 풀 부트스트랩 | ✅ | 2026-06-01 SD 16GB→128GB 교체 후 cloud-init 사전설정으로 부팅 → ros-jazzy-turtlebot3 메타(2.3.6) + cartographer + nav2 + dynamixel + hls-lfcd + ld08_driver(jazzy) + ros_tcp_endpoint(0.7.0) 한 세션 셋업. udev `/dev/tb3_arduino` + `/dev/tb3_opencr` + `/dev/tb3_lidar` 추가. `/etc/urhynix.env` 템플릿 작성 (SUPABASE_KEY 빈 상태). evidence: `docs/evidence/2026-06-01-new-sd-128gb-ros2-jazzy-bootstrap.md`. |
| 학원 Wi-Fi(codelab_5G) 영구 연결 + mDNS + IP-drift zero-touch | ✅ | 2026-06-01 netplan `60-wifi.yaml`로 wlan0=192.168.0.82(Mac과 같은 망) 영구 자동 연결. 랜선 분리 + 재기동 검증 PASS. avahi-daemon → `urhynix-robot.local` mDNS 작동. **B+C 작업: Unity Scene/Script rosIP=`urhynix-robot.local` + `scripts/tb3.sh`에 TB3_HOSTNAME + tb3-ip mDNS 우선 추가**. Mac `~/.ssh/config` 별칭 `Host urhynix-robot`. 이후 DHCP IP 변경 시 ssh/helper/Unity 모두 자동 follow (zero-touch). `ip-drift-resync` 스킬은 안전망으로만 남음. |
| Arduino UNO + OpenCR + LDS-03 USB 12+ 단계 검증 | ✅ | 2026-06-01 lsusb: Arduino UNO `2341:0043` + OpenCR `0483:5740` + CP2102(LDS-03) `10c4:ea60` 모두 정상. udev 심볼링크 3종 작동. Arduino 시리얼 캡처: "=== PIR + LDR Test === / Warming up.........". 스케치 살아있음 확인. (재플래시는 D2 핀 정렬용으로 별도 잔여.) |
| RealSense 카메라 모델 확정 (D435, D435i 아님) | ✅ | 2026-06-01 저녁 `sudo rs-enumerate-devices` 검증: Product ID `0B07`, Serial `254522075185`, Asic Serial `350423023342`, FW `5.15.1.55`, USB 3.2 SuperSpeed, `Imu Type: IMU_Unknown`. Depth/RGB/IR stream profile 전체 노출(Depth 1280×720@30 등). evidence: `docs/evidence/2026-06-01-realsense-d435-mac-sdk-smoke.md`. **영향**: VIO 폐기, RGB-D SLAM + LDS-03 + wheel odom으로 매핑. 박물관 계획 95% 유지. |
| RealSense Mac SDK streaming 검증 | 🟥 | 2026-06-01 저녁 `rs-hello-realsense` Frame timeout 15s + Dispatcher `mutex lock failed: Invalid argument`. 원인 3중 호환 이슈: ① macOS Monterey+ sudo 필수(해결) ② brew formula 빌드 옵션 누락(`HWM_OVER_XU`/`FORCE_RSUSB_BACKEND`) ③ macOS Tahoe(26.3.1) 공식 미지원 + adhoc 서명 IOUSBHost entitlement 부재. 결정: Pi4 이전(HANDOFF 잔여 액션 #6). |
| Pi Camera 모델 확정 (Module v2 / Sony IMX219) | ✅ | 2026-06-01 저녁 신규 SD에서 첫 진단: `lsmod`에 `imx219` 로드, `bcm2835_unicam`+`bcm2835_isp`+`bcm2835_codec` 활성, `i2c-10` 0x10 응답, `/dev/video0`=unicam-image, `/dev/media0~4`. 즉 **하드웨어/드라이버 100% 정상**. 모델: Raspberry Pi Camera Module v2 (Sony IMX219, 8MP, 3280×2464). evidence: `docs/evidence/2026-06-01-rpi-camera-imx219-source-build.md`. |
| Pi Camera user-space 도구 (rpicam-apps/libcamera Pi fork) | ✅ | 2026-06-01 16:36 빌드 PASS. libcamera Pi fork `v0.7.1+rpt20260429` + rpicam-apps `v1.12.0` 6분만에 빌드 (capabilities: egl:1 qt:1 drm:1 libav:0). 함정 3건 잡음: ① Ubuntu 24.04 ports repo 미제공(소스 빌드) ② libepoxy-dev 누락(추가) ③ libav API mismatch(`-Denable_libav=disabled`). evidence: `docs/evidence/2026-06-01-rpi-camera-imx219-source-build.md`. 재사용 스크립트: `scripts/build-picamera.sh`. |
| Pi Camera 캡처 검증 (rpicam-still + rpicam-vid) | ✅ | 2026-06-01 16:38 `rpicam-still -n -t 2000 --width 1920 --height 1080` 1920×1080 JPG 283KB 캡처 + `rpicam-vid --framerate 30 -t 5000` 1280×720@30Hz × 5초 H.264 2.9MB 캡처 PASS. Mac 미리보기에서 시각 검증. 산출물: `docs/evidence/pi_cam_test_2026-06-01.{jpg,h264}`. **모드 노출**: 3280×2464@21fps, 1920×1080@47fps, 1280×720@30~60fps, 640×480@103fps. |
| 박물관 시연 듀얼 카메라 Unity 라이브 (젠지 + 티원) | ✅ | 2026-06-02 오후 사용자 확인 "둘다 잘나옴". 젠지 `/tb3_2/camera/image_raw/compressed` 30Hz @ 640×480 (지연 1~2초 → 실시간) + 티원 `/tb3_1/camera/color/image_raw/compressed` 32.985Hz @ 640×480. 잡은 함정 4건: ssh-copy-id 1회 자동화, `compressed_image_transport` 별도 설치, `camera_namespace:=tb3_1` 토픽 구조, robot reboot 시 IP변경 → mDNS 자동 follow. evidence: `docs/evidence/2026-06-02-camera-ros2-topic-unity-batch-setup.md` Phase 8. |
| Custom YOLO 라벨링/검수/오탐 정제 UI | ✅ | 2026-06-10 `scripts/yolo_training/custom_yolo_studio.py` + T1 `t1_compressed_mjpeg_server.py`로 브라우저 학습실 PASS. 주소 `http://127.0.0.1:8766/`, low-latency preview `http://192.168.10.250:8090/preview.jpg`. Space 촬영, ROI 자동연사, SAM2/rembg/GrabCut bbox 보정, `best.pt` 최신 자동 로드, 앱 안 검수(`검수 시작`, `←/→`, `D 삭제`, `Delete/Backspace`, `Esc`), `review_masks` cache 검수 이미지, `N 오탐 배경 저장` hard-negative 빈 라벨 샘플까지 구현. 배경 오탐은 `.pt` 직접 수정이 아니라 `negative_*.jpg` + 빈 `.txt`를 모아 재학습하는 루프로 결정. 최신 확인 URL `http://127.0.0.1:8766/?v=hard-negative-20260610-1806-clean`. evidence: `docs/evidence/2026-06-10-mac-yolo-realsense-live.md`. |
| Robot safe shutdown 문서화 | 🟡 | 2026-06-10 안전 셧다운 절차를 `docs/ref/tech/ROS2-ROBOT.md`와 `docs/status/HANDOFF.md`에 반영. 표준 순서: ROS/카메라/브릿지 프로세스 정리 → `ssh t1@192.168.10.250 'sudo poweroff'` → ping 100% loss 확인 → 메인 슬라이드 스위치 OFF → LiPo 분리/충전 상태 기록. 문서 업데이트 시점 점검에서는 T1 ping 2/2 응답 + 8090 status fresh라 실제 셧다운 완료는 미확인. |
| Custom YOLO ROI mask bbox 자동 라벨 보정 | ✅ | 2026-06-10 `ROI crop -> mask -> bbox -> YOLO txt` 경로 추가. `/api/auto_label_roi`는 rembg 설치 시 rembg mask, 현재 기본 환경은 OpenCV GrabCut, 실패 시 ROI fallback. UI에 `ROI 안 물체 bbox 자동 보정` 체크박스와 `bbox 보정/fallback` 카운터 표시. 검증: py_compile PASS, T1 8090 fresh, local API status PASS, 테스트 캡처 1장 `engine=grabcut fallback=false` 후 jpg/txt 즉시 삭제. 스킬화: `.claude/skills/urhynix-yolo-capture-train` + 공용 하네스 반영. |
| Custom YOLO 실시간 세그 preview | ✅ | 2026-06-10 ROI 안에서 물체를 움직이며 mask/bbox를 화면으로 볼 수 있는 `실시간 세그 보기` 추가. `/api/segment_frame.jpg`는 T1 8090 preview frame을 사용해 저장 없이 반투명 mask + bbox JPEG를 반환. preview 전용 GrabCut은 최대 220px/2 iterations로 경량화. 검증: HTTP 200 JPEG 5회 `0.399~0.867s`(1회 제외 없이 안정), Browser snapshot에서 체크박스 표시 확인. |
| Custom YOLO 데이터셋 다중 삭제 UI | ✅ | 2026-06-10 촬영 목록에 체크박스 + `전체 선택` + `라벨 없음 선택` + `선택 삭제` 추가. `/api/delete_items`는 선택 항목의 jpg/txt를 같이 삭제하고 삭제 전 confirm을 띄움. 검증: py_compile PASS, 빈 payload 삭제 smoke `deleted_files=0`, Browser snapshot에서 버튼/선택 카운터 표시 확인. 이후 기존 잘못된 데이터셋 삭제 완료 상태: train/val 이미지·라벨 0장, 기존 `.pt` run은 보존. |
| Custom YOLO 탐지 보기 저지연화 | ✅ | 2026-06-10 최신 run `학습대상_20260610_153621/weights/best.pt` 로드 후 탐지 보기 끊김 개선. `/api/detect_frame.jpg`를 full snapshot 대신 T1 8090 preview frame 기반으로 바꾸고 브라우저 detect polling delay를 900ms→80ms로 단축. 검증: detect API 5회 `0.287~0.695s`(기존 단일 호출 `2.196s`), HUD `fast best.pt` 표시 확인. SAM은 탐지 표시 속도 문제가 아니라 라벨 품질 개선용으로 유지. |
| Teachable Machine / Keras 객체 분류 스파이크 기준 | 🟡 | 2026-06-02 14:30 회의 기준. 학습 도구 Google Teachable Machine, 모델 형식 TensorFlow/Keras, 클래스 `빈공간`·`박스`·`마우스(검정/흰색)`·`손`. 목적은 로봇 카메라 영상 객체 분류 테스트. Jira `SCRUM-44/61` 반영 완료, 실제 모델 파일/추론 로그 검증은 다음 단계. |
| 2026-06-02 Jira 최신 업데이트 | ✅ | `SCRUM-44`, `SCRUM-51`, `SCRUM-54`, `SCRUM-56`, `SCRUM-61`, `SCRUM-62`, `SCRUM-64` 설명에 14:30 회의 내용 반영 완료. 검증: Atlassian `_editjiraissue` 응답으로 각 issue description 갱신 확인. |
| 2026-06-01 회의록(로봇 역할 분리 + UI 요구사항) SSOT 반영 | ✅ | Confluence page `5111810`의 “tb3_1=비전(D435) / tb3_2=센서+Arduino+PiCam(IMX219)” 및 UI 버튼/상호작용 정의를 **문서로만** 반영. 구현/장착/토픽 검증은 별도 evidence 필요. 반영 위치: `docs/status/DECISION-LOG.md`, `docs/ref/PROJECT-PLAN.md`. |
| 기술별 ref 라우팅 | ✅ | 2026-06-02 `docs/ref/TECH-INDEX.md` + `docs/ref/tech/{UNITY,ROS2-ROBOT,ARDUINO-SENSORS,DATABASE-SUPABASE,VISION-CAMERA,OPS-HARNESS}.md` 추가. 루트 진입 문서와 `.claude/skills/README.md`, `task-intake-router`에서 discoverable. 검증: `rg -n "docs/ref/TECH-INDEX|docs/ref/tech/UNITY" AGENTS.md AGENT.md CLAUDE.md ai-context/START-HERE.md .claude/skills docs/ref docs/status`. |
| ControlRoom Phase 2.7 — 젠지 Pi Camera 라이브 결선 + 4종 함정 영구 자산화 | ✅ | 2026-06-04 ControlRoom 신 프로젝트(Unity 6.3 LTS)에 `/tb3_2/camera/image_raw/compressed` 30Hz 라이브 RGB 결선 완료. 사용자 확인 "카메라 화면 잘나옴". 산출물: `Scripts/Ros/CameraStreamSubscriber.cs`(76) + `Editor/CameraStreamSetup.cs`(60) + UXML 1줄(`VisualElement`→`Image`) + `CameraPanelView.cs`(30→43 추가만) + `ControlRoomApp.cs ConfigureRos()` + `ProjectSettings: Standalone: ROS2` + robot `server.py:125` `.rstrip("\x00").strip()` 패치 + `loginctl enable-linger kim`. 잡은 함정 4종(#13 KillUserProcesses, #14 server.py [:-1], #15 macOS open -a, #16 ★ Unity ROS1 default → ROS2 define) 모두 영구 패치/스킬화. UI Contract Lock 침해 UXML 1줄(태그만)만. 컴파일 31 assemblies + Console 0 errors + robot RegisterSubscriber OK. evidence: `docs/evidence/2026-06-04-controlroom-camera-live-pass.md`. 스킬 보강: `.claude/skills/robot-camera-bringup/SKILL.md`(#13~16) + `.claude/skills/unity-camera-panel/SKILL.md`(ROS2 define + Image element + open -a). 다음: 티원 D435 같은 패턴 + Phase 2.8 Gemma 4 12B 통합. |
