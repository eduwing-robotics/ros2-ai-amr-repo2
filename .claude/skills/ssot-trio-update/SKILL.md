---
name: ssot-trio-update
description: 작업 1건 PASS/FAIL 직후 URHYNIX 3종 SSOT(`docs/status/DECISION-LOG.md` + `PROJECT-STATUS.md` + `HANDOFF.md`)를 1회 호출로 정합되게 갱신하는 스킬. `docs/status/` 3파일만 다룸 — HTML 보드/Jira/Slack 손 안 댐. 트리거 — "문서 업데이트", "문서 갱신", "문서 동기화", "상태 문서 업데이트", "SSOT 갱신". 범위가 HTML 보드까지면 `ssot-board-sync`, Jira/Slack 전파까지면 `decision-broadcast`로 위임(이 스킬은 가장 가벼운 기본 입구).
user_invocable: true
tags: [documentation, ssot, status, post-work, wrap-up]
trigger: "작업 끝나고 결과/학습/다음진입을 SSOT 3종에 박을 때 (HTML/Jira는 별도)"
version: 1
---

# SSOT Trio Update

## 목적

URHYNIX는 모든 작업 결과를 `docs/status/` 3종 파일에 시계열로 박는다. 한 작업이 끝나면 이 3파일이 동시에 갱신돼야 다음 세션 진입에서 드리프트가 없다.

- **DECISION-LOG.md** — 결정/절차/결과/학습의 시계열 정본. 새 entry는 해당 날짜 섹션 **최상단**.
- **PROJECT-STATUS.md** — 한 줄 현재 상태(`Last updated: ...`) + 역할 매트릭스. **이전 상태는 "이전: ..." 로 한 줄에 chain.**
- **HANDOFF.md** — 다음 세션 진입 1페이지 캡슐. **`**Last updated**:`** 가장 최근 + `**이전(YYYY-MM-DD)**: ...`로 history chain.

이 스킬은 **3파일 동시 편집**만 다룬다. HTML 보드(`docs/dev-plan*.html`)는 `ssot-board-sync`, Jira/Slack은 `decision-broadcast`로 위임.

## Use When

- 작업 1건이 PASS/FAIL로 명확히 결판났을 때 (테스트 결과, 검증 매트릭스, 시각 확인 등 evidence 있음)
- 다음 세션이 본 결과를 캡슐로 받아야 할 때 ("일단 마무리", "현재 상태 박기")
- 핵심 학습 1건 이상 생긴 결정 (이전 노트 정정, 새 패턴 발견 등)
- 사용자가 명시: "ssot 박아줘", "상태 업데이트", "마무리"

## Skip When

- 단순 오타·문법 수정
- 코드만 바뀌고 결정/상태 영향 0 (그건 `doc-sync`)
- SSOT 1줄 변경에 그치고 timeline 가치 없음 (직접 편집)
- Jira/Slack까지 흘려야 함 (그건 `decision-broadcast`로 escalate)

> **Note**: HTML 보드(`docs/dev-plan*.html`)는 현재 URHYNIX 운영 대상 아님. 본 스킬은 `docs/status/` 3파일만 다룬다.

## 3파일 갱신 매핑

| 파일 | 위치 | 형식 |
|---|---|---|
| `docs/status/DECISION-LOG.md` | `## YYYY-MM-DD` 아래 **최상단** | 새 `### 제목` entry (이전 entry는 그 아래 그대로) |
| `docs/status/PROJECT-STATUS.md` | 파일 최상단 `Last updated: ...` 한 줄 | 새 한 줄 통째 교체, 이전 내용은 `이전: ...` 로 chain |
| `docs/status/HANDOFF.md` | 파일 최상단 `**Last updated**: ...` 캡슐 | 새 캡슐 + `**이전(YYYY-MM-DD)**: <이전 캡슐 압축>` chain |

## 절차

### Step 1 — 3파일 현재 상태 읽기 (병렬)

```
Read DECISION-LOG.md (최상단 5~10줄)
Read PROJECT-STATUS.md (최상단 1~3줄)
Read HANDOFF.md (최상단 1~3줄)
```

### Step 2 — Entry 본문 구성

DECISION-LOG entry는 아래 7섹션 구조 (모두 필수는 아니지만 시계열 가치 있는 만큼 박는다):

```markdown
### <한 줄 제목 — 결정/PASS/해결 내용>

- **결정/증상**: 무슨 일이 일어났나 (1~2줄)
- **원인** 또는 **결정**: 핵심 root cause 또는 합의 내용
- **해결 절차** (재현 가능): 1.~5. 번호로 박은 단계
- **결과 매트릭스** (선택): 표 또는 ✅/❌
- **핵심 학습 N건** (선택): 이전 정정 또는 새 패턴
- **부수 산출물**: 만든/바뀐 파일 경로 1~3개
- **다음 진입**: 다음 세션 첫 행동 1~2줄
```

