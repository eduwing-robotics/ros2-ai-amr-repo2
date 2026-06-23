# Unity Control Room Conversion Plan

> 변경 목적: Gemini 단일 HTML 관제 화면(`robot_control_system.html`)을 Unity C# 관제 앱으로 전환하기 위한 정본 계획을 고정한다.
> 작성일: 2026-06-02
> Change Class: `unity-ui-surface`, `robot-runtime`, `design-token`, `asset-generation`, `ros-contract`, `db-contract`

## 1. 결론

- UI는 **Unity UI Toolkit**을 사용한다.
- 화면 구조는 `UXML + USS + C# Binder`로 나눈다.
- 디자인 토큰은 `ControlRoomTokens.uss`와 `UiTokens.cs` 양쪽에 둔다.
- SVG는 사용하지 않고, 모든 아이콘은 **PNG**로 통일한다.
- 일반 UI 아이콘은 단순 PNG 세트로 관리하고, 로봇/경보/보호대상처럼 시연 인상이 중요한 아이콘은 Imagen 생성 후 리사이징한다.
- 3D 화면은 공식 ROBOTIS TurtleBot3 `jazzy` 브랜치의 `turtlebot3_description` URDF/mesh를 Unity URDF Importer로 가져와 prefab으로 고정한다.
- 로봇/센서/기능은 하드코딩하지 않고 `Config + Registry + Interface` 구조로 확장한다.
- Unity는 관제/시각화/명령 요청 UI이며, 실제 주행 안전 판단의 진실값은 ROS/Nav2에 둔다.
- Unity 클라이언트에는 Supabase `service_role` 키를 넣지 않는다. 쓰기 작업은 robot-side DB writer, backend proxy, 또는 RLS가 허용된 제한 권한 경로만 사용한다.

## 2. 외부 근거

- ROBOTIS TurtleBot3 URDF (`jazzy`): <https://github.com/ROBOTIS-GIT/turtlebot3/tree/jazzy/turtlebot3_description/urdf>
- ROBOTIS TurtleBot3 meshes (`jazzy`): <https://github.com/ROBOTIS-GIT/turtlebot3/tree/jazzy/turtlebot3_description/meshes>
- ROBOTIS TurtleBot3 Simulation e-Manual: <https://emanual.robotis.com/docs/en/platform/turtlebot3/simulation/>
- Unity URDF Importer: <https://github.com/Unity-Technologies/URDF-Importer>

## 3. HTML에서 Unity로 옮길 화면

| HTML 영역 | Unity 담당 | 설명 |
|---|---|---|
| Top Header | `TopBarView` + `RobotTabView` + `PowerButtonView` | 로고, 로봇 탭, 시스템 상태, 시계, 경보, 전원 버튼 |
| 위험상황 테스트 제어 | `ScenarioPanelView` | 화재, 침입, 소리, 도난 데모 트리거 |
| 동작 제어 | `MovePanelView` | 수동 조작, 순회 시작/정지 |
| 모드 설정 | `ModePanelView` | 자동/수동 전환 |
| 동작 특수 모드 | `FeatureToggleListView` | 스캔, 가속, SLAM, 카메라 등 기능 토글 |
| 순회 목록 | `WaypointListView` | waypoint 표시, 순서 조정, 충전소 지정 |
| 2D 맵 canvas | `Map2DView` | HTML canvas 대체 |
| 3D 맵 | `Map3DView` | Unity scene object와 imported TurtleBot prefab 표시 |
| 카메라 피드 | `CameraPanelView` | ROS compressed image topic 표시 |
| 이벤트 로그 | `LogPanelView` | 이벤트/명령/DB 저장 로그 |
| 원격 상태 계측 | `TelemetryPanelView` + `SensorCardListView` | 배터리(Telemetry) + 가스/소리/조도/PIR/화재 센서 5종(SensorCardList) |
| 하드웨어 사양 | `HardwarePanelView` | 모델, IP, firmware, role |
| 보호대상 목록 | `ProtectedTargetView` | 액자/작품/중요품 목록 + 상태 배지 (safe/check/missing). Phase 2.5 신설. 상세 구조는 §10 참고 |
| 관제 옵션 토글 | `FeatureToggleListView` | 기능 목록을 config 기반 자동 생성 |
| 경보 팝업 | `AlertPopupView` | 위험 이벤트 발생 시 modal alert |

## 4. 최종 폴더 트리

