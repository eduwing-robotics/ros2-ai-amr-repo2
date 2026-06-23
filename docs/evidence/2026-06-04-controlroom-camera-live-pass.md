# ControlRoom 젠지 Pi Camera 라이브 PASS (2026-06-04) — Phase 2.7

> Unity ControlRoom(신 프로젝트, Unity 6.3 LTS) 카메라 패널에 젠지(`/tb3_2/camera/image_raw/compressed`) 30Hz 라이브 RGB 표시 + 로그 패널 "🟢 Pi Camera 연결됨" + "⚪ Gemma 4 12B 대기 중" 2줄 PASS. 함정 4종 발견 + 모두 영구 패치/스킬화. UI Contract Lock 침해 UXML 1줄(VisualElement→Image)만.

## 환경

| 항목 | 값 |
|---|---|
| 호스트 (젠지) | `urhynix-robot` (kim@192.168.0.x) — Pi 4 Model B, Ubuntu 24.04.4 |
| ROS | Jazzy + `ros-jazzy-camera-ros 0.6.0` + `ros-jazzy-compressed-image-transport` |
| ROS-TCP-Endpoint | v0.7.0 (ROS2 branch, commit `54c1a64`) — `~/turtlebot3_ws/src/ROS-TCP-Endpoint` |
| Unity Editor | **6000.3.16f1 (Unity 6.3 LTS)** — 6/2 검증 시점의 6.0과 다름 |
| ROS-TCP-Connector | v0.7.0 (Unity 측) — `manifest.json` |
| 프로젝트 | `unity/ControlRoom/` (신규 Phase 2.5 완료, Phase 2.7 진입) |
| Mac | macOS Tahoe 26.3.1 (arm64) |
| ROS_DOMAIN_ID | 230 |

## 산출물 (코드/설정)

| 파일 | 종류 | 줄 |
|---|---|---|
| `unity/ControlRoom/Assets/Scripts/Ros/CameraStreamSubscriber.cs` | 🆕 신규 | 76 |
| `unity/ControlRoom/Assets/Editor/CameraStreamSetup.cs` | 🆕 신규 | 60 |
| `unity/ControlRoom/Assets/UI/Parts/CameraAndLogPanel.uxml` | ✏️ 1줄 (VisualElement → Image) | 27 |
| `unity/ControlRoom/Assets/Scripts/UI/CameraPanelView.cs` | ✏️ 30 → 43 (추가만) | 43 |
| `unity/ControlRoom/Assets/Scripts/App/ControlRoomApp.cs` | ✏️ ROS IP set + Gemma 대기 로그 1줄 | 46 |
| `unity/ControlRoom/ProjectSettings/ProjectSettings.asset` | ✏️ `scriptingDefineSymbols.Standalone: ROS2` | — |
| `unity/ControlRoom/Assets/Scripts/App/ControlRoomApp.cs` | ✏️ `ConfigureRos()` 추가 (RosIP=`urhynix-robot.local`:10000) | — |
| robot `~/turtlebot3_ws/build/ros_tcp_endpoint/ros_tcp_endpoint/server.py:125` | ✏️ `[:-1]` → `.rstrip("\x00").strip()` 패치 | — |
| robot `loginctl enable-linger kim` | 영구 활성화 | — |

## UI Contract Lock 침해 검사

| 대상 | 수정 | 침해? |
|---|---|---|
| UXML | 1줄 (`VisualElement` → `Image`, 시각 변화 0, 기능 확장만) | 경미 |
| USS | 0줄 | 없음 |
| 기존 View C# 라인 | 0줄 수정 (추가만) | 없음 |
| ControlRoomEvents | 0줄 (Subscriber static event로 우회) | 없음 |

## 함정 종합 (4종 신규 발견)

### 함정 #13. Ubuntu 24.04 `KillUserProcesses=yes`로 nohup+disown까지 죽음

**증상**: ssh 끊김 시 `ros2 run camera_ros camera_node` 등 백그라운드 노드 즉시 사라짐. `pgrep -af camera_node` 0건.

**원인**: systemd-logind 기본 `KillUserProcesses=yes` (Ubuntu 22.04+). user 로그아웃 시 user의 모든 프로세스 종료. nohup의 SIGHUP 무시도 무효.

**해결**: 1회 활성화 (영구)
```bash
sudo loginctl enable-linger kim
loginctl show-user kim | grep Linger   # Linger=yes 확인
```

이후 ssh 끊겨도 user systemd manager 유지 → tmux 세션 + 자식 프로세스 살아남.

### 함정 #14. Unity 6.3 + ROS-TCP-Connector v0.7.0 syscommand JSON `[:-1]` 호환 안 됨

**증상**: robot 측 ros_tcp_endpoint server.py에서 `json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 91 (char 90)`. Unity는 `socket has been shut down` 반복.

