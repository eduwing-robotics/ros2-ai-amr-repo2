# Assets/Scripts/Ros/

> ROS-TCP-Connector pub/sub. 토픽 이름은 `TopicRegistry`에서 중앙화.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `RosConnectionService.cs` | ROS-TCP-Connector 연결 관리 |
| `TopicRegistry.cs` | 토픽 이름 상수 (SSOT) |
| `RobotPoseSubscriber.cs` | `/tb3_*/pose` 구독 |
| `BatterySubscriber.cs` | `/battery_state` 구독 |
| `SensorSubscriber.cs` | 센서 토픽 구독 |
| `SecurityEventSubscriber.cs` | `/security/event` 구독 |
| `DispatchPublisher.cs` | `/security/dispatch` 발행 |
| `PowerCommandPublisher.cs` | 정지/대기/종료 요청 발행 |
| `CameraStreamSubscriber.cs` | 카메라 이미지 토픽 구독 (unity-smoke `CameraStreamPanel` 재이식) |

## 토픽 정본 (참고)

| 카메라 | 토픽 |
|---|---|
| 젠지 (Pi Camera v2 IMX219) | `/tb3_2/camera/image_raw/compressed` |
| 티원 (RealSense D435) | `/tb3_1/camera/color/image_raw/compressed` |

ROS_DOMAIN_ID=210 통일. (2026-06-15 210으로 갱신, cross-discovery PASS)

## 규칙

- 토픽 이름 하드코딩 금지 — 항상 `TopicRegistry`를 거침.
- subscribe/publish는 이 폴더 안에서만 직접 호출. 다른 폴더는 이 서비스를 호출.
- ROS_DOMAIN_ID 변경은 환경변수가 아니라 manifest/config로 잠금 (현재 210 고정, 2026-06-15 갱신).