```text
unity-src/Assets/ControlRoom
├── Scenes
│   └── ControlRoomMain.unity                  # 관제 메인 씬
│
├── UI
│   ├── ControlRoomMain.uxml                   # 전체 화면 레이아웃
│   ├── ControlRoomStyle.uss                   # 화면 스타일
│   ├── ControlRoomTokens.uss                  # 색상/간격/폰트/상태 토큰
│   └── Parts
│       ├── TopBar.uxml                        # 상단바, 로봇 탭, 시간, 경보, 전원 버튼
│       ├── LeftControlPanel.uxml              # 조작, 순회, 시나리오 버튼
│       ├── MapPanel.uxml                      # 2D/3D 전환, 맵 상태 표시
│       ├── CameraAndLogPanel.uxml             # 카메라와 이벤트 로그
│       └── RightStatusPanel.uxml              # 배터리, 센서, 기능 토글, 장치 정보
│
├── Scripts
│   ├── App
│   │   ├── ControlRoomApp.cs                  # 앱 시작점
│   │   ├── ControlRoomState.cs                # 선택 로봇, 화면 모드, 세션 상태
│   │   ├── ControlRoomEvents.cs               # UI/ROS/DB 이벤트 연결
│   │   └── ViewMode.cs                        # TwoD, ThreeD 전환값
│   │
│   ├── Data
│   │   ├── RobotInfo.cs                       # 로봇 ID, 이름, 모델, IP, 역할, 토픽
│   │   ├── RobotLiveState.cs                  # 위치, 배터리, 모드, 연결 상태
│   │   ├── RobotPowerState.cs                 # online, standby, shutdown, error
│   │   ├── RobotFeatureInfo.cs                # 자율주행, SLAM, 카메라 같은 기능 정의
│   │   ├── SensorInfo.cs                      # 센서 이름, 타입, 단위, 토픽
│   │   ├── WaypointInfo.cs                    # 순회 지점
│   │   ├── BlockedAreaInfo.cs                 # 차단 구역
│   │   ├── ProtectedTargetInfo.cs             # 지켜야 할 대상, 액자/작품/중요물품
│   │   ├── EventInfo.cs                       # 화재, 침입, 소음, 도난 이벤트
│   │   ├── DispatchInfo.cs                    # 출동 명령과 도착 기록
│   │   └── CameraInfo.cs                      # 카메라 라벨, 토픽, 해상도
│   │
│   ├── UI
│   │   ├── ControlRoomBinder.cs               # UXML과 C# 상태 연결
│   │   ├── TopBarView.cs                      # 상단바 표시와 버튼 처리
│   │   ├── RobotTabView.cs                    # 로봇 탭 자동 생성
│   │   ├── PowerButtonView.cs                 # 로봇 ON/OFF/대기 버튼
│   │   ├── ScenarioPanelView.cs               # 위험상황 테스트 버튼 처리
│   │   ├── MovePanelView.cs                   # 수동 조종, 순회 시작/정지 버튼 처리
│   │   ├── ModePanelView.cs                   # 자동/수동/스캔/가속 모드 처리
│   │   ├── FeatureToggleListView.cs           # 기능 토글 자동 생성
│   │   ├── SensorCardListView.cs              # 센서 카드 자동 생성
│   │   ├── WaypointListView.cs                # 순회 목록 표시와 편집
│   │   ├── ProtectedTargetView.cs             # 보호대상 목록/상태 표시
│   │   ├── MapPanelView.cs                    # 맵 UI와 2D/3D 버튼 처리
│   │   ├── CameraPanelView.cs                 # 카메라 화면과 FEED ON/OFF 처리
│   │   ├── LogPanelView.cs                    # 이벤트 로그 표시, 삭제, 내보내기
│   │   ├── TelemetryPanelView.cs              # 배터리, 가스, 소음, 조도 표시
│   │   ├── HardwarePanelView.cs               # 로봇 모델, IP, 펌웨어, 장치 정보 표시
│   │   └── AlertPopupView.cs                  # 위험 경보 팝업
│   │
│   ├── Map
│   │   ├── Map2DView.cs                       # HTML canvas를 대체하는 2D 맵
│   │   ├── Map3DView.cs                       # Unity 3D 로봇/공간 맵 표시
│   │   ├── MapViewSwitcher.cs                 # 2D/3D 버튼 전환 담당
│   │   ├── MapCameraController.cs             # 줌, 팬, 카메라 시점 제어
│   │   ├── Robot3DSpawner.cs                  # URDF import prefab 로봇 생성
│   │   ├── ProtectedTargetMarker.cs           # 보호대상 2D/3D 마커
│   │   ├── WaypointDrawer.cs                  # 순회 지점과 연결선 렌더링
│   │   ├── RobotMarkerDrawer.cs               # 로봇 위치 마커 렌더링
│   │   ├── BlockedAreaDrawer.cs               # 차단 구역 렌더링과 편집
│   │   └── PathFinder.cs                      # A* 우회 경로 계산
│   │
│   ├── Robot
│   │   ├── RobotManager.cs                    # 여러 로봇 통합 관리
│   │   ├── RobotSelector.cs                   # 현재 선택 로봇 변경
│   │   ├── RobotCommandService.cs             # 이동/정지/순회 명령 공통 서비스
│   │   ├── RobotPowerService.cs               # 대기, 재시작, 종료 요청
│   │   ├── PatrolService.cs                   # 자동 순회 시작/정지
│   │   ├── ManualMoveService.cs               # 수동 이동 명령
│   │   └── BatteryService.cs                  # 배터리 부족, 충전 복귀 로직
│   │
│   ├── Features
│   │   ├── IRobotFeature.cs                   # 기능 추가용 공통 인터페이스
│   │   ├── FeatureRegistry.cs                 # 기능 등록소
│   │   ├── AutoDriveFeature.cs                # 자율주행 기능
│   │   ├── SlamFeature.cs                     # SLAM 기능
│   │   ├── ScanFeature.cs                     # 360도 스캔 기능
│   │   ├── CameraFeature.cs                   # 카메라 기능
│   │   └── TurboFeature.cs                    # 가속 모드 기능
│   │
│   ├── Sensors
│   │   ├── ISensorModule.cs                   # 센서 추가용 공통 인터페이스
│   │   ├── SensorRegistry.cs                  # 센서 등록소
│   │   ├── BatterySensor.cs                   # 배터리 센서
│   │   ├── GasSensor.cs                       # 가스 센서
│   │   ├── SoundSensor.cs                     # 소리 센서
│   │   ├── LightSensor.cs                     # 조도 센서
│   │   ├── PirSensor.cs                       # PIR 인체 감지 센서
│   │   └── FireSensor.cs                      # 화재/불꽃 센서
│   │
│   ├── Ros
│   │   ├── RosConnectionService.cs            # ROS-TCP-Connector 연결 관리
│   │   ├── TopicRegistry.cs                   # 토픽 이름 등록소
│   │   ├── RobotPoseSubscriber.cs             # /tb3_*/pose 구독
│   │   ├── BatterySubscriber.cs               # /battery_state 구독
│   │   ├── SensorSubscriber.cs                # 센서 토픽 구독
│   │   ├── SecurityEventSubscriber.cs         # /security/event 구독
│   │   ├── DispatchPublisher.cs               # /security/dispatch 발행
│   │   ├── PowerCommandPublisher.cs           # 정지/대기/종료 요청 발행
│   │   └── CameraStreamSubscriber.cs          # 카메라 이미지 토픽 구독
│   │
│   ├── Database
│   │   ├── SupabaseClient.cs                  # 제한 권한 Supabase REST 또는 backend proxy 클라이언트
│   │   ├── RobotConfigRepository.cs           # 로봇/기능/센서 설정 조회
│   │   ├── ProtectedTargetRepository.cs       # 보호대상 저장/조회
│   │   ├── SessionRepository.cs               # session_meta 저장/조회
│   │   ├── EventRepository.cs                 # events 저장/조회
│   │   ├── DispatchRepository.cs              # dispatches 저장/조회
│   │   └── CameraRepository.cs                # camera_captures 저장/조회
│   │
│   ├── Simulation
│   │   ├── DemoScenarioService.cs             # HTML의 화재/침입/소리/도난 데모 로직
│   │   ├── FakeRobotData.cs                   # 실제 로봇 없을 때 쓰는 임시 로봇 데이터
│   │   └── FakeSensorData.cs                  # 실제 센서 없을 때 쓰는 임시 센서값
│   │
│   └── Design
│       ├── UiTokens.cs                        # C#에서 쓰는 색상/간격/상태 이름
│       └── IconNames.cs                       # PNG 아이콘 이름 상수
│
├── Robots
│   ├── UrdfSource
│   │   └── turtlebot3_description             # ROBOTIS 공식 URDF/mesh 원본
│   ├── ImportedPrefabs
│   │   ├── TurtleBot3Burger.prefab            # Burger URDF import 결과
│   │   └── TurtleBot3WafflePi.prefab          # Waffle Pi URDF import 결과
│   └── RobotModelMap.asset                    # robot_id와 3D prefab 연결
│
├── Resources
│   ├── RobotConfig
│   │   └── default_robots.json                # 로봇 목록, 이름, 역할, 토픽 설정
│   ├── FeatureConfig
│   │   └── default_features.json              # 기능 목록과 UI 표시 규칙
│   ├── SensorConfig
│   │   └── default_sensors.json               # 센서 목록과 토픽/단위 설정
│   └── MapConfig
│       └── office_base_map.json               # 맵, 웨이포인트, 차단구역, 보호대상 위치
│
└── Art
    └── IconsPng
        ├── Common
        │   ├── alert_128.png                  # 경보
        │   ├── camera_128.png                 # 카메라
        │   ├── battery_128.png                # 배터리
        │   ├── power_on_128.png               # 전원 켜짐
        │   ├── power_off_128.png              # 전원 꺼짐
        │   ├── map_2d_128.png                 # 2D 버튼
        │   └── map_3d_128.png                 # 3D 버튼
        ├── Robot
        │   ├── turtlebot_badge_256.png        # 터틀봇 배지
        │   └── robot_standby_256.png          # 대기 로봇
        ├── Sensor
        │   ├── gas_128.png                    # 가스
        │   ├── sound_128.png                  # 소리
        │   ├── light_128.png                  # 조도
        │   ├── pir_128.png                    # 인체 감지
        │   └── fire_128.png                   # 화재
        └── Target
            ├── protected_frame_256.png        # 지켜야 할 액자
            ├── protected_art_256.png          # 지켜야 할 작품
            └── protected_object_256.png       # 지켜야 할 중요 물품
```

