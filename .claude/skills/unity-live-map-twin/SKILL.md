---
name: unity-live-map-twin
description: SLAM /map(OccupancyGrid)을 카메라 없이 순수 UI Toolkit MapPanel에 라이브 1:1 렌더하고, /tf 로봇 화살표 마커 + 우클릭 SSOT 출동(/goal_pose) + 회전 보정까지 컴포넌트화한 ControlRoom 디지털트윈 맵뷰 패턴. 2026-06-16 젠지로 검증.
when_to_use:
  - ControlRoom 맵뷰에 라이브 SLAM 맵을 띄우거나 마커/우클릭 액션을 추가할 때
  - OccupancyGrid를 Unity UI에 그릴 때(카메라/RenderTexture 없이)
  - /tf로 로봇 위치를 UI에 오버레이할 때
  - 맵 표시가 실제 경기장과 틀어져 회전 보정이 필요할 때
references:
  - docs/evidence/2026-06-16-genji-live-slam-unity-map.md
  - docs/evidence/2026-06-16-unity-live-occupancygrid-slam-research.md
  - .claude/skills/unity-unityctl-ops/SKILL.md  # 컴파일/검증 함정
  - .claude/skills/slam-nav2-arena-survey/SKILL.md  # 로봇측 SLAM 기동
---

# unity-live-map-twin

## 무엇 / 왜

SLAM `/map`(nav_msgs/OccupancyGrid)을 **카메라·RenderTexture 없이** UI Toolkit `Image`로 그린다. 평면 2D 맵엔 카메라가 과함(주인님 선호: 가벼운 안 우선, [[feedback-lightweight-then-scaffold]]). 핵심 설계는 **map-frame**: 컨테이너 안에 맵 비율로 잠긴 사각형을 중앙배치 → 양옆 여백 사라지고(테마 배경으로 채움), 마커/클릭 좌표가 frame 기준이라 letterbox 보정 불필요.

## 아키텍처 (Assets/Scripts/Map/, 소형 파일 책임분리)

| 파일 | 책임 |
|---|---|
| `MapCoordinateSystem.cs` | 좌표 변환 SSOT(순수 static): world↔정규화↔frame px, `QuaternionToYaw`, 2D `ComposePose`(tf 합성) |
| `MapViewport.cs` | map-frame 생성·**비율맞춤 재배치**(GeometryChanged/맵크기) + 메타 보관 + **회전**(`SetRotation`/`AddRotation`) |
| `MapImageLayer.cs` | `MapSubscriber.OnMapUpdated` 구독 → 텍스처 할당 + viewport에 메타 전달 |
| `MapMarkerLayer.cs` | 로봇 화살표(▲): `RobotPoseSubscriber.OnPoseUpdated` → 위치/회전 |
| `MapHudLayer.cs` | 스케일바·방위 N·좌표 readout (pickingMode Ignore) |
| `MapInteractionController.cs` | frame 포인터: hover→HUD 좌표, 우클릭→world→컨텍스트 메뉴 |
| `MapContextMenuView.cs` | 커서 플로팅 메뉴(AlertPopup 패턴: absolute+visible, scrim 닫기) |
| `MapView.cs` | 오케스트레이터(thin): 레이어 조립 + 회전 디폴트 로드 |
| `Map/Actions/*` | `IMapAction` + `MapActionRegistry`(빌트인+SSOT) + DispatchHere/SituationDispatch/AddWaypoint/MarkTarget |

ROS 측: `Ros/MapSubscriber.cs`(/map→Texture2D+origin), `Ros/RobotPoseSubscriber.cs`(/tf 합성 map→base_footprint), `Ros/DispatchPublisher.cs`(OnDispatchRequested→/goal_pose PoseStamped). `App/ControlRoomApp.cs`가 3 구독자 코드 부착(씬 YAML 비편집). `App/ControlRoomEvents.cs`에 `OnDispatchRequested`. UI는 `MapPanelView`가 토글+회전버튼만, 2D는 `MapView`에 위임.

## 좌표 모델 (정확성 핵심)

