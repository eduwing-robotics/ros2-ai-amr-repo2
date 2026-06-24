# Project Plan — Map Waypoint Editor (MWE)

_파일 목적: Unity ControlRoom 맵 클릭 웨이포인트 에디터 + 순찰 실행 기능의 실행 계약형 플랜. project-planning 스킬 산출. 메인 PROJECT-PLAN.md(스프린트용)의 비대화 방지를 위해 분리. 2026-06-23 잠금. 구조 검증은 bash scripts/check-planning.sh 기준._

Unity ControlRoom 맵뷰에서 저장맵을 보고, 클릭으로 순찰 좌표를 찍고, 순서를 짜고, 선택 로봇을 그 경로로 출동시키는 기능. 레퍼런스(PyQt UR암 그리드 에디터)의 UX 아이디어를 ROS2/Nav2 맥락으로 재설계.

## Project Snapshot

- 기능 약칭: MWE / 순찰 편집기
- 기반: 기존 `unity-live-map-twin` Map 레이어(클릭→좌표변환→출동, /tf 마커 이미 작동, 2026-06-16 젠지 검증)
- 신규 알맹이: 순서 있는 웨이포인트 편집 + 일괄 순찰 실행 + 역할 상호교환 + 오프라인 내성
- 대상 로봇: 젠지(tb3_2), 티원(tb3_1) — 둘 다 순찰 수행 가능해야 함
- 현재 맵: arena (origin -0.734,-2.161, res 0.05, 57x58)

## Intake Verdict

- 분류: implementation(기능 구현) + 선행 planning. 기존 Map 레이어 확장이라 신규 아키텍처 아님.
- 다음 스킬: `big-task`(구현 오케스트레이션). 서브에이전트는 탐색·정형문서 한정.
- 규모: 중간(5 Phase). 단발이 아니라 phase 계약 필요.

## Problem

현재 맵뷰는 라이브 `/map`만 그려서 로봇이 꺼지면 빈 화면이 되고, 클릭 후 동작은 단발 출동(`DispatchHereAction`)뿐이다. 순서 있는 순찰 경로를 UI에서 만들고 실행하거나 저장할 수단이 없다. 로봇 역할이 코드에 하드코딩(젠지=sensor, 티원=vision)이라 서로 바꿔 쓸 수 없다.

## Goal

작업이 끝나면 다음이 가능하다.

- 저장된 arena 맵이 로봇 연결과 무관하게 UI에 상시 표시된다.
- 맵 클릭으로 웨이포인트를 추가/삭제/전체삭제하고 번호와 연결선으로 순서를 본다.
- 선택한 로봇이 그 순찰 경로를 순서대로 주행한다.
- 젠지와 티원의 역할을 런타임에 바꿔 둘 다 같은 편집기로 순찰을 발행한다.
- Wi-Fi가 끊겨도 UI와 좌표 저장이 유지되고(로컬 우선) 복구 후 동기화된다.
- 맵뷰가 화면에서 가장 크게 보인다.

## Non-Goals

- 동시 2로봇 협조 순찰, 동적 장애물 회피 튜닝.
- 3D 맵, 줌/팬 고급 제스처, 웨이포인트 드래그 재배치(순서 변경은 버튼만).
- Nav2 파라미터 편집, 순찰 중 일시정지/재개.

## Constraints

- 파일 비대화 금지: 1책임 1파일, 액션은 파일당 1개, 300줄 근처 분리.
- 가벼운 안 우선: 추가 스레딩 도입 금지, ROS-TCP 콜백·코루틴으로 비동기 처리.
- 좌표는 map 프레임 기준이며 구동측은 같은 저장맵 + AMCL이어야 유효.
- 로봇 IP 하드코딩 금지(hostAddress/alias 사용), 도메인 210 / RMW fastrtps 통일.
- 시크릿(Supabase 키)은 git 제외 유지.

## Assumptions

