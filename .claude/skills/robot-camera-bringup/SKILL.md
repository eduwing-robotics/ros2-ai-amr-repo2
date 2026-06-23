---
name: robot-camera-bringup
description: URHYNIX 박물관 시연용 카메라 노드 + ros_tcp_endpoint 백그라운드 launch + 토픽 hz 검증 표준 패턴. 젠지(Pi Camera v2 IMX219, camera_ros) + 티원(RealSense D435, realsense2_camera) + ROS-TCP-Endpoint 한 묶음. macOS Bash + ssh + sudo + LD_LIBRARY_PATH 우회 + nohup + disown + setsid 표준화. — 매 세션 첫 5분에 카메라 트랙 살리는 데 반복 사용.
---

# robot-camera-bringup

## 언제 쓰나

- 매 세션 첫 5분 — 두 로봇 카메라 트랙(camera_ros + realsense2_camera + ros_tcp_endpoint)을 한 번에 살릴 때
- 박물관 시연 dry-run 직전
- robot 재부팅 후 토픽 발행 노드들이 다 꺼졌을 때
- ROS_DOMAIN_ID 통일 검증 후 cross-visibility 확인

## 사용 호스트

| 별명 | hostname | 카메라 | 토픽 namespace | 포트 |
|---|---|---|---|---|
| 젠지 | `urhynix-robot` (kim@192.168.0.82) | Pi Camera v2 IMX219 | `/tb3_2/camera/*` | 10000 (TCP endpoint) |
| 티원 | `t1@192.168.0.250` (hostname `rb`) | RealSense D435 | `/tb3_1/camera/*` | (티원 측 endpoint) |

ROS_DOMAIN_ID=230 양쪽 동일.

## 표준 launch — 젠지 (Pi Camera)

### A. camera_ros (Pi Camera) launch — **LD_LIBRARY_PATH 우회 필수**

apt의 camera_ros는 시스템 libcamera(v0.7.0)으로 컴파일됐는데 우리 빌드한 Pi fork libcamera(v0.7.1)와 ABI 충돌(`FATAL Serializer: ControlInfoMap required`). 우리 Pi fork를 강제 로드해서 우회:

```bash
ssh -o ControlMaster=no urhynix-robot '
  source /opt/ros/jazzy/setup.bash &&
  source ~/turtlebot3_ws/install/setup.bash 2>/dev/null
  export ROS_DOMAIN_ID=230
  export LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
  export LIBCAMERA_IPA_MODULE_PATH=/usr/local/lib/aarch64-linux-gnu/libcamera
  nohup ros2 run camera_ros camera_node \
    --ros-args -r __ns:=/tb3_2 -p width:=1280 -p height:=720 \
    > ~/camera_node.log 2>&1 < /dev/null & disown
'
```

검증 (별도 ssh):
```bash
ssh urhynix-robot 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && timeout 7 ros2 topic hz /tb3_2/camera/image_raw'
# 기대: ~30 Hz
```

발행되는 토픽:
- `/tb3_2/camera/camera_info`
- `/tb3_2/camera/image_raw`
- `/tb3_2/camera/image_raw/compressed` ← Unity가 subscribe 대상

### B. ros_tcp_endpoint (Unity 다리)

```bash
ssh -o ControlMaster=no urhynix-robot '
  source /opt/ros/jazzy/setup.bash &&
  source ~/turtlebot3_ws/install/setup.bash 2>/dev/null
  export ROS_DOMAIN_ID=230
  nohup ros2 run ros_tcp_endpoint default_server_endpoint \
    --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000 \
    > ~/ros_tcp.log 2>&1 < /dev/null & disown
'
```

검증:
```bash
ssh urhynix-robot 'ss -tln | grep 10000'
# 기대: LISTEN 0      10           0.0.0.0:10000
```

## 표준 launch — 티원 (RealSense D435)

```bash
ssh t1@192.168.0.250 '
  source /opt/ros/jazzy/setup.bash
  export ROS_DOMAIN_ID=230
  nohup ros2 launch realsense2_camera rs_launch.py \
    align_depth.enable:=true pointcloud.enable:=true \
    camera_namespace:=tb3_1 \
    > ~/rs_camera.log 2>&1 < /dev/null & disown
'
```

검증:
```bash
ssh t1@192.168.0.250 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && ros2 topic list | grep tb3_1'
# 기대 토픽:
#   /tb3_1/camera/camera/color/image_raw
#   /tb3_1/camera/camera/depth/image_rect_raw
#   /tb3_1/camera/camera/aligned_depth_to_color/image_raw
```

