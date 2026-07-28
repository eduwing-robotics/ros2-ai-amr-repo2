# 팀(URHYNIX) 통합 가이드 — hc 로컬 `robot_project`

팀 정본: [ros2-ai-amr-repo2](https://github.com/eduwing-robotics/ros2-ai-amr-repo2)
**팀 git에는 푸시하지 않음** — 로컬에만 반영.

## 역할 분담 (2026-06-25 확정)

| 영역 | 사용 | 위치 |
|------|------|------|
| YOLO / 화재·연기 비전 | **hc 담당 (내 것)** | `scripts/robot_yolo_viewer.py`, `launch_robot_test.sh`, `training/`, `models/` |
| Wi-Fi 카메라 (JPEG DDS) | **hc 담당** | `launch_t1_realsense.sh`, `jpeg_compressor`, `ros_multimachine_env.sh` |
| Nav2 / 웨이포인트 | **팀** | `scripts/run_waypoints.py`, `patrol_waypoints_bridge.py`, `wp_capture.sh` |
| Nav2 파라미터 | **팀 베이스** | `nav2_burger_arena.yaml` — **Smac2D+MPPI** (순찰·출동·배터리복귀 공통). 구버전: `nav2_burger_map1.yaml`(DWB), `nav2_burger_map1_mppi.yaml` |
| SLAM / 맵 | **팀** | `scripts/_t1_slam_*.sh`, `pgm_to_map_slot.py`, `~/maps/` |
| Unity 연동 | **팀** | `unity/ControlRoom/`, ROS-TCP, `patrol_waypoints_bridge.py` |
| Arduino / 센서 | **팀** | `scripts/arduino_bridge.py` |
| ArUco 주차 | **팀** | `scripts/aruco_parking/` |
| SSH / IP / bringup 헬퍼 | **팀 + hc 배포** | `scripts/tb3.sh` + `ssh_t1.py` / `sync_to_robot.sh` |

---

## Nav2: 텔레옵 vs 고정 YAML?

**권장: 팀 방식(텔레옵 캡처 + `run_waypoints.py`)**

| | 텔레옵 캡처 (팀) | 고정 YAML (기존 hc) |
|--|------------------|---------------------|
| 맵 | 실 SLAM 맵 (`arena_v3`, `map1`) | 합성 1.8×1.8m 맵 |
| Unity | ControlRoom goal / patrol 토픽 연동 | 없음 |
| 현장 보정 | 텔레옵으로 찍으면 됨 | 좌표 수동 계산 |
| 검증 | 2026-06-23 젠지 실주행 기록 있음 | 필드 검증 없음 |

고정 `waypoints.yaml` 방식은 **제거됨**. 순찰은:

```bash
# 1) 텔레옵으로 웨이포인트 캡처
./scripts/launch_nav2_team.sh teleop-capture

# 2) Nav2 + 저장 맵
MAP_YAML=~/maps/arena_v3.yaml ./scripts/launch_nav2_team.sh nav2

# 3) 순찰 실행
python3 -u scripts/run_waypoints.py waypoints_tb3_1_final.yaml --dynamic-start --loop
```

Unity에서 보낼 때는 `patrol_waypoints_bridge.py --robot tb3_1`.

---

## Bringup 비교

### 팀 `_t1_up.sh` (Unity / SLAM / 관제)

- `namespace:=tb3_1` — 멀티로봇 격리
- FastDDS + `ROS_STATIC_PEERS` + ROS-TCP `:10000`
- RealSense color 640×480×15
- **용도**: Unity ControlRoom, SLAM, Nav2, 팀 DDS 도메인

### hc `launch_t1_realsense.sh` (YOLO Wi-Fi)

- namespace 없음 (또는 `/camera/...`)
- CycloneDDS peers + **JPEG compressed** 토픽
- RealSense 424×240 ultra + `jpeg_compressor`
- **용도**: 노트북 `robot_yolo_viewer.py` — **검증된 baseline**

### 권장: **모드 분리 (동시에 띄우지 않음)**

| 모드 | 실행 |
|------|------|
| 비전 테스트 | 로봇: `./scripts/launch_t1_realsense.sh` / 노트북: `./scripts/launch_robot_test.sh run` |
| Unity·Nav2·SLAM | 로봇: `bash scripts/_t1_up.sh <LAPTOP_IP>` (팀) |
| 젠지 | `bash scripts/_genji_core_up.sh <LAPTOP_IP>` |

같은 `ROS_DOMAIN_ID=210`에서 두 bringup을 동시에 켜면 `/scan`, 카메라 토픽이 충돌할 수 있음.

---

## SSH / IP 차이

| | 팀 `tb3.sh` | hc `ssh_t1.py` / `sync_to_robot` |
|--|-------------|----------------------------------|
| 대상 | 주로 젠지 `kim@192.168.20.7` | T1 고정 `t1@192.168.20.101` |
| IP 찾기 | mDNS `.local` → MAC 스캔 → LAN sweep | 환경변수 `ROBOT_HOST` 고정 |
| 비밀번호 | `~/.tb3rc` (`TB3_PASSWORD`) | `ROBOT_SSH_PASSWORD` |
| 기능 | ssh, vnc, up/down, slam, nav2, unity, poweroff | 원격 명령 1줄, **코드 rsync 배포** |
| VNC | `tb3-vnc` 내장 | 없음 |

**둘 다 쓰면 됨**: 일상은 `source scripts/tb3.sh` → `tb3-ssh` / `tb3-nav2`, T1 코드 배포는 `./scripts/sync_to_robot.sh`.

T1 IP를 tb3에 맞추려면 `~/.tb3rc` 또는 셸에서:

```bash
export TB3_ROBOT_IP_HINT=192.168.20.7
export TB3_USER=t1
```

---

## 팀에서 가져온 것 (로컬만)

- `unity/`, `docs/` (팀 문서), `.claude/skills/`, `db/`, `test/`
- `scripts/tb3.sh`, `_t1_*.sh`, `_genji_*.sh`, `arduino_bridge.py`, `patrol_waypoints_bridge.py`, `run_waypoints.py`, `aruco_parking/`, …

## hc에서 제거한 것 (겹침 처리)

- `arduino_bridge_node`, `unity_socket_bridge`, `waypoint_patrol_node`
- `museum_navigation.launch.py`, `launch_museum_nav.sh`
- 합성 맵 `museum_map.*`, `generate_museum_map.py`
- 커스텀 `nav2_burger_museum.yaml` → `nav2_burger.yaml` (TB3 stock 복사본)

## hc에 남긴 것

- 전체 YOLO 파이프라인 + `museum_patrol_system` (yolo, jpeg, task_manager)
- `docs/t1_camera_wifi_baseline.md`

---

## 빠른 명령

```bash
# tb3 헬퍼 등록 (한 번)
echo 'source ~/workspace/robot_project/scripts/tb3.sh' >> ~/.bashrc

# YOLO (hc)
./scripts/launch_t1_realsense.sh          # robot
./scripts/launch_robot_test.sh run        # laptop

# Nav2 (팀)
MAP_YAML=~/maps/arena_v3.yaml ./scripts/launch_nav2_team.sh nav2
python3 -u scripts/run_waypoints.py waypoints.yaml --dynamic-start

# Arduino (팀, 젠지에서)
python3 scripts/arduino_bridge.py
```
