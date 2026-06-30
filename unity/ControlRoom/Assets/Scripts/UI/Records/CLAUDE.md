# Assets/Scripts/UI/Records/

> 기록 탭(`page-records`)의 3서브탭(로그 / 이벤트·출동 / KPI)을 담당하는 View들.

## 파일

| 파일 | 책임 |
|---|---|
| `RecordsPageView.cs` | 서브탭 전환, 하위 View 조립, 전역 이벤트 구독, coordinator |
| `RecordsLogSubtab.cs` | 로그 칩 필터(category/level) + 로그 카드 렌더 |
| `RecordsTimelineSubtab.cs` | 이벤트/출동 머지 + 타임라인 카드 렌더 |
| `RecordsKpiSubtab.cs` | KPI 4장 비동기 로드/표시 |
| `RecordsChipBar.cs` | 칩 UI 생성/토글 헬퍼(공통) |

## 규칙

- `RecordsPageView`는 직접 렌더하지 않는다. 각 서브탭이 독립적으로 칩/리스트/새로고침을 관리.
- 서브탭은 `IRecordsSubtab`(`Build()`/`Load()`/`Refresh()`)을 구현.
- DB Repository는 `RecordsPageView`에서 한 번 만들어 각 서브탭에 주입.
- 파일 크기 300줄 초과 금지.
