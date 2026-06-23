---
name: urhynix-battery-bringup
description: URHYNIX 듀얼 로봇 배터리 결선 표준 — turtlebot3_bringup namespace 인자 + ros_tcp_endpoint 자급 빌드 + Unity BatterySubscriber + voltage 선형 환산(LiPo 3S) + 끊김 감지 3중(timeout/present/voltage). 매 세션 배터리 트랙 살리는 데 반복 사용. 함정 #19~#23(OpenCR percentage 무효값/본체 메인 스위치/dialout 미가입/3대 launch 충돌/Wi-Fi IP drift)까지 포함.
---

# urhynix-battery-bringup

## 언제 쓰나

- 매 세션 — 양 로봇 `/tb3_*/battery_state` 토픽 살리고 Unity ControlRoom 우측 패널 배터리 게이지에 실 voltage 표시할 때
- TB3 본체 재부팅 후 turtlebot3_node 자동 시작 안 됨 (수동 launch 필요)
- 박물관 시연 dry-run 직전
- 배터리 끊김 감지 시연 (한쪽 본체 전원 OFF → 5초 후 ⚠️ 토픽 끊김 로그)

## 사용 호스트

| 별명 | hostname | IP (현재) | namespace | OpenCR 포트 |
|---|---|---|---|---|
| 티원 | `rb` | `t1@192.168.10.250` | `/tb3_1` | `/dev/ttyACM0` |
| 젠지 | `kim-desktop` | `kim@192.168.10.87` | `/tb3_2` | `/dev/ttyACM0` |

- `ROS_DOMAIN_ID=230` 양쪽 동일
- `TURTLEBOT3_MODEL=burger`, `LDS_MODEL=LDS-03`
- IP는 DHCP drift 빈번 → `default_robots.json` SSOT로 관리 (`ControlRoomApp.ConfigureRos`가 자동 읽음)

## 표준 launch — 양 로봇

### A. turtlebot3_bringup (namespace 인자 필수)

```bash
# 티원 (tb3_1)
ssh t1@192.168.10.250 'nohup bash -c "
  source /opt/ros/jazzy/setup.bash &&
  source ~/turtlebot3_ws/install/setup.bash &&
  export ROS_DOMAIN_ID=230 &&
  export TURTLEBOT3_MODEL=burger &&
  export LDS_MODEL=LDS-03 &&
  export OPENCR_PORT=/dev/ttyACM0 &&
  exec ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1
" > /tmp/tb3_bringup_t1.log 2>&1 & disown'

# 젠지 (tb3_2)
ssh kim@192.168.10.87 'nohup bash -c "
  source /opt/ros/jazzy/setup.bash &&
  source ~/turtlebot3_ws/install/setup.bash &&
  export ROS_DOMAIN_ID=230 &&
  export TURTLEBOT3_MODEL=burger &&
  export LDS_MODEL=LDS-03 &&
  export OPENCR_PORT=/dev/ttyACM0 &&
  exec ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_2
" > /tmp/tb3_bringup_g1.log 2>&1 & disown'
```

핵심: **`namespace:=tb3_*` 인자 필수**. 없으면 root namespace로 `/battery_state` 발행 → SSOT 약속(`/tb3_*/battery_state`)과 어긋남 + 양 로봇 토픽 충돌.

> ⚠️ **SLAM과 공존 시 예외**: cartographer는 전역 `/scan`→`/map`을 기대하므로 `namespace:=tb3_*`를 주면 `/scan`이 `/tb3_*/scan`이 되어 SLAM이 깨진다. **SLAM 포함 풀스택**은 non-namespaced bringup으로 가고 배터리만 `/battery_state`→`/tb3_2/battery_state` **relay**로 변환한다. → `urhynix-fullstack-bringup`.

### B. ros_tcp_endpoint (단일 호스트만, 보통 티원)

