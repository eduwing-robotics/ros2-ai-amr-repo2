---
name: urhynix-dual-fullstack-unity
description: 두 로봇(젠지 tb3_2 + 티원 tb3_1)을 한 ROS_DOMAIN(210)에 동시에 올려 Unity ControlRoom에서 카메라(Pi+RealSense)·배터리·센서(LDR/PIR)·SLAM 맵을 모두 띄우고 로봇 전환까지 검증하는 듀얼 풀스택 드라이런. 젠지=SLAM/맵 담당(non-ns), 티원=비전 담당(ns tb3_1)으로 글로벌 토픽 충돌을 회피하고, 젠지 endpoint 하나가 크로스 디스커버리로 양쪽을 다 Unity에 중계. unityctl 0.4.0 대응. 2026-06-17 양 로봇 PASS.
when_to_use:
  - 듀얼 로봇을 동시에 Unity 디지털트윈에 띄워야 할 때 (시연/검증)
  - 한 로봇은 SLAM, 다른 로봇은 카메라/센서만 올릴 때 (글로벌 /scan,/map,/tf 충돌 진단)
  - 단일 로봇 풀스택은 되는데 "두 대 같이"가 안 될 때 (네임스페이스 격리/크로스 디스커버리)
  - unityctl 0.4.x로 Play/검증할 때 (0.2.x와 명령 체계 다름)
references:
  - .claude/skills/urhynix-fullstack-bringup/SKILL.md   # 단일 젠지 5트랙 (이 스킬의 모태)
  - .claude/skills/slam-nav2-arena-survey/SKILL.md       # cartographer + 맵 저장
  - .claude/skills/unity-live-map-twin/SKILL.md          # 맵뷰 + /tf 마커
  - .claude/skills/unity-unityctl-ops/SKILL.md           # unityctl 함정 (0.4.0 추가됨)
  - .claude/skills/robot-camera-bringup/SKILL.md         # 카메라 launch
  - scripts/_genji_core_up.sh                            # 젠지 bringup+ros_tcp
  - scripts/_genji_rest_up.sh                            # 젠지 slam+camera+relay+arduino
  - scripts/_t1_up.sh                                    # 티원 ns bringup+ros_tcp+realsense
---

# urhynix-dual-fullstack-unity

## 무엇 / 왜

젠지(tb3_2) + 티원(tb3_1) **두 대를 한 도메인(210)에 동시**에 올려 Unity ControlRoom에 카메라·배터리·센서·맵을 다 띄우고 로봇 탭 전환까지 검증한다. 단일 로봇은 `urhynix-fullstack-bringup`이 모태고, 이 스킬은 **두 대 같이** 돌릴 때만 나오는 충돌·격리·크로스 디스커버리·unityctl 0.4.0이 본체다.

### ★ 핵심 설계: 비대칭 네임스페이스 (한 대만 SLAM)

`/map`,`/scan`,`/tf`는 **네임스페이스 없는 글로벌 단일 토픽**이다. 두 대가 동시에 SLAM(cartographer)을 돌리면 `/scan`,`/map`이 충돌한다. → **SLAM 담당은 무조건 1대.**

| 로봇 | 역할 | bringup | 발행 토픽 |
|---|---|---|---|
| **젠지 tb3_2** | SLAM/맵 | **non-namespaced** | 글로벌 `/scan`,`/map`,`/tf`,`/battery_state`; relay→`/tb3_2/battery_state`; `/tb3_2/camera/...`; `/sensors/ldr`,`/sensors/pir` |
| **티원 tb3_1** | 비전 | **`namespace:=tb3_1`** | `/tb3_1/scan`,`/tb3_1/battery_state`,`/tb3_1/camera/color/...` (전부 격리 → 젠지 글로벌과 충돌 0) |

→ 티원은 SLAM을 안 하므로 `namespace:=tb3_1`로 `/scan`·`/battery`를 격리하면 젠지 글로벌 토픽과 안 부딪힌다.

### ★ 핵심 설계: endpoint 1개로 양쪽 중계 (크로스 디스커버리)

