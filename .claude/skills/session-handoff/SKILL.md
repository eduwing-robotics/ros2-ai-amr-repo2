---
name: session-handoff
description: Use when ending a session or pausing a large task and you need a compact capsule for the next agent or the next day: entrypoint, blockers, unfinished decisions, and first verify command.
---

# Session Handoff

## Use When

- 세션 종료 직전
- blocker 때문에 중단할 때
- parent agent가 서브에이전트 결과를 다음 세션으로 넘겨야 할 때

## Inputs

- current phase
- changed files
- blockers
- next recommended entrypoint

## Steps

1. 다음 세션의 첫 문서 또는 첫 파일을 `next entrypoint`로 적는다.
2. `read first` 순서를 1~3개 적는다.
3. blocker와 unfinished decisions를 적는다.
4. 다시 시작할 때 돌릴 첫 verify를 적는다.
5. `PROJECT-STATUS.md`의 `## Handoff Capsule`에 남긴다.

## Outputs

- handoff capsule
- blocker summary
- next verify

## Verify

- `next entrypoint`가 실제 존재하는 경로다.
- blocker가 있으면 `Next Actions`에 이어지는 안전한 다음 행동이 있다.
- first verify가 `Verification Commands`와 모순되지 않는다.

## Failure / Fallback

- blocker가 없으면 `blocker: none`으로 명시한다.
- entrypoint가 여러 개면 읽기 순서를 적고 1순위를 `next entrypoint`로 고정한다.

## References

- 좋은 capsule 예시는 [handoff-cases.md](references/handoff-cases.md)
