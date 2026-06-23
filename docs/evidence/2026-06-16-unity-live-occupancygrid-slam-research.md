<!--
2026-06-16 조사 기록: SLAM /map(OccupancyGrid) 라이브 → 유니티 컨트롤룸 맵뷰 1:1 스트리밍 실현 가능성.
웹 검증 + 로컬 패키지/코드 점검 결과. 구현 착수 전 SSOT 근거 문서.
-->

# [조사] SLAM 맵 라이브 → 유니티 맵뷰 1:1 스트리밍 가능성

- **일자**: 2026-06-16
- **대상 기체**: 젠지(`kim@192.168.10.87`, TurtleBot3 burger, 구동계 포함), ROS Jazzy, `ROS_DOMAIN_ID=210`
- **목표**: 경기장 SLAM 중 `/map`을 유니티 ControlRoom의 MapPanel에 **실시간 1:1**로 렌더
- **결론**: **가능**. 유니티 공식 예제가 동일 기능을 구현. 우리는 카메라와 동일한 Texture2D 구독 패턴(model B)으로 통합한다.

## 1. 젠지 SLAM 준비 상태 (점검 완료)

| 항목 | 결과 |
|---|---|
| ROS | Jazzy, `ROS_DOMAIN_ID=210`, `TURTLEBOT3_MODEL=burger` |
| LiDAR | `hls-lfcd-lds-driver` + `/dev/ttyUSB0` (CP210x, Silicon Labs 10c4:ea60) |
| SLAM | `cartographer`, `cartographer-ros`, `slam-toolbox` 설치됨 |
| Nav2/bringup | `turtlebot3_bringup`, `turtlebot3_cartographer`, `nav2` 전체 |
| 워크스페이스 | `~/turtlebot3_ws` (bashrc에서 source) |
| 구동계 | OpenCR/바퀴 포함 (표준 bringup 사용 가능) — 2026-06-16 주인님 확인 |

→ 로봇 단독 SLAM은 추가 설치 없이 즉시 가능.

## 2. 유니티 맵뷰 현황 (점검 완료)

- **준비된 것**: `MapPanelView.cs`(2D/3D 버튼), `MapPanel.uxml`(레이아웃·placeholder), `MapConfigData.cs`(맵 메타 구조), ROS-TCP-Connector v0.7.0의 `OccupancyGridMsg`/`MapMetaDataMsg` 타입.
- **없는 것 (신규 개발 필요)**:
  - `/map` 토픽 구독자 (`MapSubscriber.cs` 미존재)
  - 맵 텍스처 렌더러 (`Map2DView` 미존재)
  - 로봇 위치(pose/odom) 구독자
  - `TopicRegistry.cs`에 `/map` 미등록
  - **visualizations 패키지(`com.unity.robotics.visualizations`) 미설치** — manifest엔 `ros-tcp-connector`만.

## 3. 구현 경로 (웹 검증)

라이브 OccupancyGrid → 유니티는 **유니티가 공식 지원하는 검증된 패턴**. 두 갈래:

### (A) 공식 Visualizations 패키지 — 빠른 백업
- `DefaultVisualizationSuite` 프리팹 추가 → Play → HUD Topics 탭에서 `/map` 3D 토글 → 자동 렌더.
- 장점: 코드 0줄. 단점: **RViz를 유니티 3D 씬에 띄우는 방식**이라 우리 컨트롤룸 UI(UI Toolkit MapPanel)와 별개로 표시됨. 패키지 추가 필요.

### (B) 커스텀 Texture2D 구독 — 채택 ★
- 이미 성공한 카메라 구독(model B)과 동일 패턴: `ROSConnection.Subscribe<OccupancyGridMsg>("/map", ...)` → `info.width/height/resolution/origin` + `sbyte[] data`(-1 unknown, 0 free, 100 occupied)를 `Texture2D`로 변환 → MapPanel에 렌더.
- 장점: **우리 컨트롤룸 UI 안에 1:1 통합** (진짜 목표). 리스크 낮음(검증된 패턴 재사용).
- 신규 파일: `Ros/MapSubscriber.cs`, MapPanel 렌더 연결, `TopicRegistry`에 `/map` 등록.

## 4. 성능 / 함정 (웹 검증)

- `/map`은 카토그래퍼 갱신 시마다 주기 발행. 데이터 = `width×height` 바이트. 예) 30m 경기장 @0.05m 해상도 ≈ 600×600 = 360KB → TCP로 충분.
- ⚠️ **Play 모드 종료 전에 ROS 노드를 먼저 종료**할 것 (안 하면 destruction 에러) — 공식 문서 명시.
- 대형 맵/publisher 유실 시 프리징 사례 보고됨 → cartographer **async 모드** 권장.
- DDS는 codelab_robot_team_2_5G에서 multicast 정상이나 **간헐 끊김 이력** 있음([[urhynix-wifi-codelab-status]]). 맵은 로봇 내부 생성이라 끊겨도 안 깨지나, teleop 끊김 시 로봇이 마지막 명령 유지 → 저속 운전.

## 5. SLAM 데이터 수집 요령 (맵 품질)

- 제자리 360° 회전만으론 **불충분**(보이는 벽만 채움). 이동이 핵심.
- 정석: ① 중심에서 1바퀴 초기화 → ② 저속(`0.1~0.15 m/s`)으로 가장자리 한 바퀴 + 가운데 가로지르기, 장애물 뒤편도 통과 → ③ 코너마다 살짝 회전(루프 클로저) → ④ **출발점 복귀**로 누적오차 보정.

## 6. 오늘 실행 플랜

1. `turtlebot3_bringup` → `/scan` `/odom` `/tf` 확인
2. `turtlebot3_cartographer`(async) → `/map` 발행 확인
3. Mac cross-host `ros2 topic echo /map --once` 수신 검증
4. 유니티 `MapSubscriber.cs` + `TopicRegistry` `/map` + MapPanel 렌더 연결 (경로 B)
5. teleop 저속 주행으로 맵 차오름 확인
6. `nav2_map_server map_saver_cli`로 pgm/yaml 백업 + evidence 기록

## 출처

- Unity Nav2-SLAM Example: https://github.com/Unity-Technologies/Robotics-Nav2-SLAM-Example/blob/main/readmes/unity_viz.md
- ROS-TCP Visualizations README: https://github.com/Unity-Technologies/ROS-TCP-Connector/blob/main/com.unity.robotics.visualizations/Documentation~/README.md
- Unity Robotics SLAM 튜토리얼: https://resources.unity.com/automotive-transportation-manufacturing-content/unity-robotics-slam
- slam_toolbox 맵 갱신 성능 이슈(sync/async): https://github.com/SteveMacenski/slam_toolbox/issues/743
