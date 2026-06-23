---
name: unity-ui-interaction-audit
description: Unity UI Toolkit View 레이어 완료 직후 모든 인터랙티브 요소(버튼/토글/탭/리스트)의 핸들러 등록 + 이벤트 발화 + 구독자 + 시각 피드백 정합성을 정적/동적 2단계로 검증. Phase A Opus 정적 감사 + Phase B unityctl 동적 검증의 한계 5종 + 우회 표. UI Contract Lock 잠그기 직전 안전판. — 2026-06-04 URHYNIX Phase 2.5 → Phase 3 진입 전 검증으로 도입.
---

# unity-ui-interaction-audit

## 언제 쓰나

- UI View 레이어 완료 후 데이터/ROS/DB 결선 진입 전 (예: URHYNIX Phase 2.5 → Phase 3 경계)
- View 클래스 다수를 SRP로 분리한 직후 핸들러 누락 / 구독자 없음 / 시각 피드백 누락 잡을 때
- **UI Contract Lock 원칙** (UXML/USS/View 0 줄 수정) 잠그기 직전
- 박물관 시연 같이 critical 시연 일정 직전 회귀 검증

## 핵심 자산 3종

| 자산 | 역할 |
|---|---|
| **Phase A 정적 감사** (Opus 서브에이전트) | 16~25개 인터랙티브 요소 매트릭스 + 코드 인용. 30분 안에 80% 결함 잡음. 안전. |
| **Phase B 동적 시도** (unityctl exec + Editor 자동화) | 5종 한계 + 우회 표. 함정 알고 진입해야 시간 안 버림. |
| **표준 보고서 형식** | 매트릭스 + 결함 6분류(A~F) + 시연 critical 우선순위 + Phase B 준비물 |

## Phase A — 정적 코드 감사 (안정, 30분)

### Opus 서브에이전트 프롬프트 톤

- 읽기 대상: View N개 + UXML M개 + ControlRoomEvents / State / Binder
- 산출 매트릭스 컬럼: `# / element ID / UXML 파일 / 담당 View / 핸들러 등록? / 이벤트 발화 / 구독자 / 시각 피드백 / critical / 상태`
- 코드 인용 형식: `파일명:줄번호`, 추측 금지
- 결함 6분류:
  - **A. 핸들러 누락** — `Q<Button>("id")` 후 `.clicked +=` 없음
  - **B. 이벤트 발화 누락** — 핸들러는 등록됐지만 `ControlRoomEvents.RaiseXxx` 호출 안 함
  - **C. 구독자 없음** — `OnXxx +=` 한 곳 없는 고아 이벤트
  - **D. 시각 피드백 누락** — active class 토글 / 라벨 갱신 / style 변경 없음
  - **E. null reference 위험** — `Q<>()` 결과 null 체크 빠짐
  - **F. unsubscribe 누락** — `+=` 만 있고 OnDestroy/Dispose에서 `-=` 없음 (Domain Reload leak)
- 시연 critical 우선순위: 🔥 HIGH / 🟡 MID / 🟢 LOW
- Phase B 준비물 섹션 필수 (element ID 완전 명세 + 클릭 시뮬 템플릿 + 스크린샷 기준)
- 저장: `<repo>/PHASE-A-INTERACTION-AUDIT.md`

### Phase A 결과로 판정 가능한 것

| 판정 | 기준 |
|---|---|
| 🟢 시연 GO | 🔥 HIGH critical 결함 0건, A/B/D 0건 |
| 🟡 보강 후 GO | E/F (null 방어, unsubscribe)만 발견 — 박물관 시연 critical 아님 |
| 🔴 NO-GO | A/B/D HIGH critical 1건 이상 |

## Phase B — 동적 검증 (한계 5종, 우회 필요)

