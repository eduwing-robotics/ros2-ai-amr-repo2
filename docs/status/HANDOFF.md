<!-- opencode: 2026-06-30 - Phase 3 준비 완료. 고비용 모델 리뷰 체크리스트 추가. Coded with OpenCode; high-cost model review recommended. -->
# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-06-30 밤 — **🗺️ 가재보맵 통합 + 컴파일 블로커 해소 + 비침습 구독 역할분리 결정.**

- **컴파일 풀림**: unityctl bridge 6에러(CS0453 1·CS0029 4·CS0246 1, bridge 패키지 자체 버그) 메인 패치 → **0에러 PASS**(`Csc Assembly-CSharp.dll` 재빌드 + `get-errors` 0). 에디터 비포커스 stale은 `set frontmost`+Cmd+R+로그 offset으로 검증.
- **티원 마커 fix**: root cause = `dual_marker_up.sh`가 티원을 `endpoint=no`로 기동(Unity `RosConnectionManager`는 로봇별 전용 endpoint `.250:10000` 필요). → 티원 `yes` 영구수정, ep.log `RegisterSubscriber(/tb3_1/pose) OK` 확인.
- **가재보맵 통합**: `jaebo_v1` 2D 슬롯(`pgm_to_map_slot.py`, `arena_v\d+` regex와 격리) + `jaebo_v1.sdf`. 3D sdf 뷰 신설(`Map/SdfWallSpawner.cs` 벽89 box→Cube, `Map/Map3DView.cs` 천장뷰 RenderTexture, `MapPanelView` 2D/3D 탭 실동작). 컴파일 0에러, **런타임 육안 미검증**.
- **역할분리 결정(중요)**: 로봇 운영(bringup·map_server·AMCL·주행=publish)은 **데스크탑(팀)**, 우리 Unity는 **구독만(passive twin)** — 로봇 도메인 점유 0(팀 사용 보장). Phase 2를 "데스크탑 AMCL + 우리 구독"으로 재정의. ([[unity-passive-pose-twin]]/[[ros2-noninvasive-pose-tap]])
- **🎯 다음 액션**: ① Unity Play → `jaebo_v1` 슬롯·3D 탭(벽89)·티원 초록마커 육안 + 3D 좌표 정합(ponytail 1차안) 축·부호 조정 ② 데스크탑 운영 연동(우리는 구독만) ③ 가재보 공간서 데스크탑 AMCL → 트윈 추종. 자세히: `docs/status/DECISION-LOG.md` 2026-06-30 최상단.

**이전(2026-06-30 낮)**: Phase 3 준비(FakeSensor ROS-off·DemoScenario SSOT·Supabase 동적화) + 기록탭 컴포넌트 분리 — bridge 6에러로 컴파일 막혔던 것 이번 해소. **이전(2026-06-29)**: 기록 탭(Phase 3) + DB Repository 확장 + 메인 리뷰.

---

## ⚡ Top 1 Action (가장 최신)

**고비용 모델 리뷰: Phase 3 준비 코드 + bridge 컴파일 에러 분기**

- **배경**: 실제 로봇/ROS 연동은 고비용 모델과 함께 진행하기로 결정. 지금은 인터페이스 분기/설정 기반 동적화만 끝낸 준비 상태.
- **관련 파일**:
  - Simulation: `unity/ControlRoom/Assets/Scripts/Simulation/FakeSensorData.cs`, `unity/ControlRoom/Assets/Scripts/Simulation/DemoScenarioService.cs`
  - UI: `unity/ControlRoom/Assets/Scripts/UI/ScenarioPanelView.cs`
  - Config: `unity/ControlRoom/Assets/Resources/SituationConfig/default_situations.json`
  - DB: `unity/ControlRoom/Assets/Scripts/Database/SupabaseDbService.cs`
  - Events/Actions: `unity/ControlRoom/Assets/Scripts/App/ControlRoomEvents.cs`, `unity/ControlRoom/Assets/Scripts/Map/Actions/DispatchHereAction.cs`, `unity/ControlRoom/Assets/Scripts/Map/Actions/SituationDispatchAction.cs`
  - App bootstrap: `unity/ControlRoom/Assets/Scripts/App/ControlRoomApp.cs`
  - UXML: `unity/ControlRoom/Assets/UI/Parts/LeftControlPanel.uxml`
- **다음 액션**:
  1. 아래 **고비용 모델 리뷰 체크리스트**를 검토.
  2. `unityctl bridge` 6 compile error가 본 작업과 무관한지 판단. 필요 시 bridge 패키지 다운그레이드/패치 결정.
  3. Unity Editor 재기동 후 `unityctl script get-errors` 재확인.
  4. `unityctl exec`로 `SensorVerifyConsole.SwitchTo("tb3_2")` → `Dump()` 런타임 검증.

---

