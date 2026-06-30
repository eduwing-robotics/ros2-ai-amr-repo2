# GLM-5.2 Code Review Prompt — URHYNIX ControlRoom UI Polish

> 본 prompt는 URHYNIX Unity ControlRoom의 Phase 1~4 변경사항을 GLM-5.2가 리뷰하도록 한다.
> 리뷰 완료 후 `PASS` / `FAIL` / `REQUEST-CHANGES` 판정과 개선 제안을 사용자에게 알려준다.

## 리뷰 범위

### Phase 1 — 디자인 토큰 SSOT 복원
- `unity/ControlRoom/Assets/UI/ControlRoomTokens.uss`
- `unity/ControlRoom/Assets/Scripts/Design/UiTokens.cs`
- `unity/ControlRoom/Assets/Scripts/Design/CLAUDE.md`

### Phase 2 — USS 하드코딩 토큰화
- `unity/ControlRoom/Assets/UI/ControlRoomPanels.uss`
- `unity/ControlRoom/Assets/UI/ControlRoomMap.uss`
- `unity/ControlRoom/Assets/UI/ControlRoomStyle.uss`
- `unity/ControlRoom/Assets/UI/ControlRoomLayout.uss`

### Phase 3 — Left 사이드바 정보 밀도 업
- `unity/ControlRoom/Assets/UI/Parts/LeftControlPanel.uxml`
- `unity/ControlRoom/Assets/Scripts/UI/RobotRoleCardView.cs`
- `unity/ControlRoom/Assets/Scripts/UI/QuickActionView.cs`
- `unity/ControlRoom/Assets/Scripts/UI/TeleopPadView.cs`
- `unity/ControlRoom/Assets/Scripts/UI/ControlRoomBinder.cs`
- `unity/ControlRoom/Assets/Scripts/App/ControlRoomEvents.cs`

### Phase 4 — 문서/레퍼런스
- `docs/ref/DESIGN-DECISIONS.md`
- `unity/ControlRoom/Assets/Art/References/foxglove-reference.png`
- `unity/ControlRoom/Assets/Art/References/grafana-reference.png`
- `docs/status/PROJECT-STATUS.md`
- `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md`

## 검증 결과 (OpenCode 수행)

- `unityctl check`: PASS (31 assemblies, no compile error)
- `unityctl status`: Playing, `isDomainReloading=false`
- 하드코딩 색상 grep (`#RGB`/`rgba()` not `var(--)`): 0건
- `git diff --stat`: 53 files changed, 1072 insertions, 884 deletions

## 리뷰 포인트

1. **토큰 SSOT 일관성**
   - `ControlRoomTokens.uss`와 `UiTokens.cs`가 1:1로 매핑되는가?
   - 누락되거나 중복된 토큰이 있는가?

2. **하드코딩 잔여 여부**
   - 색상/폰트/레이아웃/크기 중 여전히 하드코딩된 곳이 있는가?
   - 1px border, 160px/320px min-height 등은 의도된 예외인가?

3. **아키텍처 규칙 준수**
   - `TeleopPadView`가 ROS를 직접 호출하지 않고 `ControlRoomEvents`를 통해 명령을 발행하는가?
   - `QuickActionView`도 동일하게 이벤트 발행만 하는가?
   - View가 비즈니스 로직을 직접 수행하지 않는가?

4. **UI/UX 적정성**
   - 236px 고정 폭 사이드바에서 새로 추가된 카드들이 overflow 없이 표시될 것인가?
   - Teleop D-pad 버튼이 터치/클릭하기에 적절한 크기인가?
   - 수동 모드가 아닐 때 Teleop 카드가 명확히 비활성 표시되는가?

5. **이벤트 설계**
   - `OnTeleopCmd`의 `isPressed`가 버튼 뗌/나감 시 `false`로 잘 발행되는가?
   - `OnQuickAction`의 actionId 집합이 명확하고 확장 가능한가?

6. **문서 동기화**
   - `DESIGN-DECISIONS.md`가 실제 코드 변경과 일치하는가?
   - `PROJECT-STATUS.md` Evidence Status가 누락 없이 갱신됐는가?
   - `UNITY-CONTROLROOM-CONVERSION-PLAN.md` 매핑 표가 최신인가?

7. **코드 스타일/품질**
   - C# 네이밍, namespace, 상단 헤더 코멘트 규칙 준수
   - USS 클래스명 일관성
   - 매직 넘버/색상 제거 여부

## 특히 확인할 위험 항목

- `RobotRoleCardView.cs`에서 inline `new Color(...)`로 색상을 하드코딩한 부분이 있었으나, 이번 수정에서 USS 클래스(.vision/.sensor/.unknown)로 이동되었다. 토큰 `--color-role-*`과 USS가 1:1로 매핑되는지 검증.
- `TeleopPadView.cs`의 `PointerLeaveEvent` 핸들러가 버튼을 누른 채 패드 밖으로 나갈 때 정지를 보장하는가? `holding` 딕셔너리 플래그를 사용해 불필요한 0/0 발행을 방지했는지 확인.
- `QuickActionView.cs`의 actionId가 `QuickActionIds.cs` 상수를 사용하는지 확인.
- `LeftControlPanel.uxml`의 `ScrollView`가 236px 폭에서 탭 전환 시 스크롤 위치가 의도치 않게 움직이지 않는지 확인.
- 퀙액션 버튼이 실제 로봇 안전에 미치는 영향. 현재는 이벤트 발행만 하지만, 향후 구독자가 어떤 동작을 할지 고려.

## 판정 기준

- **PASS**: 모든 포인트에서 문제 없거나, 사소한 개선 제안만 있음.
- **REQUEST-CHANGES**: 중대한 버그, 아키텍처 위반, 또는 누락된 기능이 있음. 구체적인 수정 제안 포함.
- **FAIL**: 컴파일/런타임 오류, 데이터 손상 위험, 보안 문제.

## 출력 형식

```text
## 종합 판정: PASS / REQUEST-CHANGES / FAIL

## 주요 발견 (있는 경우)
- ...

## 개선 제안 (우선순위 순)
1. ...
2. ...

## 잔여 리스크
- ...
```
