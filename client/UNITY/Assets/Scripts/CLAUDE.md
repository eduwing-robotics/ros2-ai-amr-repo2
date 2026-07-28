# Assets/Scripts/

> ControlRoom의 모든 런타임 C# 코드. 도메인별로 11개 하위 폴더로 분리.

## 폴더 매트릭스

| 폴더 | 책임 |
|---|---|
| `App/` | 앱 진입점, 전역 상태, UI/ROS/DB 이벤트 결선 |
| `Data/` | 도메인 데이터 클래스 (RobotInfo, SensorInfo, EventInfo, ...) — 불변 데이터 |
| `UI/` | UXML과 상태를 연결하는 View/Binder |
| `Map/` | 2D 캔버스 + 3D 씬 맵 표시, 로봇 마커, 웨이포인트 렌더링 |
| `Robot/` | 로봇 매니저, 커맨드 서비스, 배터리/순회 로직 |
| `Features/` | `IRobotFeature` 인터페이스 + 구현체 (자율주행/SLAM/스캔/카메라/가속) |
| `Sensors/` | `ISensorModule` 인터페이스 + 구현체 (배터리/가스/소리/조도/PIR/화재) |
| `Ros/` | ROS-TCP-Connector pub/sub (pose, battery, sensor, security event, dispatch, power, camera) |
| `Database/` | Supabase repositories (제한 권한 클라이언트만) |
| `Simulation/` | 로봇 없을 때 쓰는 가짜 데이터 (DemoScenarioService 등) |
| `Design/` | C# 상수 (UiTokens, IconNames) — UI USS 토큰과 1:1 |

## 규칙

- 도메인 간 직접 참조 금지. 의존 흐름: `App` → `UI/Map/Robot/Features/Sensors` → `Ros/Database/Simulation/Data/Design`.
- `Data/`는 외부 의존 없는 순수 POCO.
- 새 클래스 만들 때 파일 최상단 1~5줄 헤더 주석 필수 (`// 파일명 — 한 줄 역할`).

## namespace

권장 prefix: `URHYNIX.ControlRoom.<폴더>` (예: `URHYNIX.ControlRoom.Ros`). 강제는 아니지만 일관성 유지.
