# Assets/Scripts/Simulation/

> 실제 로봇/센서 없을 때 쓰는 가짜 데이터. 데모/개발용.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `DemoScenarioService.cs` ✅ | HTML의 화재/침입/소리/도난 데모 트리거 로직 |
| `FakeRobotData.cs` | 가짜 로봇 위치/배터리/모드 (현재 FakeSensorData에 통합) |
| `FakeSensorData.cs` ✅ | 가짜 배터리/가스/소음/조도 Perlin·Sin 기반 generator |

## 규칙

- **시뮬은 최대한 실기기 우선** (사용자 명시). 가짜 데이터는 fallback.
- 실기기 연결 안 됐을 때만 시뮬 자동 활성화 (예: `RosConnectionService` 미연결 감지 시).
- 시뮬 데이터는 실제 ROS topic과 같은 인터페이스를 따라야 함 (UI 코드 변경 0).
