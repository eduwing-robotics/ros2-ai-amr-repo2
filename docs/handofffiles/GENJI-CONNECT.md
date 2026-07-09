# 젠지(genji / tb3_2) 접속 가이드

> 동료 핸드오프용. 젠지 라즈베리파이에 SSH로 붙고, ROS2 도메인·네트워크 함정을 피하는 최소 지식.
> ⚠️ IP는 DHCP로 **항상 바뀜** — 아래 값은 스냅샷(2026-06-30 기준). 안 붙으면 "IP 드리프트" 절로.

## 한 줄 요약

젠지 = TurtleBot3 `tb3_2`, 라즈베리파이, 계정 **`kim`**, **ROS_DOMAIN_ID=1**. 티원(tb3_1, 계정 `t1`, 도메인 2)과 **도메인이 다름** — 둘은 서로 안 보임(의도된 격리).

## 1. SSH 접속

| 경로 | 주소 | 비고 |
|---|---|---|
| WiFi (wlan0) | `192.168.20.7` | 평소 경로. 팀 wifi 불안정 시 끊길 수 있음 |
| 랜선 직결 (eth0) | `192.168.10.50` | wifi AP isolation으로 무선이 막힐 때 우회 |

```bash
ssh kim@192.168.20.7          # 현재 IP (드리프트하면 아래 참조)
```

**ssh alias를 쓰려면** 본인 `~/.ssh/config`에 추가:
```
Host urhynix-robot genzi g1
    HostName 192.168.20.7      # drift 시 이 줄만 갱신
    User kim
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30
```
→ 이후 `ssh genzi` / `ssh g1`.

- **키 인증이 안 되면**: 본인 pubkey를 젠지 `~/.ssh/authorized_keys`에 등록 요청, 또는 password 인증.
- **sudo 비번**: 보안 정책상 git에 안 박음 — **팀 채널로 별도 공유**(계정 `kim`). 셧다운/센서 등 sudo 필요 작업 시 필요.

## 2. ROS2 환경 (붙은 다음)

```bash
source /opt/ros/jazzy/setup.bash
source ~/turtlebot3_ws/install/setup.bash      # 있으면
export ROS_DOMAIN_ID=1                          # ★젠지=1 (티원=2)
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
ros2 topic list                                 # /tb3_2/... 또는 비-ns 토픽 확인
```
젠지는 **비-namespaced 단일 nav2 스택**(nav_up.sh)을 쓴다 — 티원의 tb3_1 네임스페이스 방식과 다름. 자세한 건 `skill-urhynix-genji-nav2-drive.md`.

## 3. IP 드리프트 (제일 흔한 막힘)

`192.168.20.7`이 안 되면 DHCP로 IP가 바뀐 것. 순서:

1. **`skill-robot-ip-detect-fallback.md`** — mDNS(`urhynix-robot.local`/`rb.local`) 시도 → 안 되면 ARP 캐시 + 라즈베리파이 OUI(`d8:3a:dd`, `b8:27:eb` 등)로 실제 IP 탐색.
2. **`skill-ip-drift-resync.md`** — 찾은 IP로 `default_robots.json`(Unity SSOT) + `known_hosts`를 한 번에 동기화. Unity가 "로봇 연결 안 됨"인데 ssh는 되는 경우도 이걸로.
3. ssh config의 `HostName` 한 줄 갱신.

> 참고: Unity SSOT `default_robots.json`는 `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json`. ssh config와 별도 파일이라 자동 동기 안 됨 — drift 시 둘 다 갱신.

## 4. 네트워크 함정

- **팀 wifi `codelab_robot_team_2_5G`**: 로봇이 현재 붙는 망. 간헐적으로 끊김(배너교환 타임아웃) — 몇 초 후 재시도로 대부분 복구.
- **AP isolation**: 팀 ipTIME은 AP isolation이라 같은 wifi여도 Mac↔로봇 무선 SSH가 막힐 수 있음 → **랜선 직결(eth0 192.168.10.50)** 또는 Mac↔젠지 직결+DHCP로 우회.
- **도메인 진단**: 로봇이 Unity 맵에 안 뜨거나 노드가 두 개씩 보이거나 `/map`·`/tf`가 엉키면 `skill-urhynix-ros-domain-diagnose.md`(ROS_DOMAIN_ID 빈값/충돌 진단).

## 5. 다음 스텝 → 스킬 인덱스

접속됐으면 `README.md`의 스킬 순서대로. 젠지 주행 핵심은 `skill-urhynix-genji-nav2-drive.md`, 5트랙 풀스택은 `skill-urhynix-fullstack-bringup.md`, 종료는 `skill-urhynix-robot-shutdown.md`.

---
**한줄정리**: 젠지=`kim`@`192.168.20.7`(드리프트하면 ip-detect-fallback→ip-drift-resync), ROS_DOMAIN_ID=**1**, 비-ns nav2. sudo 비번은 팀 채널 별도공유. 안 붙으면 AP isolation→랜선직결(eth0 .50).