권한 함정 (티원 첫 셋업 시 1회): `sudo usermod -aG video,plugdev t1` (이후 sudo 없이 enumerate 가능).

## 함정 + 우회 표

| 함정 | 증상 | 우회 |
|---|---|---|
| ABI 충돌 (camera_ros vs Pi fork libcamera) | `FATAL Serializer ControlInfoMap required` | `LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu` + `LIBCAMERA_IPA_MODULE_PATH=/usr/local/lib/aarch64-linux-gnu/libcamera` |
| ssh 비-인터랙티브 ROS env 누락 | `ros2: command not found`, `ROS_DOMAIN_ID=` 빈값 | `source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash` 명시 |
| ssh ControlMaster connection 끊김 (255) | `Exit code 255` | `ssh -o ControlMaster=no` 강제 새 연결 |
| nohup 백그라운드 ssh 종료 시 죽음 | 노드 즉시 사라짐 | `nohup ... > log 2>&1 < /dev/null & disown` 패턴 |
| sudo 비번 stdin 필요 (apt install 등) | `[sudo] password for kim:` 멈춤 | `. ~/.tb3rc && printf '%s\n' "$TB3_PASSWORD" \| ssh urhynix-robot 'sudo -S apt ...'` |
| ROS_DOMAIN_ID drift (양쪽 다름) | `ros2 topic list`에 상대 토픽 안 보임 | `~/.bashrc`에서 `export ROS_DOMAIN_ID=230` 통일 |
| ros_tcp_endpoint launch 파일 이름 | `default_server_endpoint.launch.py was not found` | `ros2 run ros_tcp_endpoint default_server_endpoint` 직접 run (launch 아님) |
| `realsense2_camera` 권한 | `/dev/video* Permission denied` (non-root) | `sudo usermod -aG video,plugdev <user>` 후 재로그인 |
| `pkill -f realsense`가 ssh 자기 자신 죽임 | ssh exit 255 + 명령 누락 | `kill <PID>` 직접 또는 `pgrep -af "ros2 launch r"` 정확한 패턴으로 |
| `camera_namespace:=tb3_1`가 만드는 토픽 구조 — `/tb3_1/camera/color/...` (camera 한 번, 중복 아님) | Unity가 `/tb3_1/camera/camera/...` subscribe하면 publisher 0 | `ros2 topic list \| grep tb3_1`로 실제 발행되는 정확한 이름 확인 후 Unity topic 매칭 |
| `realsense2_camera`에 `compressed` plugin 자동 안 들어옴 | `/...image_raw/compressed` 토픽 발행 안 됨 (raw만) | `sudo apt install -y ros-jazzy-compressed-image-transport` 별도. 설치 후 realsense2_camera 재시작 |
| 티원 측 ssh 비번이 젠지와 다름 → 우리 자동화 불가 | `Permission denied (publickey,password)` | 1회 `ssh-copy-id -o StrictHostKeyChecking=accept-new t1@192.168.0.250` (비번 1회) → 영구 자동 |
| Pi Camera 1280×720@30Hz로 Unity 지연 1~2초 | Wi-Fi/buffer 누적 백로그 | camera_node 해상도 **640×480@30Hz** (frame 크기 1/4) → 지연 0.1~0.3초 실시간 |
| `urhynix-robot` IP 변경 (reboot 후 .82 → .150) | ssh urhynix-robot은 OK지만 .82 IP는 ping 안 됨 | mDNS `urhynix-robot.local` 사용 (자동 follow) + Unity rosIP도 mDNS 박아둠 |
| **13. Ubuntu 24.04 `KillUserProcesses=yes`로 nohup+disown까지 ssh 끊김 시 죽음** (2026-06-04 발견) | 백그라운드 ROS 노드 즉시 사라짐, `pgrep camera_node` 0건 | **1회 영구**: `sudo loginctl enable-linger kim` → `Linger=yes` 확인. 이후 tmux 세션 + 자식 프로세스 살아남 |
| **14. Unity 6.3 + ROS-TCP-Connector v0.7.x syscommand JSON `[:-1]` 호환 안 됨** (2026-06-04 발견) | robot `json.JSONDecodeError: Expecting ',' delimiter: line 1 column 91`. Unity socket shut down 반복 | **server.py:125 패치**: `data.decode("utf-8")[:-1]` → `data.decode("utf-8").rstrip("\x00").strip()`. src/ + build/ 둘 다 박고 colcon build 권장 |
| **15. macOS `setsid+nohup` Unity 시동이 LaunchServices attach 실패로 빨리 죽음** (2026-06-04 발견) | Unity 프로세스 28~41줄 log에서 즉시 종료. `ps -ef` 0건 | **`open -a` 사용**: `open -a "/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app" --args -projectPath ... -logFile ...` + `sleep 5` + `osascript -e 'tell application "Unity" to activate'` |
| **16. ★ Unity는 기본 ROS1 모드. ROS2 endpoint와 binary format 비대칭으로 OverflowException** (2026-06-04 발견) | RegisterSubscriber는 OK지만 frame deserialize 시 `OverflowException` + `ArgumentException: Offset and length were out of bounds`. Unity Console: `Incompatible protocol: ROS-TCP-Endpoint is using ROS2, but Unity is in ROS1 mode` | **GUI**: `Edit → Project Settings → Player → Other Settings → Scripting Define Symbols → "ROS2" 추가`. **직접 편집** (Editor 죽음 시 비상): `ProjectSettings.asset`의 `scriptingDefineSymbols:` 아래 `Standalone: ROS2` 박기. **신 Unity 프로젝트 첫 진입 시 무조건 첫 액션** |
| **17. Write/외부 에디터로 만든 신규 `.cs`는 `.meta` 미생성 → 어셈블리 누락** (2026-06-05 발견) | 같은 namespace의 다른 파일에서 `error CS0103: The name '<Class>' does not exist in the current context`. `Library/ScriptAssemblies/*.dll` mtime이 갱신 안 됨 | **unityctl**: `unityctl asset import --project <proj> --path Assets/Scripts/.../<file>.cs --json` → `.meta` 생성 + Asset Pipeline 등록 한 번에. **GUI**: Project 창 우클릭 → Refresh (`Cmd+R`). 자세히: `docs/evidence/2026-06-05-controlroom-dual-camera-toggle.md` 함정 #17 |
| **18. Play 모드 중에는 도메인 리로드 차단 → 새 코드 미적용** (2026-06-05 발견) | `unityctl asset refresh` + `RequestScriptCompilation` 호출해도 `Library/ScriptAssemblies/Assembly-CSharp*.dll` mtime 옛값 유지. `unityctl exec`로 메서드 호출 시 옛 코드 실행 | **5단계 표준**: `unityctl play stop` → settled 대기(`unityctl status` `Ready`) → `unityctl exec --code 'UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation()'` → assembly mtime 갱신 확인 → `unityctl exec --code '<Method>()'` → `unityctl play start`. 자세히: `docs/evidence/2026-06-05-controlroom-dual-camera-toggle.md` 함정 #18 |
| **19. `nohup ... & disown` heredoc 안에서 detach 실패** (2026-06-10 발견) | `ssh t1@... 'bash -lc " ... nohup ros2 launch ... > ~/x.log 2>&1 < /dev/null & disown "'` 형태로 띄우면 SSH session 종료 시 launch도 같이 죽음. **로그 파일조차 생성 안 됨**. nohup이 SIGHUP 차단해도 SSH가 child process group을 닫는 케이스 | **`ssh -fn` 패턴으로 교체** (아래 §C 참고). ssh가 본명령 start 직후 자체 detach + stdin=/dev/null. 본 세션에서 realsense+foxglove+bringup 3개 다 ssh -fn로 깔끔히 detach 성공 |

