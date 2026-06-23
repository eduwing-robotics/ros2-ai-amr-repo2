# Mac Docker SLAM 진행 evidence — 2026-05-29

> 라즈베리파이 디스크 회피를 위한 Mac Docker SLAM 셋업 과정 + Discovery 디버깅 출발점.

## 한 줄 요약

Robot bringup + Mac Docker + Discovery Server 인프라까지 모두 작동하지만 **macOS Docker host networking의 inbound UDP가 컨테이너 프로세스로 라우팅되지 않아** Mac 컨테이너에서 robot 토픽 발견 실패. 다음 세션 디버깅 출발점 보관.

## Timeline

| 시각 | 사건 |
|---|---|
| 10:20 | Robot 첫 부팅, 디스크 96% (641MB) |
| 10:23 | `apt install ros-jazzy-turtlebot3-cartographer ros-jazzy-turtlebot3-navigation2 ros-jazzy-nav2-map-server` 시작 |
| 10:40-50 | dpkg가 디스크 0 byte까지 떨어지며 hang. 4/4 패키지 commit은 끝났지만 ldconfig trigger 멈춤 |
| 11:00 | 사용자가 메인 스위치 OFF/ON. journalctl 196MB 해제로 디스크 1.1GB 회복 |
| 11:16 | bringup 시도 — workspace 깨짐 (`coin_d4_driver/single_coin_d4_node not found`). 원인: 디스크 정리 시 `~/turtlebot3_ws/build` 같이 삭제로 install/setup.bash hook 일부 깨짐 |
| 11:40 | 워크스페이스 클린 재빌드 시작 — `colcon build --symlink-install --parallel-workers 1 --executor sequential` |
| 11:46 | 빌드 완료 — 8 packages, 6분 17초 |
| 12:06 | bringup 정상 launch. `/scan /odom /tf` 등 13 topic publish |
| 12:12 | Mac Docker `robotis/turtlebot3:jazzy-pc-latest` 5GB pull 완료 |
| 12:13 | 컨테이너에서 `ros2 topic list` → robot 토픽 안 보임. Fast RTPS multicast 차단 추정 |
| 12:14 | Fast DDS Discovery Server fallback 시도. `urhynix_dds` 컨테이너 11811 listen |
| 12:15 | Robot에 `ROS_DISCOVERY_SERVER=192.168.0.104:11811` env export + bringup 재시작 |
| 12:16 | DS 로그에 robot 접속 메시지 0건. `nc -uvz 192.168.0.104 11811` 통과지만 actual UDP packet은 docker 컨테이너 process로 라우팅되지 않음 |

## 재현 명령

### Robot 측
```bash
# 워크스페이스 클린 재빌드 (sequential, 메모리 부담 최소)
cd ~/turtlebot3_ws
rm -rf install build log
source /opt/ros/jazzy/setup.bash
nohup colcon build --symlink-install --parallel-workers 1 --executor sequential > /tmp/colcon.log 2>&1 &
disown
# 약 6-10분 후 완료 검증
grep Summary /tmp/colcon.log
```

### Mac 호스트 (검증 + 디버그)
```bash
. ~/.tb3rc && . ~/jason/URHYNIX/scripts/tb3.sh

# 1) bringup
tb3-up
sleep 12
ssh kim@$(tb3-ip) 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash 2>/dev/null && export ROS_DOMAIN_ID=56 RMW_IMPLEMENTATION=rmw_fastrtps_cpp && ros2 daemon stop >/dev/null; ros2 daemon start; sleep 3; ros2 topic list | sort'
# 기대: /scan /odom /tf 등 13개 표시

# 2) Discovery Server 컨테이너
docker rm -f urhynix_dds 2>/dev/null
docker run -d --name urhynix_dds --network host \
  robotis/turtlebot3:jazzy-pc-latest \
  bash -c "source /opt/ros/jazzy/setup.bash && fastdds discovery -i 0 -l 0.0.0.0 -p 11811"
sleep 4
docker logs urhynix_dds
# 기대: "Server is running" 메시지

# 3) 컨테이너에서 robot 토픽 발견 시도
docker run --rm --network host \
  -e ROS_DOMAIN_ID=56 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e ROS_DISCOVERY_SERVER=127.0.0.1:11811 \
  -e ROS_SUPER_CLIENT=true \
  -e TURTLEBOT3_MODEL=burger \
  robotis/turtlebot3:jazzy-pc-latest \
  bash -c "source /opt/ros/jazzy/setup.bash; ros2 daemon stop >/dev/null; ros2 daemon start; sleep 4; ros2 topic list"
# 현재: /parameter_events /rosout만 (robot 토픽 미발견)
```

