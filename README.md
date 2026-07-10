# URHYNIX-AMR

> **다중 TurtleBot3 기반 디지털트윈 경비 순찰 로봇 시스템** — ROS 2 Jazzy 자율주행 + Unity 관제(디지털트윈) + Supabase 백엔드.
> 실내 아레나를 로봇이 무한 순찰하고, Unity 관제 화면이 실시간 지도·순찰·출동을 지휘한다.

---

## 개요

| 구성 | 역할 | 스택 |
|---|---|---|
| **`src/`** | 로봇 자율주행 (ROS 2 워크스페이스) | ROS 2 Jazzy · Nav2 · AMCL · TurtleBot3 |
| **`client/`** | Unity 관제 UI (디지털트윈) | Unity 6.3 LTS · UI Toolkit · ROS-TCP-Connector |
| **`server/`** | 로그·출동·포즈 저장 | Supabase (PostgreSQL) |
| **`src/urhynix_nav/maps/`** | 저장 SLAM 맵 (arena_shared) | Nav2 map_server (pgm+yaml) |

로봇↔Unity는 **ROS-TCP-Connector**(토픽 기반)로 연결되고, ROS 2 액션(Nav2)은 로봇측 브리지(`patrol_waypoints_bridge.py`)가 "토픽→액션"으로 번역한다.

---

## 레포 구조

```
urhynix-amr/
├── src/                       # ROS 2 워크스페이스 (colcon)
│   ├── urhynix_bringup/       # 로봇 하드웨어 기동 (TurtleBot3 + 센서)
│   ├── urhynix_nav/           # Nav2 · AMCL · 독 재시딩 · nav 파라미터
│   ├── urhynix_patrol/        # ★주행 알고리즘: 경로 최적화 · 무한순찰 브리지 · 주행준비
│   ├── urhynix_bridge/        # Unity↔ROS 상주 서비스 (systemd user)
│   ├── urhynix_slam/          # 지도 작성 · 스캔 검증 · RTAB-Map
│   └── urhynix_perception/    # Arduino 센서 · ArUco 주차 · YOLO
├── client/ControlRoom/        # Unity 관제 프로젝트
├── server/                    # Supabase 마이그레이션 · SQL
│   └── urhynix_nav/maps/     # 저장 맵 (pgm + yaml)
├── urhynix.repos              # 외부 ROS2 의존 (turtlebot3 등, vcs)
└── README.md
```

---

## 🚗 주행 알고리즘

이 프로젝트의 핵심. 로봇이 **좁은 회랑(로봇 26cm가 겨우 통과)** 을 낀 두 구역 아레나를 안전하게 무한 순찰하도록 만든 4가지 알고리즘이다.

### 1. 데이터 기반 최적 순찰 경로 — `urhynix_patrol/patrol_route_optimizer.py`

저장 맵(pgm)에서 **직접 경로를 계산**한다. 사람이 웨이포인트를 찍으면 로봇보다 좁은 틈을 관통해 벽을 스치므로(grazing), 다음 파이프라인으로 안전 경로를 뽑는다:

1. **Clearance field** — 모든 자유 셀에서 가장 가까운 장애물까지 거리(다중소스 BFS).
2. **방 중심 추출** — 각 구역의 최대 여유점(좌 0.44m / 우 0.42m 여유).
3. **Widest-path 스파인** — 방 중심들을 **"최소 병목 여유를 최대화"(maximin)** 하는 경로로 연결 → 회랑을 **정중앙**으로 통과.
4. **여유 보장 단순화** — 모든 레그의 직선 최소 여유가 로봇 반폭(0.13m) 이상이 되도록 재귀 분할(RDP + clearance guard).
5. **검증** — 레그별 최소 여유 + 커버리지 %를 출력.

```bash
python3 src/urhynix_patrol/patrol_route_optimizer.py
# → 왕복 웨이포인트 + 레그별 최소여유 + 커버리지 + ASCII 시각화
```

> **효과**: 코너 커팅 경로(최악 레그 여유 **4cm**) → 정중앙 스파인(**14cm**). grazing·잠김 근절.

### 2. Nav2 자율주행 스택 — `urhynix_nav/`

- **AMCL 독 재시딩** (`_dock_reseed.sh`) — 충전독 고정좌표를 `/initialpose`로 선언(nomotion 갱신). 로봇이 항상 독에서 출발하므로 위치를 즉시 수렴시킨다.
- **Nav2 파라미터 생성** (`patch_nav_params_ns.py`) — collision_monitor(PolygonStop/Slow/Limit), SmacPlanner2D, controller_server를 협소 회랑에 맞춰 튜닝. 좁은 회랑용 얇은 inflation, source_timeout 여유 등.
- **8노드 lifecycle 기동** (`_restart_nav_ns.sh`) — controller/planner/behavior/bt_navigator/smoother/velocity_smoother/collision_monitor/waypoint_follower를 configure→activate.

### 3. Unity↔ROS 브리지 & 무한순찰 — `urhynix_patrol/patrol_waypoints_bridge.py`

ROS-TCP는 액션 미지원 → 이 노드가 Unity의 `PoseArray`를 받아 Nav2 `goToPose`로 실행한다.

