# ControlRoom 듀얼 카메라 분기 PASS — 모델 B (2026-06-05) Phase 2.7-dual

> Unity ControlRoom(신 프로젝트, Unity 6.3 LTS)의 상단 로봇 탭(티원/젠지) 클릭 시 카메라 패널이 **지연 0ms**로 즉시 전환되도록 듀얼 카메라 결선. 사용자 직접 확인 "딜레이없이 전환잘됨 실시간표시됨". 모델 B(동시 구독 + display 토글) 채택. 신규 함정 2종(`.meta` 미생성 + Play 중 도메인 리로드 차단) 영구 자산화.

## 환경

| 항목 | 값 |
|---|---|
| 호스트 (젠지) | `urhynix-robot` Pi 4 Model B, Ubuntu 24.04.4, camera_ros 0.6.0 |
| 호스트 (티원) | `t1@192.168.0.250` hostname `rb`, RealSense D435 (Serial 254522075185), realsense2_camera |
| ROS | Jazzy + `ROS_DOMAIN_ID=230` 통일 |
| ROS-TCP-Endpoint | 젠지 1개만 (port 10000). 티원에 별도 endpoint 불필요 (cross-host visibility 검증 PASS) |
| Unity Editor | 6000.3.16f1 (Unity 6.3 LTS) |
| ROS-TCP-Connector | v0.7.0 (`#if ROS2` 분기, ScriptDefineSymbol `ROS2` 영구) |
| unityctl | `/Users/family/.dotnet/tools/unityctl` (dotnet tool) — Bridge IPC `unityctl_*` |
| 프로젝트 | `unity/ControlRoom/` (Phase 2.7 → 2.7-dual) |

## 전환 모델 결정 — 모델 B 채택

### 두 모델 비교 (Wi-Fi/CPU/지연 측정 기반)

| 항목 | 모델 A (토글 구독) | 모델 B (동시 구독 + display 토글) |
|---|---|---|
| 전환 지연 | 80~200ms LAN, 300~500ms Wi-Fi 변동 시 | **0ms (다음 frame, 최대 33ms)** |
| Wi-Fi 대역 | 1채널 (1~3 Mbps) | 2채널 (2~6 Mbps, 학원망 100Mbps+ 대비 6%) |
| 젠지 Pi 부하 | 1토픽 forward | 2토픽 forward (+5~10% CPU) |
| 로딩 스피너 | 필요 | **불필요** |
| 시연 위험 | Wi-Fi 변동 시 검은 화면 | 양쪽 카메라 모두 살아있어야 함 |

### 결정 근거

- Mac↔젠지 LAN ping 22ms 평균, Mac↔티원 53ms (17~88, Wi-Fi 변동성)
- 학원 Wi-Fi 100Mbps+ 대역 → 2채널(6Mbps) 여유
- 시연 흐름이 끊기지 않는 게 핵심 → 0ms 즉시 전환이 결정타
- 사용자(주인님) 결정: **모델 B**

### 사용자 실측 PASS

- 사용자 직접 확인: "**딜레이없이 전환잘됨 실시간표시됨**"
- robot 측 `ESTAB + Send-Q 77KB` (영상 흐름) 양쪽 모두 정상

## 산출물 (코드)

| 파일 | 종류 | 줄 | 비고 |
|---|---|---|---|
| `unity/ControlRoom/Assets/Scripts/Ros/TopicRegistry.cs` | 🆕 신규 | 16 | 토픽 SSOT (Ros/CLAUDE.md 규칙 준수). `GenjiCameraCompressed`, `T1CameraCompressed`, `GetCameraCompressed(robotId)` |
| `unity/ControlRoom/Assets/Scripts/Ros/CameraStreamSubscriber.cs` | ✏️ 리팩 | 76 → 81 | `robotId` 필드 + 정적 event 시그니처 `(string robotId, Texture2D, float)`. `topicName` 비우면 TopicRegistry lookup |
| `unity/ControlRoom/Assets/Scripts/UI/CameraPanelView.cs` | ✏️ 리팩 | 43 → 46 | `activeRobotId` 필드 + frame robotId 필터링. `OnRobotChanged` 시 hz 초기화 + 전환 로그 발화 |
| `unity/ControlRoom/Assets/Editor/CameraStreamSetup.cs` | ✏️ 리팩 | 60 → 80 | `SubSpec[]` 배열로 두 Subscriber GameObject(`_Genji`/`_T1`) idempotent 생성. 메뉴 라벨 `(Dual)` |
| `unity/ControlRoom/Assets/Scripts/UI/RobotTabView.cs` | 변경 0 | 38 | 이미 `Button.clicked → SelectRobot → OnRobotChanged` + active class 토글 완성돼있었음 |
| `unity/ControlRoom/Assets/Scripts/App/ControlRoomState.cs` | 변경 0 | — | `SelectRobot(robotId)`이 `RaiseRobotChanged` 발화 완성돼있었음 |
| `unity/ControlRoom/Assets/UI/Parts/TopBar.uxml` | 변경 0 | — | `tab-tb3_1`/`tab-tb3_2` Button 이미 존재 |

