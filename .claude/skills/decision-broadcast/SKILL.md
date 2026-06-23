---
name: decision-broadcast
description: 한 건의 결정(하드웨어 확정·작업 분담·범위 변경 등)을 5채널(DECISION-LOG → SSOT → HTML 보드 → Jira → Slack)에 한 번에 동기화하는 스킬. ssot-board-sync 위에 Jira와 Slack을 얹은 풀-체인.
user_invocable: true
tags: [decision, ssot, jira, slack, broadcast, post-decision]
trigger: "오늘 합의된 결정을 모든 채널에 흘려야 할 때 (DECISION-LOG·SSOT·HTML·Jira·Slack)"
version: 1
---

# Decision Broadcast

## 목적

한 건의 결정(예: "하드웨어 확정", "Day-1 작업 분담", "범위 축소 결정")이 들어오면 5개 채널이 모두 같은 한 줄을 받아야 한다. 한 채널만 빠지면 즉시 드리프트가 발생하고 팀이 다른 진실을 보게 된다.

이 스킬은 `ssot-board-sync`(SSOT + HTML 동기화)의 상위 호출자로, 그 위에 **Jira 티켓 본문/담당자 갱신**과 **Slack 채널 공지**까지 묶어 한 번에 처리한다.

## Use When

- 새 결정이 사용자 발언으로 들어왔을 때 ("이걸로 확정", "이렇게 가자", "오늘부터 이걸 시작")
- 결정이 (a) 하드웨어 구성, (b) 작업 분담, (c) 일정/범위 변경, (d) 인터페이스 계약 중 하나에 해당할 때
- DECISION-LOG, SSOT, HTML, Jira, Slack 중 **두 채널 이상**에 영향을 줄 때

## Skip When

- 단순 오타·문법 수정
- 코드만 변경 (그건 `doc-sync`)
- SSOT만 바뀌고 Jira/Slack 영향 없음 (그건 `ssot-board-sync`만으로 충분)

## 5채널 매핑

| 채널 | 무엇을 갱신 | 도구 |
|---|---|---|
| **1. DECISION-LOG** | `docs/status/DECISION-LOG.md`에 새 결정 항목 append (결정 / 이유 / 영향 / 산출물) | Edit |
| **2. SSOT** | 영향받는 `docs/ref/*` + `docs/status/PROJECT-STATUS.md` 본문 갱신 | Edit |
| **3. HTML 보드** | `dev-plan*.html` 7페이지 + `build_bundle.py` + 번들 재빌드 (→ `ssot-board-sync` 위임) | Edit + Bash |
| **4. Jira** | 영향받는 SCRUM-N 티켓 본문/제목/담당자/Sprint 갱신, 필요시 상태 전환 | `mcp__atlassian__editJiraIssue` |
| **5. Slack** | 팀 채널에 결정 요약 메시지 발송 (포맷은 아래 템플릿) | `mcp__claude_ai_Slack__slack_send_message` |

## 실행 순서

1. **결정 한 줄을 명확히 정리** — "무엇을 결정했나" + "왜" + "누구에게 영향"
2. **DECISION-LOG append** 먼저 (역사가 가장 먼저 남도록, 다른 모든 갱신의 근거 문서)
3. **SSOT 본문 갱신** — PRD/ARCHITECTURE/CONTRACT/SCHEMA/PROJECT-PLAN/PROJECT-STATUS/JIRA-MAP 중 영향받는 파일만
4. **`ssot-board-sync` 위임** — HTML 7페이지 + 번들 재빌드. `python3 docs/whiteboards/build_bundle.py`
5. **Jira 티켓 갱신** — `editJiraIssue` 반복. 큰 결정이면 5~10개 티켓. 영향 매트릭스를 미리 만들어 한 번에 일괄 처리.
6. **Slack 메시지 발송** — 아래 템플릿. URHYNIX 채널 `C0B5Q43A27R` (CONTRACT.md §5 참조).
7. **검증** — `PROJECT-STATUS.md` Evidence Status 행 ✅ 갱신.

## Slack 메시지 템플릿

