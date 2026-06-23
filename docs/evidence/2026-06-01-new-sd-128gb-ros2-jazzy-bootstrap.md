# 2026-06-01 — 신규 128GB SD 굽기 + Ubuntu 24.04.4 + ROS2 Jazzy 풀 부트스트랩

> 어제 분리된 가벽 진단 정정 이후, 라즈베리파이4 SD를 16GB→128GB로 교체. 새 SD에 cloud-init 사전설정 박아서 굽고, ROS2 Jazzy + turtlebot3 메타 + ld08_driver + ros_tcp_endpoint까지 한 번에 끝낸 세션.

## 결과 요약 (PASS / 부분)

| 항목 | 상태 |
|---|---|
| Ubuntu 24.04.4 LTS Server (arm64) for Pi SD 굽기 | ✅ dd 4.14GB / 148초 / 27MB/s |
| cloud-init NoCloud 자동 인식 (system-boot 루트의 user-data/network-config/meta-data) | ✅ `status: done` `extended_status: done` `DataSourceNoCloud [seed=/dev/mmcblk0p1]` |
| 사용자 `kim` + 비번 `1234` + SSH 키 등록 | ✅ Mac → `ssh urhynix-robot` 비번 없이 진입 |
| hostname `urhynix-robot` | ✅ |
| timezone `Asia/Seoul` / locale `ko_KR.UTF-8` | ✅ |
| eth0 DHCP IP | ✅ `192.168.10.59` (학원 다른 서브넷이지만 라우터가 192.168.0.x↔10.x 라우팅) |
| 128GB SD rootfs 자동 확장 | ✅ `/dev/mmcblk0p2 117G 8.6G 104G 8% /` |
| 시간 동기화 NTP | ✅ `active` `synchronized: yes` |
| `sudo apt upgrade` 보안 패치 | ✅ 재부팅 불필요 |
| avahi-daemon 설치/enable | ✅ `active` (단 mDNS .local은 Mac/robot 서브넷이 달라 라우터 건너 불가) |
| ROS2 Jazzy ros-base + 빌드도구 | ✅ `/opt/ros/jazzy/setup.bash` |
| `ros-jazzy-turtlebot3` 메타 (bringup·cartographer·description·example·navigation2·node·teleop) | ✅ 2.3.6-1noble.20260413 |
| `ros-jazzy-cartographer` + `ros-jazzy-cartographer-ros(-msgs)` | ✅ |
| `ros-jazzy-nav2-bringup` | ✅ |
| `ros-jazzy-hls-lfcd-lds-driver` (LDS-01 폴백) | ✅ |
| `ros-jazzy-dynamixel-sdk` | ✅ |
| `ros-jazzy-rmw-cyclonedds-cpp` | ✅ |
| src 빌드: `ld08_driver` (LDS-03, jazzy 브랜치) | ✅ 47.0s |
| src 빌드: `ros_tcp_endpoint` (Unity 통신, main-ros2 0.7.0) | ✅ 7.2s (setuptools deprecation 경고 1건, 빌드 성공) |
| `~/.bashrc` 환경 source (ros-jazzy + ws + TURTLEBOT3_MODEL=burger + LDS_MODEL=LDS-03 + OPENCR_PORT + ROS_DOMAIN_ID=230) | ✅ | 초기 30 → 2026-06-02에 230으로 통일(티원과 일치) |
| udev rules `/dev/tb3_arduino` (Arduino UNO 2341:0043, 2a03:0043) + `/dev/tb3_opencr` (STM 0483:5740) | ✅ |
| `/etc/urhynix.env` 템플릿 (`640 root:kim`) | ✅ — **단 SUPABASE_KEY=PASTE_... 채워야 함** |
| Mac `~/.ssh/config` `Host urhynix-robot` 별칭 | ✅ `ssh urhynix-robot` 한 단어 진입 |
| Mac `~/.tb3rc` IP/LAN hint 192.168.10.x 갱신 | ✅ |

## 재현 명령 (다음 SD 새로 굽기 / 다른 동료 세팅 시)