- ROS-TCP-Connector가 Nav2 FollowWaypoints 액션을 지원한다(미지원 시 Phase 3 fallback 가동).
- arena 저장맵 origin/resolution이 구동측 AMCL 맵과 일치한다.
- 좌표 프레임이 안정적이다(정적맵 + AMCL, 라이브 Cartographer 아님).

## Risks

- ROS-TCP가 FollowWaypoints 액션을 미지원하면 순찰 실행 재설계 필요(중간). 완화: Phase 3 결정게이트 선검증.
- StreamingAssets 런타임 로드가 에디터와 빌드에서 다를 수 있음. 완화: streamingAssetsPath + UnityWebRequest 통일.
- 역할교환 시 네임스페이스 충돌(젠지 non-ns vs 티원 ns). 완화: `urhynix-dual-fullstack-unity` 규칙 준수.
- 파일 비대화. 완화: 1책임 1파일 + 300줄 게이트.

## Dependencies

- 구동측(다른 PC)에서 Nav2 + AMCL + 같은 저장맵 운영.
- Supabase(`PatrolRepository` 동기화) — anon 키, RLS.
- 도메인 210 ROS2 그래프 가용.

## Success Metrics

- 로봇 OFF 상태에서도 arena 맵이 화면 최대로 보인다.
- 맵 클릭 N회로 번호 경로가 시각화되고 저장/삭제가 동작한다.
- 순찰 시작으로 선택 로봇이 경로를 주행한다(영상 evidence).
- 젠지와 티원을 전환해도 동일 편집기로 순찰이 발행된다.
- Wi-Fi 끊긴 채 저장 성공, 복구 후 DB 반영 확인.

## Naming Contract