**원인**: `server.py:125`의 `message_json = data.decode("utf-8")[:-1]`이 Unity가 보낸 syscommand 메시지의 마지막 1 byte를 무조건 cut. Unity 6.3에서 trailing null byte 안 보내는 케이스 발생 → valid JSON 끝 char까지 잘라서 broken JSON.

**해결**: server.py:125 패치
```python
# 변경 전
message_json = data.decode("utf-8")[:-1]
# 변경 후
message_json = data.decode("utf-8").rstrip("\x00").strip()
```

영구 적용: `~/turtlebot3_ws/build/ros_tcp_endpoint/ros_tcp_endpoint/server.py` 직접 패치. (src/도 같이 박아 colcon build 시 유지하는 게 권장. 본 evidence에서는 build/만 즉시 패치.)

### 함정 #15. macOS에서 `setsid+nohup` Unity 시동이 LaunchServices attach 실패로 빨리 죽음

**증상**: `setsid nohup /Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app/Contents/MacOS/Unity ...`로 시동하면 Unity 프로세스가 init 단계에서 즉시 종료. `ps -ef`에 0건. 로그도 28~41줄에서 멈춤.

**원인**: macOS의 GUI 앱은 LaunchServices를 통해 띄워야 정상 attach. `setsid+nohup`로 detach하면 Apple Event 채널 / Window Server 핸들 못 받음 → init 실패.

**해결**: `open -a` 사용
```bash
open -a "/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app" --args \
  -projectPath /Users/family/jason/URHYNIX/unity/ControlRoom \
  -logFile /tmp/unity-foo.log
sleep 5
ps -ef | grep "Unity.app/Contents/MacOS/Unity" | grep -v grep | head -2
osascript -e 'tell application "Unity" to activate'
```

`open -a`는 LaunchServices를 통해 시동 → GUI 정상 시작. `-args` 뒤에 Unity CLI 옵션 그대로 전달.

### 함정 #16. ★ Unity는 기본 ROS1 모드. ROS2 endpoint와 binary format 비대칭으로 OverflowException