- **무한 왕복 순찰** — 웨이포인트를 왕복(1→N→1)으로 `/patrol_stop`이 올 때까지 반복.
- **레그별 사전 회전** — 다음 목표 방위로 먼저 회전 후 이동("보고 출발"). 등지고 출발 대비 실측 4~5배 빠름.
- **탈출 리커버리** — 레그 실패(주로 "Start occupied": 출발 셀이 장애물 셀) 시 `clearCostmap + 후진`으로 자유공간 복귀 → 무한순찰이 중간에 죽지 않는다.
- **복귀 주차** — 정지 시 충전독으로 복귀(위치는 goToPose, 방향은 Spin 정렬).
- **주행 기록** — 레그/랩/주차를 `~/patrol_runs.jsonl`(JSONL)로 영속 기록 → 사후 판정.

### 4. 주행준비 원버튼 — `urhynix_patrol/t1_drive_ready.sh` + `urhynix_bridge/robot_services/readyd.py`

Unity 버튼 → `/prepare_drive`(Bool) → readyd 데몬이 6단계를 1회 실행:
`bringup → 배터리 게이트 → nav 파라미터 → AMCL/map_server + 독 재시딩 → nav2 8노드 lifecycle → 검증`.
진행 상황은 `/drive_ready_status`(String, latched)로 Unity에 실시간 회신.

**주고받는 토픽** (`<robot>` = 예: `tb3_1`):

| 토픽 | 타입 | 방향 | 의미 |
|---|---|---|---|
| `/<robot>/prepare_drive` | Bool | Unity→로봇 | 주행준비 6단계 실행 |
| `/<robot>/reseed` | Bool | Unity→로봇 | 독 좌표로 위치만 재선언 |
| `/<robot>/drive_ready_status` | String | 로봇→Unity | 진행 로그 |
| `/<robot>/patrol_waypoints` | PoseArray | Unity→로봇 | 순찰 경로 |
| `/<robot>/patrol_stop` | Bool | Unity→로봇 | 무한순찰 정지→복귀주차 |
| `/<robot>/goal_pose` | PoseStamped | Unity→로봇 | 단발 출동 |

---

## 🛠 로봇 실행법

### 사전 요구사항

- **로봇**: TurtleBot3 (Raspberry Pi + OpenCR), ROS 2 Jazzy (Ubuntu 24.04)
- **관제 PC**: Unity 6.3 LTS 이상 (Windows/macOS/Linux)
- 같은 네트워크 + 로봇별 `ROS_DOMAIN_ID` (예: tb3_1=2)

### 1) 워크스페이스 설치 (로봇에서)

```bash
git clone <this-repo> ~/urhynix-amr && cd ~/urhynix-amr
vcs import src < urhynix.repos          # turtlebot3 등 외부 의존
rosdep install --from-paths src -y      # 의존성
colcon build --symlink-install          # (또는 src/urhynix_*의 스크립트를 직접 실행)
source install/setup.bash
export ROS_DOMAIN_ID=2                   # 로봇별 도메인
export URHYNIX_MAPS=$PWD/src/urhynix_nav/maps   # 미설정 시 레포 상대경로 자동
```

### 2) 로봇 기동 → 주행준비 → 순찰

```bash
# 하드웨어 + 센서 bringup
bash src/urhynix_bringup/_t1_up.sh

# 주행준비 원버튼 (bringup 검증 → AMCL 독 시딩 → nav2 8노드 → 검증)
bash src/urhynix_patrol/t1_drive_ready.sh
#   또는 Unity에서 "🔧 주행준비" 버튼 → /prepare_drive 발행

# 순찰 시작: 최적 경로를 로봇에 발행 (Unity "▶ 순찰 시작"과 동일)
python3 src/urhynix_patrol/patrol_presets.py --pubcmd 1 | bash   # 프리셋1=최적 안전순찰
#   무한 왕복 순찰 시작 → 정지: /<robot>/patrol_stop 발행

# 주행 판정
cat ~/patrol_runs.jsonl        # 레그별 시간·주차 오차
```

### 3) 상주 서비스 (재부팅 생존, 선택)

```bash
# endpoint(:10000) / scanfix / posepub / bridge / readyd 를 systemd user로
cp src/urhynix_bridge/robot_services/*.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now urhynix-*
```

### 4) Unity 관제 클라이언트

1. Unity Hub로 `client/ControlRoom/` 열기 (Unity 6.3 LTS).
2. `Resources/RosConfig/ros_endpoint.json`에서 로봇 IP·포트(10000) 설정.
3. `Resources/SupabaseConfig/supabase.json` 생성 (**anon key만**, service_role 금지 — `.gitignore` 대상).
4. Play → 맵 우클릭으로 순찰 편집·주행준비·순찰 시작.

---

## 🌐 크로스플랫폼

- **경로**: 맥 절대경로를 전부 제거 → `URHYNIX_MAPS` 환경변수(미설정 시 레포 상대경로 자동). Windows는 WSL2 권장.
- **Unity 관제**: Windows/macOS/Linux 어디서든 프로젝트를 열 수 있다(Unity 크로스플랫폼).
- **로봇**: ROS 2 Jazzy 표준 — Ubuntu 24.04. 스크립트는 bash(로봇) 기준.

## ⚙️ 주요 환경변수

| 변수 | 기본 | 용도 |
|---|---|---|
| `ROS_DOMAIN_ID` | (로봇별) | 멀티로봇 도메인 격리 (예: tb3_1=2) |
| `URHYNIX_MAPS` | 레포 `maps/` | 저장 맵 디렉토리 |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | DDS 구현 |

## 라이선스

MIT — [LICENSE](LICENSE) 참조.
