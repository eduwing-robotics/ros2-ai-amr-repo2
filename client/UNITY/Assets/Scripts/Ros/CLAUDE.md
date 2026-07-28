# Assets/Scripts/Ros/

> ROS-TCP-Connector pub/sub. 토픽 이름은 `TopicRegistry`에서 중앙화.

## 현재 주요 파일

| 파일 | 역할 |
|---|---|
| `RosConnectionManager.cs` | 로봇별 ROS-TCP endpoint 연결 관리 |
| `TopicRegistry.cs` | 토픽 이름 상수 (SSOT) |
| `RobotPoseSubscriber.cs` | `/tb3_*/pose` 구독 |
| `BatterySubscriber.cs` | `/battery_state` 구독 |
| `CameraStreamSubscriber.cs` | 로봇별 compressed image 구독 |
| `LaserSubscriber.cs` | LaserScan 구독 |
| `PrepareDrivePublisher.cs` | 주행 준비·재시드 요청 |
| `FollowWaypointsPublisher.cs` | 순찰 waypoint 요청 |
| `TeleopCmdPublisher.cs` | 선택 로봇 수동 속도 명령 |

## 토픽 정본 (참고)

| 카메라 | 토픽 |
|---|---|
| 젠지 (Pi Camera v2 IMX219) | `/tb3_2/camera/image_raw/compressed` |
| 티원 (RealSense D435) | `/tb3_1/camera/color/image_raw/compressed` |

현재 로봇별 분리 도메인은 젠지=1, 티원=2입니다. `ROS_DOMAIN_ID`는 로봇 측 설정이며 Unity에 하드코딩하지 않습니다. Unity는 `RosConnectionManager`가 선택 로봇의 endpoint에 연결합니다.

## 규칙

- 토픽 이름 하드코딩 금지 — 항상 `TopicRegistry`를 거침.
- subscribe/publish는 이 폴더 안에서만 직접 호출. 다른 폴더는 이 서비스를 호출.
- ROS_DOMAIN_ID는 로봇 측 설정이라 Unity 코드에 하드코딩하지 않는다.
