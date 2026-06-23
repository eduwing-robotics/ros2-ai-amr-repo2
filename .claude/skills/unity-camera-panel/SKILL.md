---
name: unity-camera-panel
description: URHYNIX Unity 관제 UI에 ROS2 카메라 라이브 RGB 패널을 추가하는 표준 패턴. CameraStreamPanel.cs 컴포넌트(topic Inspector 입력) + CameraPanelSetup.cs Editor script(batch mode 자동 실행). 새 카메라 추가 시 AddCameraPanel 한 줄로 확장. — 시연용 Unity 패널 작업의 핵심 자산.
---

# unity-camera-panel

## 언제 쓰나

- Unity 관제 UI에 새 카메라 라이브 RGB 패널 추가할 때
- 박물관 시연 발표 자료용 라이브 영상 셋샷 필요할 때
- 카메라 두 개(젠지 + 티원) 동시 표시
- 코드 손대지 않고 Inspector에서 topic 만 바꿔서 확장

## 핵심 자산 3종

| 파일 | 역할 |
|---|---|
| `unity-smoke/Assets/Scripts/CameraStreamPanel.cs` | 한 컴포넌트가 한 카메라. Inspector에 topic + label 입력 |
| `unity-smoke/Assets/Editor/CameraPanelSetup.cs` | Unity Editor script — 메뉴 `URHYNIX → Setup Camera Panels` 또는 batch mode로 GameObject 자동 생성 |
| Unity batch mode CLI | Editor 안 켜고 Scene에 패널 자동 추가 |

## 컴포넌트 설계 (CameraStreamPanel.cs)

핵심 필드:
- `topicName` (string) — 예: `/tb3_2/camera/image_raw/compressed`
- `displayLabel` (string) — 예: `젠지` 또는 `티원`
- `targetImage` (RawImage) — 같은 GameObject의 RawImage 자동 사용
- `labelText` (Text) — 옵션, hz 표시

작동:
1. Start에서 `ROSConnection.Subscribe<CompressedImageMsg>(topicName, ...)`
2. callback에서 `Texture2D.LoadImage(msg.data)` — JPEG/PNG 자동 decode
3. Update에서 매 1초 hz 계산 + 라벨 갱신

→ 카메라 추가 = GameObject 복제 + Inspector에서 topic + label 한 줄 변경.

## 자동 실행 — Unity batch mode

Unity Editor 안 켜고 명령으로 GameObject 자동 추가:

```bash
/Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app/Contents/MacOS/Unity \
  -batchmode -quit -nographics \
  -projectPath /Users/family/jason/URHYNIX/unity-smoke \
  -executeMethod CameraPanelSetup.Setup \
  -logFile /tmp/unity_camera_setup.log
```

소요: 약 60~90초 (Unity 6 batch 시작 오버헤드).

검증:
```bash
grep "CameraPanelSetup" /tmp/unity_camera_setup.log
# 기대:
#   [CameraPanelSetup] Canvas created
#   [CameraPanelSetup] GenjiCameraPanel → topic=... label=...
#   [CameraPanelSetup] T1CameraPanel → topic=... label=...
#   [CameraPanelSetup] Done. Scene saved
```

Scene 파일 변경 검증:
```bash
git diff --stat unity-smoke/Assets/Scenes/SampleScene.unity
# 기대: 500+ lines insertions
grep "topicName" unity-smoke/Assets/Scenes/SampleScene.unity
```

## 함정 + 우회 표

