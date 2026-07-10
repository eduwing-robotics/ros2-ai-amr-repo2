# Assets/Scripts/Services/

> ROS/UI 비의존 순수 도메인 로직 서비스. 상태를 들고 `ControlRoomEvents`로만 외부와 통신.

## 파일

| 파일 | 책임 |
|---|---|
| `PatrolService.cs` | 순찰 웨이포인트 목록 CRUD(add/removeLast/clear/renumber), 변경 시 이벤트 발화 |
| `ActiveRobotService.cs` (Phase 4) | 활성 로봇(역할 교환) SSOT |

## 규칙

- ROS/Unity 렌더 API import 금지(가벼운 타입만). 영속은 `Persistence/`에 위임.
- 상태 변경은 `ControlRoomEvents` 이벤트로 전파(직접 참조 금지).
- 싱글톤(`Instance`) 패턴은 `ControlRoomState`와 동일.