## §C — ssh -fn 표준 detach 패턴 (2026-06-10 추가)

기존 `nohup ... & disown` 패턴이 SSH session 종료 시 child 같이 죽는 케이스(함정 #19) 회피. **3종 동시 launch에서 검증됨**: realsense2_camera + foxglove_bridge + turtlebot3_bringup.

```bash
# 패턴: ssh -fn <host> "bash -c 'source ... && exec <ros2 cmd>' > /tmp/x.log 2>&1"
#  -f: 본명령 start 직후 ssh 자체 background
#  -n: stdin /dev/null (background 모드 필수)
#  exec: bash 한 단계 줄여 PID 단순화

# RealSense D435 (티원)
ssh -fn t1@<T1_IP> "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && exec ros2 launch realsense2_camera rs_launch.py enable_color:=true enable_depth:=true rgb_camera.color_profile:=640,480,30 depth_module.depth_profile:=640,480,30' > /tmp/local-rs.log 2>&1"

# foxglove_bridge (Mac/Unity 시각화 다리, port 8765)
ssh -fn t1@<T1_IP> "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && exec ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 -p address:=0.0.0.0' > /tmp/local-fx.log 2>&1"

# turtlebot3_bringup (namespace=tb3_1)
ssh -fn t1@<T1_IP> "bash -c 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=230 && export TURTLEBOT3_MODEL=burger && export LDS_MODEL=LDS-03 && export OPENCR_PORT=/dev/ttyACM0 && exec ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1' > /tmp/tb3_bringup.log 2>&1"
```

각 ssh 명령 즉시 exit 0 반환 후 백그라운드에서 살아 있음. 검증: `ssh t1@... 'pgrep -af "realsense|foxglove|turtlebot3"'`

## §D — foxglove_bridge 통합 (2026-06-10 추가)

ROS-TCP-Endpoint(Unity용)에 더해서 **WebSocket 기반 Foxglove Studio 다리** 동시 운용 가능. 서로 다른 포트라 충돌 없음.

| 다리 | 포트 | 클라이언트 | 용도 |
|---|---|---|---|
| `ros_tcp_endpoint` | 10000 | Unity ControlRoom | 박물관 시연 본선 |
| `foxglove_bridge` | 8765 | Foxglove Studio (.dmg) | 카메라 끊김 진단, 디버그 화면 |

설치:
```bash
ssh t1@<T1_IP> 'echo "<sudo_pw>" | sudo -S apt-get install -y ros-jazzy-foxglove-bridge'
```

Mac:
```bash
brew install --cask foxglove-studio
open -a Foxglove
# 앱에서 File → Open connection → Foxglove WebSocket → ws://<T1_IP>:8765
```

## §E — compressed 우선 정책 (2026-06-10 추가)

Wi-Fi 65 Mbps 환경에서 RealSense color 640x480@30 raw = 14.24 MB/s = 114 Mbps → **무조건 끊김**. 항상 `/camera/.../image_raw/compressed` (2.17 MB/s) 토픽을 외부 다리에 노출.

| 토픽 | 외부 노출 | 비고 |
|---|---|---|
| `/camera/camera/color/image_raw` | ❌ (라즈베리 내부만) | image_transport zero-copy |
| `/camera/camera/color/image_raw/compressed` | ✅ Foxglove/Unity/Mac | JPEG, 30Hz 유지 |
| `/camera/camera/depth/image_rect_raw` | depth 필요 시만 | 압축 손실 큼, 저해상도/저FPS 권장 |

자세한 진단 절차는 `robot-camera-stream-diag` 스킬 참고.

## §F — cross-host STATIC_PEERS 우회 (2026-06-15, 와이파이 multicast 차단 대응)

일부 와이파이(팀 전용 ipTIME 등)가 **DDS multicast discovery를 차단**해 단일 endpoint가 cross-host 로봇 토픽(카메라/센서)을 못 받을 때. `ROS_STATIC_PEERS`로 상대 IP를 직접 지정해 **unicast discovery**로 우회한다.

**증상 (이 우회가 필요한지 판별)**:
- `ros2 topic list`엔 상대 로봇 토픽이 부분적으로 뜸 (discovery 일부만 통과)
- `ros2 topic echo /상대토픽 --once` → `does not appear to be published yet` + `Could not determine the type`
- `ping 224.0.0.1`(multicast)은 응답 오는데 DDS group(`239.255.x`)은 차단
- Unity: endpoint `RegisterSubscriber` OK인데 frame("Pi Camera 연결됨") 0장

**해결 — 양쪽에 상대 IP 박기** (IP는 매번 바뀜 — mDNS/ARP로 현재값 확인 후 대입):
```bash
GZ=<젠지 현재 IP>; T1=<티원 현재 IP>

# 젠지 카메라 노드 (peer=티원)
ssh -fn kim@$GZ "bash -c 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 && export ROS_STATIC_PEERS=$T1 && export LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu:\$LD_LIBRARY_PATH && export LIBCAMERA_IPA_MODULE_PATH=/usr/local/lib/aarch64-linux-gnu/libcamera && exec ros2 run camera_ros camera_node --ros-args -r __ns:=/tb3_2 -p width:=640 -p height:=480' > /tmp/cam.log 2>&1"

# 티원 endpoint (peer=젠지) — endpoint가 cross-host로 젠지 카메라+센서 받아 Unity로 forward
ssh -fn t1@$T1 "bash -c 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 && export ROS_STATIC_PEERS=$GZ && exec ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000' > /tmp/ros_tcp.log 2>&1"
```

**검증 (3단계)**:
```bash
# 1) 데이터 실측 — talker/listener (작은 메시지로 cross-host 확정). topic list만 보지 말 것!
ssh -fn t1@$T1 "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=210 && export ROS_STATIC_PEERS=$GZ && exec ros2 run demo_nodes_cpp talker' >/tmp/talker.log 2>&1"
ssh kim@$GZ "source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210; export ROS_STATIC_PEERS=$T1; timeout 12 ros2 topic echo /chatter --once"
#   기대: data: 'Hello World: N'  ← cross-host 데이터 통함

# 2) 카메라 cross-host (endpoint 호스트 티원에서 젠지 토픽)
ssh t1@$T1 "source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210; export ROS_STATIC_PEERS=$GZ; timeout 8 ros2 topic echo /tb3_2/camera/camera_info --once"

# 3) 센서 cross-host (젠지 아두이노 /sensors/*)
ssh t1@$T1 "source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210; export ROS_STATIC_PEERS=$GZ; timeout 8 ros2 topic echo /sensors/ldr --once"
```

**원리**: multicast discovery가 막혀도 `ROS_STATIC_PEERS`가 participant를 unicast로 발견 + 데이터 unicast UDP는 통과(SSH-TCP 되는 망이면 대개 UDP unicast OK). 단일 endpoint(티원)가 `STATIC_PEERS=젠지`면 젠지 카메라(`/tb3_2`)+센서(`/sensors/*`)를 다 받아 Unity로 forward → **양 로봇 동시 표시 + 0ms 즉시 전환**(모델 B, `unity-camera-panel`).

| 함정 | 우회 |
|---|---|
| **20. ★ 와이파이 multicast 차단 → cross-host 토픽 데이터/타입 안 옴** (2026-06-15) | 양 노드+endpoint에 `ROS_STATIC_PEERS=<상대IP>` |
| endpoint에 STATIC_PEERS 안 박음 | endpoint가 cross-host 로봇 토픽 수신 못 함 → **endpoint에도 필수** |
| `.bashrc`에 엉뚱한 `ROS_STATIC_PEERS` 잔재 (2026-06-15 젠지 `.bashrc`에 `192.168.10.70` 발견) | 제거/교정. ssh 비대화형 launch는 `.bashrc` 미source라 영향 없지만 대화형/노드 source 시 오염 |

> **§F가 불필요한 경우**: 와이파이가 multicast 허용하면(`ros2 topic echo` cross-host 바로 됨) STATIC_PEERS 없이 §C 그대로. 새 와이파이 진입 시 위 "증상"으로 먼저 판별.

## 다음 세션 진입 한 줄 (젠지 풀 launch)

```bash
. ~/.tb3rc && printf '%s\n' "$TB3_PASSWORD" | ssh -o ControlMaster=no urhynix-robot '
  source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash 2>/dev/null
  export ROS_DOMAIN_ID=230
  export LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
  export LIBCAMERA_IPA_MODULE_PATH=/usr/local/lib/aarch64-linux-gnu/libcamera
  pkill -f camera_node 2>/dev/null
  pkill -f ros_tcp_endpoint 2>/dev/null
  sleep 1
  nohup ros2 run camera_ros camera_node --ros-args -r __ns:=/tb3_2 -p width:=1280 -p height:=720 > ~/camera_node.log 2>&1 < /dev/null & disown
  nohup ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=0.0.0.0 -p ROS_TCP_PORT:=10000 > ~/ros_tcp.log 2>&1 < /dev/null & disown
  sleep 5
  pgrep -af "camera_node|ros_tcp_endpoint" | head -5
  ss -tln | grep 10000
'
```

기대 출력 (마지막 2줄):
```
12454 ... ros2 run camera_ros camera_node ...
12886 ... default_server_endpoint ...
LISTEN 0  10  0.0.0.0:10000  0.0.0.0:*
```

## helper script로 자동화 (선택)

`scripts/tb3-camera-up.sh` 생성 후 위 명령 박으면 한 줄 호출 가능:

```bash
bash scripts/tb3-camera-up.sh
```

## 검증 evidence

- `docs/evidence/2026-06-01-rpi-camera-imx219-source-build.md` (Pi Camera 빌드 + 캡처)
- `docs/evidence/2026-06-01-robot2-realsense-d435-ros2-smoke.md` (D435 ROS2 통합)
- `docs/evidence/2026-06-02-pi-camera-ros2-topic-30hz.md` (이 스킬 검증, 작성 예정)

## 한줄정리

박물관 시연 카메라 트랙(젠지 Pi Camera + 티원 D435 + ROS-TCP-Endpoint)을 매 세션 첫 5분에 한 번에 살리는 표준 패턴. **LD_LIBRARY_PATH 우회 + ROS env 명시 source + nohup/disown + ControlMaster=no** 4종 함정 모두 잡혀있음. 다음 세션 진입 한 줄로 카메라 ready 검증까지 끝.