## 5. 하드코딩 제거 계획

| 기존 HTML 하드코딩 | 새 위치 | 설명 |
|---|---|---|
| `robot1`, `robot2` | `RobotInfo.robotId` | DB/ROS 기준은 `tb3_1`, `tb3_2` |
| `T1`, `Gen.G` | `RobotInfo.displayName` | UI 별명은 설정값 |
| IP 주소 | `RobotInfo.hostAddress` | mDNS 우선, IP는 fallback |
| camera URL | `CameraInfo.topicName` | ROS compressed image topic 우선 |
| waypoint 배열 | `office_base_map.json` 또는 Supabase | 순회 지점 설정 |
| blockedAreas 배열 | `office_base_map.json` 또는 Supabase | 차단구역 설정 |
| sensor values | ROS topic 또는 fake data | 실제/시뮬 소스 분리 |
| scenario state | `DemoScenarioService` | 데모용만 별도 보관 |
| icon SVG | `Art/IconsPng` | PNG만 사용 |

## 6. 3D TurtleBot 적용 계획

1. `unity-src/Assets/ControlRoom/Robots/UrdfSource/turtlebot3_description`에 공식 ROBOTIS `jazzy` 브랜치의 `turtlebot3_description`을 가져온다.
2. Unity URDF Importer를 설치한다.
3. `turtlebot3_burger.urdf`와 `turtlebot3_waffle_pi.urdf`를 import한다.
4. import 결과 prefab을 `Robots/ImportedPrefabs`에 둔다.
5. `RobotModelMap.asset`에서 `tb3_1`, `tb3_2`와 prefab을 연결한다.
6. `Robot3DSpawner`가 config를 읽어 3D 화면에 로봇을 생성한다.
7. `RobotPoseSubscriber`가 ROS pose를 받아 prefab 위치/방향을 갱신한다.
8. 사용한 ROBOTIS repository URL, branch, commit hash를 evidence 또는 `RobotModelMap.asset` 메모에 남긴다.

주의:
- Unity import용 URDF/mesh는 원본과 import 결과를 분리한다.
- 실제 센서/카메라 장착물은 URDF 원본을 직접 고치기보다 Unity child object로 올린 뒤, 최종 확정 시 URDF patch 여부를 결정한다.
- "최신 URDF"는 매번 floating으로 쓰지 않는다. 한 번 가져온 뒤 commit hash를 잠가서 재현성을 확보한다.

## 7. 로봇 ON/OFF 가능 범위

