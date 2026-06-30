<!-- opencode: 2026-06-30 - Unity ControlRoom 목업→실데이터 교체 로드맵 + 컴포넌트 인덱스. Coded with OpenCode; high-cost model review recommended. -->
# Unity ControlRoom Mock → Real Data Roadmap

> 변경 목적: ControlRoom의 목업/하드코딩 데이터를 실제 ROS/DB/Config 기반 데이터로 교체하고, 파일 크기가 커지지 않도록 컴포넌트화하며, 리뷰하기 쉬운 인덱스를 함께 유지한다.
> 범위: `unity/ControlRoom/Assets/` (Scripts/UI/Database/Simulation/Resources)
> 작성일: 2026-06-30

## 1. 외부 도구 검증

### 1.1 codebase-memory-mcp (`DeusData/codebase-memory-mcp`)
- **형태**: 단일 정적 바이너리, 14개 MCP tool, 158개 언어 지원, OpenCode 자동 감지/설정.
- **장점**: 커밋된 `.codebase-memory/graph.db.zst`로 팀원 간 reindex 생략, call graph/impact 분석, 토큰 절감.
- **단점**: 에이전트 설정 파일(opencode.json/AGENTS.md)을 직접 수정하며, 현재 프로젝트가 작아 효과 대비 복잡도가 큼.
- **판정**: **지금 도입하지 않는다.**
  - C# 스크립트 ~50개, 문서 체계가 이미 `CLAUDE.md` + `TECH-INDEX.md`로 인덱싱되어 있음.
  - 목업→실데이터 교체는 파일 수가 적고 교차 영향이 명확해 grep/read로 충분.
  - 프로젝트가 150개 이상의 소스 파일 또는 멀티 레포로 확장되면 재검토.

### 1.2 code-review-graph (`tirth8205/code-review-graph`)
- **형태**: Python 패키지(`pip install code-review-graph`), Tree-sitter + SQLite 그래프, OpenCode 설정 자동화.
- **장점**: PR 리뷰/변경 영향 범위 분석, 시맨틱 검색, 커뮤니티 시각화.
- **단점**: 새 Python 의존성 + 가상환경 필요, 임베딩/igraph 등 선택 그룹 추가 시 무거워짐.
- **판정**: **지금 도입하지 않는다.**
  - 이미 `.claude/skills/code-review-graph-ops`와 `change-impact-map` 스킬이 있음.
  - 본 작업의 영향 범위는 `change-impact-map` 스킬 1회 호출로 충분히 그릴 수 있음.
  - 대규모 리팩터링 또는 PR 자동 리뷰가 필요해지면 재검토.

### 1.3 대안: 경량 인덱싱 규칙
- 평가 대신 **이 문서 자체를 인덱스**로 사용.
- 각 폴드별 `CLAUDE.md`는 이미 존재하며, 신규 파일은 최상단 1~5줄 헤더 주석으로 self-documenting.
- 교체 진행 상황은 아래 표로 관리 → diff 리뷰 시 한눈에 확인 가능.

## 2. 프로젝트 구조 (핵심 트리)

```text
unity/ControlRoom/
├── Assets/
│   ├── Art/
│   │   └── IconsPng/               # PNG 아이콘 (Common/Robot/Sensor/Target/Generated)
│   ├── Editor/                     # 씬 자동 생성, 칩라 패널 셋업
│   ├── Resources/
│   │   ├── FeatureConfig/default_features.json
│   │   ├── MapConfig/office_base_map.json
│   │   ├── RobotConfig/default_robots.json
│   │   ├── RosConfig/ros_endpoint.json
│   │   ├── SensorConfig/default_sensors.json
│   │   ├── SituationConfig/default_situations.json
│   │   └── SupabaseConfig/supabase.json
│   ├── Scenes/ControlRoomMain.unity
│   ├── Scripts/
│   │   ├── App/                    # ControlRoomApp, ControlRoomState, ControlRoomEvents
│   │   ├── Data/                   # RobotInfo, SensorInfo, EventRow, DispatchRow, LogRow, ...
│   │   ├── Database/               # SupabaseClient, Repositories, SupabaseDbService
│   │   ├── Design/                 # UiTokens, IconNames, QuickActionIds
│   │   ├── Features/               # FeatureRegistry
│   │   ├── Map/                    # MapView, layers, actions
│   │   ├── Persistence/            # PatrolRepository
│   │   ├── Robot/                  # (예정) 로봇 명령 서비스
│   │   ├── Ros/                    # Subscriber/Publisher
│   │   ├── Sensors/                # SensorRegistry
│   │   ├── Services/               # PatrolService, ActiveRobotService
│   │   ├── Simulation/             # FakeSensorData, DemoScenarioService
│   │   └── UI/                     # View/Binder (25개+)
│   ├── StreamingAssets/Maps/       # arena_v5, arena_v5_pretty 슬롯
│   ├── Tests/
│   ├── UI/                         # UXML/USS/Token
│   └── UI Toolkit/                 # Unity default theme
├── Packages/com.unity.robotics.ros-tcp-connector/
├── ProjectSettings/
└── README.md
```

