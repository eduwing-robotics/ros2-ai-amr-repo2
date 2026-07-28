# Robot Navigation

ROS 2 Jazzy에서 T1과 Gen.G 로봇의 Nav2 순찰 및 ArUco/LiDAR 도킹 실행 파일을 로봇별로 분리해 관리합니다. 두 로봇 설정을 섞지 말고 실행 대상 폴더의 README를 먼저 확인하세요.

## 폴더 구성

- `t1_rpp_patrol2_aruco_dock/`: T1 전용 RPP 순찰, RealSense, ArUco ID 11 및 후방 LiDAR 도킹
- `geng_rpp_patrol_dock/`: Gen.G 전용 RPP 순찰, IMX219, ArUco ID 12 및 후방 LiDAR 도킹

## 사용 방법

저장소 루트에서 대상 로봇 폴더로 이동합니다.

```bash
# T1
cd Slam_Nav2/t1_rpp_patrol2_aruco_dock

# Gen.G
cd Slam_Nav2/geng_rpp_patrol_dock
```

그다음 각 폴더의 `README.md`에 있는 환경 설정, Nav2 실행, 순찰 및 도킹 명령을 따릅니다.

## 주의사항

- T1과 Gen.G 스크립트 및 파라미터는 로봇별로 독립되어 있습니다.
- 실행 전에 ROS domain, namespace, 로봇 IP, 지도와 초기 위치를 확인하세요.
- 같은 `/cmd_vel`에 여러 제어기가 동시에 명령을 보내지 않도록 수동 조작과 자동 주행을 분리하세요.
- 실제 주행 전 비상 정지와 `stop_all` 스크립트를 확인하세요.