```bash
# 0) 이미지 다운로드 + 검증
mkdir -p ~/Downloads/urhynix-sd && cd ~/Downloads/urhynix-sd
curl -L -O https://cdimage.ubuntu.com/releases/24.04.4/release/ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz
shasum -a 256 ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz | grep 790652faeb4f61ce7bb12f5cb61734595c61d3cd882915b8b5f9918106c80d37

# 1) cloud-init 3개 파일 작성 (system-boot 파티션 루트에 둘 것)
#    - user-data: 사용자/비번/SSH키/hostname/timezone/locale/avahi
#    - network-config: eth0 DHCP
#    - meta-data: instance-id/local-hostname
#    내용은 ~/Downloads/urhynix-sd/cloud-init/ 참조

# 2) SD 굽기 (diskutil list 후 디스크 번호 사람과 함께 검증 필수)
diskutil unmountDisk /dev/disk8
xz -dc ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz | sudo dd of=/dev/rdisk8 bs=1m status=progress
sudo sync

# 3) cloud-init 복사
cp ~/Downloads/urhynix-sd/cloud-init/{user-data,network-config,meta-data} /Volumes/system-boot/
sync && diskutil eject /dev/disk8

# 4) 라즈베리파이에 꽂고 전원 ON (라즈베리파이 본체 RJ45에 LAN 직결 — 다른 곳 X)
# 5) 부팅 1~3분 대기, IP 확인:
ssh urhynix-robot 'hostname -I'

# 6) ROS2 Jazzy + turtlebot3 풀 설치 (이 evidence 그대로 재현)
ssh urhynix-robot 'sudo apt-get install -y avahi-daemon avahi-utils && sudo systemctl enable --now avahi-daemon'
ssh urhynix-robot 'sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y'
ssh urhynix-robot 'sudo add-apt-repository universe -y && sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && echo "deb [arch=arm64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/ros2.list && sudo apt-get update'
ssh urhynix-robot 'sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ros-jazzy-ros-base python3-colcon-common-extensions python3-rosdep python3-vcstool python3-argcomplete build-essential git'
ssh urhynix-robot 'sudo rosdep init; rosdep update'
ssh urhynix-robot 'sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-msgs ros-jazzy-cartographer ros-jazzy-cartographer-ros ros-jazzy-cartographer-ros-msgs ros-jazzy-nav2-bringup ros-jazzy-dynamixel-sdk ros-jazzy-hls-lfcd-lds-driver ros-jazzy-rmw-cyclonedds-cpp'
ssh urhynix-robot 'mkdir -p ~/turtlebot3_ws/src && cd ~/turtlebot3_ws/src && git clone -b jazzy https://github.com/ROBOTIS-GIT/ld08_driver.git && git clone -b main-ros2 https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git'
ssh urhynix-robot 'source /opt/ros/jazzy/setup.bash && cd ~/turtlebot3_ws && rosdep install --from-paths src --ignore-src -r -y && colcon build --symlink-install --parallel-workers 2 --cmake-args -DCMAKE_BUILD_TYPE=Release'
```

## 검증된 다음 세션 진입 경로

```bash
# Mac 어디서든:
ssh urhynix-robot   # ← config 별칭, 비번 없이 즉시 진입
# (또는 ssh kim@192.168.10.59)

# robot 안에서 즉시 ROS2 사용 가능 (~/.bashrc 자동 source):
echo $ROS_DISTRO         # → jazzy
echo $TURTLEBOT3_MODEL   # → burger
echo $LDS_MODEL          # → LDS-03
ros2 pkg list | grep -E "turtlebot3|cartographer|nav2|ld08|ros_tcp"
```

## 가벼운 함정 (다음 세션 메모)

1. **mDNS `.local` 안 잡힘** — Mac(192.168.0.71)과 robot(192.168.10.59)가 다른 서브넷이라 mDNS multicast가 라우터 못 건넘. avahi는 robot 안에서 정상 작동. Mac에서는 IP/별칭 사용.
2. **LAN sweep도 의미 약함** — 학원 라우터가 192.168.0.x ↔ 192.168.10.x 라우팅은 해주지만 ARP broadcast는 건너 못 감. `helper sweep`로 robot 못 찾음 → `TB3_ROBOT_IP_HINT` 직접 지정으로 우회 (이미 `~/.tb3rc`에 반영).
3. **LAN 케이블은 라즈베리파이 본체 RJ45에 직결 필수** — 처음에 케이블이 다른 곳(또는 무선 자격증명 가정)에 있어서 `eth0 DOWN`이었음. Wi-Fi 추가 안 한 cloud-init이라 유선 필수.
4. **`/etc/urhynix.env`의 `SUPABASE_KEY=PASTE_SERVICE_ROLE_JWT_HERE`** — 발표 직전 주인님이 수동 채워야 함. 절대 commit 금지.