## 3. 목업 → 실데이터 교체 대상

| # | 파일 | 현재 상태 | 실데이터 소스 | 교체 방향 | 우선순위 | 상태 |
|---|------|-----------|---------------|-----------|----------|------|
| A1 | `Simulation/FakeSensorData.cs` | tb3_1용 가짜 배터리/소음/온도 Perlin 생성 | ROS topic (`/battery_state`, `/sensors/*`) | ROS 연결 감지 시 자동 비활성, 미연결 로봇만 fake 유지 | P1 | ✅ 완료 |
| A2 | `Simulation/DemoScenarioService.cs` | 버튼 누륾 시 가짜 경보/로그 발화 | `SituationConfig/default_situations.json` + 실제 ROS test 명령 | SituationConfig SSOT 기반 동적 처리, `demoMode=true`에서만 모의 발화(실제 연동은 Phase 4) | P1 | ✅ 완료 |
| A3 | `UI/HomePageView.cs` | 세션 누적 KPI 카운터 (이벤트/경보/출동) | DB `events`/`dispatches` count 또는 세션 카운터 중 선택 | KPI 정책 결정 후 반영. 현재는 세션 카운터로 시연 가능하므로 **유지/선택** | P2 | 대기 |
| A4 | `UI/ProtectedTargetView.cs` | 하드코딩 `frameA/B`, `objectA` | `Resources/MapConfig/office_base_map.json`의 `protectedTargets[]` | config 기반 동적 카드 생성, theft 시나리오는 상태 toggle → 실제 DB `protected_assets` 적용 시 교체 | P1 | ✅ 완료 |
| A5 | `UI/WaypointListView.cs` | 하드코딩 5개 버튼 (`wp-1`~`wp-5`) | `PatrolService.Points` 또는 `MapConfig/waypoints[]` | `PatrolService` 구독 → 동적 버튼 생성/선택/로그 | P1 | ✅ 완료 |
| A6 | `UI/SensorCardListView.cs` | pir/sound/temp/laser 4개 하드코딩, laser는 "미결선" 고정 | `Sensors/SensorRegistry` + `SensorConfig/default_sensors.json` | config 기반 카드 동적 생성; laser disabled 플래그 | P1 | ✅ 완료 |
| A7 | `Database/SupabaseDbService.cs` | dispatch INSERT 시 `simulated:true` 강제, pose 로그 robot_id=default | `ControlRoomEvents.RaiseDispatchRequested`에 simulated 플래그 추가, pose는 실제 robot_id | `simulated` 값을 이벤트 파라미터에서 결정; pose robot_id 동적 | P1 | ✅ 완료 |
| A8 | `Database/DispatchRepository.cs` | `simulated` 컬럼 SELECT | DB 스키마 동일 | 컬럼 그대로 유지, 실데이터 식별용이므로 **유지** | P3 | 유지 |
| A9 | `Editor/ControlRoomSceneSetup.cs` | 씬 생성 시 FakeSensorData/DemoScenarioService 강제 부착 | 설정/플래그 기반 선택 부착 | `ControlRoomApp`에서 코드로 생성, 씬 YAML 비의존. 실제 연동은 Phase 4 | P2 | ✅ 완료 |
| A10 | `Resources/MapConfig/office_base_map.json` | `museum_floor1` placeholder (origin 0,0, 800x600) | `StreamingAssets/Maps/arena_v5.{png,json}` 실제 SLAM 맵 | MapConfig 로더가 StreamingAssets 카탈로그를 우선 사용하도록 변경 | P2 | 대기 |
| A11 | `Resources/SensorConfig/default_sensors.json` | topic `/sensors/*` | 실제 arduino_bridge_quad 발행 토픽 | 토픽명 교차검증 후 수정 | P1 | 대기 |
| A12 | `Resources/SituationConfig/default_situations.json` | `noise` 누락, icon emoji | DemoScenarioService 시나리오 목록과 정합 | `noise` 추가, icon은 PNG iconName으로 교체 | P2 | 대기 |
| A13 | `UI/RecordsPageView.cs` | 494줄, 3서브탭+칩+로드+렌더 모두 한 파일 | - | 컴포넌트 분리 (아래 §4) | P1 | 대기 |

