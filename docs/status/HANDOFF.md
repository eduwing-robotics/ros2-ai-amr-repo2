<!-- opencode: 2026-07-01 - 2.5D 우클릭 메뉴 + 로봇 마커 추가, 합성이벤트 검증 PASS. -->
# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-07-08 (**🏛️ 2.5D 박물관 디오라마 완성 + dogfood 감사 P1~7 수정 — 컴파일 PASS, 육안 검증만 남음** — Gallery Room 팩 마젠타는 URP 변환으로 해결(`GalleryRoomUrpUpgrade.cs` 재사용 가능), 장식은 전부 `StreamingAssets/Maps/arena_shared.decor.json` 데이터 주도: 검정 그리드 바닥·벽 직선화(표시 전용, 로봇 pgm 불변)·액자+벽당 트랙레일 조명·니케상/스핑크스(scale=실높이m)·충전독 연한 티원색 패치·**차폐벽(wall_13, 평소 열림→화재 출동 시 하강→10초 자동 개방)**·TB3 burger 실모델 마커. dogfood 감사(신규 스킬 `urhynix-dogfood-audit`)로 잡은 Blocker 2건 수정 완료: 데모 "화재" 버튼이 이제 모의 출동까지 발화(셔터+로봇 연쇄), 맵 슬롯 전환 시 2.5D 재빌드. +오프라인 출동 게이트, 시점 리셋 버튼+각도 영속, barrier 로그. **다음 Unity 세션 첫 행동**: Play → 2.5D 탭 → 육안 체크리스트(장식 전경/데모 화재 버튼→셔터 하강/시점 리셋/슬롯 전환/스케일은 decor.json 노브). ⚠️ unityctl 컴파일은 사용자 Play 중이면 stale — `play stop` 후 `exec 'UnityEditor.AssetDatabase.Refresh()'` 표준. 자세히: `docs/status/DECISION-LOG.md` 2026-07-08 최상단). **이전(2026-07-03)**: 🔋 축소마진 4점 순찰 웨이포인트 1~2 클린 통과 도중 **배터리 완전 방전**으로 tf 정지 — OpenCR 크래시·AMCL garbage-pose 등이 저전압 단일원인으로 수렴. **로봇 트랙 Top 액션 유지: 완전 충전 후 순찰 #3~#4 완주**(재개 시 AMCL 충전독 재시딩부터). **이전(2026-07-03, 같은날 더 이전)**: 🔩 PolygonStop 과대 반경 0.18/0.22/0.20m 축소 + PolygonLimit 활성 리스트 누락 수정 / 🚦 첫 라이브 실주행 중 젠지 실충돌 → 속도·정지마진 하향. **이전(2026-07-01)**: 🗺️ arena_shared 재캡처 교체 + AMCL 재확보 패턴 스킬화.

---

## ⚡ Top 1 Action (가장 최신)

**완전 충전 후 재개 → 웨이포인트#3~#4 완주 확인 → 장애물 테스트**

- **배경**: 안전마진 축소(0.18/0.22/0.20m) 자체는 웨이포인트 1~2 클린 통과로 **부분 검증 성공**. 그런데 같은 세션 안에서 겪은 `turtlebot3_ros` SIGABRT 크래시(odom 소실→AMCL garbage-pose)와 #3 도중 tf 정지가 둘 다 **배터리 완전방전과 시점이 겹침** — 별개 버그가 아니라 저전압 하나가 근본원인이었을 가능성이 높음(시리얼 패킷 파싱 실패는 전압강하 시 흔한 증상). 지난 세션 미해결이던 AMCL garbage-pose(x=79428) 이상현상도 같은 계열로 재해석됨.
- **할 일(순서대로)**:
  1. **완전 충전 후 시작** — 저전압 상태에서의 재시도는 진단에 노이즈만 더함(우선순위 최상단).
  2. bringup 후 `/tb3_1/odom` 발행자 수 확인 + `/tmp/nsbu_tb3_1.log`에서 `stack smashing`/`no status packet` **재발 여부 확인** — 완전충전 후에도 재발하면 그때 비로소 OpenCR 물리연결(케이블/보드) 점검으로 넘어갈 것(저전압 가설이 틀렸다는 뜻이므로).
  3. AMCL 재시딩(`x=0.038,y=1.405,yaw=0.293` — arena_shared 기준) → `/tb3_1/amcl_pose` sane 확인.
  4. nav2 8노드 재기동 + `ros2 param get /tb3_1/collision_monitor PolygonStop.radius`로 **0.18m** 로드 확인(0.30 아님), `polygons`에 `PolygonLimit` 포함 확인.
  5. 4점 순찰 재트리거 → 이번엔 **#3~#4까지 완주** 확인(1~2는 이미 클린 통과 확인됨).
  6. 완주 PASS면 **일부러 장애물(사람/젠지)을 경로에 놓고** 재주행 — 안전마진이 실제 장애물에도 통하는지 의도적 테스트(아직 미검증).
  7. 그 다음 7웨이포인트 전체 재계산(`patrol_multi_waypoint.py`) → 완주 검증 → ssot-trio-update.
