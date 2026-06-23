# docs/presentation — 팀 온보딩 프레젠테이션 프레임워크

재사용 가능한 발표(deck) 엔진. **엔진(고정) + deck 데이터(교체)** 구조로, 슬롯(slide block)을
바꿔끼우며 여러 주제를 같은 UI로 보여준다. 외부 의존성 0, `index.html` 더블클릭으로 오프라인 동작.

## 구조

- `index.html` — 진입점. 전체 CSS + 상단 UI(드롭다운/네비/메모 버튼) + 스크립트 로드.
- `engine/deck-engine.js` — deck 레지스트리 + 슬라이드/블록 렌더러 + 네비 + 툴팁 + 흐름 하이라이트.
- `engine/glossary.js` — 어려운 용어 → 설명 사전 (hover 툴팁 소스). `window.GLOSSARY`.
- `engine/annotate.js` — 회의 메모 핀(슬롯/좌표 앵커) + localStorage 저장 + Markdown 복사.
- `decks/*.js` — 발표 1개 = 파일 1개. `registerDeck({...})` 로 등록하면 드롭다운에 자동 노출.

## 새 발표 추가법

1. `decks/내주제.js` 생성, 최상단 헤더 주석 + `registerDeck({ id, title, theme, slides:[...] })`.
2. `index.html` 의 `<!-- DECKS -->` 블록에 `<script src="decks/내주제.js"></script>` 한 줄 추가.
3. 슬롯 타입: `cover / bullets / cards / diagram / flow / filetree / table / progress` (README 레퍼런스).

## 규칙

- 슬라이드 1개 = 블록(슬롯) 1개. "슬롯 교체"는 slides 배열의 객체 1개를 바꾸는 것.
- deck 데이터는 SSOT(docs/ref/*, docs/status/*) 에서 가져와 하드코딩 — 출처를 각 파일 헤더에 적는다.
- Jira 스프린트는 정적 스냅샷 + `lastSynced` 날짜. 라이브 API는 file://에서 불가.

## 발표용 산출물

- `presentation-bundle.html` — 단일 파일 발표본. deck-engine 안 `KEYWORD_MODE`(기본 `true`)가 켜지면
  슬라이드는 키워드만 크게 보여주고 설명 산문(lead/d/note/subtitle/body)은 숨긴다. `false`로 두면 원래대로 복원.
- `presentation-script.md` — 위에서 숨긴 설명을 슬라이드와 1:1로 풀어쓴 발표 대본(핸드폰용). 슬라이드 바뀌면 같이 갱신.