- 메타: originX/Y(좌하단 m), resolution(m/cell), widthCells/heightCells. W=cells·res.
- world→정규화 `u=(x-ox)/W, v=(y-oy)/H`; 정규화→frame px `px=u·Fw, py=(1-v)·Fh`(v=1 북쪽=상단). 클릭은 역변환.
- **텍스처는 북쪽=상단**으로 표시됨(UI Image upright). 마커/클릭이 상하 뒤집히면 v만 반전.
- 마커 회전: ▲(북향) 기준 `화면각(cw+) = 90 − yawDeg`.
- **회전은 표시 정렬일 뿐** → 우클릭 출동 좌표는 회전과 무관하게 정확한 map 좌표로 나감(frame-local은 transform 역보정됨).

## tf 로봇 pose (RobotPoseSubscriber)

`/tf` 누적 dict(child→parent,x,y,yaw) → target(base_footprint→base_link)부터 root(map)까지 `ComposePose`로 합성. cartographer `map→odom` 보정 반영(=정확). `/odom` 직접은 드리프트(fallback만). TB3 프레임: map→odom→base_footprint→base_link.

## 회전 보정 (실제 경기장 정렬)

SLAM 원점이 실제와 틀어지면 `MapViewport.SetRotation(deg)`로 frame 전체(맵+마커) 회전. 디폴트 영속 2단:
1. **PlayerPrefs** `urhynix.map.displayRotationDeg` — ⟲/⟳ 조정 시 자동 저장(머신 디폴트).
2. **SSOT** `Resources/MapConfig/office_base_map.json` `map.displayRotationDeg` — 팀 공유/재현(PlayerPrefs 없을 때 폴백).
시작 시 `PlayerPrefs ?? json` 적용. (2026-06-16 젠지 경기장 = **85° CW**.)
값 확인법: 회전 시 `[MapView] rotation = N°` 로그(Editor.log) 또는 `defaults read unity.DefaultCompany.turtlebot 'urhynix.map.displayRotationDeg'`.

## 검증 (로봇 ON 필요)

1. 로봇 SLAM 기동([[slam-nav2-arena-survey]]) → `/map` 1Hz, `/tf` 발행.
2. `MapPanelView`가 default_robots.json `robots[0]`의 host로 endpoint 연결(쓸 로봇을 [0]에).
3. endpoint 로그: `RegisterSubscriber(/map …) OK`, `(/tf …) OK`, `RegisterPublisher(/goal_pose, PoseStamped) OK`.
4. Unity Editor.log: `[MapSubscriber] 🟢 first /map frame`, `[RobotPoseSubscriber] 🟢 first pose`, `[DispatchPublisher] ready`.
5. 우클릭 출동: `ros2 topic echo /goal_pose --once`로 클릭 좌표 일치 확인.
6. ⚠️ 화면 스크린샷은 검정(UI Toolkit 오버레이는 카메라 캡처 안 됨) → **Unity 창 직접 확인**. ([[unity-unityctl-ops]])

## 함정 (이번에 물린 것)

| 증상 | 원인 | 해결 |
|---|---|---|
| 맵 영역 전부 흰색 | 컨테이너에서 `.map-placeholder`(flex-grow/min-height) 제거돼 찌그러져 흰 카드 비침 | `container2D.style.flexGrow=1; minHeight=320` |
| `transformOrigin` 컴파일 에러 | VisualElement 직접 속성 아님 | `el.style.transformOrigin = new TransformOrigin(...)` |
| HUD가 우클릭 가로챔 | 라벨 pickingMode 기본 | HUD 요소 `pickingMode=Ignore` |
| 마커가 글리프 크기만큼 어긋남 | 고정 px 오프셋 | `style.translate = Translate(-50%,-50%)` + transformOrigin center |
| Unity가 죽은 로봇에 연결 시도 | `robots[0]`가 꺼진 로봇 | 쓸 로봇을 `default_robots.json` [0]으로 |

## 향후 확장점 (스캐폴딩 완료)

웨이포인트/보호대상 마커(MarkerLayer 패턴), Nav2 실연동(/goal_pose→실주행), 줌/팬, LiDAR /scan 오버레이, 3D 로봇 모델 — `IMapAction`·`ControlRoomEvents`·`MapCoordinateSystem`이 확장점.

## 한줄정리

카메라 없이 map-frame(비율맞춤)으로 /map을 그리고, /tf 화살표 마커 + 우클릭 SSOT 출동 + 회전보정(PlayerPrefs+SSOT)을 컴포넌트화. 검증은 endpoint Register 로그 + Editor.log Debug.Log(스크린샷은 검정이라 창 직접 확인).
