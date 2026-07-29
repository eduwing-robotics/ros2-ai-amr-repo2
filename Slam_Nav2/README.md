# Robot Navigation

ROS 2 Jazzy에서 T1과 Gen.G의 Nav2 순찰 및 ArUco/LiDAR 도킹 실험을 관리합니다. **사용할 로봇 하나를 선택한 뒤, 해당 폴더의 README만 따라 실행하세요.**

## 로봇 선택

| 로봇 | 이동할 폴더 | 구성 |
|---|---|---|
| **T1** | `t1_rpp_patrol2_aruco_dock/` | RealSense, RPP 순찰, ArUco ID 11, 후방 LiDAR 도킹 |
| **Gen.G** | `geng_rpp_patrol_dock/` | IMX219, RPP 순찰, ArUco ID 12, 후방 LiDAR 도킹 |

## 시작 방법

저장소 루트에서 대상 로봇 폴더로 이동한 뒤, 그 폴더의 `README.md`에 있는 환경 설정, Nav2 실행, 순찰 및 도킹 명령을 순서대로 실행합니다.

```bash
# T1
cd Slam_Nav2/t1_rpp_patrol2_aruco_dock

# Gen.G
cd Slam_Nav2/geng_rpp_patrol_dock
```

## 실행 전 안전 점검

- T1과 Gen.G의 스크립트·파라미터·지도·초기 위치를 섞지 않습니다.
- ROS domain, namespace, 로봇 IP, 사용 지도를 확인합니다.
- 수동 조작과 자동 주행이 동시에 `/cmd_vel`을 발행하지 않도록 제어기를 하나만 사용합니다.
- 실제 주행 전 비상 정지 방법과 `stop_all` 스크립트를 확인합니다.
