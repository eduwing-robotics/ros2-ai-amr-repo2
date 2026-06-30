# Unity UI ↔ 실기능 배선 계약 (UI Wiring Contract)

> URHYNIX ControlRoom UI 요소를 **실제 ROS publish / DB write / 상태변경에 연결하기 위한 1:1 배선 계약**.
> "버튼은 있는데 기능에 안 붙은" 미연결 요소를 잠그고, 무엇을 어느 토픽/이벤트/구독자에 연결할지 규정한다.
> 근거: 2026-06-29 코드 정찰(ControlRoomEvents/TopicRegistry/각 View/ControlRoomApp 원본 검증). 작성: 메인.
> 상위 계획은 `UNITY-CONTROLROOM-CONVERSION-PLAN.md`, 시스템 토픽 SSOT는 `CONTRACT.md` §1·§3.

---

## 결론 (BLUF)

미연결 UI 요소 **8개**. 패턴은 둘로 갈린다.

- **A. 이벤트는 정확히 발화하나 구독자(Publisher)가 없음 (2개)** — `TeleopPad`, `QuickAction`. UI는 손댈 필요 없고 **Ros/ 폴더에 Publisher 1~2개만 추가 + `ControlRoomApp.CreateRosSubscribers()`에 등록**하면 끝. 가장 싸다.
- **B. 핸들러 본문이 로그/상태만, 실이벤트 미발화 (6개)** — `MovePanel`, `WaypointList`, `FeatureToggle`, `PowerButton`, `RobotRoleCard`(하드코딩), `PatrolEditMode`(이중배선). View 본문 수정이 필요해 더 무겁다.

**기준선(이미 살아있음):** 맵 우클릭 출동(`DispatchPublisher`→`/<id>/goal_pose`), 순찰 실행(`FollowWaypointsPublisher`→`/<id>/patrol_waypoints`), 시나리오 경보, 맵 슬롯 전환. → **로봇 직접제어(Teleop/Quick/Power) 라인만 비어 있다.**

---

## 배선 표 (미연결 8개)

| # | UI 요소 | View:line | 발화 이벤트(있으면) | 구독자 | 목표 토픽 | 메시지 | 로봇측 소비 | 패턴 |
|---|---------|-----------|---------------------|--------|-----------|--------|-------------|------|
| 1 | TeleopPad 4방향+정지 | `TeleopPadView.cs:44,72` | `OnTeleopCmd(id,lin,ang,pressed)` | **없음** | `/<id>/cmd_vel` | **TwistStamped** ⚠ | TurtleBot3 HW (Nav2 비경유, 수동) | A |
| 2 | QuickAction 4종 | `QuickActionView.cs:26` | `OnQuickAction(id,actionId)` | **없음** | actionId별(아래 분해) | 혼합 | 혼합 | A |
| 3 | MovePanel 순회 시작/정지 | `MovePanelView.cs:25-39` | 없음(로그만) | (FollowWaypointsPublisher 재사용) | `/<id>/patrol_waypoints` | PoseArray | `patrol_waypoints_bridge.py` | B |
| 4 | PowerButton 전원 | `PowerButtonView.cs:14-20` | 없음(로그만) | PowerCommandPublisher(미작성) | 미정(`/<id>/power`?) | 미정 | 미정 | B |
| 5 | WaypointList wp선택 | `WaypointListView.cs:26-31` | 없음(UI클래스만) | PatrolService | (로컬 데이터) | — | — | B |
| 6 | FeatureToggle 스캔/가속/SLAM | `FeatureToggleListView.cs:17-25` | 없음(로그만) | FeatureRegistry(§8) | 기능별 | 기능별 | 기능별 | B |
| 7 | RobotRoleCard 연결상태 | `RobotRoleCardView.cs:39` | — (하드코딩 "온라인") | (구독자가 카드 갱신) | `/<id>/pose` heartbeat | PoseStamped | (수신만) | B |
| 8 | PatrolEditMode 토글 | `ControlRoomState.cs:54-55` | `OnPatrolEditModeChanged` | 없음(MapPanel 직접호출 이중) | — | — | — | 정리 |

