---
name: stack-drift-guard
description: Use when a project may have drifted away from its original stack profile and you need a stable, drifting, or reprofile-needed verdict based on boundaries, verification commands, file map, and contract names.
---

# Stack Drift Guard

## Use When

- 프로젝트가 처음 선택한 stack profile에서 벗어난 느낌이 들 때
- worker, backend, runtime boundary가 새로 생겼을 때
- verify command나 contract token이 profile과 다르게 커졌을 때

## Inputs

- `docs/ref/PROJECT-PLAN.md`
- `docs/ref/STACK-PROFILES.md`
- `docs/ref/ARCHITECTURE.md`
- `docs/status/PROJECT-STATUS.md`

## Steps

1. 현재 stack line과 추천 profile을 읽는다.
2. boundaries, file map, verify commands, naming contract token을 비교한다.
3. verdict를 아래 중 하나로 정한다.
   - `stable`
   - `drifting`
   - `reprofile-needed`
4. recommendation과 이유를 남긴다.
5. `reprofile-needed`면 drift note와 required doc updates를 같이 적는다.

## Outputs

- drift verdict
- recommended profile
- drift note

## Verify

- verdict는 boundary, verify, contract token 중 최소 2개 근거를 가진다.
- `reprofile-needed`이면 note와 next safe action이 같이 있다.
- 자동 재작성 없이 recommendation만 남긴다.

## Failure / Fallback

- 신호가 약하면 `drifting`으로 두고 profile recommendation을 같이 남긴다.
- 문서가 오래됐으면 문서 sync 후 다시 drift를 판정한다.

## References

- drift 판정 예시는 [drift-cases.md](references/drift-cases.md)
