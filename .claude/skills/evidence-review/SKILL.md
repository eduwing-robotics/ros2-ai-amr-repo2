---
name: evidence-review
description: Use before saying work is done, especially after code or document changes, to confirm executed verify commands, changed docs, assumptions, residual risks, and a clear release verdict.
---

# Evidence Review

## Use When

- 완료 선언 직전
- 리뷰 요청 전
- 문서만 바뀌었더라도 verify와 근거를 남겨야 할 때

## Inputs

- executed commands
- changed docs
- assumptions
- residual risks
- current phase

## Steps

1. 실제로 실행한 verify 명령만 적는다.
2. 바뀐 문서와 왜 바뀌었는지 적는다.
3. 아직 확인 못 한 가정과 남은 리스크를 적는다.
4. `release verdict`를 `not-ready`, `ready-for-review`, `ready-to-share` 중 하나로 정한다.
5. 결과를 `PROJECT-STATUS.md`의 `## Evidence Status`에 남긴다.

## Outputs

- evidence checklist
- release verdict
- residual risk summary

## Verify

- `executed verify` 명령은 `Verification Commands`에 존재한다.
- changed docs가 실제 변경 축과 맞는다.
- evidence가 없으면 `release verdict`는 `not-ready`다.

## Failure / Fallback

- verify를 안 돌렸으면 완료 선언 대신 `not-ready`로 남긴다.
- docs가 밀렸으면 먼저 `doc-sync`로 닫고 다시 evidence review를 한다.

## References

- 좋은/나쁜 증거 예시는 [evidence-cases.md](references/evidence-cases.md)