| 함정 | 증상 | 우회 |
|---|---|---|
| `new GameObject(name)`로 만든 UI GameObject의 RectTransform 없음 | `MissingComponentException: RectTransform` | `new GameObject(name, typeof(RectTransform))` 패턴 |
| Canvas 없는 Scene에서 UI 추가 | Canvas 자식이 안 보임 | `Object.FindFirstObjectByType<Canvas>()` 후 없으면 자동 생성 + ScreenSpaceOverlay |
| EventSystem 없으면 UI 인터랙션 안 됨 | 버튼/입력 무반응 | Setup에서 EventSystem 자동 추가 |
| Scene 저장 안 됨 | batch 실행 후 변경 사라짐 | `EditorSceneManager.MarkSceneDirty(scene)` + `SaveScene(scene)` 명시 |
| 한글 디스플레이 라벨 폰트 깨짐 | □□ 또는 안 보임 | `Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf")` 사용 또는 한글 폰트 별도 import |
| 컴파일 에러로 batch 실패 | `Aborting batchmode due to failure: executeMethod method ... threw exception` | log 파일 grep으로 line 번호 확인 후 수정 |
| Unity license 활성화 | `Access token is unavailable` 경고 | 무시 가능 (Personal License로 batch 작동) |
| **★ Unity 기본은 ROS1 모드. ROS2 endpoint 사용 시 `Define Symbol ROS2` 필수** (2026-06-04 발견) | Console: `Incompatible protocol: ROS-TCP-Endpoint is using ROS2, but Unity is in ROS1 mode`. 그 뒤 `OverflowException` + `ArgumentException` deserialize 실패 반복. frame 0장 | **신 Unity 프로젝트 첫 진입 시 무조건**: `Edit → Project Settings → Player → Other Settings → Scripting Define Symbols → "ROS2" 추가 → Apply`. 또는 `ProjectSettings.asset`에 `scriptingDefineSymbols:\n  Standalone: ROS2`. 자세히: `docs/evidence/2026-06-04-controlroom-camera-live-pass.md` 함정 #16 |
| **UI Toolkit `VisualElement`에는 Texture2D 동적 주입 불가** (ControlRoom Phase 2.7) | 카메라 placeholder에 영상 안 흐름 (런타임 background-image asset 변경 안 됨) | UXML에서 `<ui:VisualElement>` → **`<ui:Image>`** (1줄). View에서 `root.Q<Image>("camera-image").image = streamTexture` |
| **macOS Unity 시동 시 `setsid+nohup`은 빨리 죽음** | log 28~41줄에서 종료, ps에 프로세스 0건 | `open -a "/Applications/Unity/Hub/Editor/<ver>/Unity.app" --args -projectPath ... -logFile ...` |
| **★ Write/외부 에디터로 만든 신규 `.cs`는 `.meta` 미생성 → 어셈블리 누락** (2026-06-05 발견) | 같은 namespace의 다른 파일에서 `error CS0103: The name '<Class>' does not exist in the current context`. `Library/ScriptAssemblies/*.dll` mtime이 갱신 안 됨 | **unityctl**: `unityctl asset import --project <proj> --path Assets/Scripts/.../<file>.cs --json` → `.meta` 생성 + Asset Pipeline 등록 한 번에 (`guid` 발급으로 검증). **GUI 우회**: Project 창 우클릭 → Refresh (`Cmd+R`). 자세히: `docs/evidence/2026-06-05-controlroom-dual-camera-toggle.md` 함정 #17 |
| **★ Play 모드 중에는 도메인 리로드 차단 → 새 코드 미적용** (2026-06-05 발견) | `unityctl asset refresh` + `RequestScriptCompilation` 호출해도 어셈블리 mtime 옛값. `unityctl exec`로 메서드 호출 시 옛 코드 실행 (예: 옛 단일 Subscriber 로그) | **5단계 표준**: `play stop` → settled 대기(`status==Ready`) → `exec UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation()` → mtime 갱신 확인 → `exec <Setup>()` → `play start`. 자세히: 본 SKILL "unityctl 자동화 표준 5단계" 섹션 |

## 새 카메라 추가 (확장성 패턴)

### Option A: Editor script에 한 줄 추가 (영구)

`CameraPanelSetup.cs`의 `Setup()` 안에 한 줄 추가:

```csharp
AddCameraPanel(
    canvas: canvas,
    name: "NewRobotCameraPanel",
    topic: "/tb3_3/camera/image_raw/compressed",   // 새 카메라 토픽
    label: "신규 로봇",
    anchorMin: new Vector2(0, 1),
    anchorMax: new Vector2(0, 1),
    pivot: new Vector2(0, 1),
    anchoredPos: new Vector2(20, -20),              // 위치만 조정
    size: new Vector2(320, 240)
);
```

그 다음 batch mode 재실행 → Scene에 자동 추가.

### Option B: Unity Editor 직접 (즉석)

1. Hierarchy에서 `GenjiCameraPanel` 우클릭 → **Duplicate**
2. 이름 변경
3. Inspector에서 `topicName` + `displayLabel` 한 줄 변경
4. Rect Transform 위치 조정

## 박물관 시연 매핑 (회의록 5111810)

| 패널 이름 | 별명 | 카메라 | 토픽 |
|---|---|---|---|
| GenjiCameraPanel | 젠지 | Pi Camera v2 (IMX219) | `/tb3_2/camera/image_raw/compressed` |
| T1CameraPanel | 티원 | RealSense D435 | `/tb3_1/camera/color/image_raw/compressed` |

