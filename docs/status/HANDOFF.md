<!-- opencode: 2026-07-01 - 2.5D 우클릭 메뉴 + 로봇 마커 추가, 합성이벤트 검증 PASS. -->
# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-07-03 (**🗺️ arena_shared 맵 재캡처 교체 + AMCL "위치고정+방향탐색" 재확보 패턴 스킬화 + RTAB-Map 3D 정합검증 + Unity 3D 탭 점군 렌더링 후 역할재정의** — 2D SSOT맵을 재캡처본으로 교체(Unity슬롯+SDF+로봇배포 전부 재생성). 옛 dock좌표가 새맵에서 안 먹혀서 AMCL 재확보의 새 표준패턴 도출(사용자 클릭 ground truth + 위치고정/방향탐색 시딩), `urhynix-t1-amcl-saved-map` 스킬에 영구화. RGB-D 매핑+RTAB-Map 3D 재구성으로 2D맵/AMCL 정합 교차검증(시작점 근처 PASS, 방 전체는 loop closure 실패로 드리프트 — 흰벽 위주 방의 근본적 특징부족, 라이다/시각 양쪽 다 겪음). Unity 3D 탭에 실사 점군 렌더링(Pcx 패키지)까지 붙였다가 클릭-좌표찍기 불안정 확인 후 **역할재정의**: 2D/2.5D=좌표입력, 3D=보기전용으로 스코프 정리. 티원 안전 셧다운. 자세히: `docs/status/DECISION-LOG.md` 2026-07-03 최상단 entry). **이전(2026-07-01)**: 🤖 티원 7웨이포인트 순회 인프라 완성 + keepout zone 구현 + `/dev/shm` 시스템정체 규명(재부팅 해결), 웨이포인트1 clean PASS(7웨이포인트 완주는 배터리로 이월 → **새맵 교체로 좌표 자체가 무효화돼 재계산 필요**). **이전(2026-07-01, 더 이전)**: 🗺️ 2.5D 탭 순회지점 미표시 버그 수정.

---

## ⚡ Top 1 Action (가장 최신)

**새 arena_shared 맵 기준으로 7웨이포인트 재계산 → 순회 재검증**

- **배경**: 오늘 맵을 재캡처본으로 통째 교체하면서 좌표계 원점이 바뀌어, 기존 `patrol_multi_waypoint.py`의 `WAYPOINTS`(7개)가 새 맵에서 무효 상태(DOCK만 오늘 재확정, 좌표는 옛맵 기준으로 이월 표시해둠). AMCL/nav2 인프라 자체(keepout, `/dev/shm` 안정성, 벽인접 보정 스크립트)는 전부 살아있고 검증됨 — **좌표만 다시 잡으면 됨**.
- **할 일(순서대로)**:
  1. 티원 전원 켜고 bringup+AMCL(**충전독에 물리적으로 있는지 확인 후** x=0.038,y=1.405,yaw=0.293 초기포즈 재시딩, `urhynix-t1-amcl-saved-map`의 "맵 교체 시 초기포즈 재확보 절차" 참고).
  2. Unity에서 새 맵 위에 7웨이포인트 새로 클릭(또는 `scripts/patrol_safe_clearance.py`로 옛 좌표를 새맵 기준 근사 재배치 후 육안 보정).
  3. `patrol_multi_waypoint.py`의 `WAYPOINTS` 갱신 → 로봇 재배포 → foreground 실행, 7웨이포인트+복귀주차 전부 `STATUS_SUCCEEDED` 확인.
  4. PASS면 `urhynix-t1-nav2-patrol-drive` 검증 섹션 갱신 + ssot-trio-update.
- **관련 파일**: `scripts/{patrol_multi_waypoint.py,patrol_safe_clearance.py}`, `.claude/skills/urhynix-t1-amcl-saved-map/SKILL.md`(새 패턴), `.claude/skills/urhynix-t1-nav2-patrol-drive/SKILL.md`.
- **병행 이월(여전히 유효)**: 2.5D 우클릭/로봇마커 육안 확인 — `Map25DInteractionController.cs`/`Map25DRobotMarkerLayer.cs`는 합성이벤트로 로직만 검증됨.

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
