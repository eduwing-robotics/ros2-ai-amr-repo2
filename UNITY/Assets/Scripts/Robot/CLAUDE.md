# Assets/Scripts/Robot/

> 로봇 매니저, 커맨드 서비스, 배터리/순회 로직.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `RobotManager.cs` | 여러 로봇(`tb3_1`/`tb3_2`) 통합 관리 |
| `RobotSelector.cs` | 현재 선택 로봇 변경 |
| `RobotCommandService.cs` | 이동/정지/순회 공통 커맨드 |
| `RobotPowerService.cs` | 대기/재시작/종료 요청 (실제 ROS publish는 `Ros/PowerCommandPublisher`) |
| `PatrolService.cs` | 자동 순회 시작/정지 |
| `ManualMoveService.cs` | 수동 이동 (`/cmd_vel`) |
| `BatteryService.cs` | 배터리 부족 + 충전 복귀 로직 |

## 규칙

- 모든 명령은 `RobotCommandService`를 거쳐 발행 (안전 게이트 1곳).
- ROS publish는 직접 안 함. `Ros/*Publisher.cs` 호출.
- 전원 종료처럼 비가역적 명령은 사용자 확인 흐름 강제.