## 4. 컴포넌트화 계획

### 4.1 RecordsPageView 분리

| 새 파일 | 책임 | 예상 줄수 |
|---------|------|-----------|
| `UI/Records/RecordsPageView.cs` | 서브탭 전환, 하위 View 조립, 이벤트 구독 | ~110 |
| `UI/Records/IRecordsSubtab.cs` | 서브탭 인터페이스 | ~10 |
| `UI/Records/RecordsLogSubtab.cs` | 로그 칩 필터 + 로그 카드 렌더 | ~160 |
| `UI/Records/RecordsTimelineSubtab.cs` | 이벤트/출동 머지 + 타임라인 카드 렌더 | ~120 |
| `UI/Records/RecordsKpiSubtab.cs` | KPI 4장 비동기 로드/표시 | ~80 |
| `UI/Records/RecordsChipBar.cs` | 칩 UI 생성/토글/상태 관리 (공통) | ~100 |
| `UI/Records/RecordsRenderHelpers.cs` | 카드/시간 포맷 헬퍼 | ~80 |

- `Assets/Scripts/UI/Records/` 폴드 생성 + `CLAUDE.md` 추가.
- 기존 `UI/RecordsPageView.cs` 삭제, coordinator로 재작성.
- `ControlRoomBinder`의 `using URHYNIX.ControlRoom.UI.Records;` 갱신.

### 4.2 SensorCardListView 분리 (후보)
- `UI/Sensors/SensorCardView.cs` — 단일 센서 카드.
- `UI/SensorCardListView.cs` — config 순회해서 카드 생성.
- 단, 현재 113줄이라 당장 분리는 선택; config 기반 동적화 시 분리 권장.

## 5. 구현 Phase

### Phase 0 — 문서/영향 범위 고정 (이번 세션)
- [x] 프로젝트 트리 스캔
- [x] 외부 도구 검증 및 판정
- [x] 목업→실데이터 교체 대상 목록 작성 (본 문서)
- [x] `PROJECT-PLAN.md` Intake Verdict 갱신
- [x] `PROJECT-STATUS.md` Evidence Status 갱신

### Phase 1 — 컴포넌트 분리 + 검증 루프
- [x] `UI/Records/` 폴드 + 7개 클래스/인터페이스 생성
- [x] `RecordsPageView.cs` coordinator로 교체
- [x] `ControlRoomBinder` 갱신
- [x] `unityctl check` → `unityctl script get-errors` → 0 errors 확인

### Phase 2 — Config/Registry 기반 동적 UI
- [x] `SensorCardListView` → `SensorRegistry` 기반 동적 생성
- [x] `WaypointListView` → `PatrolService` 기반 동적 생성
- [x] `ProtectedTargetView` → `MapConfigData` 기반 동적 생성
- [ ] `DemoScenarioService` ↔ `SituationConfig` 정합
- [x] `unityctl check` after each file