> ⚠️ realsense2_camera에 `camera_namespace:=tb3_1`을 주면 토픽이 **`/tb3_1/camera/color/...`** (camera 1번)로 발행됨. 이전 SKILL 표의 `/tb3_1/camera/camera/...` 형은 잘못된 가정 — 실측 확인. (`robot-camera-bringup` 함정 #10 참조)

## 듀얼 카메라 분기 — 모델 B (2026-06-05 PASS)

상단 탭(티원/젠지) 클릭 시 카메라 패널이 **0ms 즉시 전환**되도록 하는 표준 패턴. 사용자 확인: "딜레이없이 전환잘됨".

### 두 모델 비교 (구현 전 결정)

| 항목 | 모델 A (토글 구독) | 모델 B (동시 구독 + display 토글) |
|---|---|---|
| 전환 지연 | 80~200ms LAN, 300~500ms Wi-Fi 변동 | **0ms (다음 frame ≤ 33ms)** |
| Wi-Fi 대역 | 1채널 (~3 Mbps) | 2채널 (~6 Mbps, 학원 Wi-Fi 100Mbps+ 대비 6%) |
| Pi 부하 | 1토픽 forward | 2토픽 forward (+5~10% CPU) |
| 로딩 스피너 | 필요 | **불필요** |
| 시연 위험 | Wi-Fi 변동 시 검은 화면 | 양쪽 카메라 모두 살아있어야 함 |

→ **시연용 권장 모델 B** (지연 0ms + 스피너 불필요 + 시연 흐름 끊김 없음). 모델 A는 Pi CPU/Wi-Fi 한계 닿을 때만.

### 모델 B 핵심 4파일

| 파일 | 역할 |
|---|---|
| `Scripts/Ros/TopicRegistry.cs` | 토픽 SSOT (`Ros/CLAUDE.md` 규칙). `GetCameraCompressed(robotId)` lookup |
| `Scripts/Ros/CameraStreamSubscriber.cs` | `robotId` 필드 + 정적 event 시그니처 `(string robotId, Texture2D, float)`. 인스턴스 1개당 토픽 1개 |
| `Scripts/UI/CameraPanelView.cs` | `activeRobotId` 필드 + frame robotId 필터링. `ControlRoomEvents.OnRobotChanged` 구독 |
| `Editor/CameraStreamSetup.cs` | `SubSpec[]` 배열로 두 Subscriber GameObject(`_Genji`/`_T1`) idempotent 생성 |

### 시그니처 변경 (단일 → 듀얼)

```csharp
// 단일 (Phase 2.7)
public static event Action<Texture2D, float> OnFrameUpdated;
OnFrameUpdated?.Invoke(streamTexture, currentHz);

// 듀얼 (Phase 2.7-dual) — robotId 식별자 추가
public static event Action<string, Texture2D, float> OnFrameUpdated;
OnFrameUpdated?.Invoke(robotId, streamTexture, currentHz);
```

### View 측 robotId 필터링

```csharp
void OnFrameUpdated(string robotId, Texture2D tex, float hz)
{
    if (robotId != activeRobotId) return;   // 비활성 로봇 frame 무시
    cameraImage.image = tex;
    hzLabel.text = $"{hz:F1} Hz";
}

void OnRobotChanged(string robotId)
{
    activeRobotId = robotId;
    hzLabel.text = "-- Hz";   // 첫 frame 도착 전까지 표시
}
```

### Cross-host visibility 검증 (Endpoint는 1개만)

`ROS_DOMAIN_ID` 통일 + **cross-host DDS가 통하면** endpoint 1개가 양쪽 토픽 모두 forward 가능. 추가 endpoint 불필요.

```bash
# endpoint 호스트에서 상대 로봇 토픽 데이터가 실제 오나? (topic list 말고 echo!)
ssh <endpoint호스트> 'ros2 topic echo /tb3_2/camera/camera_info --once'   # header 오면 OK
```

> ⚠️ **`topic list`만 보고 cross-host 됐다고 판단 금물** (2026-06-15). discovery 일부가 통과해 topic list엔 떠도 실제 데이터는 0인 경우가 있다 — 반드시 `echo --once`로 실데이터 확인.
>
> ⚠️ **와이파이가 DDS multicast를 차단하면**(팀 전용 와이파이 등) `echo`가 `does not appear to be published` + `Could not determine the type`로 실패하고, Unity는 `RegisterSubscriber` OK인데 **frame 0장**이 된다. 이때 **`ROS_STATIC_PEERS=<상대IP>`로 unicast discovery 우회** 필수 — 카메라/센서 노드 + `ros_tcp_endpoint` **양쪽 모두**에 박아야 endpoint가 cross-host 토픽을 받는다. 전체 절차: `robot-camera-bringup` §F. 2026-06-15 PASS(젠지 카메라+센서 → 티원 endpoint → Unity 양 로봇 즉시 전환).

### 검증 흐름

```bash
# 1) robot 양쪽 카메라 살아있나 (robot-camera-bringup)
# 2) Unity 컴파일 + Setup 호출 (unityctl 자동화 표준 5단계, 아래)
# 3) Play start
unityctl play start --project <proj> --json

# 4) robot 측 LISTEN + ESTAB
ssh urhynix-robot 'ss -tn | grep ":10000"'
# 기대: ESTAB ... 192.168.0.80:10000 <Mac IP>:<port>

# 5) 사용자 시각 확인 (탭 클릭 → 패널 즉시 전환)
```

## unityctl 자동화 표준 5단계 (함정 #17 + #18 동시 우회)

신규 `.cs` 파일 생성 + Editor 메서드 호출까지 한 번에 가는 표준. 매 Unity 코드 변경 직후 사용.

```bash
PROJ=/Users/family/jason/URHYNIX/unity/ControlRoom

# 1) 새 .cs 파일이라면 강제 import (함정 #17 회피: .meta 자동 생성)
unityctl asset import --project "$PROJ" --path Assets/Scripts/<...>/New.cs --json

# 2) Play 정지 (함정 #18 회피: 도메인 리로드 차단 해제)
unityctl play stop --project "$PROJ" --json

# 3) Editor settled 대기
until s=$(unityctl status --project "$PROJ" 2>/dev/null); echo "$s" | grep -q "Ready"; do sleep 3; done

# 4) 컴파일 강제 (도메인 리로드 자동 동반)
unityctl exec --project "$PROJ" \
  --code 'UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation()' --json

# 다시 settled 대기 + assembly mtime 갱신 확인
stat -f "%Sm" "$PROJ/Library/ScriptAssemblies/Assembly-CSharp-Editor.dll"

# 5) Setup 호출 (이제 새 코드 실행) — 세미콜론 X
unityctl exec --project "$PROJ" \
  --code 'URHYNIX.ControlRoom.Editor.CameraStreamSetup.Setup()' --json

# 마지막: 재생
unityctl play start --project "$PROJ" --json
```

**Tip**:
- `unityctl exec --code 'X()'` 형식. 세미콜론 붙이면 `No public static property '<X>();'` 에러. **세미콜론 절대 X**.
- IPC가 도메인 리로드 직후 잠시 `103 IPC not ready`. `Ready` 폴링으로 우회.
- Editor focus 없으면 IPC 안 뜸. `osascript -e 'tell application "Unity" to activate'` 권장.

## 의존성

- ROS-TCP-Connector (`Unity.Robotics.ROSTCPConnector`) — unity-smoke에 이미 설치
- `RosMessageTypes.Sensor.CompressedImageMsg` — 어셈블리 import
- robot 측 `ros_tcp_endpoint` 노드 실행 중 + 같은 LAN + ROS_DOMAIN_ID 일치
- robot 측 camera 토픽 발행 중 (`robot-camera-bringup` 스킬 참조)

## 검증 흐름 (full smoke)

```bash
# 1) robot 측 카메라 + ros_tcp_endpoint launch (robot-camera-bringup 스킬)
# 2) Unity batch mode로 Scene에 패널 자동 추가
/Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app/Contents/MacOS/Unity \
  -batchmode -quit -nographics \
  -projectPath /Users/family/jason/URHYNIX/unity-smoke \
  -executeMethod CameraPanelSetup.Setup \
  -logFile /tmp/unity_setup.log

# 3) Unity Editor 켜고 Play → 라이브 영상 확인
#    (사람 작업, 발표 자료 스크린샷 캡처)
```

## 한줄정리

`CameraStreamPanel.cs` 한 컴포넌트 + `CameraPanelSetup.cs` Editor script + Unity batch mode 명령 3종이면 박물관 시연 카메라 패널을 **코드 손 안 대고 추가**할 수 있어요. 새 카메라 추가는 `AddCameraPanel(...)` 한 줄 박고 batch 재실행 또는 Hierarchy에서 Duplicate + Inspector topic 변경.