| # | 시도 | 결과 | 우회 |
|---|---|---|---|
| 1 | `unityctl exec --code "URHYNIX.X.Y.Z()"` 직접 호출 | ❌ Type not found | exec는 시스템 어셈블리(UnityEngine/UnityEditor.dll)만 검색. 사용자 어셈블리(Assembly-CSharp.dll) 안 봄. 우회: `[RuntimeInitializeOnLoadMethod]` 자동 실행 또는 `UnityEditor.EditorApplication.ExecuteMenuItem` |
| 2 | `UnityEditor.EditorApplication.ExecuteMenuItem("URHYNIX/...")` | ⚠️ menu 등록 시점 불확실 | 표준 menu("Window/General/Console")는 PASS인데 신규 [MenuItem]은 `result: false` 케이스. Domain reload + Editor 재시작으로 회피. `UnityEditor.EditorUtility.RequestScriptReload()` 명시 호출 권장 |
| 3 | `[RuntimeInitializeOnLoadMethod(AfterSceneLoad)]` 자동 실행 | ✅ 동작 | GameObject + MonoBehaviour 트리거 (Invoke로 1.5초 지연 후 RunAll). Play 진입 시 자동. 검증 종료 후 attribute 제거 권장 |
| 4 | `btn.clicked?.Invoke()` 클릭 시뮬 | ❌ CS0079 컴파일 에러 | `Button.clicked`는 `event Action` — 외부 invoke 불가. 우회 옵션 3개: (a) Reflection으로 `m_Clickable.clicked` 호출, (b) `ControlRoomEvents.RaiseXxx` 직접 호출(UI 우회), (c) `btn.SendEvent(new ClickEvent())` (단 ClickEvent constructor internal 가능) |
| 5 | Reflection 우회 | ⚠️ Unity internal API 의존 | `typeof(Button).GetField("m_Clickable", NonPublic).GetValue(btn)` → `Clickable.clicked` 추출 → Invoke. Unity 마이너 업데이트 시 깨질 위험. Phase B 일회용 검증으로만 사용 |

### 권고 — Phase B 안전 진입 패턴

**Option A. ControlRoomEvents 직접 호출** (가장 안전)
- UI 핸들러 자체는 검증 못 함 (Phase A에서 이미 정적 검증함)
- 이벤트 시스템 + 구독자 + 시각 피드백만 동적 검증
- 예: `ControlRoomEvents.RaiseScenarioTriggered("fire")` → SensorCardListView/AlertPopupView 반응 확인

**Option B. Editor 메뉴 직접 클릭** (수동, 가장 확실)
- 사용자가 Unity Editor 활성화 + `URHYNIX/Run Interaction Audit` 클릭
- 자동화는 못 하지만 한 번이면 25개 클릭 다 시뮬
- 박물관 시연 직전 1회 검증으로 충분

**Option C. 정적만으로 GO** (Phase A로 충분)
- Phase A에서 코드 인용 근거 박힌 25/25 PASS면 시연 critical 충분
- Phase B 동적은 박물관 시연 직전 사용자가 Editor에서 시각 확인

## 함정 + 우회 표 (전체)

| 함정 | 증상 | 우회 |
|---|---|---|
| `script validate` PASS인데 실제 컴파일 fail | "Compilation succeeded" 받고 Play 진입 → Type not found / RuntimeInitializeOnLoadMethod 안 호출됨 | **Editor.log grep `CS[0-9]{4}`로 확인 필수**. `unityctl console get-count` errors가 1+면 의심. validate는 syntax check일 뿐 |
| exec --code 사용자 어셈블리 unreachable | `Type not found: <namespace>.<Class>` | UnityEditor namespace 통한 ExecuteMenuItem 또는 RuntimeInitializeOnLoadMethod 자동 실행 패턴 |
| Button.clicked event invoke 컴파일 fail | CS0079: "can only appear on the left hand side of += or -=" | Reflection 우회 / ControlRoomEvents 직접 호출 / Editor 메뉴 클릭 (Phase B Option A~C 참고) |
| Editor freeze 후 OS가 죽임 | `pgrep -lf "Unity.app/Contents/MacOS/Unity"` 결과 없음, Editor.log 라이센스 핸드셰이크에서 끊김 | `pkill -9 -f "Unity.app/Contents/MacOS/Unity"` 후 `open -na "/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app" --args -projectPath "$PROJ"` 재시작 + 120초 polling |
| `rtk grep`/`ls` 출력 빈 채로 나옴 | 파일 있는데 결과 empty | `find <dir> -type f` 또는 `ls -la` 직접 사용 |
| Domain reload 안 일어남 | 새 [MenuItem] / type 어셈블리 로드 안 됨 | Play stop → `unityctl asset refresh` → Play start. 또는 `unityctl exec --code "UnityEditor.EditorUtility.RequestScriptReload()"` |
| unityctl 출력 Spectre.Console markup 깨짐 | `InvalidOperationException: Could not find color or style 'Busy'/'InvalidParameters'` | `--json` 옵션 사용 (모든 명령 일관) |
| Editor 폴더 코드가 Play 모드 unreachable | `Assets/Editor/`의 .cs는 Editor 어셈블리에 박혀 Play 모드 AppDomain에서 Type 검색 실패 | Runtime assembly에 두기. 폴더명 "Editor" 피하고 `Assets/Scripts/<Domain>/`로 |
| **EventSystem만 있고 InputModule 누락** | UI Toolkit 클릭 0 반응 (코드 다 박혔는데 마우스 이벤트 자체 안 옴) | Scene EventSystem GameObject에 **InputSystemUIInputModule** (com.unity.inputsystem 사용 시) 또는 **StandaloneInputModule** (옛 InputSystem) 컴포넌트 추가. `new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule))` 패턴 |
| **Phase A 정적 감사가 Scene 구성 결함 못 잡음** | 코드 핸들러 25/25 PASS인데 Play에서 클릭 0 반응 | Phase A는 View 코드만 검증 — **Scene GameObject + Component 구성은 별도 검증 필요**. `unityctl gameobject get --id <EventSystem-id>`로 component 리스트 dump해서 InputModule 존재 확인. UIDocument의 PanelSettings/sourceAsset null 체크도 같이 |