두 로봇이 같은 `ROS_DOMAIN_ID=210` + `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`이면 **서로의 토픽을 다 본다**. Unity는 `default_robots.json` `robots[0]`(=젠지 .87) endpoint 하나에 붙고, 젠지 endpoint가 티원 `/tb3_1/*`까지 중계한다. → **티원에도 ros_tcp_endpoint를 띄우지만 Unity는 젠지 것만 쓴다**(티원 endpoint는 예비/대칭용).
검증: 젠지에서 `ros2 topic list | grep tb3_1` 가 티원 토픽을 보이면 크로스 디스커버리 OK.

## USB 디바이스 (로봇마다 다름 — 배터리 죽음의 주범)

재부팅마다 ACM 번호가 스왑되므로 **벤더ID로 확인**: `udevadm info -q property -n /dev/ttyACMn | grep ID_VENDOR_ID` (2341=Arduino, 0483=OpenCR).

| 로봇 | 구성 | bringup usb_port | arduino |
|---|---|---|---|
| 젠지 | ACM0=Arduino(2341), ACM1=OpenCR(0483), USB0=라이다 | `usb_port:=/dev/ttyACM1` | ACM0 |
| 티원 | ACM0=OpenCR(0483) only, USB0=라이다, RealSense=USB3 | `usb_port:=/dev/ttyACM0` | 없음 |

## 함정표 (2026-06-17 양 로봇 PASS에서 도출)

| 증상 | 원인 | 해결 |
|---|---|---|
| 티원 `tmux: command not found` | 기체에 tmux 미설치(기체마다 다름) | **setsid+nohup**으로 띄움: `setsid nohup bash script > log 2>&1 </dev/null &`. (sudo 없이) |
| arduino_bridge가 `/dev/tb3_arduino` 못 찾음 + sudo 비번 없음 | `SERIAL_DEVICE`가 .py에 하드코딩(os.environ 아님), 심링크는 sudo 필요 | **원본 무수정**: `sed 's\|/dev/tb3_arduino\|/dev/ttyACM0\|' ~/arduino_bridge.py > /tmp/copy.py` 후 실행 [[feedback_no_modify_originals]] |
| arduino LDR/PIR이 tb3_1로 발행됨 | `URHYNIX_ROBOT_ID` 기본값 tb3_1 | 젠지는 `export URHYNIX_ROBOT_ID=tb3_2` |
| `camera_ros` pkg "없음" | env 미source (ros_tcp용 ws만 source됨) | `/opt/ros/jazzy`에 apt판 있음. camera 세션에서 별도 source |
| RealSense `no-realsense-usb` (lsusb에 8086 없음) | USB-C 케이블 빠짐/헐거움/USB2에 꽂힘 | **USB3 포트(파란색)에 재체결** — 물리 작업(사용자). 재확인 `lsusb\|grep 8086` |
| 젠지 bringup이 turtlebot3_node 죽임 | usb_port가 Arduino(ACM0)를 가리킴 | `usb_port:=/dev/ttyACM1`(OpenCR) — battery #26/#27 |
| `/scan` `ros2 topic hz` 빈 출력인데 정상 | hz 측정 윈도/grep 타이밍 artifact | `ros2 topic info /scan` Publisher count + `echo --once --field ranges`로 실데이터 확인 |
| Unity 초반 `No route to host` 후 정상 | codelab 무선 churn, ROS-TCP 자동 재연결 | 이후 인덱스에 `🟢 first /map frame` 뜨면 회복된 것. 링크 안정은 근접 배치 [[urhynix-wifi-codelab-status]] |
| 맵에 로봇 1대(젠지)만 표시 | cartographer `map→odom`이 젠지 것뿐 → 티원은 `map→tb3_1/odom` 링크 없음(SLAM 안 함) | 티원을 맵에 올리려면 **티원 AMCL(공유맵 localization)** 또는 **static tf** 필요. (향후 확장) |

## 기동 순서 (스크립트 방식 — 재부팅 시 /tmp 소실 대비 매번 재작성)

전제: 두 로봇 부팅 + codelab 망 + `ROS_DOMAIN_ID=210`. 노트북 LAN IP를 `ROS_STATIC_PEERS`로.

