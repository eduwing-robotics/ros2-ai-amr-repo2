# Assets/Scripts/Data/

> 도메인 데이터 클래스. 외부 의존 없는 순수 POCO.

## 예정 파일

| 파일 | 의미 |
|---|---|
| `RobotInfo.cs` ✅ | 로봇 ID/이름/모델/IP/역할/토픽 |
| `RobotLiveState.cs` | 위치, 배터리, 모드, 연결 상태 |
| `RobotPowerState.cs` | online/standby/shutdown/error enum |
| `RobotFeatureInfo.cs` ✅ | 기능 정의 (자율주행/SLAM/카메라/...) |
| `SensorInfo.cs` ✅ | 센서 이름/타입/단위/토픽 |
| `WaypointInfo.cs` ✅ | 순회 지점 (MapConfigData.cs 안에 통합) |
| `BlockedAreaInfo.cs` | 차단 구역 |
| `ProtectedTargetInfo.cs` ✅ | 보호대상 (액자/작품/물품) |
| `MapConfigData.cs` ✅ | office_base_map.json 직렬화 컨테이너 (MapMeta + Waypoint[] + ProtectedTarget[]) |
| `EventInfo.cs` | 화재/침입/소음/도난 이벤트 |
| `DispatchInfo.cs` | 출동 명령 + 도착 기록 |
| `CameraInfo.cs` | 카메라 라벨/토픽/해상도 |
| `RobotPoseEntry.cs` ✅ | 시계열 pose 1건 (Supabase `pose_logs` 1행 매핑) |

## 규칙

- ROS/Unity API import 금지. `Vector2`, `Vector3` 같은 가벼운 타입만 OK.
- JSON 직렬화 가능해야 함 (`Resources/*.json` 또는 Supabase row와 매핑).
- 모든 필드는 `public` + 명확한 이름.
