# Assets/Scripts/UI/

> UXML 마크업과 C# 상태를 연결하는 View/Binder.

## 예정 파일

| 파일 | 영역 |
|---|---|
| `ControlRoomBinder.cs` ✅ | UXML 루트와 ControlRoomState 연결, 7 View 초기화, 시계 갱신 |
| `TopBarView.cs` ✅ | 상단바 + 로봇 탭 + 전원 버튼 + 시계 + 경보 카운트 |
| `RobotTabView.cs` | 로봇 탭 자동 생성 |
| `PowerButtonView.cs` | 로봇 ON/OFF/대기 버튼 |
| `ScenarioPanelView.cs` | 위험상황 데모 버튼 |
| `MovePanelView.cs` | 수동 조종 + 순회 시작/정지 |
| `ModePanelView.cs` | 자동/수동/스캔/가속 모드 |
| `FeatureToggleListView.cs` | 기능 토글 자동 생성 |
| `SensorCardListView.cs` | 센서 카드 자동 생성 |
| `WaypointListView.cs` | 순회 목록 표시/편집 |
| `ProtectedTargetView.cs` | 보호대상 목록/상태 |
| `MapPanelView.cs` | 맵 UI + 2D/3D 버튼 |
| `CameraPanelView.cs` | 카메라 화면 + FEED ON/OFF (unity-smoke `CameraStreamPanel` 재이식) |
| `LogPanelView.cs` | 이벤트 로그 표시/삭제/내보내기 |
| `TelemetryPanelView.cs` | 배터리/가스/소음/조도 |
| `HardwarePanelView.cs` | 로봇 모델/IP/펌웨어 |
| `AlertPopupView.cs` | 위험 경보 팝업 |

## 규칙

- View는 UXML `VisualElement`만 다룸. 비즈니스 로직은 `App/` 또는 도메인 폴더에서 호출.
- View → 상태 변경은 항상 `ControlRoomEvents` 이벤트 발행으로.
- View 클래스는 가능한 작게. 큰 View는 부분 View로 쪼개기.
