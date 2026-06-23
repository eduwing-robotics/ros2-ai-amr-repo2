---
name: urhynix-fullstack-bringup
description: 단일 로봇(젠지)에 5트랙(배터리·파이카메라·라이다맵·LDR·PIR)을 동시에 살리고 Unity ControlRoom에서 한 번에 검증하는 SLAM 디지털트윈 풀 드라이런. SLAM(/map)과 공존하려 non-namespaced bringup + 배터리 relay를 쓰는 결정이 핵심. 2026-06-16 젠지 검증.
when_to_use:
  - 디지털트윈 시연 dry-run — 배터리/카메라/맵/센서가 Unity에 동시에 떠야 할 때
  - SLAM(/map) + 센서/배터리/카메라를 한 로봇에서 같이 돌릴 때
  - 개별 트랙은 되는데 "다 같이" 안 될 때 (네임스페이스/USB/relay 충돌 진단)
references:
  - .claude/skills/robot-camera-bringup/SKILL.md      # 카메라 launch (libcamera LD_LIBRARY_PATH)
  - .claude/skills/urhynix-sensor-bringup/SKILL.md     # arduino LDR/PIR (edge-trigger)
  - .claude/skills/urhynix-battery-bringup/SKILL.md    # 배터리 + ttyACM 스왑 함정 #26/#27
  - .claude/skills/slam-nav2-arena-survey/SKILL.md     # cartographer
  - .claude/skills/urhynix-sensor-verify-console/SKILL.md  # Dump 검증
  - .claude/skills/unity-live-map-twin/SKILL.md        # 맵뷰
  - .claude/skills/unity-unityctl-ops/SKILL.md         # Play/검증 함정
---

# urhynix-fullstack-bringup

## 무엇 / 왜

젠지 한 대에 **배터리·파이카메라·라이다맵·LDR·PIR 5트랙을 동시**에 올려 Unity ControlRoom에 다 띄운다. 개별 트랙 스킬은 따로 있으나, **다 같이** 돌릴 때만 나오는 충돌·순서·검증이 이 스킬의 본체다.

### ★ 핵심 설계 결정: non-namespaced bringup + 배터리 relay

`urhynix-battery-bringup`은 `namespace:=tb3_2`로 띄워 배터리를 `/tb3_2/battery_state`로 바로 받는다. **그러나 SLAM과 공존 불가** — 네임스페이스를 주면 `/scan`이 `/tb3_2/scan`이 되어 cartographer(전역 `/scan`→`/map` 기대)가 깨진다.
→ **SLAM 포함 풀스택은 non-namespaced bringup**(전역 `/scan`,`/map`,`/battery_state`)으로 가고, 배터리만 **relay**로 `/battery_state`→`/tb3_2/battery_state` 변환(Unity가 네임스페이스 기대). 카메라/센서는 노드 자체가 `/tb3_2/*`,`/sensors/*`로 발행.

| 트랙 | 발행 토픽 | 소스 |
|---|---|---|
| 라이다/맵 | `/map`, `/scan` | turtlebot3 bringup(lidar) + cartographer |
| 배터리 | `/battery_state` → **relay** → `/tb3_2/battery_state` | turtlebot3_node(OpenCR) + 파이썬 relay |
| 카메라 | `/tb3_2/camera/image_raw/compressed` | camera_ros (ns tb3_2) |
| LDR/PIR | `/sensors/ldr`, `/sensors/pir` | arduino_bridge.py |

## USB 디바이스 2개 주의 (배터리 죽음의 주범)

젠지엔 ttyACM 2개: **Arduino(`ID_VENDOR_ID=2341`)** + **OpenCR(`ID_VENDOR_ID=0483`, ROBOTIS)**. 재부팅마다 ACM 번호 스왑됨.
- turtlebot3 bringup → OpenCR ACM에 `usb_port:=` (틀리면 `Failed connection with Devices` → turtlebot3_node 죽음 → 배터리/odom 없음). 함정 = `urhynix-battery-bringup` #26/#27.
- arduino_bridge → Arduino ACM에 `/dev/tb3_arduino` 심링크.
- 확인: `udevadm info -q property -n /dev/ttyACMn | grep ID_VENDOR_ID` (2341=Arduino, 0483=OpenCR).

## 기동 순서 (스크립트 파일 방식 — 따옴표 지옥·재부팅 /tmp 소실 대비)

전제: `scripts/tb3.sh` 로드, `ROS_DOMAIN_ID=210`, codelab 망. **재부팅 시 `/tmp/*.sh` 날아감 → 매번 재작성.**

