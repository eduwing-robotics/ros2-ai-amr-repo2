# URHYNIX ControlRoom (Unity)

> URHYNIX 박물관/미술관 디지털트윈경비로봇 **관제 UI** Unity 프로젝트.
> HTML 관제(`robot_control_system.html`)를 Unity C#로 전환하는 정본 위치.

## 환경

| 항목 | 값 |
|---|---|
| Unity 버전 | **6000.3.16f1** (Unity 6.3 LTS, 2027-12까지 지원) |
| Render Pipeline | Universal RP 17.0.4 |
| UI | UI Toolkit (`com.unity.modules.uielements`) |
| ROS 브리지 | `com.unity.robotics.ros-tcp-connector` v0.7.0 |
| ROS 도메인 | `ROS_DOMAIN_ID=230` (티원/젠지 공통) |
| Supabase | `https://ueupkrxwybuuqxflstvg.supabase.co` |

## 첫 진입 (5분)

1. Unity Hub에서 **6000.3.16f1 설치** (Unity 6.3 LTS).
2. Unity Hub → **Add Project** → 이 폴더 (`unity/ControlRoom`) 선택.
3. 첫 Open 시 Library/ 자동 재생성 (5~10분 — 패키지 fetch + import).
4. 첫 컴파일 에러는 ROS-TCP-Connector git URL이 받아질 때까지 대기 후 자동 해소.

## 폴더 구조

```text
unity/ControlRoom/
├── Assets/
│   ├── Scenes/                          # ControlRoomMain.unity (Phase 2 생성 예정)
│   ├── UI/                              # UXML/USS/Token (Phase 2)
│   ├── Scripts/                         # App/Data/UI/Map/Robot/Features/Sensors/Ros/Database (Phase 3+)
│   ├── Editor/                          # 카메라 패널 batch setup, UXML 자동 생성
│   ├── Art/
│   │   └── IconsPng/                    # PNG 26개 (Common/Robot/Sensor/Target/Generated)
│   ├── Robots/
│   │   ├── UrdfSource/                  # ROBOTIS jazzy turtlebot3_description (Phase 6)
│   │   └── ImportedPrefabs/             # URDF import 결과 prefab (Phase 6)
│   └── Resources/
│       ├── SupabaseConfig.template.asset  # 커밋 OK, anon key 빈 값
│       └── SupabaseConfig.local.asset     # .gitignore 차단, 실제 anon key 박힘
├── Packages/manifest.json
├── ProjectSettings/                     # ProjectVersion.txt = 6000.3.16f1
└── README.md                            # 이 파일
```

## Phase 로드맵

자세한 phase는 `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md` 13절 참조.

| Phase | 산출물 | 상태 |
|---|---|---|
| 0 | 프로젝트 scaffold + 버전 결정 | ✅ 2026-06-02 |
| 1 | URDF Importer Unity 6 호환성 smoke | 다음 진입 |
| 2 | UI Toolkit skeleton (UXML/USS/Binder) | |
| 3 | 데이터 모델/Registry (RobotInfo/SensorInfo/FeatureInfo) | |
| 4 | 2D 맵 이식 (HTML canvas → C#) | |
| 5 | ROS 연동 (카메라 패널은 unity-smoke `CameraStreamPanel.cs` 이관) | |
| 6 | 3D URDF (TurtleBot3 Burger prefab + pose sync) | |
| 7 | Supabase 저장 (`supabase-csharp` + UniTask) | |
| 8 | 검증 (Play Mode + 2D/3D 전환 + 듀얼 카메라) | |

## Supabase 정책 (중요)

- **Unity 클라이언트에 service_role 키 절대 미반입.**
- 로봇 PC(젠지/티원 Python ROS2 노드)가 **주 쓰기 주체** (anon key + RLS).
- Unity는 read + 제한 INSERT(`dispatches`, `session_meta` 등 사람 액션)만.
- 민감 작업(전원 종료 등)은 Supabase Edge Function 호출만.
- anon key는 `Assets/Resources/SupabaseConfig.local.asset`에 박고 `.gitignore`로 차단.

## 카메라 패널 이관

unity-smoke에 검증된 자산을 Phase 5에서 그대로 옮긴다:

| 원본 (unity-smoke) | 이관 위치 (ControlRoom) |
|---|---|
| `Assets/Scripts/CameraStreamPanel.cs` | `Assets/Scripts/Ros/CameraStreamPanel.cs` |
| `Assets/Editor/CameraPanelSetup.cs` | `Assets/Editor/CameraPanelSetup.cs` |
| topic `/tb3_2/camera/image_raw/compressed` | 동일 (젠지 Pi Camera) |
| topic `/tb3_1/camera/color/image_raw/compressed` | 동일 (티원 D435) |

## 관련 SSOT

- `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md` — 13절 phase + 검증 체크리스트
- `docs/status/DECISION-LOG.md` — 2026-06-02 최상단 2건 (버전 결정 + Supabase 정책)
- `.claude/skills/robot-camera-bringup/` — 카메라 트랙 launch 표준
- `.claude/skills/unity-camera-panel/` — Unity 카메라 패널 batch