⚠ **메시지 타입 드리프트**: `CONTRACT.md:16,20`은 `cmd_vel`을 `geometry_msgs/Twist`로 규정하나, 실기 TurtleBot3 Jazzy는 **TwistStamped**(HANDOFF `teleop_stamped.py /tb3_*/cmd_vel`). **ground truth = TwistStamped.** Publisher 작성 시 TwistStamped 사용 + CONTRACT.md 정정 필요.

---

## QuickAction 4종 분해 (actionId → 실기능)

`QuickActionView.cs:14-17`의 `QuickActionIds` 4종. 각자 소비 인터페이스가 다르다.

| actionId | 의미 | 제안 연결 | 로봇측 인터페이스 | 결정 상태 |
|----------|------|-----------|-------------------|-----------|
| `stop` | 즉시정지 | `cmd_vel` 0 발행 (+ Nav2 cancel) | TwistStamped 0 / Nav2 cancel | cmd_vel 0은 즉시 가능, Nav2 cancel은 **미정** |
| `return_home` | 충전소복귀 | `/<id>/goal_pose`로 충전독 좌표 발행 (DispatchPublisher 재사용) | 기존 `patrol_waypoints_bridge.py` | 충전독 좌표 SSOT 필요(순회지점1=티원주차/2=젠지주차) |
| `aruco_park` | ArUco정밀주차 | 로봇측 `aruco_parking/parking_node` 트리거 | 트리거 토픽 **없음** (현재 수동 `ros2 run`) | **로봇측 협의 필요** |
| `lock_drive` | 주행잠금 | 미정 | 인터페이스 없음 | **로봇측 협의 필요** |

→ QuickAction은 "구독자 1개"가 아니라 **actionId별 디스패처**가 맞다. `stop`·`return_home`은 기존 자산 재사용으로 즉시 가능, `aruco_park`·`lock_drive`는 로봇측 명령 인터페이스부터 정의해야 한다.

---

## 연결 작업 명세 (싼 것 → 비싼 것)

### W1. Teleop → `/<id>/cmd_vel` Publisher 신설 (패턴 A, 최저비용) — ✅ 구현·컴파일 PASS (2026-06-29)
- **신규 파일**: `Assets/Scripts/Ros/TeleopCmdPublisher.cs` — `FollowWaypointsPublisher.cs` 패턴 복제. `OnTeleopCmd` 구독 → `TopicRegistry.GetCmdVel(id)` → `RegisterPublisher<TwistStampedMsg>`(1회) → `linear.x`/`angular.z` 발행.
- **TopicRegistry 추가**: `GetCmdVel(robotId) => $"/{robotId}/cmd_vel"` (`TopicRegistry.cs`).
- **등록**: `ControlRoomApp.CreateRosSubscribers()`에 `TeleopCmdPublisher` 블록 추가.
- UI(`TeleopPadView`)는 **수정 없음** — 이미 정확히 발화 중.
- **검증**: `unityctl script get-errors` → **0 errors**. **실로봇 주행(화면 D-pad→로봇 이동) end-to-end는 미검증** — 로봇 bringup + endpoint 필요(다음 하드웨어 세션).

### W2. QuickAction stop/return_home (패턴 A, 저비용 — 기존 자산 재사용)
- **신규 파일**: `Assets/Scripts/Ros/QuickActionDispatcher.cs` — `OnQuickAction` 구독 → `switch(actionId)`.
  - `stop`: TeleopCmdPublisher 경로로 0 발행(또는 직접 cmd_vel 0).
  - `return_home`: 충전독 좌표를 `ControlRoomEvents.RaiseDispatchRequested(id, x, y, "return_home")`로 위임(DispatchPublisher 재사용).
- **선결정**: 충전독 좌표 SSOT(로봇별). `aruco_park`·`lock_drive`는 W-later로 분리.

### W3. MovePanel 순회 시작/정지 (패턴 B)
- `MovePanelView.cs:25-39`의 `OnStart()`가 `RaisePatrolRunRequested(SelectedRobotId)`를 **발화하도록** 본문 교체(현재 로그만). 구독자(FollowWaypointsPublisher)는 이미 있음.
- `OnStop()`은 정지 인터페이스(Nav2 cancel) 미정 → W-later.
- 주의: 순찰 실행 진입점이 MapPanel "순찰 실행" 버튼과 **이중**이 됨 — 의도적 이중(좌패널+맵)인지 확정.

