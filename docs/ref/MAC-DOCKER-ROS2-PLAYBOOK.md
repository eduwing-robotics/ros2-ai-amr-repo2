# Mac Docker ROS2 SLAM Playbook — URHYNIX

> **목적**: 라즈베리파이 SD 디스크 부족 문제를 회피하기 위해 cartographer + nav2를 Mac Docker 컨테이너로 옮긴다. 로봇은 bringup만 담당, 호스트가 SLAM을 처리한다.
>
> **마지막 갱신**: 2026-05-29 · **출처**: 본문 하단 Sources

## 1. 왜 Mac Docker인가

| 비교 | 로봇 측 SLAM | Mac Docker SLAM |
|---|---|---|
| 라즈베리파이 SD | 15GB (96-100% 사용) | 손 안 댐 |
| 설치 시간 | apt 7-15분 (디스크 부족 위험) | 이미지 pull 10-30분 (1회) |
| 성능 | RPi 4 CPU 부담 | Mac M-series 빠름 |
| 재시도 비용 | dpkg lock 복구 어려움 | 컨테이너 삭제 후 재실행 |
| 네트워크 | LAN 직접 | Docker host network 필요 |

## 2. 아키텍처

```
[로봇 RPi 192.168.0.x]              [Mac (Apple Silicon)]
  bringup tmux            ──→ /scan /odom /tf ──→  Docker container
  arduino_bridge tmux                              robotis/turtlebot3:
  ros_tcp_endpoint tmux                            jazzy-pc-latest
       ↑ (그대로 유지)                             ↓
                                                  cartographer
                                                  ↓ /map
                                                  ↓
                                                  map_saver_cli
                                                  ↓ pgm + yaml
                                                  ↓ (volume mount)
                                                  Mac host filesystem
                                                  → docs/evidence/maps/
                                                  → unity-smoke/Assets/Maps/
```

핵심 결정:
- **로봇은 bringup만**. cartographer/nav2/map-server는 로봇에 깔지 않는다.
- **호스트 네트워크 모드** (`--network host`) — 컨테이너가 Mac LAN에 직접 노출돼 DDS multicast (239.255.0.1:7400) 양방향 도달.
- **ROS_DOMAIN_ID=56 + RMW=rmw_fastrtps_cpp** — 양쪽 일치.
- **volume mount** — 컨테이너 안의 `~/maps/`를 Mac의 `docs/evidence/maps/`로 바로 매핑.

## 3. 사전 요구사항

### Mac 측
- macOS 14+ (Apple Silicon 권장)
- **Docker Desktop 4.34 이상** — host networking 지원이 4.34에서 처음 도입됨
- Docker Hub 계정 (host networking은 Docker 계정 sign-in 필요)
- 디스크 여유 ≥ 10GB (이미지 5GB + 작업 공간)
- 같은 LAN에 로봇 (`192.168.0.0/24`)

### 로봇 측 (이미 충족)
- `tb3-go`로 bringup + ros_tcp_endpoint + arduino_bridge 작동
- ROS_DOMAIN_ID=56 export
- `/scan`, `/odom`, `/tf` publish 살아있음

## 4. Phase 별 절차

### Phase A) Docker Desktop 설치 + 호스트 네트워크 활성

```bash
# Apple Silicon Homebrew:
brew install --cask docker
open -a Docker
# 첫 실행 시:
# - 라이선스 동의
# - Docker Hub sign-in (host networking 활성 조건)

# Settings → Resources → Network → "Enable host networking" 체크 → Apply & Restart

# 검증:
docker --version       # 28.x 이상
docker info | grep -i 'host networking\|server version'
```

### Phase B) 이미지 pull + 첫 컨테이너

```bash
# 1) 5GB 다운로드 (10-30분, 회선 따라)
docker pull robotis/turtlebot3:jazzy-pc-latest

# 2) 첫 실행 (네트워크 발견 검증)
docker run --rm -it \
  --network host \
  --platform linux/arm64 \
  -e ROS_DOMAIN_ID=56 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET \
  -e ROS_STATIC_PEERS=192.168.0.148 \
  -e TURTLEBOT3_MODEL=burger \
  robotis/turtlebot3:jazzy-pc-latest \
  bash

# 컨테이너 안에서:
source /opt/ros/jazzy/setup.bash
source /opt/turtlebot3_ws/install/setup.bash 2>/dev/null || true   # 이미지에 따라 경로 다름
ros2 topic list                 # /scan /odom /tf /battery_state 보여야 함
ros2 topic hz /scan             # ≥ 5 Hz (LDS-03)
```