Unity에서 가능한 것:
- 운행 활성/비활성
- 자율주행 기능 ON/OFF
- 센서 구독 ON/OFF
- `/cmd_vel` zero publish를 통한 즉시 정지
- robot-side management agent가 있을 때 ROS 노드 start/stop 요청
- robot-side management agent와 승인 흐름이 있을 때 robot PC 재시작/종료 요청
- 안전 대기 모드 전환

Unity만으로 불가능한 것:
- 완전히 전원이 꺼진 TurtleBot을 다시 켜는 것
- robot-side agent 없이 임의의 ROS 프로세스를 직접 시작/중지하는 것

완전 전원 ON까지 필요할 때 필요한 추가 장치:
- 스마트 플러그
- 릴레이 보드
- 별도 MCU 전원 컨트롤러
- 항상 켜져 있는 관리용 전원 장치

## 8. 기능 추가 아키텍처

기능은 `IRobotFeature`와 `FeatureRegistry`로 관리한다.

```text
default_features.json
  -> FeatureRegistry
  -> IRobotFeature 구현체
  -> FeatureToggleListView 자동 UI 생성
  -> ROS topic/service/action 또는 local simulation 실행
```

새 기능 추가 절차:

1. `default_features.json`에 기능 ID, 표시 이름, 아이콘, 기본 상태, 연결 명령을 추가한다.
2. 필요한 경우 `IRobotFeature` 구현체를 만든다.
3. `FeatureRegistry`에 등록한다.
4. UI는 `FeatureToggleListView`가 자동 생성한다.
5. ROS 명령이 필요하면 `RobotCommandService` 또는 전용 publisher를 연결한다.

## 9. 센서 추가 아키텍처

센서는 `ISensorModule`과 `SensorRegistry`로 관리한다.

```text
default_sensors.json
  -> SensorRegistry
  -> ISensorModule 구현체
  -> SensorCardListView 자동 UI 생성
  -> SensorSubscriber topic 연결
  -> EventRepository 저장
```

새 센서 추가 절차:

1. `default_sensors.json`에 센서 ID, 표시 이름, 단위, 토픽, 경고 임계값, 아이콘을 추가한다.
2. 단순 수치 센서는 generic sensor renderer로 처리한다.
3. 특수 로직이 있으면 `ISensorModule` 구현체를 만든다.
4. `SensorRegistry`에 등록한다.
5. UI 카드는 `SensorCardListView`가 자동 생성한다.
6. 위험 이벤트로 승격할 조건은 `SecurityEventSubscriber` 또는 sensor module 안에 둔다.

## 10. 보호대상 구조

보호대상은 작품/액자/중요물품을 통합해서 `ProtectedTargetInfo`로 다룬다.

필드:
- `targetId`
- `displayName`
- `targetType`: `frame`, `art`, `object`
- `x`, `y`, `theta`
- `status`: `safe`, `check_needed`, `missing`, `unknown`
- `iconName`
- `expectedMarker`
- `lastSeenAt`

UI 표시:
- 2D 맵: PNG marker
- 3D 맵: billboard marker + optional small pedestal/outline
- 오른쪽 패널: 보호대상 목록과 상태 배지
- 이벤트 로그: `asset_seen`, `asset_missing`, `unverified`

## 11. PNG 아이콘 생성 계획

먼저 생성할 Imagen 계열 PNG:

| 파일 | 용도 | 스타일 |
|---|---|---|
| `turtlebot_badge_512.png` | 로봇 대표 배지 | 깨끗한 3D 아이콘, 흰/남색/민트 포인트 |
| `fire_alert_512.png` | 화재 경보 | 강한 경보성, 붉은/주황, 단순 형태 |
| `protected_frame_512.png` | 지켜야 할 액자 | 박물관 액자, 보안 실드 느낌 |
| `protected_art_512.png` | 지켜야 할 작품 | 전시 작품, 보안 표시 |
| `protected_object_512.png` | 중요 물품 | 진열대 위 중요 물품, 보호 마커 |
| `sensor_badge_512.png` | 센서 공통 | 센서/신호/파형 느낌 |

리사이징 규칙:
- 원본: `512x512`
- UI 아이콘: `256`, `128`, `64`
- 파일명은 snake_case를 사용한다.
- Unity import 설정은 `Texture Type = Sprite (2D and UI)`로 맞춘다.

## 12. 스킬/하네스 사용 계획

이 전환 작업은 화면 이식, Unity 런타임, ROS/DB 계약, 카메라/SLAM 실기 검증이 섞여 있다. 따라서 매 단계마다 스킬과 하네스를 명시적으로 고른다.

### 12.1 현재 URHYNIX 로컬 스킬 목록