1. **bringup + ros_tcp**: `tb3-up` (urhynix_robot_up.sh, non-namespaced). turtlebot3_node가 죽으면(노드목록에 없음) → bringup을 `usb_port:=/dev/ttyACM<OpenCR>`로 재기동.
2. **SLAM**: apt판 cartographer (ws 오버레이의 `cartographer.launch.py`가 깨진 심볼릭이면 `/opt/ros/jazzy`만 source). `slam-nav2-arena-survey` 참고.
3. **카메라**: camera_ros, ns tb3_2, `LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu` + `LIBCAMERA_IPA_MODULE_PATH` (스크립트 파일로 — `$LD_LIBRARY_PATH`가 중첩 따옴표에서 빈값되면 `librcl_action.so 못찾음`). 640×480 권장(대역↓). `robot-camera-bringup` 참고.
4. **arduino**: `/dev/tb3_arduino`→Arduino ACM 심링크(sudo) + `python3 ~/arduino_bridge.py` (URHYNIX_ROBOT_ID=tb3_2). `urhynix-sensor-bringup` 참고.
5. **배터리 relay**: `/battery_state`→`/tb3_2/battery_state` 파이썬 relay (BatteryState 구독→재발행).

각 노드는 tmux 세션(bringup/ros_tcp/slam/camera/arduino/batrelay)으로. 모든 export에 `ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`.

배터리 relay 노드(검증된 최소형):
```python
import rclpy; from rclpy.node import Node
from sensor_msgs.msg import BatteryState
rclpy.init(); n=Node('battery_relay_tb3_2')
p=n.create_publisher(BatteryState,'/tb3_2/battery_state',10)
n.create_subscription(BatteryState,'/battery_state',lambda m:p.publish(m),10)
rclpy.spin(n)
```

## 검증 (로봇측 → Unity측)

```bash
# 로봇: 5트랙 발행자(pub=1) + 배터리 voltage
for t in /map /tb3_2/camera/image_raw/compressed /battery_state /tb3_2/battery_state /sensors/ldr /sensors/pir; do
  ros2 topic info $t | grep "Publisher count"; done
# Unity: 한 방 Dump (urhynix-sensor-verify-console)
unityctl exec --project <P> --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.SwitchTo("tb3_2")'
unityctl exec --project <P> --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()'
# 기대 state tb3_2: battery=NN light=NN pir=N + 라벨 'NN %','NN%·보통','감지!'
# 맵/카메라: Editor.log 'first /map frame' + endpoint RegisterSubscriber(/tb3_2/camera) OK (영상은 Unity 창 직접)
```

## 함정표 (2026-06-16)

| 증상 | 원인 | 해결 |
|---|---|---|
| 배터리만 안 뜸, turtlebot3_node 노드 없음 | 재부팅 USB 스왑 → bringup이 OpenCR을 Arduino ACM에서 찾음 | bringup `usb_port:=/dev/ttyACM<OpenCR>` (battery #26/#27) |
| 배터리 토픽 pub=1인데 데이터 없음 | `/battery_state` 소스(turtlebot3_node) 죽음 | 위 usb_port 고치면 relay가 자동 정상 |
| LDR/PIR pub=1인데 echo 비어있음 | **edge-trigger** (변화 시에만 발행) = 정상 | 손/빛으로 유도 또는 `ros2 topic pub` 강제 (sensor-bringup #1/#2) |
| 카메라 노드 즉사 `librcl_action.so` | 중첩 따옴표에서 `$LD_LIBRARY_PATH`가 빈값 → ROS lib 경로 소실 | **스크립트 파일**로 작성해 런타임 확장 |
| Unity가 volatile 토픽(배터리·센서·카메라) 유실, 맵만 뜸 | wifi churn(Broken pipe) + `/map`만 TRANSIENT_LOCAL(latched) | 링크 안정화(직결/근접) 또는 **fresh boot로 endpoint/연결 리셋** |
| ros_tcp endpoint 죽음 `InvalidHandle: destruction was requested` | 구독 churn/재연결 스트레스 | **ros_tcp 세션만 재기동**(bringup/slam 안 끊고): `tmux new -d -s ros_tcp 'bash /tmp/_tb3_ros_tcp.sh ...'` |
| 재부팅 후 `/tmp/*.sh` 다 없음 | tmpfs 초기화 | 기동 스크립트 5종 매번 재작성(이 스킬 순서대로) |
| 재부팅 후 wifi 재association 지연/실패 | codelab 불안정 | 1~2분 대기 + arp sweep, 안 되면 직결 [[urhynix-team-wifi-isolation-direct-link]] |

## 결론 (2026-06-16 젠지)

5트랙 동시 Unity 표시 PASS — battery 36.7% / light 51%·보통 / PIR 감지! / map 101×80 라이브+마커 / camera 30Hz. 결정타: **usb_port=ttyACM1(OpenCR)** + **non-ns bringup + 배터리 relay** + **fresh boot로 연결 안정화**. 영상 캡처는 UI Toolkit이라 불가 → Unity 창 직접 확인([[unity-unityctl-ops]]).

## 한줄정리

SLAM과 공존하려면 non-namespaced bringup(+배터리 relay)으로 5트랙을 띄우고, USB 2개(Arduino 2341 / OpenCR 0483) 포트만 정확히 잡으면(usb_port·심링크) 배터리·카메라·맵·LDR·PIR이 Unity에 동시에 뜬다. 검증은 SensorVerifyConsole.Dump 한 방.