```bash
ssh t1@192.168.10.250 'nohup bash -c "
  source /opt/ros/jazzy/setup.bash &&
  source ~/turtlebot3_ws/install/setup.bash &&
  export ROS_DOMAIN_ID=230 &&
  exec ros2 run ros_tcp_endpoint default_server_endpoint \
    --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000
" > /tmp/ros_tcp.log 2>&1 & disown'
```

같은 도메인 230이라 단일 endpoint가 양 로봇 토픽 모두 forward. 젠지 endpoint는 미사용 (자급 빌드는 권장).

## TopicRegistry SSOT (Unity 측)

```csharp
// Assets/Scripts/Ros/TopicRegistry.cs
public const string T1BatteryState    = "/tb3_1/battery_state";
public const string GenjiBatteryState = "/tb3_2/battery_state";
```

## Unity Scene 박는 패턴

| GameObject | 컴포넌트 | 속성 |
|---|---|---|
| `BatterySubscriber_T1` | `BatterySubscriber` | `robotId=tb3_1`, `displayLabel=티원` |
| `BatterySubscriber_G` | `BatterySubscriber` | `robotId=tb3_2`, `displayLabel=젠지` |
| `ROSConnection` | `ROSConnection` | `m_RosIPAddress=192.168.10.250`, `m_RosPort=10000` (또는 `default_robots.json` 자동) |

unityctl 자동화:

```bash
unityctl gameobject create --name BatterySubscriber_T1
unityctl component add --id <gid> --type URHYNIX.ControlRoom.Ros.BatterySubscriber
unityctl component set-property --component-id <cid> --property robotId --value tb3_1
unityctl scene save
```

## Voltage 환산 공식 (LiPo 3S burger)

```csharp
float pct = Mathf.Clamp01((voltage - 10.5f) / (12.6f - 10.5f)) * 100f;
// 12.6V (만충) → 100% / 10.5V (cutoff 직전) → 0%
```

⚠️ `BatteryState.percentage` 필드는 OpenCR 펌웨어가 117% 같은 무효값 채움 — **voltage 선형 변환만 신뢰**.

## 끊김 감지 3중

| 신호 | 트리거 | 로그 |
|---|---|---|
| 토픽 timeout | `Time.time - lastMessageTime > 5f` (Update 폴링) | `⚠️ 배터리 토픽 끊김 5초 이상` |
| `present=false` | 메시지 도착했지만 OpenCR가 분리 보고 | `⚠️ 배터리 비정상 — present=false` |
| `voltage < 5.0V` | OpenCR 펌웨어 비정상값 | `⚠️ 배터리 비정상 — voltage=X.XV` |
| 복구 시 | 위 상태에서 정상 메시지 도착 | `🟢 배터리 토픽 복구` / `🟢 배터리 정상 회복` |

## 함정표 (#19~#27, 2026-06-08~09 영구 자산화)

