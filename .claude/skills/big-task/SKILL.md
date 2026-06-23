---
name: big-task
description: 규모가 큰 작업을 단계화하고 검증/문서 동기화까지 닫는 오케스트레이션 스킬
user_invocable: true
tags: [planning, execution, orchestration, review]
trigger: "작업이 3단계 이상이거나 변경 파일이 많을 때"
version: 1
---

# Big Task

## Use When

- 파일 변경이 10개 이상 예상될 때
- 단계가 3개 이상인 작업일 때
- 구현과 문서와 검증을 같이 닫아야 할 때

## Steps

### Step 1: change class 적기

- route/surface
- schema/model
- pipeline/flow
- automation/prompt
- design/token
- config/infra

### Step 2: 마일스톤 쪼개기

예시:

```markdown
M1 — 탐색/범위 확정
M2 — 구현
M3 — 검증
M4 — 문서 동기화
```

### Step 3: 독립성과 의존성 표시

- 독립 작업은 병렬 가능
- 같은 파일/같은 계약을 건드리면 순차

### Step 4: 마일스톤별 검증 연결

- typecheck
- build
- focused test
- smoke

### Step 5: 각 phase 끝에 미니 self-review

- M1 뒤: scope review
- M2 뒤: implementation review
- M3 뒤: validation review
- M4 뒤: doc-sync review

상세 체크포인트는 `references/phase-review-checkpoints.md` 참고.

### Step 6: 마지막에 self-review + doc-sync

큰 작업은 구현만 끝나면 안 된다.

## Output Format

```markdown
## Plan
- M1 ...
- M2 ...

## Validation
- ...

## Doc Sync
- ...
```

## Verify

- [ ] change class가 적혔다
- [ ] 마일스톤이 3개 이상으로 나뉘었다
- [ ] 각 마일스톤에 검증이 연결되었다
- [ ] 각 phase 끝의 미니 self-review가 포함되었다
- [ ] 마지막에 문서 동기화가 포함되었다

## Failure / Fallback

- 범위가 너무 크면: 탐색 마일스톤만 먼저 끝낸다
- 병렬 여부가 애매하면: 순차 실행으로 보수적으로 간다
