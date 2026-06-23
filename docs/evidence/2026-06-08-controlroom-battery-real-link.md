# 듀얼 로봇 실 배터리 결선 PASS (2026-06-08) Phase 2.7

> Unity ControlRoom에서 `/tb3_1/battery_state` (티원 12.59V→99.5%) + `/tb3_2/battery_state` (젠지 11.73V→59.0%) 동시 라이브 표시. 우측 TelemetryPanelView 배터리 게이지 + % 텍스트 토글 시 즉시 갱신. 사용자 확인 "양쪽 다른 voltage 다른 % 표시 PASS".

## 환경

| 항목 | 값 |
|---|---|
| 호스트 (티원) | `t1@192.168.10.250` hostname `rb` |
| 호스트 (젠지) | `urhynix-robot` kim@192.168.10.87 |
| ROS | Jazzy + `ROS_DOMAIN_ID=230` 통일 |
| Unity Editor | 6000.3.16f1 (Unity 6.3 LTS) |
| ROS-TCP-Connector | v0.7.0 (`#if ROS2` 분기) |
| 프로젝트 | `unity/ControlRoom/` (Phase 2.7) |

## 검증 매트릭스

| 항목 | 결과 |
|---|---|
| 티원 publisher `/tb3_1/battery_state` | ✅ 활성 (hz 약 1~2 Hz) |
| 젠지 publisher `/tb3_2/battery_state` | ✅ 활성 (hz 약 1~2 Hz) |
| 젠지 ros_tcp_endpoint port 10000 forward | ✅ LISTEN + 양 토픽 모두 forward |
| Unity TopicRegistry.GetBatteryState("tb3_1") | ✅ T1BatteryState 상수 정의 |
| Unity TopicRegistry.GetBatteryState("tb3_2") | ✅ GenjiBatteryState 상수 정의 |
| Unity BatterySubscriber 인스턴스 x2 | ✅ Scene 박힘 (_T1 + _G) |
| voltage 선형 환산 (pct = (v-10.5)/2.1*100 clamped) | ✅ Ti원 12.59V→99.5%, 젠지 11.73V→59.0% |
| 끊김 감지 3중 (timeout 5초 / present=false / v<5V) | ✅ 구조 박힘 (재현 대기: 한쪽 전원 OFF) |
| TelemetryPanelView OnRobotChanged 구독 | ✅ 탭 전환 즉시 게이지 갱신 (0ms) |
| default_robots.json IP fallback | ✅ `user@host` 분리 후 IP 추출 (mDNS 실패 시 안전망) |

## 신규 함정 5건

### #19. TurtleBot3 OpenCR pub `BatteryState.percentage` 필드 무효값 (예: 117%)

**증상**: OpenCR firmware가 percentage 필드를 percentage(0~100)이 아닌 다른 값으로 채움.

**우회**: Voltage 선형 변환 사용.

**공식**: `pct = clamp((voltage - 10.5) / 2.1 * 100, 0, 100)`
- LiPo 3S nominal 11.1V, max 12.6V, min 10.5V
- 10.5V = 0%, 12.6V = 100%

### #20. TB3 본체 메인 전원 스위치 OFF — Dynamixel 응답 0 후 프로세스 죽음

**증상**: 본체 메인 스위치가 OFF 상태면 OpenCR은 USB 5V로 살아있지만 Dynamixel(XL430 같은 모터)에 전원이 안 가서 응답 0. ROS 노드에서 `[TxRxResult] There is no status packet` 반복 후 `process has died, exit code -6` 종료.

**우회**: 본체 메인 스위치 ON 확인 먼저.

### #21. 새 OS 사용자 `dialout` 그룹 미가입 → `/dev/ttyACM0` 권한 부족

**증상**: 새 Ubuntu 사용자는 기본적으로 dialout 그룹에 미가입 → `/dev/ttyACM0`가 `crw-rw----` (group=dialout)이므로 non-root 진입 불가 → turtlebot3_bringup 실행 시 `Failed to open port /dev/ttyACM0`.

**우회**: 
```bash
sudo usermod -aG dialout <user>    # 영구 (재로그인 필요)
sudo chmod 666 /dev/ttyACM0        # 즉시 우회 (재부팅 시 리셋)
```

### #22. 3대 컴퓨터에서 동시 ssh launch → ttyACM0 선점 경쟁

**증상**: 컴퓨터 A, B, C에서 모두 `ssh urhynix-robot 'ros2 launch turtlebot3_bringup robot.launch.py'` 실행 → ttyACM0는 1개뿐이라 선점 경쟁 + OpenCR USB baudrate handshake 반복 → publisher count 0이 깜빡임.

**우회**: 1대만 launch 실행. 나머지는 subscribe-only. Topic list 확인하고 필요한 데이터만 pull.