## 다음 세션 잔여 (주인님 손이 꼭 필요)

| # | 항목 | 명령/액션 | 소요 |
|---|---|---|---|
| 1 | `/etc/urhynix.env` SUPABASE_KEY 채우기 | `ssh urhynix-robot 'sudo nano /etc/urhynix.env'` (service_role JWT 붙여넣기) | 1분 |
| 2 | OpenCR firmware 재플래시 | `export OPENCR_PORT=/dev/tb3_opencr; export OPENCR_MODEL=burger; cd /opt/ros/jazzy/share/turtlebot3_bringup && ./scripts/flash_burger.sh` (필요 시) | 5분 |
| 3 | Arduino PIR/LDR 스케치 재플래시 (D2 핀 SSOT 정렬) | Mac에서 `arduino-flash` 스킬 + USB 연결 | 5분 |
| 4 | Pi 카메라 동작 검증 | `libcamera-hello -t 0` 또는 ROS2 카메라 노드 | 5분 |
| 5 | bringup 검증 (`/scan` `/odom` topic) | `ssh urhynix-robot 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export TURTLEBOT3_MODEL=burger && export LDS_MODEL=LDS-03 && ros2 launch turtlebot3_bringup robot.launch.py'` | 10분 |
| 6 | 가벽 보강 (라이다 높이 < 가벽 OPTION A) + arena_v2 매핑 | HANDOFF 5/29 항목 | 30~60분 |

## §사후 검증 (2026-06-01 13:05~13:10) — Robot 재기동 + Wi-Fi 추가 + 12+ 단계 USB 확인

### 확인 결과 (PASS 13/13)

| 단계 | 항목 | 결과 |
|---|---|---|
| A-1 | SSH 진입 (`ssh urhynix-robot`) | ✅ mDNS resolve OK (학원 Wi-Fi 추가 후 mDNS multicast 작동) |
| A-2 | uptime | ✅ up 10 minutes |
| A-3 | IPs | ✅ eth0=192.168.10.59, wlan0=**192.168.0.82** (Mac 192.168.0.71과 같은 망) |
| A-4 | 환경 변수 (`~/.bashrc` 자동 source) | ✅ interactive SSH 자동, non-interactive는 명시적 source 필요 |
| A-5 | `ros2 pkg list` 핵심 6종 | ✅ turtlebot3, cartographer_ros, nav2_bringup, ld08_driver, ros_tcp_endpoint, hls_lfcd_lds_driver |
| B-6 | Arduino lsusb | ✅ Bus 001 Device 004: `2341:0043 Arduino SA Uno R3 (CDC ACM)` |
| B-7 | 시리얼 디바이스 | ✅ /dev/ttyACM0 (Arduino), /dev/ttyACM1 (OpenCR), /dev/ttyUSB0 (CP2102/LDS-03) |
| B-8 | `/dev/tb3_arduino` udev | ✅ → ttyACM0 |
| B-9 | vendor/product/serial | ✅ `2341:0043` `054433A4937351E02849` |
| B-10 | 시리얼 5~10초 캡처 (9600 baud) | ✅ `=== PIR + LDR Test === / Warming up.........` (스케치 살아있음, PIR HW-740 워밍업 ~30초라 본격 데이터는 그 후) |
| C-11 | `/dev/tb3_opencr` udev | ✅ → ttyACM1 |
| C-12 | OpenCR lsusb | ✅ `0483:5740 STMicroelectronics Virtual COM Port` |
| **D-13 (보너스)** | **`/dev/tb3_lidar` 신규 udev** | ✅ → ttyUSB0 (CP2102 LDS-03 LiDAR USB-Serial 안정 심볼링크 추가) |

### 변경 사항 (사후 검증 중 추가된 것)

1. **netplan `/etc/netplan/60-wifi.yaml`** — codelab_5G Wi-Fi 자동 연결 추가. eth0 + wlan0 둘 다 dhcp4/optional. 재부팅 후에도 자동.
2. **`/etc/udev/rules.d/99-tb3-arduino.rules`** 에 LDS-03 라인 추가: `SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="tb3_lidar", MODE="0666"`
3. **Mac `~/.ssh/config`** — `HostName urhynix-robot.local` (mDNS) 으로 변경 (이전: 192.168.10.59 IP hardcode). DHCP IP 바뀌어도 자동 작동.

### 무선 영구 운용 가능