- 경로 데이터: `PatrolRoute` { routeId, mapId, robotId, points } / `PatrolPoint` { seq, x, y, theta }
- 런타임 서비스: `PatrolService` (add/remove/clear/reorder/run, 순수 C#)
- 영속: `PatrolRepository` (로컬 우선 + Supabase 비동기)
- 마커: `PatrolMarkerLayer` (번호 + 연결 폴리라인)
- 저장맵 로더: `StaticMapLoader` (StreamingAssets 맵을 MapImageLayer로)
- 활성 로봇: `ActiveRobotService` (역할교환 SSOT, `RobotTabView` 선택과 연동)
- 순찰 발행: `FollowWaypointsPublisher` (per-robot `/{robotId}/follow_waypoints`)
- 맵 ID 기본값: arena
- 쓰지 않을 이름: 고정 role 문자열(capabilities 배열로 대체), 하드코딩 IP, 단일 office_base 가정

## File Map

- create: `unity/ControlRoom/Assets/StreamingAssets/Maps/arena.png`
- create: `unity/ControlRoom/Assets/StreamingAssets/Maps/arena.json`
- create: `unity/ControlRoom/Assets/StreamingAssets/Maps/CLAUDE.md`
- create: `unity/ControlRoom/Assets/Scripts/Map/StaticMapLoader.cs`
- create: `unity/ControlRoom/Assets/Scripts/Data/PatrolRoute.cs`
- create: `unity/ControlRoom/Assets/Scripts/Services/PatrolService.cs`
- create: `unity/ControlRoom/Assets/Scripts/Services/ActiveRobotService.cs`
- create: `unity/ControlRoom/Assets/Scripts/Persistence/PatrolRepository.cs`
- create: `unity/ControlRoom/Assets/Scripts/Map/PatrolMarkerLayer.cs`
- create: `unity/ControlRoom/Assets/Scripts/Map/Actions/RemoveWaypointAction.cs`
- create: `unity/ControlRoom/Assets/Scripts/Map/Actions/ClearWaypointsAction.cs`
- create: `unity/ControlRoom/Assets/Scripts/Map/Actions/RunPatrolAction.cs`
- create: `unity/ControlRoom/Assets/Scripts/Ros/FollowWaypointsPublisher.cs`
- modify: `unity/ControlRoom/Assets/Scripts/Map/Actions/AddWaypointAction.cs`
- modify: `unity/ControlRoom/Assets/Scripts/Map/Actions/MapActionRegistry.cs`
- modify: `unity/ControlRoom/Assets/Scripts/Data/RobotInfo.cs`
- modify: `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json`
- modify: `unity/ControlRoom/Assets/Scripts/App/ControlRoomApp.cs`
- modify: `unity/ControlRoom/Assets/Scripts/App/ControlRoomEvents.cs`
- modify: `unity/ControlRoom/Assets/UI/Parts/MapPanel.uxml`
- modify: `unity/ControlRoom/Assets/UI/ControlRoomMain.uxml`
- modify: `unity/ControlRoom/Assets/UI/ControlRoomStyle.uss`
- keep: `unity/ControlRoom/Assets/Scripts/Map/MapCoordinateSystem.cs`
- keep: `unity/ControlRoom/Assets/Scripts/Map/MapImageLayer.cs`
- keep: `unity/ControlRoom/Assets/Scripts/Map/MapInteractionController.cs`
- keep: `unity/ControlRoom/Assets/Scripts/Ros/MapSubscriber.cs`
- keep: `unity/ControlRoom/Assets/Scripts/Ros/RobotPoseSubscriber.cs`
- keep: `unity/ControlRoom/Assets/Scripts/Ros/DispatchPublisher.cs`
- keep: `unity/ControlRoom/Assets/Scripts/UI/RobotTabView.cs`
- keep: `unity/ControlRoom/Assets/Scripts/Data/MapConfigData.cs`
- candidate: 런타임 저장 위치 persistentDataPath/patrols (Phase 1 결정)
- candidate: PGM에서 PNG 변환 방식 사전변환 스크립트 (Phase 1 결정)

## Folder Boundaries

- `unity/ControlRoom/Assets/StreamingAssets/Maps/` — 저장맵 이미지 + 메타(읽기 전용 런타임 로드). 로컬 `CLAUDE.md`로 경계 명시.
- `unity/ControlRoom/Assets/Scripts/Services/` — ROS·UI 비의존 순수 로직(PatrolService, ActiveRobotService).
- `unity/ControlRoom/Assets/Scripts/Persistence/` — 저장·동기화 책임 분리(PatrolRepository).
- 런타임 사용자 데이터는 Assets 밖 persistentDataPath/patrols 에 기록(빌드 후 쓰기 가능).

## Skill Routing

`project-planning`(현재) 다음, 토픽·스키마를 코드에 박기 전 `api-contract-guard`, 구현 오케스트레이션은 `big-task`, 각 Phase 컴파일·Play 검증은 `unity-unityctl-ops`(IPC 막히면 `unity-scene-yaml-patch`), UI 잠그기 전 `unity-ui-interaction-audit`, DB 점검은 `supabase-db-health-ping`, 키 점검은 `secret-scan`, 완료 선언 전 `evidence-review`, 상태 반영은 `ssot-trio-update`. 좌표·맵 도메인은 `urhynix-teleop-waypoint-capture`, `map-pgm-waypoint-autogen`, `unity-live-map-twin`, `live-map-pull-from-domain` 참조.

## Impact Map Summary

- UI 표면: MapPanel(툴바 추가), ControlRoomMain/Style(레이아웃), RobotTabView(활성 로봇).
- 데이터: RobotInfo(capabilities), default_robots.json, 신규 PatrolRoute, StreamingAssets 맵.
- ROS 계약: per-robot `/{robotId}/follow_waypoints`(신규), 기존 `/goal_pose`, `/tf`, `/map`.
- DB: pose_logs 또는 신규 patrol_routes(Phase 5 결정).
- 동반 문서: `docs/ref/CONTRACT.md`(토픽), `docs/ref/SCHEMA.md`(테이블), `docs/status/PROJECT-STATUS.md`.

## Sub-Agent Opportunities

- 넓은 코드 탐색이 필요하면 `Explore`로 Map/Ros/App 레이어 의존 그래프만 수집(컨텍스트 절약).
- 정형 문서 삽입(evidence, SSOT 항목)은 `doc-writer` 서브에이전트로 분담.
- 설계·리뷰·아키텍처 판단은 메인 모델이 직접 수행(서브에이전트 격상 금지).

## Doc Sync Targets

- `docs/ref/PLAN-map-waypoint-editor.md`
- `docs/status/PROJECT-STATUS.md`
- `docs/status/DECISION-LOG.md`
- `docs/status/HANDOFF.md`
- `docs/ref/CONTRACT.md`
- `docs/ref/SCHEMA.md`

## Phase Plan

### Phase 1 — Static Map Display + Layout 최대화 [구현완료/컴파일PASS]
Goal: 저장 arena 맵이 로봇 연결과 무관하게 UI에 표시되고 맵뷰가 화면에서 가장 크다.
Files: create `StaticMapLoader.cs` + `arena.png/json` + `StreamingAssets/Maps/CLAUDE.md`; modify `ControlRoomMain.uxml`, `ControlRoomStyle.uss`, `MapPanel.uxml`, `ControlRoomApp.cs`; candidate 2건(저장위치, PGM변환) 확정.
Skills: `unity-live-map-twin`, `unity-unityctl-ops`, `unity-scene-yaml-patch`, `map-pgm-waypoint-autogen`.
Verification: 로봇 OFF에서 Play 시 arena 맵 렌더(에디터 창 직접 확인), 클릭 시 HUD가 map 좌표(-0.73~2.12 범위)로 표시, 라이브 /map 켜지면 덮어쓰기 동작.
Doc Sync: `docs/ref/PLAN-map-waypoint-editor.md`, `docs/status/PROJECT-STATUS.md`.
Exit Criteria: 오프라인 맵 표시 + 맵뷰 최대 + 클릭 좌표 정확.
Decision Gates: 라이브 /map과 저장맵 동시 존재 시 라이브 우선; 저장위치 persistentDataPath 채택.

### Phase 2 — Waypoint Editor Core [구현완료/컴파일PASS]
Goal: 클릭으로 번호 마커와 연결선을 만들고 마지막 제거 및 전체삭제가 동작한다.
Files: create `PatrolService.cs`, `PatrolMarkerLayer.cs`, `RemoveWaypointAction.cs`, `ClearWaypointsAction.cs`; modify `AddWaypointAction.cs`, `MapActionRegistry.cs`, `ControlRoomEvents.cs`, `MapPanel.uxml`.
Skills: `unity-ui-interaction-audit`, `unity-unityctl-ops`, `urhynix-teleop-waypoint-capture`.
Verification: 클릭 N회로 번호 1..N 마커 + 폴리라인 생성, 버튼/우클릭으로 마지막·전체 삭제 반영, PatrolService 상태와 마커 카운트 일치 dump.
Doc Sync: `docs/ref/PLAN-map-waypoint-editor.md`, `docs/ref/CONTRACT.md`.
Exit Criteria: 추가·삭제·전체삭제와 시각화가 일치한다.
Decision Gates: 추가 트리거를 좌클릭 직접으로 채택(레퍼런스 UX), 우클릭은 메뉴 유지.

### Phase 3 — Patrol Execution (Nav2) [구현완료/컴파일PASS · 로봇 라이브 검증 완료/잔여 맵정합]
Goal: 순찰 시작 버튼으로 선택 로봇이 웨이포인트 순서대로 주행한다.
Files: create `FollowWaypointsPublisher.cs`, `RunPatrolAction.cs`; modify `ControlRoomApp.cs`.
Skills: `api-contract-guard`, `urhynix-teleop-waypoint-capture`, `evidence-review`, `unity-unityctl-ops`.
Verification: 순찰 시작 시 per-robot follow_waypoints goal 발행 확인(ros2 action list/echo), 1점 baseline 후 다점, 같은 저장맵+AMCL 전제 확인.
Doc Sync: `docs/ref/PLAN-map-waypoint-editor.md`, `docs/status/DECISION-LOG.md`.
Exit Criteria: 다점 순찰 1바퀴 성공.
Decision Gates: FollowWaypoints 액션 채택, ROS-TCP 미지원이면 goal_pose 순차 fallback.
Note: 2026-06-23 젠지 실측: Nav2/액션/Unity관찰 PASS, 잔여=좌표↔맵 불일치·localize 방향(evidence 2026-06-23-genji-nav2-patrol-test.md). 다음: 새 SLAM 매핑→웨이포인트 재캡처로 해결.

### Phase 4 — Role Interchange (젠지 티원) [구현완료/컴파일PASS]
Goal: 활성 로봇 전환 시 순찰·출동 대상이 따라가고 두 로봇 모두 순찰을 수행한다.
Files: create `ActiveRobotService.cs`; modify `RobotInfo.cs`, `default_robots.json`.
Skills: `api-contract-guard`, `unity-unityctl-ops`, `unity-ui-interaction-audit`.
Verification: 탭에서 젠지에서 티원 전환 후 순찰 시작 시 해당 로봇 토픽으로 발행, 둘 다 capabilities에 patrol, 미보유 capability엔 액션 비활성(AppliesTo).
Doc Sync: `docs/ref/PLAN-map-waypoint-editor.md`, `docs/ref/CONTRACT.md`.
Exit Criteria: 두 로봇 모두 동일 편집기로 순찰 발행 가능.
Decision Gates: 네임스페이스 규칙(젠지 non-ns, 티원 ns) 충돌은 dual-fullstack 규칙 준수.

### Phase 5 — Persistence, Resilience, Layout Close [구현완료/컴파일PASS · DB 적용 이월]
Goal: 경로를 로컬 저장·불러오기하고 Wi-Fi가 끊겨도 안전하며 패널 레이아웃을 마감한다.
Files: create/complete `PatrolRepository.cs`; modify `ControlRoomApp.cs`, `ControlRoomStyle.uss`.
Skills: `supabase-db-health-ping`, `api-contract-guard`, `secret-scan`, `evidence-review`, `ssot-trio-update`, `session-retro`.
Verification: 저장 후 재시작 불러오기 라운드트립, Wi-Fi 내린 상태 저장 즉시 성공(로컬), 복구 후 Supabase 반영, db_ping으로 행수 증가, 1280과 1920 폭에서 맵뷰 최대.
Doc Sync: `docs/ref/SCHEMA.md`, `docs/status/HANDOFF.md`, `docs/status/PROJECT-STATUS.md`.
Exit Criteria: 오프라인 저장 + 온라인 동기화 + 레이아웃 마감 + 문서 정합.
Decision Gates: 경로 저장 테이블은 신규 patrol_routes 채택(pose_logs는 로그 성격).
Note: 로컬 영속(persistentDataPath/patrols) 구현 완료. patrol_routes.sql DB 적용 이월.

## Later Backlog

- 순찰 중 일시정지/재개 및 단일 웨이포인트 점프.
- 웨이포인트 드래그 재배치, 줌/팬.
- 동시 2로봇 협조 순찰, 충전소 자동 복귀.
- LiDAR scan 오버레이, 3D 로봇 모델.

## Handoff Notes

- 시작점은 Phase 1: `StaticMapLoader.cs`와 arena 저장맵 배치부터.
- 좌표 변환은 `MapCoordinateSystem.cs`(SSOT)를 그대로 쓰고 새로 만들지 않는다.
- 액션은 `IMapAction` + `MapActionRegistry` 확장점에만 추가한다.
- 첫 검증 명령: `bash scripts/check-planning.sh` 후 `unity-unityctl-ops`로 컴파일 PASS.

## Open Questions

- FollowWaypoints 액션의 ROS-TCP 지원 여부(Phase 3 선검증).
- 순찰 중 일시정지 필요 여부(현재 Non-Goal).