| 스킬 | 언제 사용 | 어디서 사용 |
|---|---|---|
| `task-intake-router` | 새 요청이 들어와 작업 성격을 먼저 분류해야 할 때 | 모든 큰 작업 시작 전 |
| `project-planning` | 파일 구조, phase, 검증 계약을 잠글 때 | 본 전환 계획, phase 재설계 |
| `big-task` | 여러 phase로 쪼개야 하는 구현 작업일 때 | HTML → Unity 전체 전환, 2D/3D/ROS/DB 통합 |
| `design-to-code` | 화면 설계나 리디자인을 코드 구조로 바꿀 때 | UI Toolkit skeleton, UXML/USS/패널 분해 |
| `socratic-review` | 큰 설계 결정을 구현 전에 검토할 때 | UI Toolkit vs uGUI, PNG 정책, 전원 제어 범위 결정 |
| `change-impact-map` | UI/DB/ROS/설정 변경 영향 범위를 먼저 봐야 할 때 | 로봇 config, 센서 config, ROS topic, Supabase schema 변경 전 |
| `doc-sync` | 코드 변경 뒤 어떤 문서를 같이 고칠지 정할 때 | 구현 후 `ARCHITECTURE`, `PROJECT-STATUS`, `SCHEMA`, 본 문서 동기화 |
| `evidence-review` | 완료 선언 전에 검증 근거를 정리할 때 | 각 phase 종료 전 |
| `api-contract-guard` | DB 테이블, ROS topic, env key, 외부 package 이름을 코드에 넣기 전 | Supabase/ROS/URDF/Unity package 계약 고정 |
| `migration-manifest` | 기존 HTML 기능을 Unity 기능으로 빠짐없이 이전해야 할 때 | HTML 화면/함수/상태 → Unity parity 추적 |
| `parallel-qa` | 데모 전 넓은 회귀 검증을 나눠 돌릴 때 | 2D/3D/카메라/ROS/DB/전원 버튼 QA |
| `failure-mode-playbooks` | 검증 누락, 문서 드리프트, phase 과대화가 생겼을 때 | 작업이 꼬였을 때 복구 |
| `session-handoff` | 세션을 멈추거나 다음 작업자에게 넘길 때 | 하루 작업 종료, 다음 진입 캡슐 |
| `session-retro` | 반복 가능한 성공/실패 패턴을 자산화할 때 | 카메라, URDF, Unity batch, ROS 문제 해결 후 |
| `secret-scan` | 커밋/공유 전에 키/토큰 노출을 확인할 때 | Supabase/Jira/ROS env 문서나 config 변경 후 |
| `ssot-board-sync` | SSOT 변경을 dev-plan HTML 보드와 번들에 동기화할 때 | 주요 결정이나 계획 변경 후 |
| `decision-broadcast` | 결정사항을 DECISION-LOG/SSOT/Jira/Slack에 전파해야 할 때 | UI 라이브러리, URDF, 전원 정책 같은 결정 확정 시 |
| `stack-drift-guard` | 프로젝트가 원래 Unity/Robot/C# 프로필에서 벗어났는지 볼 때 | 웹/Unity/ROS 경계가 흐려질 때 |
| `code-review-graph-ops` | cross-cutting 변경 범위를 좁혀야 할 때 | 대량 C#/문서 변경 리뷰 전 |
| `arduino-flash` | Arduino 센서 스케치 업로드와 시리얼 검증이 필요할 때 | PIR/LDR/소리/불꽃 센서 변경 |
| `slam-nav2-arena-survey` | TurtleBot SLAM/Nav2/Unity map import 전체 흐름을 돌릴 때 | 경기장/박물관 맵 재측정 |
| `map-quality-eval` | SLAM 산출 맵 품질을 정량 평가할 때 | `pgm/yaml` 산출 직후 |
| `ip-drift-resync` | DHCP IP 변경으로 Unity/SSH 동기화가 필요할 때 | 매 세션 첫 5분 또는 IP 변경 발견 시 |
| `robot-camera-bringup` | 두 로봇 카메라와 ros_tcp_endpoint를 살릴 때 | 매 세션 카메라 검증 시작 |
| `unity-camera-panel` | Unity에 ROS2 카메라 패널을 추가하거나 갱신할 때 | 카메라 UI 패널 구현/확장 |

주의:
- `edge-hardening`, `supabase-mcp`는 현재 URHYNIX가 아니라 TaillogToss 설명을 가진 스킬이므로 본 작업 기본 라우팅에서는 제외한다.
- Codex 전역 스킬 `urhynix-turtlebot-unity-ros2-success-pattern`은 TurtleBot/ROS2/RViz/Unity smoke 검증을 재현하거나 설명할 때 사용한다.
- Codex 전역 스킬 `imagegen`은 PNG 아이콘/보호대상/시각 자산 생성 시 사용한다.

### 12.2 Claude 운영 자산 목록

Claude 쪽 자산 위치: `/Users/family/jason/URHYNIX/.claude`

| 자산 | 현재 목록 | 언제 사용 | 본 전환 작업에서의 위치 |
|---|---|---|---|
| Commands | `/intake`, `/impact-map`, `/profile-recommend`, `/evidence-review`, `/handoff`, `/doc-update`, `/self-review`, `/bootstrap-project` | Claude에서 수동 작업 절차를 바로 호출할 때 | 새 phase 시작은 `/intake`, cross-cutting 변경 전 `/impact-map`, 완료 전 `/evidence-review`, 종료 전 `/handoff` |
| Agents | `doc-audit`, `doc-writer` | 문서 정합성 감사 또는 정형 문서 반영을 분리할 때 | 주 1회/PR 전 `doc-audit`, 결정된 사실의 단순 문서 반영은 `doc-writer` |
| Automations | `daily-recap`, `skill-harvest`, `urhynix-morning-orchestrator`, `urhynix-nightly-orchestrator` | 반복 점검/요약/스킬 후보 수확 | 매일 아침 drift/secret/Jira 점검, 매일 밤 recap, 주 1회 skill harvest |
| Hooks | `doc-drift-reminder.sh` | Claude가 Write/Edit 후 문서 드리프트를 상기할 때 | Unity C# 또는 문서 편집 후 `PROJECT-STATUS`, `DECISION-LOG` 동기화 리마인더 |
| Settings | `settings.json`, `settings.local.json` | Claude Code hook/권한 설정 | `PostToolUse` Write/Edit hook으로 doc drift reminder 실행 |

Claude command 사용 규칙:

| command | 실행 시점 | 산출물 |
|---|---|---|
| `/intake` | 새 요청을 받자마자 | 요청 분류, 다음 스킬 1~2개, `PROJECT-PLAN` intake 갱신 |
| `/impact-map` | UI/DB/ROS/설정이 여러 파일에 번질 때 | 영향 경로, companion docs, verify matrix |
| `/doc-update` | 구현이 끝났거나 구조 결정이 바뀐 뒤 | change class별 문서 갱신 |
| `/evidence-review` | 완료 선언 직전 | 실제 verify 명령, residual risk, release verdict |
| `/handoff` | 세션 종료나 작업 인계 전 | 다음 entrypoint, blocker, first verify |
| `/self-review` | 작업 종료 직전 | scope creep, 검증, 문서 동기화 자가 점검 |
| `/profile-recommend` | stack 경계가 흔들릴 때 | Unity/Robot/C# 프로필 유지 여부 |
| `/bootstrap-project` | 새 하위 프로젝트나 독립 skeleton 생성 시 | AGENTS/CLAUDE/초기 문서/첫 검증 |