이제 랜선 없이 학원 Wi-Fi (codelab_5G) 만으로 robot이 자동 LAN 붙음. `ssh urhynix-robot` 한 줄 진입은 유선/무선 무관하게 작동.

### §사후 검증 추가 — 랜선 분리 + 무선 단독 (2026-06-01 13:12)

주인님이 랜선 물리적으로 분리 + (안전 종료 후) 재기동. Mac에서 검증:

| 항목 | 결과 |
|---|---|
| `ping urhynix-robot.local` (mDNS resolve) | ✅ → 192.168.0.82 |
| `ping 192.168.0.82` (16ms) | ✅ 0% loss |
| `ssh urhynix-robot` | ✅ 키 인증 자동 |
| robot 안에서 `ip -4 -br addr show eth0` | ✅ **IP 없음** (랜 분리 상태 정상) |
| robot 안에서 `ip -4 -br addr show wlan0` | ✅ 192.168.0.82/24 |

→ **netplan `60-wifi.yaml`이 영구 자동 연결 보장** 확정. 발표/개발 동안 랜선 자유. 학원 Wi-Fi 비번이 바뀌면 한 번 더 박아야 함.

### §사후 검증 — IP-drift zero-touch 화 (2026-06-01 13:20) — B+C 작업

**문제**: DHCP가 새 IP를 줄 때마다 Unity Scene + Script + helper의 hardcoded IP를 patch해야 했음 (`ip-drift-resync` 스킬 호출 1줄). 영구 해결책으로 mDNS hostname을 모든 진입점에 박음.

**B안 — Unity rosIP를 mDNS hostname 으로 박음**

| 파일 | 변경 |
|---|---|
| `unity-smoke/Assets/Scenes/SampleScene.unity:151` | `rosIP: 192.168.0.33` → `rosIP: urhynix-robot.local` |
| `unity-smoke/Assets/Scripts/RosSmokeDashboard.cs:10` | `public string rosIP = "192.168.0.33"` → `public string rosIP = "urhynix-robot.local"` |

→ Unity의 ROS-TCP-Connector는 hostname도 받음. OS resolver가 mDNS resolve 처리. **이후 IP 변경 시 Unity가 자동 follow** (재기동 시 새 IP로 자동 연결).

**C안 — `scripts/tb3.sh` helper에 mDNS 우선 시도**

| 변경 | 내용 |
|---|---|
| 새 export | `export TB3_HOSTNAME='urhynix-robot'` (mDNS hostname) |
| `tb3-ip()` 함수 맨 앞 | mDNS resolve 우선 시도 (`ping <hostname>.local`에서 IP 추출). 실패 시 기존 ARP sweep으로 fallback |

검증:
```
$ tb3-ip
192.168.0.82   (4.6초 — mDNS, 이전 ARP sweep 10초+ 대비 빠름)
```

**최종 zero-touch 상태**

| 영역 | IP 변경 시 |
|---|---|
| `ssh urhynix-robot` | ✅ 자동 (`~/.ssh/config` mDNS) |
| `tb3-ip` helper | ✅ 자동 (TB3_HOSTNAME mDNS resolve) |
| Unity Scene `rosIP` | ✅ 자동 (hostname 자체가 박혀있음) |
| RosSmokeDashboard.cs 기본값 | ✅ 자동 (동일) |
| ssh known_hosts | ✅ 자동 (별명 키 유지) |
| `~/.tb3rc` IP hint | ⚠️ 비활성 (fallback 전용, mDNS 성공 시 무시) |

→ `ip-drift-resync` 스킬은 이제 **안전망**으로만 남음 (mDNS 죽었거나 다른 망에 갈 때만 호출).

## 한줄정리

신규 128GB SD에 Ubuntu 24.04.4 + cloud-init 자동 부팅 + SSH 키 인증 + ROS2 Jazzy 풀 스택(turtlebot3 메타 / cartographer / nav2 / ld08_driver / ros_tcp_endpoint) 한 세션에 완전 부트스트랩 + 사후 검증으로 학원 Wi-Fi 영구 연결 + Arduino/OpenCR/LDS-03 udev 3종 모두 PASS. `ssh urhynix-robot` 한 줄 진입(mDNS, 유선/무선 무관). 발표 직전 잔여는 SUPABASE_KEY 주입 + OpenCR/Arduino 재플래시 + 카메라 검증 + bringup `/scan` `/odom` 검증 + 가벽 보강 5건뿐.