## 자동화 명령 시퀀스 (Phase B Option A 기준)

```bash
PROJ="/Users/family/jason/URHYNIX/unity/ControlRoom"

# 1) Editor 부팅 (필요 시)
open -na "/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app" --args -projectPath "$PROJ"

# 2) Editor ready polling (최대 120초)
i=0; until unityctl status --project "$PROJ" --json 2>&1 | grep -q '"success": true' || [ $i -ge 60 ]; do sleep 2; i=$((i+1)); done

# 3) Console clear + 컴파일 errors 확인 (script validate는 신뢰 X)
unityctl console clear --project "$PROJ" --json
unityctl console get-count --project "$PROJ" --json   # errors 0 확인
grep -E "CS[0-9]{4}" ~/Library/Logs/Unity/Editor.log | tail -5

# 4) Play start + audit MonoBehaviour 초기화 대기
unityctl play start --project "$PROJ" --json
sleep 5

# 5) 이벤트 직접 호출 (Phase B Option A — UI 우회 이벤트 시뮬)
#    UnityEditor.EditorApplication.ExecuteMenuItem 또는 우리 AuditMenu 호출
unityctl exec --project "$PROJ" --code "UnityEditor.EditorApplication.ExecuteMenuItem(\"URHYNIX/Run Event Audit\")" --json

# 6) 결과 console + screenshot
unityctl console get-count --project "$PROJ" --json
unityctl screenshot capture --project "$PROJ" --view game --output /tmp/audit-result.png --json

# 7) Play stop
unityctl play stop --project "$PROJ" --json
```

## 산출물 형식 (PHASE-A-INTERACTION-AUDIT.md)

```markdown
# Phase A: 정적 인터랙션 감사

**대상**: <project name> Phase X.Y
**감사일**: YYYY-MM-DD
**범위**: N View + M UXML + ControlRoomEvents

## Executive Summary
- 인터랙티브 요소: N개
- 결함: 0 critical / X 경고
- 시연 준비도: 🟢 GO / 🟡 보강 / 🔴 NO-GO

## 1. 인터랙션 매트릭스
(섹션별: TopBar / LeftPanel / MapPanel / CameraPanel / RightPanel / AlertPopup)

## 2. 결함 분류 (A~F)

## 3. 시연 Critical 우선순위 (🔥 HIGH / 🟡 MID / 🟢 LOW)

## 4. Phase B 준비물
- Element ID 완전 명세 (yaml)
- 클릭 시뮬 템플릿 (코드)
- 스크린샷 기준 (Before/After)

## 5. 권장 개선 (단계별)

## 6. 최종 판정 (PASS/FAIL 매트릭스)

## Appendix A. 이벤트 발화 흐름도
## Appendix B. 코드 인용 (근거)
```

## 검증 흐름 (full)

1. Phase A Opus 서브에이전트 백그라운드 시작 (30분 예상)
2. 그 사이 Editor 부팅 + unityctl 능력 확인 (`exec --help`, `play --help` 등)
3. Phase A 보고서 도착 → 매트릭스 검토
4. 시연 critical 결함 0건 확인 → 🟢 GO 판정
5. (선택) Phase B 동적 검증 진입 — Option A (ControlRoomEvents) 또는 Option B (메뉴 클릭)
6. 결과 SSOT에 박음 (DECISION-LOG entry)
7. UI Contract Lock 잠그기 + Phase 3 진입

## URHYNIX 적용 (2026-06-04)

- Phase 2.5 직후 적용 — 25/25 PASS, 시연 GO
- 보고서: `/Users/family/jason/URHYNIX/PHASE-A-INTERACTION-AUDIT.md`
- Phase B는 한계 5종 발견 후 Option C(정적만으로 GO)로 결정
- 함정 5종 모두 본 스킬 표에 박혀 차기 적용 시간 절약

## 한줄정리

UI View 레이어 잠그기 전 인터랙션 정합성을 Opus 정적 감사로 25개 요소 매트릭스화 + 결함 6분류(핸들러/이벤트/구독자/시각/null/leak)로 잡고, 동적 검증은 unityctl `exec` 한계(사용자 어셈블리 unreachable + Button.clicked event invoke 불가)를 우회 표로 미리 알고 가야 시간 안 버려요 주인님.