## 다음 디버깅 출발점

### 1) Inbound UDP 실제 수신 확인 (가장 먼저)
```bash
docker exec urhynix_dds bash -c "apt-get update -qq && apt-get install -y tcpdump >/dev/null && timeout 10 tcpdump -n -i any 'udp port 11811'"
# robot 측에서 bringup 실행한 뒤 packet count 확인
# 0이면 macOS docker host networking inbound 라우팅 issue 확정
```

### 2) Fast DDS XML strict unicast peer (multicast 우회)
- robot 측: `ROS_DISCOVERY_SERVER` 대신 InitialPeers XML로 mac IP 명시
- Mac 컨테이너: InitialPeers XML로 robot IP 명시
- `FASTDDS_DEFAULT_PROFILES_FILE` env로 path 지정
- 참고: https://fast-dds.docs.eprosima.com/en/latest/fastdds/transport/datasharing/datasharing.html

### 3) Cyclone DDS 양쪽 동기화
```bash
# Robot 측:
sudo apt install ros-jazzy-rmw-cyclonedds-cpp
# 약 100MB. 디스크 1.1GB 남음 → 위험. 우선 디스크 추가 정리 필요

# Mac 컨테이너에 cyclonedds CYCLONEDDS_URI XML 설정
# 양쪽 RMW=rmw_cyclonedds_cpp 통일
```

### 4) `osrf/ros:jazzy-desktop` base 시도
- robotis 이미지의 내부 DDS 설정 영향 가능성 우회
- `apt install ros-jazzy-turtlebot3-cartographer` 한 줄 추가 (1-2분)

### 5) 동료 Ubuntu native fallback
- macOS Docker 우회. native Linux의 multicast는 정상 작동
- Phase B-E는 Mac Docker와 동일, host만 Ubuntu로

## 학습

1. **`~/turtlebot3_ws/build` 절대 지우지 말 것** — install/setup.bash가 build/의 hook 일부에 의존. 디스크 정리 시 build 보호.
2. **sequential 빌드 패턴**: `--parallel-workers 1 --executor sequential` — RPi 4 (4GB RAM) + SD swap 환경에서 OOM/thrash 회피.
3. **dpkg hang 회복 패턴**: 디스크 풀로 trigger 멈춤 → reboot으로 자체 회복 + journalctl --vacuum-size=10M (sudo `echo password | ssh -T host 'sudo -S cmd'` 패턴)으로 200MB+ 회복.
4. **macOS Docker host networking 한계**: outbound는 작동하지만 inbound UDP는 컨테이너 process로 라우팅 안 함 (`com.docker`가 받아도 컨테이너 안의 listener는 못 받음). Docker Desktop 4.34+ release notes에 명시 안 됨.

## 자산 인벤토리 (오늘 만든 것)

- `docs/ref/MAC-DOCKER-ROS2-PLAYBOOK.md` — Mac Docker SLAM 셋업 250줄 + Known Issue §6.5
- `docs/ref/ARENA-DEPLOYMENT-CHECKLIST.md` — 경기장 출동 가방·소프트·현장 10단계·비상·회수
- `.claude/skills/slam-nav2-arena-survey/SKILL.md` — 6 Phase 흐름 + Unity 좌표축 변환 표 + 평가 체크리스트
- `scripts/tb3.sh` — `tb3-docker-*` 8 helpers (pull/topics/shell/slam/mhz/save/logs/stop) + `tb3-disk-cleanup` + `tb3-pkg-install` 추가
- `scripts/urhynix_robot_up.sh` — `ROS_DISCOVERY_SERVER` env export 추가
