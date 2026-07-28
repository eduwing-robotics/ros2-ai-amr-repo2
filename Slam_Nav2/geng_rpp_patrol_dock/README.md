# Gen.G RPP 순찰 · ArUco 도킹 패키지

Gen.G(ROS Domain 1) **시동 / 카메라 / RPP 주행 / 순찰 / ArUco 도킹 / 맵** 에 필요한 파일만
모아 둔 독립 폴더입니다. `main`의 다른 코드와 섞이지 않도록 **전용 브랜치**에 올립니다.

- 로봇: Gen.G (`192.168.20.7`, `ROS_DOMAIN_ID=1`, ns `tb3_2`)
- 맵: `maps/museum_map.{yaml,pgm}`
- Nav2: Smac2D + **RPP** (`config/nav2_params_geng_rpp.yaml`)
- 마커: ArUco ID **12** (`aruco_markers/`)

---

## 브랜치 사용법 (다른 파일과 안 섞이게)

```bash
git clone https://github.com/eduwing-robotics/ros2-ai-amr-repo2.git
cd ros2-ai-amr-repo2

# 이 작업만 들어 있는 브랜치로 이동
git fetch origin
git checkout feature/geng-rpp-patrol-aruco-dock
```

- **브랜치** = `main`에서 갈라진 작업 줄. 통합 후 `Slam_Nav2/geng_rpp_patrol_dock/`에서 관리됩니다.
- `main`에는 바로 합치지 않고, 리뷰 후 PR로 병합하면 다른 사람과 충돌을 줄일 수 있습니다.

---

## RViz에서 하던 “위치 찍기” → Unity에서는?

### 지금 (RViz)
1. Nav2를 켠다.
2. RViz **2D Pose Estimate**로 맵 위 실제 위치·방향을 찍는다.
3. 그 값이 ROS **`/initialpose`** 로 들어가 AMCL이 잠긴다.
4. 이후 로봇 위치는 **`/amcl_pose`** (또는 TF `map`→`base_footprint`)로 계속 갱신된다.
5. 목적지/순찰은 Nav2 Action으로 보낸다.

### Unity 관제 연동 시 (같은 일, UI만 Unity)
1. Unity에 **같은 맵** (`museum_map.pgm` + yaml의 resolution/origin)을 띄운다.
2. 사람이 맵에서 “로봇이 지금 여기”를 지정한다.
   → Unity(또는 Gateway)가 ROS **`/initialpose`** 발행 (= RViz Pose Estimate와 동일).
3. Unity 화면의 로봇 아이콘은 **`/amcl_pose`를 구독**해서 그린다.
   (Unity가 위치를 “추정”하는 게 아니라 ROS AMCL 결과를 표시)
4. 목적지·경유지는 `map` 프레임 `x, y, yaw`로 보내고 Nav2 Action으로 주행한다.

| 역할 | ROS 토픽/액션 | 비고 |
|------|----------------|------|
| 초기 위치 지정 | `/initialpose` | RViz 2D Pose Estimate와 동일 |
| 실시간 위치 표시 | `/amcl_pose` | Unity 맵 아이콘 |
| 한 곳 이동 | `NavigateToPose` | |
| 여러 경유 | `NavigateThroughPoses` / `FollowWaypoints` | |
| 좌표계 | `frame_id=map` | 픽셀↔map 변환 필요(이미지 Y 반전) |

권장: Unity가 Nav2를 직접 만지기보다 **Gateway 노드**가 `/initialpose`, pose 구독, Nav2 Action을 중계.

자세한 연동 메모: `docs/UNITY_POSE_AND_CONTROL.md`

---

## 실행 순서 (노트북)

```bash
cd Slam_Nav2/geng_rpp_patrol_dock

# 1) 로봇 bringup (robot_project 쪽 헬퍼 사용)
#    ./scripts/robot_bringup_all.sh start geng   # robot_project에서

# 2) 카메라 (로봇에서 start_geng_camera_remote.sh 실행)
#    토픽: /tb3_2/camera/image_raw/compressed

# 3) Nav2 RPP (raw /scan + raw odom TF — Gen.G 전용 철학)
ROBOT=geng ./scripts/go_nav2_geng_rpp.sh

# 4) RViz + 2D Pose Estimate (LaserScan이 벽에 맞게)
ROBOT=geng ./scripts/nav2_rviz.sh

# 5) 순찰 1회
ROBOT=geng ./scripts/run_patrol.sh

# 6) ArUco 도킹 (뷰어는 끄고)
ROBOT=geng ./scripts/dock_geng_aruco.sh
```

순찰+도킹 한 줄 (권장):

```bash
ROBOT=geng ./scripts/run_geng_patrol_aruco_dock.sh
```

또는 분리 실행:

```bash
ROBOT=geng ./scripts/run_patrol.sh && ROBOT=geng ./scripts/dock_geng_aruco.sh
```

---

## 폴더 구성

```
geng_rpp_patrol_dock/
  README.md
  docs/UNITY_POSE_AND_CONTROL.md
  scripts/          # bringup helpers, Nav2, patrol, dock, camera, aruco
  config/           # nav2_params_geng_rpp.yaml, waypoints.yaml
  maps/             # museum_map
  launch/           # nav2_bringup.launch.py
  rviz/
  aruco_markers/    # markers.yaml + ID12 images
  behavior_trees/
```

---

## 스크립트 목록과 사용법

노트북에서 `cd Slam_Nav2/geng_rpp_patrol_dock` 후 `ROBOT=geng` 을 붙입니다.
(Domain **1**, ns `tb3_2`)

### 자주 쓰는 것 (권장 순서)