### Phase 3 — DB/ROS 실데이터 정합
- [ ] `FakeSensorData` ROS 연결 감지 자동 비활성
- [ ] `SupabaseDbService` dispatch `simulated` 플래그화
- [ ] `SupabaseDbService` pose_logs robot_id 동적
- [ ] `MapConfig` 실제 StreamingAssets 맵 카탈로그 우선 사용
- [ ] end-to-end Play Mode 검증 (DB live 필요)

### Phase 4 — 문서 동기화
- [ ] `UNITY-CONTROLROOM-CONVERSION-PLAN.md` §3.5 이후 항목 갱신
- [ ] `PROJECT-STATUS.md` PASS/BLOCKED 갱신
- [ ] `HANDOFF.md` next entrypoint 갱신
- [ ] `DECISION-LOG.md` "목업→실데이터 교체" 결정 기록

## 6. 검증 루프

각 Phase마다 다음 명령을 반복:

```bash
cd /Users/family/jason/URHYNIX/unity/ControlRoom
unityctl check
# 또는
unityctl script get-errors
```

- **PASS 기준**: `scriptCompilationFailed: false`, `isCompiling: false`, `Errors: 0`.
- **경고**: 기존 CS0618/CS0219/CS0414 경고는 당장 차단하지 않음. 신규 warning이 발생하면 해당 Phase에서 해결.
- **Play Mode**: 컴파일 PASS 후 Unity Editor 직접 Play → 홈/대응/기록 탭 smoke.

## 7. 파일/폴드 명명 규칙

- C# 클래스: `PascalCase.cs`, 파일명=큰명.
- View 하위 폴드: `UI/<Domain>/` (예: `UI/Records/`, `UI/Sensors/`).
- UXML: `PascalCase.uxml`.
- Config: `default_<plural>.json`.
- 모든 신규 폴드에 `CLAUDE.md` 3~10줄.
- 모든 신규 C# 파일 최상단에 `// <파일명> — <한 줄 역할>` 헤더.

## 8. 인덱스 (리뷰용)

| 영역 | 핵심 파일 | 데이터 소스 | 교체 상태 |
|------|-----------|-------------|-----------|
| 홈 대시보드 | `HomePageView.cs` | `ControlRoomState` + 이벤트 | 세션 카운터 유지, DB 카운터 선택 |
| 대응 탭 | `ResponsePageView.cs` | `EventRepository`/`DispatchRepository` | ✅ 실데이터 |
| 기록 탭 | `RecordsPageView.cs` → `UI/Records/*` | `LogRepository`/`EventRepository`/`DispatchRepository` | ✅ 실데이터, 분리 완료 |
| 센서 카드 | `SensorCardListView.cs` | `SensorRegistry`/`default_sensors.json` | ✅ 동적 생성 완료 |
| 순찰 지점 | `WaypointListView.cs` | `PatrolService`/`office_base_map.json` | ✅ 동적 생성 완료 |
| 보호대상 | `ProtectedTargetView.cs` | `office_base_map.json` | ✅ 동적 생성 완료 |
| 시나리오 | `DemoScenarioService.cs` | `default_situations.json` | 목업 → P1 |
| Fake 센서 | `FakeSensorData.cs` | ROS topic fallback | fallback 유지, 자동 on/off |
| DB 쓰기 | `SupabaseDbService.cs` | 이벤트 + ROS pose | simulated 플래그화 P1 |

## 9. 잔여 리스크

- `protected_assets` 테이블은 아직 DB에 적용되지 않음(SCRUM-23 예정). 보호대상 실데이터는 config 단계로 한정.
- `events` 테이블에 실제 센서 이벤트가 쌓이려면 로봇 측 `arduino_bridge_quad` + DB insert 경로가 살아 있어야 함.
- `SupabaseDbService`의 `OnDispatchRequested` simulated 플래그 추가는 `ControlRoomEvents` 시그니처 변경 → 모든 호출자(`Map/Actions/DispatchHereAction`, `Map/Actions/SituationDispatchAction` 등) 동시 수정 필요.
- `unityctl script validate`가 실패 상황에서도 `succeeded=True`를 반환하는 버그가 있어, 반드시 `get-errors` 또는 `check`로 병행 검증.