**증상**: 
- robot `RegisterSubscriber(/tb3_2/camera/image_raw/compressed, ...) OK` 정상 (#14 패치 후)
- Unity 측 `OverflowException` + `ArgumentException: Offset and length were out of bounds` 반복
- 스택 트레이스: `MessageDeserializer.Read[T]` → `CompressedImageMsg..ctor` → `RosTopicState.OnMessageReceived` → `ROSConnection.Update`
- frame 한 장도 못 받음
- 정확한 Unity Console 메시지: **"Incompatible protocol: ROS-TCP-Endpoint is using ROS2, but Unity is in ROS1 mode. Switch it from the Robotics/Ros Settings menu."**

**원인**: ROS-TCP-Connector v0.7.0 코드의 `#if ROS2` 컴파일 분기. **`ROS2` define symbol 없으면 ROS1 binary format으로 컴파일** (CompressedImageMsg `data` 배열 length field 해석이 다름). ROS2 endpoint가 보낸 메시지의 length가 ROS1로 해석되면 거대값 → OverflowException + ArgumentException.

**해결**: `ProjectSettings.asset`의 `scriptingDefineSymbols`에 `ROS2` 추가.

GUI 경로 (권장):
```
Edit → Project Settings → Player → Other Settings → Scripting Define Symbols
  → "ROS2" 추가 → Apply
```

직접 편집 (Editor 죽어있을 때 비상시):
```yaml
# ProjectSettings/ProjectSettings.asset
  scriptingDefineSymbols:
    Standalone: ROS2
```

Unity 재시동 → 컴파일 자동 트리거 (`#if ROS2` 분기 활성) → CompressedImageMsg ROS2 binary format으로 deserialize → 라이브 영상 흐름.

> 📌 **이게 진짜 핵심**. 다른 3종 함정 다 잡아도 #16 안 잡으면 영상 0 frame.

## 검증 매트릭스 (최종 PASS)

| 항목 | 결과 |
|---|---|
| Compilation | 31 assemblies, `scriptCompilationFailed: false` ✅ |
| Console errors | 0건 ✅ |
| robot port 10000 LISTEN | ✅ |
| robot `Connection from 192.168.0.x` | ✅ |
| robot `RegisterSubscriber(/tb3_2/camera/image_raw/compressed) OK` | ✅ |
| robot `RegisterSubscriber(/tf) OK` | ✅ |
| Unity `ROS Connection to urhynix-robot.local:10000 succeeded!` | ✅ |
| Unity `[CameraStreamSubscriber:젠지] subscribed → /tb3_2/...` | ✅ |
| Unity `[ControlRoomApp] ROS IP set: urhynix-robot.local:10000` | ✅ |
| 카메라 패널 라이브 RGB 표시 | ✅ (사용자 확인 "카메라 화면 잘나옴") |
| 로그 패널 "🟢 Pi Camera 연결됨 (젠지 · ...)" | ✅ |
| 로그 패널 "⚪ Gemma 4 12B 대기 중" | ✅ |
| 토픽 hz | 29.9~30.0 Hz 안정 ✅ |

## 데이터 흐름 (최종)

```
[젠지 Pi Camera v2 IMX219 @ 30Hz]
   │
   ↓ camera_ros (tmux 'camera') + LD_LIBRARY_PATH Pi fork libcamera
   │
   ↓ /tb3_2/camera/image_raw/compressed (JPEG 640×480)
   │
   ↓ ros_tcp_endpoint v0.7.0 (tmux 'rostcp', server.py:125 patched)
   │     port 10000 LISTEN
   │
   ↓ TCP (Wi-Fi 학원망)
   │
   ↓ Unity ROS-TCP-Connector v0.7.0 (#if ROS2 컴파일 분기)
   │     ROSConnection (rosIP=urhynix-robot.local, RosPort=10000)
   │
   ↓ CompressedImageMsg deserialize (ROS2 binary format)
   │
   ↓ CameraStreamSubscriber.OnImageReceived → Texture2D.LoadImage(msg.data)
   │
   ↓ static event OnFrameUpdated(Texture2D, hz)
   │
   ↓ CameraPanelView.OnFrameUpdated → ui:Image.image = tex + hz 갱신 + placeholder 숨김
   │
   ↓ 박물관 시연 카메라 패널 (UI Toolkit)
```

## 다음 단계 (Phase 2.7 → Phase 3 진입 전 정리)

1. **`server.py:125` 패치 src/에도 박기** — 현재 build/만 패치. colcon build 시 덮어쓰일 수 있음. `~/turtlebot3_ws/src/ROS-TCP-Endpoint/ros_tcp_endpoint/server.py`도 동일 패치 + colcon build 재실행 (또는 영구 patch 파일로 관리).
2. **티원(t1) D435 같은 패턴으로** — 같은 `loginctl enable-linger t1` + camera_namespace=tb3_1 + ros_tcp_endpoint 띄우기. 단 Unity 측은 단일 ROS-TCP 연결이므로 같은 endpoint 인스턴스에서 두 토픽 처리.
3. **CameraStreamSubscriber 2번째 인스턴스 추가** (티원용) — Scene에 GameObject "CameraStreamSubscriber_T1" 신규 + topicName=`/tb3_1/camera/color/image_raw/compressed`. CameraPanelView가 static event 1개로 양쪽 수신하려면 인스턴스 식별자 필요 — 별도 View 만들거나 토픽 필터링.
4. **Gemma 4 12B 통합 진입** (Phase 2.8) — 백엔드 노드 추가, Unity 로그 회색 ⚪ → 녹색 🟢로 토글.

## 잡힌 함정 → 스킬 영구 자산화

| 함정 # | 추가 위치 | 비고 |
|---|---|---|
| 13 (linger) | `robot-camera-bringup` 스킬 함정표 | 매 세션 첫 5분에 활용 |
| 14 (server.py 패치) | `robot-camera-bringup` 스킬 + 본 evidence src 패치 항목 | 영구 패치 필요 |
| 15 (open -a) | `robot-camera-bringup` 스킬 함정표 | macOS Unity 시동 표준 |
| 16 (ROS2 define) | `robot-camera-bringup` + `unity-camera-panel` 스킬 양쪽 | Unity 6.x 신 프로젝트 진입 시 첫 액션 |

## 사용자 결정 분기 (Plan에서 받은 3개)

- 6.1 렌더링 방식: **A** (UI Toolkit `<ui:Image>`) — UXML 1줄 수정 |
- 6.2 로그 문구: **A** (이모지+간단) — `🟢 Pi Camera 연결됨` + `⚪ Gemma 4 12B 대기 중` |
- 6.3 듀얼/단일: **A** (젠지 단일) — 티원은 별도 단계로 |

## 외부 참조

- `.claude/skills/robot-camera-bringup/SKILL.md` — 4 종 함정 보강 후
- `.claude/skills/unity-camera-panel/SKILL.md` — ROS2 define 항목 추가
- `docs/evidence/2026-06-02-camera-ros2-topic-unity-batch-setup.md` — 이전 검증 (Unity 6.0 + unity-smoke)
- DECISION-LOG 2026-06-04 (본 작업 entry)

## 한줄정리

ControlRoom 신 프로젝트(Unity 6.3 LTS)에 젠지 Pi Camera 30Hz 라이브 결선 PASS. **4종 함정**(linger / server.py [:-1] / open -a / **ROS2 define**) 모두 잡아 영구 패치 + 스킬화. UI Contract Lock 침해 UXML 1줄만. 로그 패널에 🟢 Pi Camera 연결됨 + ⚪ Gemma 4 12B 대기 중 2줄 표시. **다음: 티원 D435 같은 패턴 + Gemma 4 12B 통합 진입**.