### Step 3 — DECISION-LOG.md 최상단 entry 박기

기존 패턴: `## YYYY-MM-DD` 헤더 바로 아래에 새 `### 제목` 박고, 이전 `### 제목`은 그 아래로 밀린다. 같은 날짜라면 헤더는 1개 유지.

```python
# 패턴
Edit:
  old_string: "# Decision Log\n\n## 2026-06-02\n\n### <이전 첫 entry 제목>"
  new_string: "# Decision Log\n\n## 2026-06-02\n\n### <새 entry 제목>\n\n<entry 본문>\n\n### <이전 첫 entry 제목>"
```

### Step 4 — PROJECT-STATUS.md Last updated 교체

기존:
```
Last updated: YYYY-MM-DD <시점> — <이전 한 줄 요약>
```

새:
```
Last updated: YYYY-MM-DD <시점> — <새 한 줄 요약>. 이전: <이전 한 줄 요약 압축 ~50자>
```

이전 줄을 통째로 `이전: ...`에 머리 잘라 끼워 history chain 유지. 너무 길어지면 가장 오래된 chain은 잘라낸다 (2~3회분 유지).

### Step 5 — HANDOFF.md Last updated 캡슐 갱신

기존:
```
**Last updated**: YYYY-MM-DD <시점> (<이전 캡슐>). **이전(YYYY-MM-DD)**: ...
```

새:
```
**Last updated**: YYYY-MM-DD <시점> (**🆕 <새 결정/PASS 한 줄>** — <2~5문장 요약 + 다음 진입 첫 행동>. 자세히: `docs/status/DECISION-LOG.md` <날짜> 최상단). **이전(YYYY-MM-DD)**: <이전 캡슐 압축 + "superseded" 마킹>. <이전 chain 그대로>
```

이모지 1개로 시각 ID (🎯/🖼️/🤖/🎨/📷 등 결정 도메인 표시).

### Step 6 — 검증

```bash
# 3파일 최상단 5줄씩 확인
head -5 docs/status/DECISION-LOG.md
head -3 docs/status/PROJECT-STATUS.md
head -3 docs/status/HANDOFF.md
```

확인 포인트:
1. DECISION-LOG 새 entry가 같은 날짜 섹션 최상단에 있다.
2. PROJECT-STATUS Last updated가 새 한 줄로 교체됐고 `이전:` chain이 살아있다.
3. HANDOFF Last updated 새 캡슐 + `**이전(YYYY-MM-DD)**:` chain.
4. 3파일이 같은 결정을 서로 다른 압축 단계로 가리킨다 (DECISION-LOG=상세, STATUS=한 줄, HANDOFF=다음 진입 캡슐).

## Outputs

- 3파일 동시 갱신 diff
- 다음 세션 진입 캡슐 (HANDOFF 최상단)

## Verify

- DECISION-LOG entry 날짜 == 오늘 날짜.
- PROJECT-STATUS Last updated 날짜 == 오늘.
- HANDOFF Last updated 새 캡슐이 DECISION-LOG entry 1순위와 일치.
- `이전:` 또는 `**이전(...)**:` chain이 끊기지 않는다 (지난 1~2건 유지).
- 새 entry/캡슐이 다음 세션 첫 행동을 명시한다.

## Failure / Fallback

- **DECISION-LOG에 오늘 날짜 섹션 없을 때**: `## YYYY-MM-DD` 헤더부터 새로 박고 그 아래에 첫 `### 제목` 박는다.
- **PROJECT-STATUS `Last updated:` 한 줄이 너무 길어졌을 때**: 가장 오래된 `이전: ...` chain 1건 잘라낸다.
- **HANDOFF `**이전(...)**` chain이 5건 이상 누적되면**: 가장 오래된 1건 잘라낸다 (Last updated 본체는 항상 가장 최근만).
- **결정 가치 애매하면**: 본 스킬 스킵 → DECISION-LOG만 1줄 노트로 박거나 evidence 파일에만 기록.

## 호출 시점 흐름

```
작업 진행 (Bash/Edit/Test 등)
  ↓ PASS/FAIL 결판
ssot-trio-update     ← 본 스킬 (status 3파일만)
  ↓ 결정 외부 broadcast 필요 시
decision-broadcast   ← Jira + Slack까지
```

## References

- 본 스킬은 `session-handoff` 스킬의 URHYNIX-구체화 확장. session-handoff가 추상 capsule, 본 스킬은 3파일 정확한 편집 위치/포맷.
- `decision-broadcast`: 결정 1건을 외부 채널(Jira/Slack)까지 broadcast.
- 예시 entry는 `docs/status/DECISION-LOG.md` 2026-06-02 최상단 5건 — 모두 본 스킬 패턴 따름.