```bash
LAPTOP_IP=$(ifconfig | grep "inet 192.168.10" | awk '{print $2}' | head -1)
# 1) 젠지 코어 (bringup usb_port=ttyACM1 + ros_tcp)
scp scripts/_genji_core_up.sh kim@192.168.10.87:/tmp/ && ssh kim@192.168.10.87 "bash /tmp/_genji_core_up.sh $LAPTOP_IP"
# (verify: turtlebot3_node alive + /scan ranges 실데이터 + /battery_state voltage)
# 2) 젠지 나머지 (cartographer + Pi캠 + 배터리relay + arduino)
scp scripts/_genji_rest_up.sh kim@192.168.10.87:/tmp/ && ssh kim@192.168.10.87 "bash /tmp/_genji_rest_up.sh"
# 3) 티원 풀 (ns tb3_1 bringup + ros_tcp + RealSense) — tmux 없으니 setsid
scp scripts/_t1_up.sh t1@192.168.10.250:/tmp/ && ssh t1@192.168.10.250 "bash /tmp/_t1_up.sh $LAPTOP_IP"
```

스크립트 3종은 `scripts/_genji_core_up.sh`, `_genji_rest_up.sh`, `_t1_up.sh`. (헤더 주석에 역할/함정 명시)

## 검증 (로봇측 → Unity측)

```bash
# 로봇(젠지): 크로스 디스커버리 + 8 토픽 pub=1
ssh kim@192.168.10.87 'source /opt/ros/jazzy/setup.bash; source ~/turtlebot3_ws/install/setup.bash
  export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
  ros2 daemon stop; ros2 daemon start; sleep 3
  for t in /map /tb3_2/camera/image_raw/compressed /tb3_2/battery_state /sensors/ldr /sensors/pir \
           /tb3_1/scan /tb3_1/camera/color/image_raw/compressed /tb3_1/battery_state; do
    echo -n "$t : "; ros2 topic info $t | grep -oE "Publisher count: [0-9]+"; done'
# 카메라 실제 흐름: Subscription count(=Unity endpoint) ≥1 + bw 숫자
ros2 topic bw /tb3_2/camera/image_raw/compressed   # 젠지 Pi ~1.6MB/s
ros2 topic bw /tb3_1/camera/color/image_raw/compressed  # 티원 RS ~0.78MB/s
```

Unity측은 **unityctl 0.4.0** (아래) — Play 후 콘솔 `subscribed → ...` 9건 + `🟢 first /map frame` + `🟢 first pose`, 그다음 `SensorVerifyConsole.SwitchTo`/`Dump`로 배터리·센서·전환 확인. 영상/맵 렌더는 스크린샷 검정이라 **Unity 창 직접 확인**.

## unityctl 0.4.0 (0.2.x와 다름 — 2026-06-17 갱신)

자세한 함정은 [[unity-unityctl-ops]]. 요점:
- **버전**: `dotnet tool update --global unityctl unityctl-mcp` (0.2→0.4 메이저 점프).
- **프로젝트 pin**: `unityctl editor select --project <P>` 한 번. 단 `play start` 등 일부는 여전히 `--project` 명시 필요.
- **`check`는 콘솔 출력 버그(Spectre StyleParser)** → 항상 `--json`. (모든 명령 `--json` 권장.)
- **`exec --code`는 단일 구문만**: `Type.Member` / `Type.Member = value` / `Type.Method(a,b)`. `;`·`return`·복수문 불가 → SwitchTo와 Dump를 **분리 호출**.
- 검증 콤보: `unityctl exec --project <P> --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.SwitchTo("tb3_1")'` → `...Dump()`. Dump가 state(양 로봇 battery/pir) + UI 라벨 동시 출력. 전환 시 배터리 라벨이 해당 로봇 값으로 재바인딩되면 OK.

## 결론 (2026-06-17 양 로봇 PASS)

8 토픽 pub=1 + 크로스 디스커버리 OK. Unity: /map 50×49 + pose 수신, 젠지 Pi 1.63MB/s·티원 RS 776KB/s(Subscription=1), 배터리 젠지 77.6%/티원 86.2%, SwitchTo로 탭 전환 재바인딩 PASS. 미해결: 맵에 티원 미표시(map→tb3_1/odom 부재) → AMCL/static tf 후속.

## 한줄정리

SLAM은 한 대만(젠지 non-ns), 다른 대는 ns로 격리(티원 tb3_1), 같은 도메인210+SUBNET이면 젠지 endpoint 하나가 양쪽을 Unity에 중계. USB 벤더ID로 usb_port 정확히, 티원 tmux 없으면 setsid, arduino는 /tmp 복사+sed, unityctl 0.4.0은 check --json + editor select + exec 단일구문. 맵 다중로봇 표시는 티원 localization이 후속.