**UI Contract Lock 침해 0건** (UXML/USS 0줄 수정).

## 데이터 흐름 (최종)

```
[젠지 Pi Camera v2 30Hz]               [티원 RealSense D435 30Hz]
       │                                       │
       ↓ camera_ros                            ↓ realsense2_camera
       │                                       │
/tb3_2/.../compressed                  /tb3_1/.../compressed
       │                                       │
       └─────────────┬─────────────────────────┘
                     │  ROS_DOMAIN_ID=230 통일 (cross-host visibility)
                     ↓
       젠지 ros_tcp_endpoint (port 10000)  ← 양쪽 토픽 모두 forward
                     │
                     ↓ TCP (학원 Wi-Fi)
                     │
       Unity ROS-TCP-Connector (단일 endpoint 연결)
                     │
       ┌─────────────┴─────────────┐
       ↓                           ↓
CameraStreamSubscriber_Genji  CameraStreamSubscriber_T1
  robotId="tb3_2"               robotId="tb3_1"
       │                           │
       ↓ OnFrameUpdated("tb3_2",   ↓ OnFrameUpdated("tb3_1",
         tex, hz)                    tex, hz)
       └─────────────┬─────────────┘
                     ↓
       CameraPanelView (static event 구독)
       activeRobotId == frame.robotId ? cameraImage.image = tex : ignore
                     │
                     ↑ RobotTabView "젠지"/"티원" Button.clicked
                     ↑ → ControlRoomState.SelectRobot(robotId)
                     ↑ → ControlRoomEvents.RaiseRobotChanged(robotId)
                     ↑ → CameraPanelView.activeRobotId 갱신 (0ms 즉시 토글)
```

## 함정 종합 (신규 2종)

### 함정 #17. Write 도구로 신규 `.cs` 파일 만들면 `.meta` 미생성 → 어셈블리 누락

**증상**: 새 클래스(`TopicRegistry`)를 디스크에 만들고 compile 트리거해도 어셈블리에 심볼 누락. 다른 파일에서 `error CS0103: The name 'TopicRegistry' does not exist in the current context`. 같은 namespace, 같은 폴더인데도 못 찾음.

**원인**: Unity는 `<file>.cs.meta` 가 있는 파일만 Asset Pipeline에 import. Write/외부 에디터로 직접 만든 `.cs`는 `.meta`가 없어 Asset Pipeline이 무시 → `Library/ScriptAssemblies/Assembly-CSharp.dll`에 들어가지 않음 → 컴파일러가 해당 심볼 못 봄.

**검증 방법**:
```bash
ls -la Assets/Scripts/Ros/TopicRegistry.cs Assets/Scripts/Ros/TopicRegistry.cs.meta
# .meta 없으면 함정 #17
```

**해결** (unityctl 사용):
```bash
unityctl asset import \
  --project /Users/family/jason/URHYNIX/unity/ControlRoom \
  --path Assets/Scripts/Ros/TopicRegistry.cs --json
# 응답: {"success":true,"data":{"guid":"<32-char>","options":"Default"}}
```

import 호출이 `.meta` 생성 + Asset Pipeline 등록을 한 번에 수행. 이후 `RequestScriptCompilation`으로 컴파일하면 새 심볼이 어셈블리에 들어감.

GUI 우회: Unity Editor에서 Project 창 우클릭 → Refresh (Cmd+R).

### 함정 #18. Play 모드 중에는 도메인 리로드 차단 → 새 코드 미적용

**증상**: `unityctl asset refresh` + `RequestScriptCompilation` 호출해도 `Library/ScriptAssemblies/Assembly-CSharp-Editor.dll` mtime이 옛값 유지. 새 코드 컴파일이 일어나지 않음. `unityctl exec`로 Editor 메서드 호출하면 옛 코드가 실행됨 (예: 옛 단일 Subscriber 로그).

**원인**: Unity의 Domain Reload는 Play 모드 중에는 기본적으로 차단됨 (ScriptableRuntimeReloadMode 설정 무관). `unityctl status` 응답에 `isPlaying: true`이면 reload 시도해도 무시.

**검증**:
```bash
unityctl status --project <proj> --json | python3 -c "
import sys,json
d=json.load(sys.stdin)['data']
print(f\"play={d['isPlaying']} compile={d['isCompiling']} reload={d['isDomainReloading']}\")"
# play=True 면 함정 #18
```

**해결 순서** (unityctl):
```bash
# 1) Play 정지
unityctl play stop --project <proj> --json

# 2) Editor settled 대기 (idle 보장)
until s=$(unityctl status --project <proj> --json 2>/dev/null); echo "$s" | grep -q "Ready"; do sleep 3; done

# 3) 컴파일 강제 (도메인 리로드 자동 동반)
unityctl exec --project <proj> \
  --code 'UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation()' --json

# 4) Settled 다시 대기 (mtime 갱신 확인)
stat -f "%Sm" Library/ScriptAssemblies/Assembly-CSharp-Editor.dll
# 갱신됐으면 새 어셈블리

# 5) Setup 메서드 호출 (이제 새 코드)
unityctl exec --project <proj> \
  --code 'URHYNIX.ControlRoom.Editor.CameraStreamSetup.Setup()' --json

# 6) Play 재시작
unityctl play start --project <proj> --json
```