### Phase C) SLAM 시작

```bash
# 컨테이너 안에서:
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=False

# 새 터미널에서 컨테이너 attach:
docker exec -it <container_id> bash
source /opt/ros/jazzy/setup.bash
ros2 topic hz /map              # ≥ 0.5 Hz
ros2 topic echo /map --once | head -10
```

### Phase D) 매핑 주행

```bash
# Mac 호스트에서 (기존 helper 그대로):
tb3-teleop                      # SSH 로봇 직접 인터랙티브
# i / j / l / , / k 로 운전, 천천히 한 방향 루프 + 출발점 복귀
```

또는 컨테이너 안에서:
```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

### Phase E) 맵 저장 (volume mount 패턴)

```bash
# 호스트에서: 컨테이너에 volume 마운트해서 띄움 (B/C/D 단계 재시작)
docker run --rm -it \
  --network host \
  --platform linux/arm64 \
  -e ROS_DOMAIN_ID=56 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e TURTLEBOT3_MODEL=burger \
  -v ~/jason/URHYNIX/docs/evidence/maps:/maps \
  robotis/turtlebot3:jazzy-pc-latest bash

# 컨테이너 안에서:
cd /maps && mkdir -p arena_v1 && cd arena_v1
ros2 run nav2_map_server map_saver_cli -f arena_v1
# → /maps/arena_v1/arena_v1.{pgm,yaml} 생성, Mac host에서 바로 접근 가능

# 호스트로 돌아와 PNG 변환 + Unity 임포트:
exit
tb3-map-to-unity arena_v1       # 기존 helper
```

### Phase F) 정리

```bash
# 컨테이너 종료 (Ctrl+D 또는 exit)
# 컨테이너는 --rm이라 자동 삭제됨
# 이미지는 보존 (다음 세션에 재사용)
docker images | grep robotis
```

## 5. 네트워크 검증 매트릭스

| 컨테이너에서 | 기대 결과 | 실패 시 조치 |
|---|---|---|
| `ping 192.168.0.148` | 응답 OK | host networking 꺼짐 또는 LAN 불일치 |
| `ros2 daemon stop && ros2 daemon start` 후 `ros2 topic list` | `/scan /odom /tf` 등 표시 | `ROS_DOMAIN_ID` 불일치, `ROS_STATIC_PEERS` 누락 |
| `ros2 topic hz /scan` | ≥ 5 Hz | LiDAR 또는 bringup 죽음 → `tb3-restart` |
| 로봇 측 `ros2 node list` | `/cartographer_node` 보임 | container의 cartographer가 robot에서 발견됨 = 양방향 OK |

## 6. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `ros2 topic list` 비어있음 | host networking 비활성 또는 DDS multicast 차단 | Docker Desktop Settings → Network → host networking ON. 안 되면 `ROS_AUTOMATIC_DISCOVERY_RANGE=OFF` + `ROS_STATIC_PEERS=<robot IP>` 강제. |
| `docker pull` 실패 (architecture) | Apple Silicon에 amd64만 받음 | `docker pull --platform linux/arm64 robotis/turtlebot3:jazzy-pc-latest` |
| `/map` 토픽 안 나옴 | TF 트리 깨짐 (`base_footprint↔odom` 누락) | 로봇 `tb3-restart`. 그래도 안 되면 robot 측 `tf2_echo` 확인 |
| 컨테이너 빠르게 종료 | 첫 실행에서 GUI 없는 launch 죽음 | `bash` 진입 후 수동 launch. `&` 백그라운드 또는 `tmux new -s slam` |
| `map_saver_cli` 빈 파일만 생성 | `/map` 토픽 publish rate 0 | cartographer 죽음 확인 (위 hz 검증) |
| Cartographer가 RPi에서 발견 못함 | Docker Desktop 4.33 이하 (host networking 미지원) | Docker Desktop 업그레이드 또는 Fast DDS Discovery Server fallback (아래 참조) |

## 6.5 Known Issue — macOS Docker inbound UDP 미라우팅 (2026-05-29 발견)

Docker Desktop 4.34+ host networking이 **outbound는 작동**하지만 (`ping`, `nc -uvz` 통과) **inbound UDP는 컨테이너 프로세스로 라우팅되지 않는** 증상 확인.

증상:
- `lsof -nP -iUDP:11811` 결과: `com.docker` (IPv6 dual-stack)가 listening, but **컨테이너 안의 process는 packet 수신 못함**
- Fast DDS Discovery Server 컨테이너 → robot 접속 메시지 0건
- robot의 publish는 정상 (다른 native Linux 호스트에서는 정상 발견됨)

진단 명령:
```bash
docker exec urhynix_dds bash -c "apt-get install -y tcpdump >/dev/null && tcpdump -n -i any 'udp port 11811' -c 5"
# Discovery Server packet count가 0이면 inbound 미라우팅 확정
```

해결 후보 (우선순위):
1. Cyclone DDS XML로 strict unicast peer (multicast 우회) — 양쪽 RMW 통일 필요
2. `osrf/ros:jazzy-desktop` 다른 base 이미지 시도 (robotis 이미지 자체 issue 가능)
3. 동료 Ubuntu native 호스트로 우회 (macOS Docker 우회)
4. Docker Desktop 다음 버전 release notes 확인 (Apple Silicon host networking 개선)

## 7. Fallback — Fast DDS Discovery Server (host networking 안 될 때)

Docker Desktop 4.34 미만 또는 host networking 문제 시:

```bash
# Mac 호스트 또는 컨테이너에 별도 Discovery Server 띄움
docker run --rm -it --network host \
  robotis/turtlebot3:jazzy-pc-latest \
  fastdds discovery -i 0 -l 0.0.0.0 -p 11811