Claude agent 사용 규칙:

| agent | 실행 시점 | 주의 |
|---|---|---|
| `doc-audit` | 큰 결정 후, PR 전, 월요일 주간 점검 | 문서를 수정하지 않고 드리프트만 보고한다 |
| `doc-writer` | parent가 결정한 사실을 정해진 파일에 넣을 때 | 새 설계나 결정은 만들지 않는다 |

Claude automation 사용 규칙:

| automation | 상태 | 실행 시점 | 목적 |
|---|---|---|---|
| `urhynix-morning-orchestrator` | planned | 평일 08:00 KST | 전일 drift, doc-audit(월요일), secret scan, Jira snapshot |
| `urhynix-nightly-orchestrator` | planned | 평일 22:00 KST | daily recap, daily 폴더 정리, skill harvest, 캐시 정리 |
| `daily-recap` | drafting | 평일 22:00 KST 또는 수동 | Slack 요약 초안/전송 |
| `skill-harvest` | planned | 일요일 22:00 KST | 반복 수동 작업을 스킬/서브에이전트 후보로 제안 |

Claude 템플릿 대비 차이:

| 템플릿에 있고 URHYNIX 로컬에 없는 것 | 처리 |
|---|---|
| `claude-code-health` | 당장 필수는 아니지만, Claude 운영 위생 점검이 필요하면 템플릿에서 이식 후보 |
| `thin-doc-update` | 문서 갱신을 더 가볍게 쪼개고 싶을 때 이식 후보 |

URHYNIX 로컬에 추가로 있는 프로젝트 전용 자산:

| 전용 자산 | 이유 |
|---|---|
| `arduino-flash` | 센서 4종 플래시/시리얼 검증 반복 |
| `robot-camera-bringup` | 젠지 Pi Camera + 티원 D435 + ros_tcp_endpoint 반복 |
| `unity-camera-panel` | Unity 카메라 패널 batch 추가 반복 |
| `slam-nav2-arena-survey` | 경기장/박물관 SLAM/Nav2/Unity import 반복 |
| `map-quality-eval` | SLAM map 품질 정량 판정 반복 |
| `ip-drift-resync` | DHCP IP 변경 대응 반복 |

### 12.3 현재 하네스 목록

하네스 원본 위치: `/Users/family/jason/jason-agent-harness-template/harnesses`

| 하네스 | 상태 | 본 전환 작업에서 사용 여부 | 사용 시점 |
|---|---|---|---|
| `design-to-code` | starter | 사용 | UI Toolkit 화면 구조를 코드 구조로 바꿀 때 |
| `change-class-doc-sync` | starter | 사용 | 구현 후 문서 동기화 기준이 필요할 때 |
| `api-contract-guard` | proven | 사용 | ROS topic, Supabase table, URDF package, env key 고정 전 |
| `migration-manifest` | candidate | 사용 | HTML 기능을 Unity 기능으로 누락 없이 옮길 때 |
| `parallel-qa` | candidate | 사용 | 시연 전 2D/3D/카메라/ROS/DB 회귀 검증 |
| `failure-mode-playbooks` | candidate | 사용 | phase가 커지거나 검증 누락이 생길 때 |
| `session-retro` | starter | 사용 | 검증 성공/실패 패턴을 스킬 후보로 남길 때 |
| `socratic-review` | starter | 사용 | 큰 설계 결정 전 |
| `project-setup` | candidate | 제한 사용 | 새 폴더/진입 문서/초기 검증 루프 만들 때 |
| `autoresearch-loop` | proven | 제한 사용 | 이미 동작하는 카메라/맵/ROS 흐름을 한 가설씩 개선할 때 |
| `claude-code-health` | proven | 제한 사용 | 에이전트 운영/문서 과밀/도구 위생 점검 |
| `media-performance-budget` | candidate | 보류 | 이미지가 많아져 빌드/메모리 문제가 생길 때 |
| `reference-site-style-extraction` | starter | 보류 | 외부 레퍼런스 사이트 스타일 분석이 생길 때 |
| `next-vercel-*`, `post-deploy-seo-submit-monitor`, `conversion-service-site-spec` | mixed | 사용 안 함 | Next/Vercel/웹 배포 전용이라 본 Unity 작업 범위 밖 |

### 12.4 Phase별 사용 순서

| Phase | 사용할 스킬 | 사용할 하네스 | 산출물 |
|---|---|---|---|
| Phase 0. 요청 분류 | `task-intake-router`, `socratic-review` | `socratic-review` | change class, non-goal, 결정 질문 |
| Phase 1. 문서/자산 기준 고정 | `project-planning`, `imagegen`, `decision-broadcast` | `design-to-code`, `change-class-doc-sync` | 본 문서, PNG icon sheet, 결정 로그 |
| Phase 2. HTML 기능 인벤토리 | `migration-manifest`, `change-impact-map` | `migration-manifest` | HTML → Unity parity manifest |
| Phase 3. UI Toolkit skeleton | `design-to-code`, `api-contract-guard` | `design-to-code`, `api-contract-guard` | UXML/USS/Binder, token SSOT |
| Phase 4. 데이터 모델/Registry | `api-contract-guard`, `change-impact-map` | `api-contract-guard` | Robot/Sensor/Feature/Target config |
| Phase 5. 2D 맵 이식 | `big-task`, `migration-manifest` | `migration-manifest` | `Map2DView`, waypoint/block/marker parity |
| Phase 6. 카메라/ROS 패널 | `robot-camera-bringup`, `unity-camera-panel`, `api-contract-guard` | `api-contract-guard` | camera topic smoke, camera UI panel |
| Phase 7. 3D URDF 화면 | `urhynix-turtlebot-unity-ros2-success-pattern`, `api-contract-guard` | `api-contract-guard` | TurtleBot prefab, pose sync |
| Phase 8. SLAM/Nav2 맵 반영 | `slam-nav2-arena-survey`, `map-quality-eval`, `ip-drift-resync` | `failure-mode-playbooks` if blocked | map evidence, Unity import |
| Phase 9. Supabase 저장 | `api-contract-guard`, `secret-scan`, `doc-sync` | `api-contract-guard`, `change-class-doc-sync` | repositories, schema sync, secret check |
| Phase 10. QA/완료 판정 | `parallel-qa`, `evidence-review`, `doc-sync` | `parallel-qa`, `change-class-doc-sync` | PASS/BLOCKED matrix, evidence status |
| Phase 11. 인계/자산화 | `session-handoff`, `session-retro`, `ssot-board-sync` | `session-retro` | HANDOFF, skill 후보, board sync |

