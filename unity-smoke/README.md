# unity-smoke — URHYNIX TurtleBot Unity Smoke

ROS-TCP-Connector 기반 라이브 모니터. `/scan`·`/odom`·`/battery_state`(터틀봇)
+ `/sensors/pir`·`/sensors/ldr`(아두이노 브리지) 5개 토픽을 구독해서 화면 가운데에 한글로 표시한다.

| 항목 | 값 |
|---|---|
| Unity Editor | `6000.0.64f1` |
| ROS-TCP-Connector | git URL `?path=/com.unity.robotics.ros-tcp-connector#v0.7.0` |
| Scripting define | `ROS2` (`Assets/csc.rsp`) |
| Default robot IP | `192.168.0.138` (`RosSmokeDashboard.rosIP` 인스펙터에서 변경) |
| Default port | `10000` |

## 처음 한 번 (Mac / Ubuntu 동일)

> **전제**: 이 머신이 로봇과 같은 LAN(`192.168.0.0/24`)에 있어야 한다. WSL2는 기본 NAT라 로봇 탐색 실패 — mirrored networking 또는 native Ubuntu 권장.

```bash
# 0) OS별 의존성
#    Ubuntu:
sudo apt update && sudo apt install -y expect openssh-client netcat-openbsd jq curl git
#    macOS (Homebrew):
brew install expect jq

# 1) URHYNIX repo clone
git clone https://github.com/URHYNIX/URHYNIX.git ~/URHYNIX

# 2) tb3 helpers source
echo 'source ~/URHYNIX/scripts/tb3.sh' >> ~/.zshrc    # macOS
# 또는
echo 'source ~/URHYNIX/scripts/tb3.sh' >> ~/.bashrc   # Ubuntu

# 3) 비밀번호/토큰 외부 분리
cat > ~/.tb3rc <<'EOF'
export TB3_PASSWORD='1234'
export TB3_VNC_PASSWORD='123456'
export SUPABASE_ACCESS_TOKEN='<your-token>'
EOF
chmod 600 ~/.tb3rc

# 4) 새 셸 열고 SSH 공개키 등록 (★ 한 번만, 이후 비번 prompt 영구 사라짐)
source ~/.zshrc   # or ~/.bashrc
tb3-key-setup     # ssh-copy-id 한 방 + 검증

# 5) Unity Hub 설치 + Editor 6000.0.64f1 설치
#    macOS:  https://unity.com/download → UnityHubSetup.dmg 설치
#    Ubuntu: https://unity.com/download → UnityHub.AppImage 다운로드 후
#            chmod +x UnityHub.AppImage && ./UnityHub.AppImage
#    Hub > Installs > 6000.0.64f1 (Universal Render Pipeline 템플릿 호환)

# 6) Unity Hub > Open > URHYNIX/unity-smoke 폴더 선택
#    첫 실행 시 Library/ 자동 재생성 (~5-10분)
```

## 매 세션 실행

```bash
tb3-go            # ★ up + wait + bridge + verify 한 줄
tb3-unity         # Unity Editor 실행 (자동 Play)
sb-tail           # events 총 수 + 최근 5건 (PIR 손 흔든 뒤 확인)
```

세부 명령 (필요 시):

```bash
tb3-myip          # 내 LAN IP (DHCP)
tb3-ip            # 로봇 IP (MAC 기반)
tb3-restart       # down + go (깨끗한 재기동)
tb3-logs          # bringup / ros_tcp / arduino_bridge 로그 한 화면
```

화면 가운데 패널에 **● 전체 LIVE** (녹) / **◐ 부분 LIVE** (노) / **○ 연결 대기** (주황) 표시.

세션 종료:

```bash
tb3-down          # 로봇 ROS tmux 모두 정리
tb3-poweroff      # 라즈베리파이 셧다운 (LiDAR는 메인 스위치 직접 OFF 필요)
```

## 표시되는 토픽

| 토픽 | 타입 | 출처 | UI 라벨 |
|---|---|---|---|
| `/scan` | `sensor_msgs/LaserScan` | TurtleBot bringup | 레이저 |
| `/odom` | `nav_msgs/Odometry` | TurtleBot bringup | 오도메트리 |
| `/battery_state` | `sensor_msgs/BatteryState` | TurtleBot bringup | 배터리 |
| `/sensors/pir` | `std_msgs/Bool` | `arduino_bridge.py` | 인체감지 |
| `/sensors/ldr` | `std_msgs/Int32` | `arduino_bridge.py` | 조도 (A0 0–1023) |

## 트러블슈팅

- **Play 후 화면이 비어있다** → 게임 뷰가 닫혀있을 수 있음. `Window > General > Game`.
- **한글이 □□로 보인다** → OS에 한글 폰트가 없음. macOS 기본 + Ubuntu `fonts-noto-cjk` 설치로 해결.
- **`ROS-TCP 끊김`** → `tb3-up`이 실패했거나 같은 LAN이 아님. `tb3-port`로 10000 확인.
- **`/sensors/*` 토픽이 안 잡힘** → `tb3-bridge` 미실행. 로봇 `tmux ls`에 `arduino_bridge` 세션이 있어야 함.
- **로봇이 안 잡힘** → `tb3-myip` 후 결과를 `tb3.sh` 위쪽 `TB3_LAN_CIDR` 또는 `TB3_ROBOT_IP_HINT`와 맞춰 보기.

## 다음 단계

- DB 선정 후 `arduino_bridge.py`에 events 테이블 insert 경로 추가 (DECISION-LOG 2026-05-28 "DB 선정 보류" 참조)
- `/security/events` 토픽 신설 시 Unity Dashboard에 신규 행 추가