```
🚀 *<프로젝트명>* — <날짜> 확정 정리

*1. <결정 카테고리 1>*
- 핵심 한 줄
- 세부 사항 점 3~5개
- ⚠️ 주의사항 1줄

*2. <결정 카테고리 2 (예: 작업 분담)>*
- A팀 — *멤버*: 작업 (관련 SCRUM)
- B팀 — *멤버*: 작업 (관련 SCRUM)

*3. <오늘 검증 라인>*
한 줄로: "X → Y → Z 통과하면 PASS 🎉"

*4. 참조*
- Confluence: <link>
- Jira 보드: <link>
- 로컬 dev-plan: `docs/dev-plan-bundle.html`

*5. 다음 액션*
- 각자 산출물 1장씩 이 채널에 공유
- 다음 마일스톤 진입: ...

> 자세한 본문은 `docs/ref/<DECISION-LOG.md>` + `<관련 ARCHITECTURE/CONTRACT 섹션>` 참조.
```

## Slack 채널 검색 / 권한 오류 대응

`channel_not_found` 에러가 나면:
1. CONTRACT.md §5에서 채널 ID 재확인
2. `slack_search_channels`로 채널명 검색 후 정확한 ID 획득
3. 그래도 안 되면 **봇이 채널에 멤버로 초대되어야 함** — 사용자에게 알리고 메시지 본문은 코드 블록으로 제공(복붙 발송 가능)
4. DM(`user_id`)으로 본인에게 발송한 뒤 채널로 옮기는 우회법도 가능

## Jira 갱신 절차

1. **영향받는 티켓 식별**: 결정이 어느 SCRUM ID와 연결되는지 매핑
2. **JQL로 현재 상태 조회**: `searchJiraIssuesUsingJql`로 제목·담당자·상태 확보
3. **일괄 본문 갱신**: 각 티켓에 결정 한 줄 + 영향 + 오늘 산출물 추가
4. **상태 전환**(필요 시): `getTransitionsForJiraIssue`로 transition ID 확인 후 `transitionJiraIssue`
5. **재조회 검증**: 갱신 후 다시 JQL로 확인

## 예시 실행 흐름 (URHYNIX Day-1 분담)

1. DECISION-LOG에 "센서 연결·적층 구조 확정" + "Day-1 작업 분담" 2건 append
2. SSOT 4개 갱신: PRD(하드웨어 표), ARCHITECTURE(적층 다이어그램), CONTRACT(§4), PROJECT-PLAN(W1 매트릭스), PROJECT-STATUS(Day-1 액션)
3. `dev-plan.html` 메인에 Day-1 박스 + `build_bundle.py` 동기화 + 번들 재빌드
4. Jira SCRUM-8/9/13/14/19/22 본문 6개 갱신 (Day-1 산출물 명시)
5. Slack 메시지 발송 (3 카테고리 · 4명 · 검증 라인 · 5 참조 링크)
6. PROJECT-STATUS Evidence Status 행 ✅

## 산출물 / Verify

```bash
# DECISION-LOG에 새 항목이 있는지
tail -40 docs/status/DECISION-LOG.md

# 영향받는 SSOT가 모두 갱신됐는지 (grep으로 결정 키워드 검사)
grep -l "<결정 키워드>" docs/ref docs/status -r

# HTML 7개 + 번들 파싱 OK
python3 -c "
from html.parser import HTMLParser
import glob
for f in sorted(glob.glob('docs/dev-plan*.html')):
    HTMLParser().feed(open(f).read())
    print('OK', f)
"

# Jira 티켓 재조회 (예: Day-1 키워드)
# mcp__atlassian__searchJiraIssuesUsingJql with jql='project = SCRUM AND text ~ "Day-1"'

# Slack 메시지 발송 결과 (성공 시 메시지 링크 반환)
```

## 한줄정리

결정 한 건이 들어오면 DECISION-LOG → SSOT → HTML → Jira → Slack 5채널에 모두 흘려야 드리프트가 안 생기고, 이 스킬은 그 흐름을 표준화한다. (HTML 부분은 `ssot-board-sync`에 위임)