- **관련 파일**: `scripts/{patch_nav_params_ns.py,patrol_waypoints_bridge.py,patrol_multi_waypoint.py,patrol_safe_clearance.py}`, `.claude/skills/urhynix-t1-nav2-patrol-drive/SKILL.md`(함정#12).
- **병행 이월(여전히 유효)**: 2.5D 우클릭/로봇마커 육안 확인. 젠지 pose 마커 표시(subscribe-only 가능 확인했으나 AMCL 초기포즈 미시딩이라 아직 `/tb3_2/pose` 없음).

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
# 1. Unity 컴파일 확인 (에디터 이미 떠있으면 생략)
unityctl script get-errors --project /Users/family/jason/URHYNIX/unity/ControlRoom --json
# → 0 error(s) 확인

# 2. arena_shared 2.5D 탭 회귀 확인(육안, 성역) — 벽 27개(외곽+칸막이+돌출) 정상 렌더되는지
# Unity Play → 맵패널 2.5D 탭 → 드래그 회전 + 휠 줌 동작 확인

# 3. 우클릭 설계 착수 전 기존 2D 패턴 읽기
#    unity/ControlRoom/Assets/Scripts/Map/MapContextMenuView.cs
#    unity/ControlRoom/Assets/Scripts/Map/MapInteractionController.cs
#    unity/ControlRoom/Assets/Scripts/Map/Actions/ (DispatchHereAction.cs 등)

# 4. (선택) 어제 bag→rtabmap PLY 스레드 살아있는지 확인 — 별개 작업, 필요시만
ssh rtabmap@orb "echo OK && ls -la ~/bags/mapping_20260630_1658/ 2>&1"
```

---

## 🔧 If Stuck (빠른 복구)

| 증상 | 명령 |
|------|------|
| `unityctl exec` project lock | Unity Editor 완전 종료 후 재시작, 또는 `unityctl session clean` 후 재시도 |
| bridge 로드 안 됨 | `unityctl init --project /Users/family/jason/URHYNIX/unity/ControlRoom` 후 Editor 재기동 |
| `SensorVerifyConsole.Dump()` 라벨 4개 안 보임 | `tb3_2` 선택 후 센서 탭 활성화 확인; `default_sensors.json`에 `robotId: tb3_2` 센서 4개 있는지 확인 |
| 동적 UI 미생성 | `RightStatusPanel.uxml`, `LeftControlPanel.uxml`에서 고정 행/버튼 제거 여부 확인 |
| bridge compile error 6건 | `Packages/com.unityctl.bridge/Editor/Commands/DescribeTypeHandler.cs` 확인. 본 작업과 무관하면 패키지 다운그레이드 또는 고비용 모델 판단 |
| `unityctl check`/`get-errors`가 옛 결과 그대로(stale) | 백그라운드 컴파일은 신뢰 불가 | `EditorUtility.RequestScriptReload()`로 강제 리로드 → `transport: batch`로 잠깐 폴백됐다 `ipc`로 돌아올 때까지 대기(수십초, 짧은 간격 재시도 금지 — project lock 악화) |
| 3D 오브젝트가 핑크로 렌더 | URP RenderPipelineAsset이 ProjectSettings에서 끊어진 참조일 수 있음(`grep customRenderPipeline ProjectSettings/QualitySettings.asset`으로 GUID가 실제 asset과 매칭되는지 확인) | `Assets/Settings/ControlRoom_URP.asset`(2026-07-01 생성)로 이미 수정됨 — 재발 시 같은 GUID로 재확인 |
| Unity kill -TERM 반복 후 씬이 이상함 | 강제종료 반복 시 auto-recovery가 stale 백업을 잘못 복원할 수 있음(2026-07-01 실제 발생, `ControlRoomMain.unity` 컴포넌트 소실) | `git status`로 씬 diff 확인 → 있으면 `git checkout -- <scene>` + `unityctl scene open --project <P> --path <scene> --force`로 디스크에서 재로드 |

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
