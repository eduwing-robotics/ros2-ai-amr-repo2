# URHYNIX Unity Dashboard

> 두 대의 TurtleBot3와 ROS 2 데이터를 2D·2.5D·3D 공간에서 관제하는 Unity 프로젝트입니다.
> 공개 정본 경로는 `client/UNITY/`이며, 기존 `ControlRoom*` 클래스·씬·namespace는 Unity 직렬화 호환성을 위해 유지합니다.

## 역할 경계

Unity Dashboard는 로봇 상태와 사건을 시각화하고 운영자의 좌표·waypoint·정지 요청을 전달합니다.
AMCL, Nav2 경로 계획, DWB/RPP 경로 추종, costmap과 Collision Monitor 같은 실제 주행 판단은 로봇 측 ROS 2가 담당합니다.

| Unity Dashboard가 담당 | 로봇 측 ROS 2가 담당 |
|---|---|
| 로봇 선택과 endpoint 연결 | 로봇별 ROS domain과 hardware bringup |
| 2D·2.5D·3D 지도와 pose 표시 | AMCL localization과 TF |
| 카메라·LiDAR·환경 센서 표시 | SmacPlanner2D, DWB/RPP와 velocity command |
| 주행 준비·순찰·단발 출동 요청 | Nav2 action 실행과 collision safety |
| 사건·출동·pose 기록 조회 | 센서 취득과 로봇 구동 |
| 명시적으로 표시된 demo scenario | 실제 하드웨어 주행 |

`Assets/Scripts/Simulation/`의 demo 이동과 장면 연출은 실제 주행 알고리즘의 근거로 사용하지 않습니다.

## 환경

| 항목 | 값 |
|---|---|
| Unity | `6000.3.16f1` · Unity 6.3 LTS |
| Render Pipeline | Universal RP `17.0.4` |
| UI | UI Toolkit |
| ROS bridge | ROS-TCP-Connector `v0.7.0` |
| Input | Unity Input System `1.17.0` |
| Point cloud | `jp.keijiro.pcx` commit `ffc3447` |
| Robot domains | Gen.G `tb3_2` = `1`, T1 `tb3_1` = `2` |
| Endpoint port | 로봇별 host의 TCP `10000` |

로봇 IP는 DHCP 환경에서 달라질 수 있습니다. 실행 전
`Assets/Resources/RobotConfig/default_robots.json`의 `hostAddress`와 실제 로봇 주소를 확인하세요.

## 빠른 시작

1. Unity Hub에서 `6000.3.16f1`을 설치합니다.
2. **Add Project**로 저장소의 `client/UNITY/`를 선택합니다.
3. 첫 import와 package restore가 끝날 때까지 기다립니다.
4. `Assets/Resources/RobotConfig/default_robots.json`에서 로봇 주소를 확인합니다.
5. `Assets/Resources/RosConfig/ros_endpoint.json`에서 시작 로봇을 선택합니다.
6. `Assets/Scenes/ControlRoomMain.unity`를 열고 Play합니다.

실제 주행 전에는 한 화면만 command owner로 선택하고, 배터리·비상정지·주변 장애물·robot ID를 확인하세요.

## 현재 화면과 데이터 경로

```text
client/UNITY/
├── Assets/
│   ├── Scenes/                    # ControlRoomMain, Demo
│   ├── Scripts/
│   │   ├── App/                   # 앱 상태·연결·이벤트 조립
│   │   ├── Ros/                   # 로봇별 pub/sub와 topic SSOT
│   │   ├── Map/                   # 2D·2.5D·3D 지도와 좌표 변환
│   │   ├── UI/                    # UI Toolkit view와 interaction
│   │   ├── Database/              # Supabase read·제한 write
│   │   └── Simulation/            # demo 전용, 실주행 근거 아님
│   ├── Resources/                 # robot·sensor·situation·ROS config
│   ├── StreamingAssets/Maps/      # 공개 지도 슬롯과 preset
│   ├── UI/                        # UXML·USS·design token
│   └── Tests/EditMode/            # 최소 smoke tests
├── Packages/manifest.json
├── ProjectSettings/
└── README.md
```

주요 데이터 흐름:

```text
Unity UI
  ├─ command topic ──> robot-side bridge ──> Nav2
  ├─ ROS-TCP <──────── pose / camera / LiDAR / sensor
  └─ Supabase <─────── session / event / dispatch / pose records
```

## 설정 정본

| 설정 | 파일 |
|---|---|
| 로봇 ID·역할·주소·카메라/pose topic | `Assets/Resources/RobotConfig/default_robots.json` |
| 시작 endpoint 선택 | `Assets/Resources/RosConfig/ros_endpoint.json` |
| 센서 topic | `Assets/Resources/SensorConfig/default_sensors.json` |
| 상황과 demo 여부 | `Assets/Resources/SituationConfig/default_situations.json` |
| ROS topic 이름 | `Assets/Scripts/Ros/TopicRegistry.cs` |
| 맵 이미지·좌표·preset | `Assets/StreamingAssets/Maps/` |

토픽이나 주소를 C# 여러 곳에 직접 쓰지 말고 위 설정과 `TopicRegistry`를 먼저 수정하세요.

## 시뮬레이션 표기

- `Demo.unity`, `DemoScenarioService`, `FakeSensorData`는 발표·UI 검증용입니다.
- demo 데이터는 실제 센서·실로봇 결과처럼 표시하거나 문서화하지 않습니다.
- 화재·침입 장면의 시각 연출과 실제 로봇 주행 근거를 분리합니다.

## 보안과 운영 안전

- Supabase `service_role` 키를 Unity나 Git에 넣지 않습니다.
- 공개 가능한 anon 설정만 사용하고 로컬 secret 파일은 `.gitignore`로 차단합니다.
- 두 대의 로봇 또는 Web Dashboard가 동시에 명령을 발행하지 않도록 command owner를 하나로 제한합니다.
- 주소, domain, namespace가 불명확하면 주행 명령을 보내지 않습니다.

## 검증

저장소 루트에서:

```bash
python3 -m py_compile \
  src/urhynix_slam/make_pretty_map_slot.py \
  src/urhynix_slam/pgm_to_map_slot.py

rg -n 'client/ControlRoom|unity/ControlRoom' . \
  --glob '!client/UNITY/README.md' \
  --glob '!client/UNITY/BRANCH-AUDIT.md'
git diff --check
```

Unity Editor가 설치된 환경에서는 프로젝트를 연 뒤 compile error가 없는지 확인하고 EditMode smoke를 실행하세요.

## 브랜치 감사

Unity 프로젝트의 브랜치별 중복·고유 변경과 삭제 판정은 [`BRANCH-AUDIT.md`](./BRANCH-AUDIT.md)에 기록했습니다.