| # | 함정 | 우회 |
|---|---|---|
| 19 | `BatteryState.percentage` 117% 같은 무효값 | voltage 선형 변환만 사용 |
| 20 | TB3 본체 메인 전원 스위치 OFF — OpenCR는 USB 5V로 살아있지만 Dynamixel 응답 0 → `[TxRxResult] There is no status packet` 후 `process has died exit -6` | 본체 메인 스위치 ON 확인 (OpenCR ttyACM0 보임에 속지 말 것) |
| 21 | 새 OS 사용자 `dialout` 그룹 미가입 → `/dev/ttyACM0` `crw-rw----` → `Failed to open port` | `sudo usermod -aG dialout <user>` 영구 + `sudo chmod 666 /dev/ttyACM0` 즉시 우회 |
| 22 | 3대 컴퓨터에서 동시 ssh launch → ttyACM0 선점 경쟁 + OpenCR baudrate handshake stress | 1대만 launch + 나머지는 subscribe-only |
| 23 | DHCP Wi-Fi 변경(`192.168.0.x` ↔ `192.168.10.x`) 시 SSOT IP drift, mDNS 일시 캐시 깨짐 | `default_robots.json` IP 갱신 + `dscacheutil -flushcache` + arp sweep으로 MAC 매칭(`2c:cf:67`=젠지, `d8:3a:dd:ca:c5:f7`=티원) 추적 |
| 24 | `ssh ... 'pkill -f "robot.launch.py"'` 가 exit 255로 즉사 — ssh 명령 라인 자체에 패턴이 박혀있어 sshd 자식 세션이 `pkill -f` 매칭에 걸려 **자기 자신을 죽임** (2026-06-09 발견) | base64 트릭으로 패턴을 ssh CLI에서 숨김: `P1=$(echo -n "robot.launch.py" \| base64); ssh t1@... "P=\$(echo $P1 \| base64 -d); pkill -f \"\$P\""`. 또는 nohup+disown으로 ssh가 0.1초 안에 빠지면 자기 자신 보호됨 (launch 띄우기에는 OK, pkill에는 NG) |
| 25 | `ros2 topic echo /tb3_*/battery_state --once` 4초 timeout으론 첫 메시지 못 받음 — battery_state는 1Hz고 publisher 정착 + DDS discovery에 시간 걸림 (2026-06-09 발견) | `timeout 10`으로 늘리거나 `--timeout 5` 옵션, 또는 sleep 6 후 echo. publisher count 1인데도 echo 실패면 정상 — 좀 더 기다리면 됨 |
| 26 | **USB `/dev/ttyACM*` 번호가 재부팅/재꽂이마다 바뀜** — Arduino UNO가 ACM0이었다가 reboot 후 ACM2가 되기도 함. `OPENCR_PORT=/dev/ttyACM0` 환경변수 하드코딩하면 다른 디바이스(Arduino) 잡고 통신 실패 → `Failed connection with Devices` 후 `process died exit -6` (2026-06-09 발견) | ① **임시**: `udevadm info -q property -n /dev/ttyACM*` 로 어느 게 OpenCR(`ID_VENDOR=ROBOTIS`) / Arduino(`ID_VENDOR=Arduino`)인지 확인 후 심링크 `sudo ln -sf /dev/ttyACM<N> /dev/tb3_arduino` (또는 `/dev/tb3_opencr`). ② **영구**: udev rule `/etc/udev/rules.d/99-tb3-devices.rules`에 `SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", SYMLINK+="tb3_arduino"` + `ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", SYMLINK+="tb3_opencr"` 박기. `sudo udevadm control --reload && sudo udevadm trigger` |
| 27 | `OPENCR_PORT` 환경변수가 `turtlebot3_bringup robot.launch.py`에 무시됨 — launch script는 **`usb_port` LaunchConfiguration**만 읽음 (line 40: `usb_port = LaunchConfiguration('usb_port', default='/dev/ttyACM0')`) (2026-06-09 발견) | launch 명령에 직접 인자 박기: `ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_2 usb_port:=/dev/ttyACM1`. SSOT 스킬에 박힌 `export OPENCR_PORT=/dev/ttyACM0` 줄은 sanity check용으로 남겨도 OK (사용은 안 됨). |

## 검증 명령

```bash
# 1) Publisher 살아있는지
ssh t1@192.168.10.250 'bash -c ". /opt/ros/jazzy/setup.bash && . ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=230 && ros2 topic info /tb3_1/battery_state"'
# 기대: Publisher count: 1

# 2) 실 voltage echo (timeout 10초 필수 — 함정 #25 참고)
ssh t1@192.168.10.250 'bash -c ". /opt/ros/jazzy/setup.bash && . ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=230 && timeout 10 ros2 topic echo /tb3_1/battery_state --once 2>&1 | grep -E \"(voltage|present)\""'
# 기대: voltage: 11~12.6V / present: true

# 3) Unity 측 [VERIFY] (임시 verifier 박혀있을 때)
grep -E "배터리 결선|\[VERIFY\]" ~/Library/Logs/Unity/Editor.log | tail -5
# 기대: tb3_1=99.52, tb3_2=59.05 같은 실수 값
```

