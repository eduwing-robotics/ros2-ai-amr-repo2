---
name: profile-recommendation
description: Use when the project stack is not fully decided or looks mixed, and you need to recommend the closest stack profile with a confidence level and one alternative.
---

# Profile Recommendation

## Use When

- 새 프로젝트 설명만 있고 stack profile이 아직 모호할 때
- 현재 폴더 경계가 profile과 어긋나 보일 때
- verify commands와 naming contract를 보고 가장 가까운 starter profile을 고르고 싶을 때

## Inputs

- project description
- `docs/ref/STACK-PROFILES.md`
- `docs/ref/PROJECT-PLAN.md`
- `docs/ref/ARCHITECTURE.md`
- `docs/status/PROJECT-STATUS.md`

## Steps

1. stack line, repo boundary, verify commands, naming contract token을 읽는다.
2. `STACK-PROFILES.md`의 각 profile과 가장 가까운 것을 고른다.
3. confidence를 `high`, `medium`, `low`로 적는다.
4. ambiguous하면 top 2와 이유를 남긴다.
5. 결과를 `Evidence Status` 또는 별도 drift note에 남긴다.

## Outputs

- recommended profile
- confidence
- alternative profile
- short reason

## Verify

- 추천 profile 이름이 `STACK-PROFILES.md`에 실제 존재한다.
- 이유가 boundary, verify, contract token 중 최소 2개를 근거로 든다.

## Failure / Fallback

- 애매하면 `confidence: low`로 적고, 구현보다 planning 보강을 먼저 추천한다.
- verify command가 너무 적으면 boundary와 naming contract 위주로 판단한다.

## References

- profile 비교 예시는 [profile-cases.md](references/profile-cases.md)
