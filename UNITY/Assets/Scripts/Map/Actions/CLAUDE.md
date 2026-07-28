# Assets/Scripts/Map/Actions/

> 맵 우클릭 컨텍스트 메뉴 액션. 각 액션은 작은 단일 파일(책임분리).

- `IMapAction.cs` — 액션 인터페이스(확장점). Id/DisplayName/AppliesTo/Execute.
- `MapActionRegistry.cs` — 빌트인 + SSOT(`Resources/SituationConfig/default_situations.json`) 상황 액션 병합.
- `DispatchHereAction` / `SituationDispatchAction` / `AddWaypointAction` / `MarkProtectedTargetAction` — 구현체.

## 규칙
- 새 액션은 `IMapAction` 구현 + Registry 등록만. 한 액션 = 한 파일.
- 액션은 `ControlRoomEvents`로만 외부와 통신(Robot/Ros 직접 호출 금지).
- 좌표 변환은 호출부(MapInteractionController)가 끝낸 `MapClickContext`를 받는다.
