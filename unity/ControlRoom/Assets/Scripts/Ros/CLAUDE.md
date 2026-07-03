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

~~ROS_DOMAIN_ID=210 통일~~ (2026-06-15 결정, **2026-06-30/07-01 재분리로 stale**). 현재는 로봇별 분리 도메인: 젠지=1, 티원=2 (`ROS_DOMAIN_ID` — 라즈베리파이 쪽 설정, Unity와 무관). Unity는 `RosConnectionManager`가 로봇별 IP로 개별 `ROSConnection`(멀티 endpoint)을 여는 구조라 애초에 하나의 공용 도메인이 필요 없음 — 각 로봇의 `ros_tcp_endpoint`가 자기 도메인에서 뜨기만 하면 됨.

## 규칙

- 토픽 이름 하드코딩 금지 — 항상 `TopicRegistry`를 거침.
- subscribe/publish는 이 폴더 안에서만 직접 호출. 다른 폴더는 이 서비스를 호출.
- ROS_DOMAIN_ID는 로봇(라즈베리파이) 쪽 설정이라 Unity 코드에 하드코딩할 대상이 아님 — 로봇별 실제값은 `.claude/skills/urhynix-t1-amcl-saved-map/SKILL.md`(티원) 등 로봇 브링업 스킬이 SSOT.
