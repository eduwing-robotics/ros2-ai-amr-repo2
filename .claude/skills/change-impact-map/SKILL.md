---
name: change-impact-map
description: Use when a route, schema, env var, worker path, or UI surface change can ripple across code, docs, and verification, and you need an explicit impact map before editing.
---

# Change Impact Map

## Use When

- route rename
- schema or table rename
- env var rename
- worker path 추가
- UI entrypoint 변경

## Inputs

- requested change
- `docs/ref/PROJECT-PLAN.md`
- `docs/ref/ARCHITECTURE.md`
- `docs/status/PROJECT-STATUS.md`

## Steps

1. 변경 축을 `route`, `schema`, `env`, `worker`, `UI`, `mixed` 중 하나로 적는다.
2. core paths를 repo-relative path로 적는다.
3. companion docs와 verify matrix를 적는다.
4. naming contract token이 바뀌면 어떤 문서에서 같은 token을 바꿔야 하는지 적는다.
5. 결과를 `PROJECT-PLAN.md`의 `## Impact Map Summary`에 남긴다.

## Outputs

- impact map summary
- companion docs list
- verify matrix
- residual risk

## Verify

- `core paths`가 `File Map` 또는 doc sync 대상과 연결된다.
- verify matrix가 최소 1개 이상 있다.
- naming contract이 바뀌면 `PRD`, `PROJECT-PLAN`, `ARCHITECTURE`, `PROJECT-STATUS` 중 필요한 문서가 포함된다.

## Failure / Fallback

- 경로를 아직 특정 못 했으면 `candidate:` 접두사로 적는다.
- 영향 범위가 너무 넓으면 `big-task`로 phase를 자르고, 조사만 서브에이전트에 넘긴다.

## References

- 예시 매트릭스는 [impact-cases.md](references/impact-cases.md)
