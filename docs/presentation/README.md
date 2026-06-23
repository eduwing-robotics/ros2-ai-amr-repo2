<!-- 재사용 발표 프레임워크 사용법 + 슬롯 타입 레퍼런스. 코드 구조는 docs/presentation/CLAUDE.md 참조. -->
# URHYNIX 팀 온보딩 프레젠테이션

`index.html` 을 **더블클릭**하면 열립니다(오프라인, 빌드 불필요). Chrome 권장(메모 localStorage/클립보드).

## 조작

| 키 | 동작 |
|---|---|
| `←` `→` / `Space` | 슬라이드 이동 (덱 끝나면 다음 덱으로) |
| `↓` `↑` / `H` | diagram·flow 슬라이드에서 데이터 흐름 단계 강조 |
| `Home` `End` | 처음 / 마지막 슬라이드 |
| `M` 또는 📌 버튼 | 메모 모드 토글 |
| 상단 드롭다운 | 발표 주제(덱) 전환 |
| 🗺 시나리오 버튼 | 박물관 경비 로봇 시나리오 다이어그램(`scenarios/index.html`)을 새 탭으로 — D3+dagre, 단계별 줌인 + 엣지 점 흐름. 별도 트랙(`scenarios/CLAUDE.md`). |

- **툴팁**: 점선 밑줄 용어에 마우스를 올리면 설명. 사전은 `engine/glossary.js`.
  같은 용어는 **발표(덱)마다 처음 나오는 슬라이드에서 1회만** 표시(이후 문장·페이지는 일반 텍스트). 덱이 바뀌면 다시 첫 등장에 표시.
  합성어 오매칭 방지를 위해 영문/숫자 단어 경계로 매칭(예: `RobotPoseSubscriber` 안의 `Subscriber`는 안 걸림).
- **메모**: 메모 모드에서 노드/카드/트리/빈 영역을 클릭 → 핀 생성 → 텍스트 입력. 새로고침에도 유지.
  `🗂 목록` 으로 슬라이드 메모 보기, `⧉ 복사` 로 현재 덱 메모를 Markdown 클립보드 복사(회의록 붙여넣기).

## 새 발표(덱) 추가

1. `decks/내주제.js` 생성:
   ```js
   registerDeck({ id: "my-topic", title: "⑤ 내 주제", theme: "cyan", slides: [ /* 슬롯들 */ ] });
   ```
2. `index.html` 의 `<!-- DECKS -->` 아래에 `<script src="decks/my-topic.js"></script>` 한 줄 추가.
3. 새로고침 → 드롭다운에 자동 노출.

`theme`: `cyan` | `violet` | `amber` | `green`.

## 슬롯(슬라이드 블록) 타입 레퍼런스

| type | 핵심 필드 |
|---|---|
| `cover` | `title`, `subtitle`, `tags[]`, `note` |
| `bullets` | `title`, `lead`, `items[]` (`"문자열"` 또는 `{h, d}`) |
| `cards` | `title`, `cols`(2/3/4), `cards[]` (`{title, body, sub, badge:{text,kind}}`) |
| `diagram` | `title`, `nodes[]` (`{label, sub}`), `note` — `↓` 로 단계 강조 |
| `flow` | `title`, `chains[]` (`{label, steps:[{k, v}]}`) — `↓` 로 단계 강조 |
| `filetree` | `title`, `tree[]` (`{name, desc, open, children[]}`) |
| `table` | `title`, `columns[]`, `rows[][]` (셀은 문자열 또는 `{v, kind}`) |
| `progress` | `title`, `items[]` (`{label, done, total, status}`) |

- 인라인 마크업: `**굵게**`, `` `코드` ``, `[표시](링크)`.
- `badge.kind` / 셀 `kind`: `ok`(초록) `warn`(노랑) `bad`(빨강) `info`(파랑) `accent`(강조).
- 슬라이드 1개 = 슬롯 1개. "슬롯 바꿔끼기"는 `slides` 배열의 객체를 교체하는 것.

## Jira 스프린트 갱신

`decks/sprint-status.js` 의 `SPRINT_SYNCED` 날짜와 `progress`/`table` 데이터를 직접 수정.
원천: `mcp__atlassian__searchJiraIssuesUsingJql` (`project=SCRUM AND statusCategory!=Done`) + `docs/ref/JIRA-MAP.md`.
라이브 API 연동은 file:// 보안 제약으로 불가 → 정적 스냅샷 유지.
