# docs/presentation/scenarios — 박물관 경비 로봇 시나리오 다이어그램 + 편집기

D3 + dagre 기반 시나리오 플로우차트. `index.html` 더블클릭으로 **오프라인** 동작(라이브러리 로컬 vendor).
발표 모드에서 단계 진행 시 활성 노드로 줌인 + 엣지 점 흐름, 편집 모드에서 폼/드래그로 직접 수정한다.

## 구조 (모듈)

- `index.html` — 진입점. CSS + vendor/data/engine 로드 + `ScenarioApp.mount("#board")`.
- `vendor/d3.v7.min.js`, `vendor/dagre.min.js` — 로컬 고정(전역 `d3`, `dagre`). CDN 의존 없음.
- `data/scenarios.js` — `window.SCENARIOS`(6종: s0 마스터 + s1~s5) + `window.RISK_LEGEND`. **SSOT는 Confluence "Sequence diagram"(page 19431426)**. 편집 기본값.
- `engine/store.js` — 상태 + localStorage(`urhynix.scenarios.v1`) + 가져오기/내보내기. `window.Store`.
- `engine/render.js` — dagre 레이아웃 → D3 SVG. 노드 `x,y` 수동좌표 오버라이드. `window.Render`(그린 모델은 `Render.L`).
- `engine/nav.js` — 좌우 분기 이동 · 자동재생 · 카메라 줌인 · 점 흐름 · 경로강조. 강조 단일원천 `Nav.path`. `window.Nav`.
- `engine/editor.js` — 폼 편집(노드/엣지/메타) + 드래그 이동 + Shift+드래그 엣지 연결. `window.Editor`.
- `engine/app.js` — UI/키/해시/모드 배선. `window.ScenarioApp`.

## 조작

- 발표: `→`/`Space` 다음 · `←` 분기(결정노드)·뒤로(일반) · `Backspace` 뒤로 · `Home` 초기화 · `End` 경로강조 · `F` 전체보기 · `P` 자동재생 · `1~6` 시나리오 · 노드 클릭 점프.
- 결정 노드: `←` = 첫 분기(없음), `→` = 둘째 분기(있음). 엣지 정렬 순서 = `[0]`없음 / `[1]`있음.
- 편집(`E` 또는 ✎ 버튼): 노드 클릭 선택 → 폼 수정 · 드래그 이동 · Shift+드래그로 엣지 연결.
- 해시 딥링크: `#s3` 시나리오 지정, `#s3/play` 로드 시 자동재생(키오스크).

## 저장/영구화 (file:// 제약)

- 브라우저는 원본 파일을 직접 못 씀(보안). 편집은 **localStorage 자동 저장**(새로고침 유지).
- 레포 영구 반영: 툴바 **⤓ 내보내기** → `scenarios.export.json` 다운로드 → `data/scenarios.js`의 `SCENARIOS`에 반영해 커밋.
- **♻ 기본값** = localStorage 비우고 `data/scenarios.js` 기본값 복원.

## 규칙

- 시나리오 내용(분기·등급·동작)은 Confluence SSOT("Sequence diagram" 손그림 플로우 6장)에서 가져와 하드코딩. 원천이 바뀌면 `data/scenarios.js` 갱신(드리프트 금지).
- 다이어그램엔 색이 없어 위험 등급(SAFE→EVACUATE)은 심각도 기준으로 매핑. "관리자 판단" 평행사변형 = 분기이므로 `decision` 타입으로 모델링.
- 상위 `docs/presentation` 덱과 별개 트랙(상단바 🗺 시나리오 링크로 새 탭 진입).
- 모듈 1파일 ≤ ~300줄 유지(비대화 시 분리).