> 📌 **함정 #17 + #18은 unityctl 자동화 시 반드시 같이 발생함**: 새 .cs 파일을 만들면 (#17) + Play 중이면 (#18) 컴파일 + 적용 모두 안 됨. asset import → play stop → RequestScriptCompilation → exec → play start 5단계 표준.

## 검증 매트릭스

| 항목 | 결과 |
|---|---|
| 코드 컴파일 (error CS) | ✅ 0건 (Assembly-CSharp.dll/Assembly-CSharp-Editor.dll 11:04:47 갱신) |
| TopicRegistry meta 생성 | ✅ guid `558cbbd9ed5ac4792b3e547f61152000` |
| Scene 두 GameObject 박힘 | ✅ `CameraStreamSubscriber_Genji`(컴포넌트 1) + `CameraStreamSubscriber_T1`(컴포넌트 1) |
| Setup batch 로그 | ✅ `[CameraStreamSetup] Scene 저장 완료 — 2개 Subscriber 활성 (Dual)` |
| robot port 10000 LISTEN | ✅ (PID 1481) |
| robot 측 cross-host 토픽 발행 | ✅ 젠지 `ros2 topic list`에 `/tb3_1/camera/color/image_raw/compressed` 정상 |
| robot 측 양 토픽 hz | ✅ `/tb3_2` 29.9~30.0Hz, `/tb3_1` 31.0Hz |
| 사용자 시각 확인 (양 패널 토글) | ✅ "딜레이없이 전환잘됨 실시간표시됨" |

## 사용자 결정 분기 (Plan에서 받은 1개)

- 모델 결정: **B** (동시 구독 + display 토글, 0ms 즉시 전환, 스피너 불필요)

## 측정값 (재현)

| 측정 | 값 |
|---|---|
| Mac↔젠지 ping (LAN) | 22ms 평균 (10~35) |
| Mac↔티원 ping | 53ms 평균 (17~88, Wi-Fi 변동) |
| 젠지 `/tb3_2` compressed hz | 29.9~30.0 |
| 티원 `/tb3_1` compressed hz (젠지에서 측정) | 31.0 |
| TCP Send-Q (robot → Mac) | 77,106 bytes (영상 backlog) |
| 토글 전환 지연 (사용자 실측) | 0ms (체감 즉시) |

## 후속 진입 (Phase 2.7-dual → 2.8)

1. **티원 `loginctl enable-linger t1` 영구화** — 현재 `Linger=no`라 ssh 끊김 시 realsense2_camera 죽음 (함정 #13 미적용). sudo 1회 필요.
2. **두 함정(#17/#18) 스킬 박기** — `unity-camera-panel` + `robot-camera-bringup` 양쪽.
3. **Phase 2.8 Gemma 4 12B 통합** — 로그 패널 회색 ⚪ → 녹색 🟢 토글.
4. **(선택) 영상 동시 표시 모드** — 모델 B는 백엔드 이미 받고 있으므로 향후 PiP/스플릿 화면 만들 때 코드 거의 변경 없음.

## 잡힌 함정 → 스킬 영구 자산화

| 함정 # | 추가 위치 | 비고 |
|---|---|---|
| 17 (.meta 미생성) | `unity-camera-panel` 함정표 + `robot-camera-bringup` 함정표 | Write/외부 에디터 자동화 시 표준 우회 |
| 18 (Play 중 reload 차단) | `unity-camera-panel` 함정표 | unityctl 자동화 표준 5단계 |
| 모델 B 듀얼 패턴 | `unity-camera-panel` "듀얼 카메라 분기" 섹션 | 모든 미래 듀얼/n-카메라 작업 표준 |

## 외부 참조

- `.claude/skills/unity-camera-panel/SKILL.md` — 듀얼 패턴 + 함정 #17/#18 추가
- `.claude/skills/robot-camera-bringup/SKILL.md` — 함정 #17/#18 추가
- `docs/evidence/2026-06-04-controlroom-camera-live-pass.md` — 이전 함정 #13~16 (linger / server.py / open -a / ROS2 define)
- DECISION-LOG 2026-06-05 (본 작업 entry)

## 한줄정리

상단 탭(티원/젠지) 클릭으로 카메라 패널이 **0ms 즉시 전환**되는 모델 B 듀얼 결선 PASS. 산출물: `TopicRegistry.cs`(신규) + `CameraStreamSubscriber.cs` 인스턴스 식별자 + `CameraPanelView.cs` robotId 필터링 + `CameraStreamSetup.cs` 두 Subscriber idempotent batch. UI Contract Lock 침해 0줄. **신규 함정 2종**(#17 `.meta` 미생성 → `unityctl asset import`, #18 Play 중 reload 차단 → play stop → RequestScriptCompilation → exec → play start 5단계) 영구 자산화. **다음**: 티원 linger 영구화 + Phase 2.8 Gemma 4 12B.