### W4. PowerButton (패턴 B, 로봇측 미정)
- `PowerCommandPublisher.cs` 미작성 + `/<id>/power` 토픽 규약 없음 → **로봇측 명령 인터페이스 정의가 선행**. 그전엔 UI 로그-only 유지.

### W5. FeatureToggle (패턴 B, 아키텍처 의존)
- `CONVERSION-PLAN.md §8`의 `default_features.json → FeatureRegistry → IRobotFeature` 자동생성 경로가 선행. 그 전엔 토글이 로그-only. 개별 토글 직결 금지(계획과 충돌).

### W6. RobotRoleCard 연결상태 (패턴 B, 저비용) — ✅ 구현·런타임 PASS (2026-06-29)
- `RobotRoleCardView.cs:39` 하드코딩 `"온라인"` 제거 → 신규 `App/RobotConnectivityMonitor.cs`가 `RobotPoseFeed.OnRobotPose`를 추적, 마지막 신호 후 3초 timeout이면 오프라인. `ControlRoomEvents.OnRobotConnectivity` 발화 → 카드뷰 라벨 갱신. `ControlRoomApp`에 모니터 등록.
- USS는 UI Contract Lock 존중해 텍스트만 변경(색/클래스 미변경).
- **검증**: 컴파일 0 errors + **런타임 시각검증 PASS**(티원 OFF 상태 Play → 카드 "오프라인" 정확 표시, 스크린샷). 로봇 켜져 `/pose` 흐르면 자동 "온라인" 전환은 충전 후 확인.

### W7. PatrolEditMode 정리 (정리)
- `OnPatrolEditModeChanged` 발화에 구독자 없고 MapPanel이 직접 `SetPatrolEditMode()` 호출 → **이중배선**. 이벤트 경유로 일원화하거나 이벤트 제거 중 택1. 기능 결손 아님(정리 항목).

---

## 신설/수정 요약 (구현 시 체크리스트)

| 항목 | 종류 | 파일 |
|------|------|------|
| `TeleopCmdPublisher` | 신규 | `Ros/TeleopCmdPublisher.cs` |
| `QuickActionDispatcher` | 신규 | `Ros/QuickActionDispatcher.cs` |
| `GetCmdVel(robotId)` | 추가 | `Ros/TopicRegistry.cs` |
| 두 Publisher 등록 | 수정 | `App/ControlRoomApp.cs:86` `CreateRosSubscribers()` |
| `RaisePatrolRunRequested` 발화 | 수정 | `UI/MovePanelView.cs:25` |
| 연결상태 구독 | 수정 | `UI/RobotRoleCardView.cs:39` |
| cmd_vel 타입 정정(Twist→TwistStamped) | 수정 | `CONTRACT.md:16,20` |

---

## 미결정 (로봇측 협의 / SSOT 필요)

1. **cmd_vel 메시지 타입** — Twist vs TwistStamped 드리프트. 실기=TwistStamped로 확정 후 CONTRACT.md 정정.
2. **충전독 좌표 SSOT** — `return_home` 목표. 로봇별(티원/젠지) world 좌표 어디에 둘지.
3. **ArUco 주차 트리거 인터페이스** — 현재 수동 `ros2 run aruco_parking parking_node`. Unity에서 켤 토픽/서비스 없음.
4. **주행잠금(lock_drive) 의미·인터페이스** — 정의 자체가 없음.
5. **Nav2 cancel(정지) 경로** — `stop`/순회정지의 실제 취소 인터페이스.
6. **순찰 실행 이중 진입점**(MapPanel+MovePanel) 의도 여부.

---

## 관련 Jira

SCRUM-127(맵 상호작용)·128(주행 모드: 수동/자동/스캔/가속)·129(상태 패널/알람)·130(카메라 스트리밍). 본 계약의 W1·W2·W3은 주로 **SCRUM-128**, W6/알람은 **SCRUM-129** 범위.
