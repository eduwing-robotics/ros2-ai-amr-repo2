---
name: session-retro
description: 세션 종료 시 성공 패턴, 실패 우회, 반복 수작업을 자산화
user_invocable: true
tags: [retro, reflection, automation, skill-extraction]
trigger: "작업 세션 종료 시, 또는 삽질 후 교훈을 남기고 싶을 때"
version: 2
---

# Session Retro

세션을 그냥 끝내지 않고, 다음 프로젝트에 재사용 가능한 규칙과 하네스로 환원하는 스킬이다.

## Signals To Capture

- success pattern
- failed-then-fixed
- repeated manual step
- user correction

## Use When

- 작업 세션 종료 직전
- 예상보다 오래 막혔다가 해결했을 때
- "이건 다음에도 반복되겠다" 싶을 때
- 좋은 패턴을 정식 하네스로 승격하고 싶을 때

## Inputs

- 오늘 작업 내역
- 최근 git diff / git log
- 작업 중 메모
- 사용자 피드백

## Steps

### Step 1: 세션 기록 스캔

```bash
git log --oneline --since="today"
git diff --stat HEAD~5 2>/dev/null || true
```

필요하면 대화/메모도 같이 본다.

### Step 2: 4가지 신호 분류

| Signal | Meaning | Promote To |
|---|---|---|
| success pattern | 잘 먹힌 절차 | skill or harness candidate |
| failed-then-fixed | 삽질 후 우회 발견 | caution note / feedback |
| repeated manual step | 두 번 이상 손으로 한 일 | automation candidate |
| user correction | 사용자가 바로잡은 규칙 | memory / rule update |

### Step 3: 간단 기록 작성

권장 형식:

```markdown
## Session Retro — YYYY-MM-DD

### Success
- ...

### Failure -> Fix
- ...

### Repeated Manual Work
- ...

### User Correction
- ...
```

### Step 4: 승격 경로 결정

- 1회 반복: 프로젝트 문서에 메모
- 2회 반복: 하네스 후보로 등록
- 3회 이상 반복: 범용 규칙/스킬로 승격

### Step 5: 실제 반영

후보만 적고 끝내지 않는다. 아래 중 최소 하나는 실제 파일에 반영한다.

- `PROJECT-STATUS.md`
- 새 하네스 초안
- `.claude/automations/` 후보
- `CLAUDE.md` 주의사항

## Outputs

- 회고 노트
- 승격 후보
- 자동화 후보
- 수정된 규칙 또는 status 메모

## Verify

- [ ] 4가지 신호 중 최소 1개 이상 기록했다
- [ ] 신호별로 다음 액션을 결정했다
- [ ] 최소 1개 이상 실제 파일 반영이 있었다
- [ ] 승격 기준(1회/2회/3회+)을 적용했다

## Failure / Fallback

- 신호가 거의 없으면: "이번 세션은 특이사항 없음" 한 줄만 남긴다
- 시간이 없으면: `PROJECT-STATUS.md`에 배운 점 1줄만 적는다
- 승격이 애매하면: 하네스보다는 프로젝트 문서에 먼저 남긴다