## 🔍 고비용 모델 리뷰 체크리스트

### 1. 아키텍처/계약 검토
| # | 항목 | 파일 | 질문 |
|---|---|---|---|
| 1.1 | `FakeSensorData` 자동 on/off | `Simulation/FakeSensorData.cs` | `RobotConnectivityMonitor.IsOnline()`을 `Update()`에서 폴링하는 방식이 실제 연결/끊김에 충분히 빠른가? timeout 3초 이내에 fake가 덮어쓰지 않는가? |
| 1.2 | `DemoScenarioService` 모드 분리 | `Simulation/DemoScenarioService.cs` | `demoMode=false`일 때 버튼 비활성화만으로 실제 운영 시 오동작을 막을 수 있는가? 실제 ROS 보안 이벤트 subscriber와 중복 발화 우려는 없는가? |
| 1.3 | `RaiseDispatchRequested` 시그니처 변경 | `App/ControlRoomEvents.cs` | `simulated` bool을 5번째 인자로 추가한 설계가 향후 실제 출동/모의 출동을 명확히 구분하는가? 호출자 6곳이 모두 올바르게 갱신됐는가? |
| 1.4 | `SupabaseDbService` pose robot_id | `Database/SupabaseDbService.cs` | `RobotPoseFeed.OnRobotPose` per-robot 이벤트를 소비해 `pose_logs.robot_id`를 동적으로 쓰는 흐름이 멀티로봇 시나리오에서 정확한가? `RobotPoseSubscriber`(`/tf`)와 중복 쓰기 가능성은 없는가? |
| 1.5 | Simulation 서비스 생명주기 | `App/ControlRoomApp.cs` | `CreateSimulationServices()`에서 `FindObjectOfType` 후 중복 생성 방지. 씬에 이미 `FakeSensorData`/`DemoScenarioService`가 있는 경우와 충돌하지 않는가? |

### 2. 코드 품질/안전성 검토
| # | 항목 | 파일 | 질문 |
|---|---|---|---|
| 2.1 | null/empty 방어 | `Simulation/DemoScenarioService.cs`, `UI/ScenarioPanelView.cs` | `SituationConfig` 로드 실패 시 동작이 graceful한가? |
| 2.2 | 딕셔너리 누수 | `Database/SupabaseDbService.cs` | `poseStates` 딕셔너리가 로봇 추가/제거 시 계속 커지지 않는가? 현재 로봇 2대라 문제 없지만, 장기 운영 시 클리어 지점이 필요한가? |
| 2.3 | 이벤트 누수 | `Database/SupabaseDbService.cs` | `RobotPoseFeed.OnRobotPose` 구독/해제가 `OnDestroy`에서 정확히 처리됐는가? |
| 2.4 | UI Toolkit 동적 생성 | `UI/ScenarioPanelView.cs` | `Button` 인스턴스의 `clicked` 이벤트에 람다가 캡처한 `s.situationId`가 의도한 값을 갖는가? 동일한 JSON 항목에 대한 클로저 문제는 없는가? |
| 2.5 | JSON 직렬화 | `Resources/SituationConfig/default_situations.json` | `noise` 항목의 `sensorTrigger="sound"`가 실제 센서 ID(`SensorInfo.sensorId`)와 일치하는가? 대소문자/오타 확인 필요. |

### 3. 실제 로봇 연동 준비도 검토 (고비용 모델이 채울 부분)
| # | 항목 | 현재 상태 | 필요한 결정/작업 |
|---|---|---|---|
| 3.1 | FakeSensorData 완전 제거 | ROS 연결 시 skip | 실제 시연 시 `FakeSensorData` 컴포넌트를 아예 비활성화할 것인가, 아니면 미연결 fallback으로 유지할 것인가? |
| 3.2 | DemoScenarioService 실제 모드 | `demoMode=false`일 때 버튼 비활성화 | 실제 보안 이벤트(화재/침입/소음/도난)가 ROS topic으로 들어오면 어떤 subscriber가 `ControlRoomEvents.RaiseScenarioTriggered` 또는 `RaiseAlert`를 발화할 것인가? |
| 3.3 | 출동 명령 실제 발행 | `DispatchPublisher`가 `/goal_pose` 발행 중 | `simulated=false` 출동에 대해 Nav2 `goToPose`가 실제로 실행되는지, `patrol_waypoints_bridge.py`와의 계약이 맞는지 확인 필요. |
| 3.4 | DB 실제 쓰기 검증 | `SupabaseDbService` 큐잉 구현됨 | 실제 Supabase 설정 하에서 `dispatches`/`pose_logs`/`logs` insert가 정상 동작하는지, RLS 정책이 anon key에 맞춰져 있는지 확인 필요. |
| 3.5 | Sensor topic 교차검증 | `default_sensors.json` topic `/sensors/*` | 실제 `arduino_bridge_quad`의 발행 토픽명과 일치하는지, `pir`/`sound`/`temp`/`laser` 네이밍이 맞는지 확인 필요. |