# 로봇 측 (별도 SSH):
export ROS_DISCOVERY_SERVER=<mac IP>:11811
ros2 daemon stop && ros2 daemon start

# 컨테이너 측 (cartographer 띄울 때):
export ROS_DISCOVERY_SERVER=127.0.0.1:11811
ros2 launch turtlebot3_cartographer cartographer.launch.py
```

## 8. 새 헬퍼 (예정)

`scripts/tb3.sh`에 추가할 helper:

| Helper | 역할 |
|---|---|
| `tb3-docker-pull` | 이미지 5GB pull (1회) |
| `tb3-docker-shell` | host network + env 자동 + bash 진입 |
| `tb3-docker-slam` | cartographer launch (tmux 백그라운드) |
| `tb3-docker-save N` | volume mount된 /maps에 저장 + 호스트로 자동 노출 |

## 9. Sources

- [Installing ROS 2 on macOS with Docker — Foxglove](https://foxglove.dev/blog/installing-ros2-on-macos-with-docker)
- [The Complete Guide to Docker for ROS 2 Jazzy Projects — automaticaddison](https://automaticaddison.com/the-complete-guide-to-docker-for-ros-2-jazzy-projects/)
- [robotis/turtlebot3 Docker Hub](https://hub.docker.com/r/robotis/turtlebot3/tags)
- [TurtleBot3 Docker Container Setup — ROBOTIS eManual](https://emanual.robotis.com/docs/en/platform/turtlebot3/docker_container_setup/)
- [Host network driver — Docker Docs](https://docs.docker.com/engine/network/drivers/host/)
- [Docker Desktop 4.34 host networking support — Docker roadmap #238](https://github.com/docker/roadmap/issues/238)
- [Fix ROS 2 Discovery Issues in Docker in 15 Minutes — markaicode](https://markaicode.com/fix-ros2-docker-discovery-issues/)
- [Using Fast DDS Discovery Server — ROS 2 Jazzy docs](https://docs.ros.org/en/jazzy/Tutorials/Advanced/Discovery-Server/Discovery-Server.html)
- [ros2docker-mac-network — dcedyga](https://github.com/dcedyga/ros2docker-mac-network)
- [TurtleBot3 ROS2 Jazzy Dev Container — prakash-aryan](https://github.com/prakash-aryan/turtlebot3_jazzy_devcontainer)

## 10. 한줄정리

Docker Desktop 4.34+ host networking + `robotis/turtlebot3:jazzy-pc-latest` 이미지로 cartographer/nav2를 Mac에서 띄우고, 로봇은 bringup만 유지하는 분산 패턴. 라즈베리파이 디스크 손 안 대고 SLAM 전체 흐름 완수 가능.
