# Assets/Scripts/App/

> 앱 진입점 + 전역 상태 + UI/ROS/DB 이벤트 결선.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `ControlRoomApp.cs` ✅ | 앱 부트스트랩, 매니저 생성, 첫 화면 로드 |
| `ControlRoomState.cs` ✅ | 선택 로봇, 화면 모드, 세션 상태 (싱글톤) |
| `ControlRoomEvents.cs` ✅ | UI ↔ ROS ↔ DB 이벤트 결선 (라우터) |
| `ViewMode.cs` | TwoD / ThreeD 전환 enum (ControlRoomState에 string으로 박힘, 별도 enum 필요 시 후속) |

## 규칙

- 직접 ROS topic이나 DB 호출 금지. 항상 `Ros/`, `Database/` 폴더의 서비스를 거침.
- 전역 상태 변경은 `ControlRoomEvents` 통해 이벤트로 전파.