### #23. DHCP Wi-Fi 변경 (`192.168.0.x` → `192.168.10.x`) 시 SSOT IP drift + mDNS 캐시

**증상**: 학원 Wi-Fi IP 대역이 변경되면 robot DHCP IP가 `.82` → `.87`로 바뀜. SSOT `default_robots.json`은 여전히 구형 IP. mDNS `urhynix-robot.local` 일시 캐시 미갱신.

**우회**: 
```bash
default_robots.json IP 갱신 (수동)
dscacheutil -flushcache        # macOS: mDNS 캐시 재로드
arp -a | grep urhynix          # 또는 MAC sweep으로 IP 추적
```

## 산출물

| 파일 | 기능 |
|---|---|
| `TopicRegistry.cs` | T1BatteryState, GenjiBatteryState 상수 + `GetBatteryState(robotId)` |
| `BatterySubscriber.cs` | Voltage 환산 + 끊김 감지 구현 (119줄) |
| `ControlRoomApp.cs` | IP fallback pattern (`default_robots.json` → hostAddress 분리 → IP 추출) |
| `TelemetryPanelView.cs` | `OnRobotChanged` 이벤트 구독 + 탭 전환 즉시 게이지 갱신 |
| `default_robots.json` | IP 갱신 (192.168.0.250 → 192.168.10.250) |

## Scene 영구 박힘

```
Hierarchy:
  BatterySubscriber_T1
    - BatterySubscriber (robotId="tb3_1", displayLabel="티원")
  BatterySubscriber_G
    - BatterySubscriber (robotId="tb3_2", displayLabel="젠지")
  ROSConnection
    - m_RosIPAddress: 192.168.10.250
    - m_RosPort: 10000
```

## 로봇 워크스페이스

### 티원 (rb / 192.168.10.250)

```bash
cd ~/turtlebot3_ws/src
git clone https://github.com/Unity-Technologies/ROS-TCP-Endpoint -b main-ros2
cd ~/turtlebot3_ws
colcon build
```

### 젠지 (kim-desktop / 192.168.10.87)

```bash
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-msgs colcon
cd ~
git clone https://github.com/ROBOTIS-GIT/turtlebot3.git
git clone https://github.com/Unity-Technologies/ROS-TCP-Endpoint -b main-ros2
git clone https://github.com/cansik/coin-d4-driver.git

cd ~/turtlebot3_ws
colcon build

echo 'export TURTLEBOT3_MODEL=burger' >> ~/.bashrc
echo 'export LDS_MODEL=LDS-03' >> ~/.bashrc
echo 'export OPENCR_PORT=/dev/ttyACM0' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=230' >> ~/.bashrc
source ~/.bashrc
```

## Voltage 환산 공식

```csharp
// LiPo 3S: 10.5V (0%) ~ 12.6V (100%)
float CalculatePercentage(float voltage)
{
    const float minVoltage = 10.5f;
    const float maxVoltage = 12.6f;
    float percentage = (voltage - minVoltage) / (maxVoltage - minVoltage) * 100f;
    return Mathf.Clamp01(percentage / 100f) * 100f;
}
```

예시:
- 12.59V → (12.59 - 10.5) / 2.1 * 100 = 99.5%
- 11.73V → (11.73 - 10.5) / 2.1 * 100 = 59.0%

## 끊김 감지 3중

1. **Timeout 5초**: ROS topic 마지막 수신 시점 이후 5초 경과 시 `⚠️ 배터리 토픽 끊김` 로그
2. **present=false**: BatteryState.present 필드가 false 로 바뀌면 즉시 감지
3. **Voltage < 5V**: Voltage가 5V 이하이면 배터리 부재 판단

회복 로그: 다시 수신되면 `배터리 토픽 복구` 출력.

## 다음 진입 후보

- **(a) 센서 카드 확장**: `SensorCardListView`에 `OnRobotChanged` 구독 추가 → `/scan` 같은 ROS 토픽 구독
- **(b) 카메라 namespace 정리**: 현 젠지 `/camera/*` → SSOT 약속 `/tb3_2/camera/*` 일관성 정리
- **(c) 끊김 감지 시연**: 한쪽 본체 전원 OFF → 5초 후 `⚠️` 로그 박힘 시각 확인
- **(d) Arduino 센서 토픽화**: 가스/소음/조도 센서를 ROS 토픽으로 발행

## 한줄정리

TurtleBot3 OpenCR firmware percentage 필드 무효값 문제(117% 등)를 voltage 선형 변환(`(v-10.5)/2.1*100`)으로 우회. 단일 ros_tcp_endpoint + SSOT IP fallback 패턴 + 3대 launch 금지 원칙으로 듀얼 배터리 실 결선 완료. 신규 함정 5건(#19~#23) 영구 자산화.