### 12.5 작업 장소별 사용 규칙

| 작업 위치 | 우선 스킬/하네스 | 규칙 |
|---|---|---|
| `docs/ref/*` | `project-planning`, `doc-sync`, `ssot-board-sync` | 정본 결정과 계획을 먼저 고정 |
| `unity-src/Assets/ControlRoom/UI` | `design-to-code` | UXML/USS/token 먼저, C# 바인딩은 그 다음 |
| `unity-src/Assets/ControlRoom/Scripts/Data` | `api-contract-guard` | DB/ROS/config 계약값 추정 금지 |
| `unity-src/Assets/ControlRoom/Scripts/Features` | `api-contract-guard`, `change-impact-map` | 새 기능은 `IRobotFeature`와 config에 동시에 등록 |
| `unity-src/Assets/ControlRoom/Scripts/Sensors` | `api-contract-guard`, `arduino-flash` | 새 센서는 `ISensorModule`, topic, 단위, 임계값을 함께 등록 |
| `unity-src/Assets/ControlRoom/Scripts/Ros` | `robot-camera-bringup`, `api-contract-guard` | topic/service/action 이름은 중앙화 |
| `unity-src/Assets/ControlRoom/Scripts/Database` | `api-contract-guard`, `secret-scan` | service_role 키는 Unity 클라이언트에 넣지 않음 |
| `unity-src/Assets/ControlRoom/Robots` | `api-contract-guard`, `urhynix-turtlebot-unity-ros2-success-pattern` | 공식 URDF source와 import prefab 분리 |
| `unity-src/Assets/ControlRoom/Art/IconsPng` | `imagegen`, `design-to-code` | PNG only, 원본/리사이즈/용도 분리 |
| `docs/evidence/*` | `evidence-review`, `map-quality-eval` | 검증 결과는 날짜별 evidence에 남김 |
| `.claude/skills/*` | `session-retro`, `skill-harvest` automation | 반복된 성공 패턴만 스킬로 승격 |

## 13. 구현 단계

### Phase 1. 문서/자산 기준 고정

- 본 문서 확정
- PNG 아이콘 1차 생성
- URDF source 위치 확정
- default config schema 초안 작성

### Phase 2. UI Toolkit 뼈대

- `ControlRoomMain.uxml`
- `ControlRoomStyle.uss`
- `ControlRoomTokens.uss`
- `ControlRoomBinder.cs`
- 2D/3D 전환 버튼 배치

### Phase 2.5. UI Visual Completion (UI Polish First) — 결정일 2026-06-02

> **전략 결정**: UI를 contract로 먼저 100% 잠그고 그 뒤 phase는 안만 채운다. 시각 시연을 빨리 확보 + 기능 phase에서 UI 변경으로 인한 꼬임 방지. fake interaction 깊이 = **알람 popup만** (센서 spike / 로봇 dot animation 등 가짜 동작은 안 함, Phase 3 이후 실 데이터로 자연 동작).

**산출물 — 9개 View 클래스 + UXML/USS 채움**:

- `Scripts/UI/MovePanelView.cs`
- `Scripts/UI/ModePanelView.cs`
- `Scripts/UI/FeatureToggleListView.cs` (정적 UXML 사용, 자동생성은 Phase 3에서)
- `Scripts/UI/WaypointListView.cs` (더미 5개 항목)
- `Scripts/UI/RobotTabView.cs`
- `Scripts/UI/PowerButtonView.cs`
- `Scripts/UI/HardwarePanelView.cs` (선택된 로봇의 더미 IP/모델/펌웨어)
- `Scripts/UI/SensorCardListView.cs` (PIR/화재 카드 추가, 총 5종)
- `Scripts/UI/ProtectedTargetView.cs` (선택)
- UXML 보강: `LeftControlPanel.uxml`(순회 지점 더미 5줄), `RightStatusPanel.uxml`(하드웨어 카드 채움, 센서 5종), `MapPanel.uxml`(placeholder 격자 + 더미 dot/waypoint), `TopBar.uxml`(전원 확인 모달)
- USS 보강: 격자 패턴, dot/waypoint 마커 스타일, 알람 popup polish

**5단계 분해 (3~4일)**:

1. 좌측 패널 View 4개 (0.5일) — Move/Mode/FeatureToggle/Waypoint
2. 상단바·우측 View 4개 (0.5일) — RobotTab/PowerButton/Hardware/SensorCardList
3. 맵 placeholder 시각 완성 (1일) — 격자 + 로봇 dot 2개 + waypoint 3개 + 보호대상 마커
4. 카메라+로그 polish (0.5일) — gradient + 5초 주기 fake log push
5. 시나리오 알람만 (1일) — 시나리오 4 버튼 → 알람 popup만 (센서 spike 등 안 함)

**검증 매트릭스 (시연 가능 판정 10개)**:

1. View 14개 전부 ✅ (⚠️/❌ 0건)
2. 좌측 모든 버튼/토글 클릭 시 active 시각 반응
3. 로봇 탭 (티원/젠지) 전환 시 우측 하드웨어 정보 변경
4. 시나리오 4 버튼 각각 다른 색/메시지의 알람 popup
5. 맵에 로봇 dot 2개 + waypoint 3개 + 보호대상 1~2개 시각 표시
6. 카메라 placeholder 자연스러움 (gradient + 라벨)
7. 로그 5초 주기 fake event 자동 추가 + 스크롤
8. 우측 센서 카드 5종(가스/소음/조도/PIR/화재) 표시
9. 전원 버튼 클릭 시 확인 모달
10. 30분 demo 영상 녹화 시 "진짜 시연 같음"

**원칙 (Phase 3 이후)**: UI Contract Lock — Phase 3~8에서 UXML/USS/View 코드 0줄 수정. 수정 필요해지면 Phase 2.5 누락이므로 그 부분 우선 보완.

### Phase 3. 데이터 모델/Registry

- `RobotInfo`, `SensorInfo`, `RobotFeatureInfo`, `ProtectedTargetInfo`
- `FeatureRegistry`
- `SensorRegistry`
- config JSON loader

### Phase 4. 2D 맵 이식

- `Map2DView`
- waypoint/blocked area/robot marker/protected target marker
- 기존 HTML canvas 로직을 C#로 분리 이식

### Phase 5. ROS 연동

- pose, battery, sensor, event 구독
- dispatch/power command 발행
- camera stream 패널 통합

### Phase 6. 3D 맵

- URDF import prefab 정리
- `Robot3DSpawner`
- pose sync
- 보호대상 3D marker
- 2D/3D 전환 검증

### Phase 7. Supabase 저장

- session/events/dispatches/camera_captures 저장
- 보호대상 확장 테이블은 실제 migration 전까지 config 기반으로 운용

### Phase 8. 검증

- Unity compile check
- Play Mode smoke
- ROS-TCP 연결
- 두 카메라 topic 표시
- 2D/3D 전환
- 로봇 대기/정지/재시작 요청 safety test

## 14. 검증 체크리스트

- `robot_control_system.html`의 주요 화면이 Unity UI에 모두 매핑됐는가
- `T1/Gen.G`가 코드 하드코딩이 아니라 config에서 오는가
- 모든 아이콘이 PNG인가
- SVG 참조가 남지 않았는가
- 2D/3D 전환 버튼이 있는가
- 3D 화면에서 TurtleBot prefab이 pose topic을 따라 움직이는가
- 보호대상 아이콘이 2D/3D 양쪽에 표시되는가
- 새 센서를 JSON + module 추가만으로 붙일 수 있는가
- 새 기능을 JSON + feature 구현체 추가만으로 붙일 수 있는가
- Unity에서 실제 전원 ON을 약속하지 않고 가능한 범위를 명확히 제한했는가

## 15. 다음 액션

1. `default_robots.json`, `default_sensors.json`, `default_features.json`, `office_base_map.json` 초안 작성.
2. HTML → Unity parity manifest 작성.
3. Supabase write path 결정: robot-side DB writer, backend proxy, 제한 RLS 중 하나 선택.
4. UI Toolkit skeleton 생성.
5. URDF source fetch + commit hash 기록 + import 작업 시작.
6. 남은 일반 UI PNG 아이콘 세트 생성: `camera`, `battery`, `power_on`, `power_off`, `map_2d`, `map_3d`, 센서별 아이콘.

## 16. 문서 자기리뷰 기록

작성일: 2026-06-02

### PASS

- HTML 화면 영역이 Unity 담당 view로 모두 매핑되어 있다.
- `T1/Gen.G`, `robot1/robot2`, waypoint, blocked area, camera URL을 config/DB/ROS 기반으로 빼는 방향이 명시되어 있다.
- PNG-only 정책과 보호대상 아이콘 필요성이 문서화되어 있다.
- 2D/3D 전환, TurtleBot URDF import, ROS pose sync 흐름이 분리되어 있다.
- 센서/기능 추가 구조가 `Config + Registry + Interface`로 잡혀 있다.
- URHYNIX 로컬 스킬, Claude commands/agents/automations/hooks, 외부 하네스 사용 시점이 phase별로 명시되어 있다.

### FIXED

- Unity 클라이언트에 Supabase `service_role` 키를 넣을 수 있는 것처럼 보일 여지를 제거했다.
- 로봇 ON/OFF 범위를 더 정확히 제한했다. ROS node start/stop과 robot PC 재시작/종료는 robot-side management agent와 승인 흐름이 있을 때만 가능하다고 명시했다.
- 최신 TurtleBot URDF를 가져온 뒤 branch/commit hash를 고정해야 한다고 명시했다.
- 다음 액션을 현재 상태에 맞게 갱신했다. PNG 1차 생성/저장은 완료된 선행 작업으로 보고, config/parity/URDF 작업을 우선순위로 올렸다.

### 남은 리스크

- `default_robots.json`, `default_sensors.json`, `default_features.json`, `office_base_map.json`의 실제 schema가 아직 없다.
- HTML → Unity parity manifest가 아직 없다.
- URDF Importer 설치 방식과 Unity package version lock이 아직 없다.
- PNG 아이콘은 1차 시트와 일부 개별 아이콘만 생성됐다. 일반 UI 아이콘(`camera`, `battery`, `power_on`, `power_off`, `map_2d`, `map_3d`, 센서별 아이콘)은 추가 생성 또는 수작업 PNG가 필요하다.
- Supabase write path는 robot-side DB writer, backend proxy, 제한 RLS 중 하나를 아직 선택하지 않았다.

### 다음 보강 우선순위

1. HTML → Unity parity manifest 작성.
2. config JSON schema 4종 작성.
3. Supabase write path 결정.
4. URDF source fetch + commit hash 기록.
5. 남은 일반 UI PNG 아이콘 세트 생성.