## 박물관 시연 매핑

| 시연 흐름 | 토픽 | UI 위치 |
|---|---|---|
| 티원 배터리 게이지 | `/tb3_1/battery_state` | 우측 패널 `battery-percent-label` (탭=티원) |
| 젠지 배터리 게이지 | `/tb3_2/battery_state` | 우측 패널 `battery-percent-label` (탭=젠지) |
| 토글 즉시 갱신 | `OnRobotChanged` 이벤트 | `TelemetryPanelView.OnRobotChanged` |
| 끊김 경고 | 5초 timeout | 로그 패널 `⚠️ 배터리 토픽 끊김 …` |

## 자급 빌드 (젠지 새 OS 케이스 — 2026-06-08 검증)

ROS 2 jazzy 미설치 머신에서 처음부터:

```bash
# Phase 1: ROS 2 jazzy base/desktop
sudo apt install software-properties-common curl gnupg lsb-release
sudo add-apt-repository -y universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-msgs \
  python3-colcon-common-extensions python3-rosdep python3-vcstool git

# Phase 2: workspace clone + build
sudo rosdep init || true
rosdep update
mkdir -p ~/turtlebot3_ws/src && cd ~/turtlebot3_ws/src
git clone -b main https://github.com/ROBOTIS-GIT/turtlebot3.git
git clone -b main-ros2 https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git
git clone https://github.com/ROBOTIS-GIT/coin_d4_driver.git
cd ~/turtlebot3_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --parallel-workers 2

# Phase 3: .bashrc env
cat >> ~/.bashrc <<EOF
export ROS_DOMAIN_ID=230
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-03
export OPENCR_PORT=/dev/ttyACM0
source ~/turtlebot3_ws/install/setup.bash 2>/dev/null
EOF

# Phase 4: dialout perm (함정 #21)
sudo usermod -aG dialout $USER
sudo chmod 666 /dev/ttyACM0  # 즉시 우회
```

총 ~15~20분 (Pi SD card 속도, 다운로드 600MB+).

## 안전 셧다운

```bash
# ROS 프로세스 정리 — base64 트릭 필수 (함정 #24 self-kill 회피)
P1=$(echo -n "robot.launch.py" | base64)
P2=$(echo -n "default_server_endpoint" | base64)
P3=$(echo -n "turtlebot3_ros" | base64)
P4=$(echo -n "single_coin_d4" | base64)
ssh t1@192.168.10.250 "P=\$(echo $P1 | base64 -d); pkill -f \"\$P\"; \
                       P=\$(echo $P2 | base64 -d); pkill -f \"\$P\"; \
                       P=\$(echo $P3 | base64 -d); pkill -f \"\$P\"; \
                       P=\$(echo $P4 | base64 -d); pkill -f \"\$P\"; echo DONE"

# OS halt (sudo 비번 stdin)
ssh t1@192.168.10.250 'echo <PASSWORD> | sudo -S poweroff'

# 10초 후 ping 확인 (응답 없으면 OS halt 완료)
ping -c 2 -W 1500 192.168.10.250
```

## 관련 자산

- 코드 — `unity/ControlRoom/Assets/Scripts/Ros/{TopicRegistry,BatterySubscriber}.cs`
- 코드 — `unity/ControlRoom/Assets/Scripts/App/ControlRoomApp.cs` (IP fallback 패턴)
- 코드 — `unity/ControlRoom/Assets/Scripts/UI/TelemetryPanelView.cs` (탭 전환 즉시 갱신)
- SSOT — `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json` (IP 드리프트 단일 변경 지점)
- evidence — `docs/evidence/2026-06-08-controlroom-battery-real-link.md`
- 상위 스킬 — `robot-camera-bringup` (카메라 트랙, 같은 ros_tcp_endpoint 공유)