### 4. 문서/SSOT 동기화 검토
| # | 항목 | 파일 | 질문 |
|---|---|---|---|
| 4.1 | ROADMAP 상태 | `docs/ref/UNITY-MOCK-TO-REAL-ROADMAP.md` | A1/A2/A7/A9가 ✅로 표시됐는가? Phase 3/4 체크리스트가 현재 상태와 일치하는가? |
| 4.2 | Evidence Status | `docs/status/PROJECT-STATUS.md` | bridge 에러와 본 `Assets/Scripts` 컴파일 상태가 분리되어 기록됐는가? |
| 4.3 | HANDOFF | `docs/status/HANDOFF.md` | 다음 세션 진입점과 고비용 모델 리뷰 항목이 명확한가? |

---

## 📋 First 5 Min Checklist

```bash
# 0. 오늘 변경 요약 확인
cd /Users/family/jason/URHYNIX
git status --short

# 1. Unity 컴파일 확인 (Editor 재기동 후)
cd /Users/family/jason/URHYNIX/unity/ControlRoom
unityctl check
unityctl script get-errors --project /Users/family/jason/URHYNIX/unity/ControlRoom

# 2. 동적 UI 런타임 확인
unityctl exec --project /Users/family/jason/URHYNIX/unity/ControlRoom \
  --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.SwitchTo("tb3_2")'
unityctl exec --project /Users/family/jason/URHYNIX/unity/ControlRoom \
  --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()'
#    → `sensor-value-pir`, `sensor-value-sound`, `sensor-value-temp`, `sensor-value-laser` 라벨이 보여야 함

# 3. 하드코딩 잔여 정적 확인
grep -R "sensor-(pir|sound|temp|laser)-value\|wp-[1-5]\"\|target-frame-a\|target-object-a" \
  /Users/family/jason/URHYNIX/unity/ControlRoom/Assets/Scripts \
  /Users/family/jason/URHYNIX/unity/ControlRoom/Assets/UI || echo "하드코딩 잔여 0건"

# 4. 시나리오 버튼 동적 생성 확인
unityctl exec --project /Users/family/jason/URHYNIX/unity/ControlRoom \
  --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()' | grep scenario
```

→ **통과 기준**: `Assets/Scripts` 기준 compile error 0 + `SensorVerifyConsole.Dump()`에 `sensor-value-*` 라벨 4개 + grep 잔여 0건 + 시나리오 버튼 4개

---

## 🔧 If Stuck (빠른 복구)

| 증상 | 명령 |
|------|------|
| `unityctl exec` project lock | Unity Editor 완전 종료 후 재시작, 또는 `unityctl session clean` 후 재시도 |
| bridge 로드 안 됨 | `unityctl init --project /Users/family/jason/URHYNIX/unity/ControlRoom` 후 Editor 재기동 |
| `SensorVerifyConsole.Dump()` 라벨 4개 안 보임 | `tb3_2` 선택 후 센서 탭 활성화 확인; `default_sensors.json`에 `robotId: tb3_2` 센서 4개 있는지 확인 |
| 동적 UI 미생성 | `RightStatusPanel.uxml`, `LeftControlPanel.uxml`에서 고정 행/버튼 제거 여부 확인 |
| bridge compile error 6건 | `Packages/com.unityctl.bridge/Editor/Commands/DescribeTypeHandler.cs` 확인. 본 작업과 무관하면 패키지 다운그레이드 또는 고비용 모델 판단 |

---

## 📚 More Info (상세 내용)

| 문서 | 용도 |
|------|------|
| **`docs/ref/UNITY-MOCK-TO-REAL-ROADMAP.md`** | Phase 2/3 완료 항목 + Phase 4 체크리스트 |
| **`docs/status/PROJECT-STATUS.md`** | Evidence Status + Handoff Capsule |
| **`docs/status/DECISION-LOG.md`** | 외부 도구 판정 + 목업 교체 결정 이력 |
| **`docs/status/HANDOFF-FULL.md`** | 이전 모든 세션 기록 |
| **`../ref/TECH-INDEX.md`** | 작업별 빠른 문서 라우팅 |

---

## ✅ 한줄정리

**2026-06-30: Unity ControlRoom Phase 3 준비 완료(FakeSensorData ROS 연결 감지 off, DemoScenarioService SSOT 정합, SupabaseDbService simulated/robot_id 동적화). 실제 로봇/ROS 연동은 고비용 모델 리뷰 후 진행. `Assets/Scripts`는 컴파일 OK, `unityctl bridge` 패키지에서 6 compile error 발생 중. 다음 세션: 고비용 모델 리뷰 → Editor 재기동 → SensorVerifyConsole 런타임 검증.**