| 스크립트 | 역할 | 사용법 |
|----------|------|--------|
| `go_nav2_geng_rpp.sh` | Nav2 **RPP** 기동 (MPPI 아님) | `ROBOT=geng ./scripts/go_nav2_geng_rpp.sh` |
| `nav2_rviz.sh` | RViz + Pose Estimate | `ROBOT=geng ./scripts/nav2_rviz.sh` |
| `run_patrol.sh` / `run_patrol.py` | 웨이포인트 순찰 1회 | `ROBOT=geng ./scripts/run_patrol.sh` |
| `run_geng_patrol_aruco_dock.sh` | **순찰 1회 → ArUco 도킹** 한 줄 | `ROBOT=geng ./scripts/run_geng_patrol_aruco_dock.sh` |
| `dock_geng_aruco.sh` | stage → ArUco 정렬 → 180° → 후방 도킹 | `ROBOT=geng ./scripts/dock_geng_aruco.sh` |
| `park_geng_aruco_stage.py` | ArUco 대기장소 주차 | `python3 scripts/park_geng_aruco_stage.py` |
| `aruco_align_geng_bearing.py` | JPEG bearing 정렬 (ID **12**, 검증된) | `dock_geng_aruco.sh` 가 호출 |
| `rotate_geng_precise.py` | odom 상대 정밀 180° | dock 스크립트가 호출 |
| `dock_geng_rear_wall_long.py` | 후방 라이다 저속 도킹 | dock 스크립트가 호출 |
| `start_geng_camera_remote.sh` | Pi 카메라 원격 기동 (로봇/SSH) | 로봇 또는 노트북→로봇 |
| `view_geng_aruco.sh` | ArUco 디버그 뷰어 | 도킹 중에는 끄기 |
| `stop_all_geng.sh` | YOLO/Nav2/RViz/카메라/bringup 전부 종료 | `./scripts/stop_all_geng.sh` |
| `stop_geng_camera.sh` | Pi 카메라만 SSH 종료 | `./scripts/stop_geng_camera.sh` |
| `save_current_waypoint.sh` / `.py` | 현재 pose를 waypoints.yaml에 저장 | `python3 scripts/save_current_waypoint.py waiting_geng_aruco_stage` |

### 카메라 · YOLO (노트북)

Pi 카메라 토픽: `/tb3_2/camera/image_raw/compressed`
노트북 YOLO는 `robot_project` 뷰어를 씁니다:

```bash
ROBOT=geng source scripts/env.sh
ros2 topic hz /tb3_2/camera/image_raw/compressed

cd ~/workspace/robot_project
source scripts/setup_ros_env.sh
export ROS_DOMAIN_ID=1
export ROS_STATIC_PEERS="192.168.20.7;$(hostname -I | awk '{print $1}');127.0.0.1"
python3 scripts/robot_yolo_viewer.py \
  --camera-topic /tb3_2/camera/image_raw/compressed \
  --model models/museum_fire_smoke.pt \
  --person-model yolov8n.pt
```

### 내부/보조 스크립트

| 스크립트 | 역할 | 비고 |
|----------|------|------|
| `env.sh` | Domain/DDS/peers | Domain 1 |
| `_common.sh` | 공통 유틸 | |
| `go_nav2.sh` | Nav2 본체 런처 | `go_nav2_geng_rpp.sh`가 호출 |
| `_nav2_wait_ready.sh` | Nav2 ready 대기 | |
| `prep_geng_aruco_dock.sh` | 도킹 사전 점검 | |
| `aruco_marker_config.py` | `markers.yaml` 로더 | |
| `aruco_align_geng.py` | 구(legacy) image_error 정렬 | **도킹 경로에서는 사용 안 함** |
| `aruco_dock_detector.py` | 마커 검출 디버그 | |
| `rotate_map_yaw.py` | map 절대 yaw 회전 | **현 도킹 경로에서는 사용 안 함** |
| `odom_tf_relay.py` / `scan_normalize.py` | 옵션 TF/scan | 기본 RPP 경로에서는 OFF |
| `dock_geng_rear_wall.py` | 후방 도킹 짧은 버전 | 보통 `*_long.py` |

### 전체 종료

```bash
./scripts/stop_all_geng.sh      # YOLO 창 + Nav2 + RViz + Pi 카메라 + bringup
./scripts/stop_geng_camera.sh   # 카메라만
```

`stop_*` 는 노트북의 `~/workspace/robot_project/scripts/ssh_genji.py`,
`robot_bringup_all.sh` 가 필요합니다.

---

## 안정화 (검증된 정렬, 2026-07-20)

T1이 더 안정적이어서 Gen.G도 **같은 단순 경로**로 맞춤:

- Nav2: **raw `/scan` + raw odom TF** (`USE_SCAN_NORM=0`, `USE_LOCAL_ODOM_TF=0`)
- ArUco: **`aruco_align_geng_bearing.py` bearing** (JPEG ROS, ID 12). H.264/image_error 경로 사용 안 함
- 180°: **`rotate_geng_precise.py`** (odom 상대) — map 절대 yaw/`rotate_map_yaw.py` 사용 안 함
- 도킹: `dock_geng_rear_wall_long.py` (Gen.G 전용)
- 유지: Domain 1, ns `tb3_2`, footprint 30×20, marker ID 12, stage 좌표

`target_bearing_deg`는 현재 `0.0`(정면 중심). face-on에서 오프셋이 있으면 T1처럼 값을 캘리브하세요.

## 종료

```bash
# YOLO 창 + Nav2/RViz + Pi 카메라 + bringup
./scripts/stop_all_geng.sh

# 카메라만
./scripts/stop_geng_camera.sh
```

노트북에 `~/workspace/robot_project/scripts/ssh_genji.py` 와 `robot_bringup_all.sh` 가 필요합니다.
