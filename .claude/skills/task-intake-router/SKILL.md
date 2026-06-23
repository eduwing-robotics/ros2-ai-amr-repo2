---
name: task-intake-router
description: Use when a new request first lands and you need to classify it into planning, implementation, doc-sync, review, impact-map, or subagent-needed, then choose the next skill and whether parallel sub-agents are worth it.
---

# Task Intake Router

## Use When

- 새 요청이 들어와서 먼저 어떤 종류의 일인지 판정해야 할 때
- planning과 implementation이 섞여 보여서 시작점을 잡아야 할 때
- 바로 서브에이전트를 켤지 말지 결정해야 할 때

## Inputs

- user request
- `docs/ref/PROJECT-PLAN.md`
- `docs/status/PROJECT-STATUS.md`
- `docs/ref/TECH-INDEX.md`
- `.claude/skills/README.md`

## Steps

1. 요청을 아래 verdict 중 하나로 분류한다.
   - `plan`
   - `implement`
   - `doc-sync`
   - `review`
   - `impact-map`
   - `subagent-needed`
2. 현재 phase와 요청의 urgency를 같이 본다.
3. 요청 기술이 명확하면 `docs/ref/TECH-INDEX.md`에서 기술 ref 1개를 고른다.
4. 다음에 읽을 문서와 next skill 1~2개를 고른다.
5. 병렬 조사, 로그 triage, 넓은 영향 범위 탐색이 필요하면 `sub-agent needed: yes`로 적는다.
6. 결과를 `PROJECT-PLAN.md`의 `## Intake Verdict`에 남긴다.

## Outputs

- intake verdict
- chosen skill
- next skill
- tech ref
- sub-agent needed 여부
- 짧은 reasoning

## Verify

- verdict가 현재 phase와 충돌하지 않는다.
- `chosen skill`과 `next skill`은 실제 `.claude/skills/`에 존재한다.
- `tech ref`가 있으면 `docs/ref/TECH-INDEX.md`에 등록되어 있다.
- `sub-agent needed: yes`이면 `Sub-Agent Opportunities` 또는 status 쪽 packet 후보가 같이 남아 있다.

## Failure / Fallback

- 하나로 분류가 안 되면 `plan`으로 시작하고 `impact-map`을 바로 붙인다.
- review와 implement가 동시에 크면 `impact-map` 먼저, 그다음 `big-task`로 분해한다.

## References

- 좋은/나쁜 분류 예시는 [routing-cases.md](references/routing-cases.md)
