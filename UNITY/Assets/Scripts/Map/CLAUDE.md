# Assets/Scripts/Map/

> 2D 캔버스 맵 + 3D 씬 맵 + 마커/웨이포인트/경로 렌더링.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `Map2DView.cs` | HTML canvas를 대체하는 2D 맵 (UI Toolkit `VisualElement.generateVisualContent`) |
| `Map3DView.cs` | Unity 3D 씬 + URDF prefab 로봇 표시 |
| `MapViewSwitcher.cs` | 2D/3D 버튼 전환 |
| `MapCameraController.cs` | 줌/팬/3D 시점 제어 |
| `Robot3DSpawner.cs` | `RobotModelMap.asset` 읽어 prefab 인스턴스화 |
| `ProtectedTargetMarker.cs` | 보호대상 2D/3D 마커 |
| `WaypointDrawer.cs` | 순회 지점 + 연결선 |
| `RobotMarkerDrawer.cs` | 로봇 위치 마커 |
| `BlockedAreaDrawer.cs` | 차단 구역 + 편집 |
| `PathFinder.cs` | A* 우회 경로 |

## 규칙

- 좌표계 통일: SLAM map 원점 + Unity 좌표 변환은 `Robot3DSpawner` 1곳에서 흡수.
- 2D/3D는 같은 데이터(`WaypointInfo`, `RobotLiveState`)를 다른 방식으로 렌더. 데이터 중복 금지.
