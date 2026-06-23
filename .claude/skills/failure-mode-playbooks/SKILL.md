---
name: failure-mode-playbooks
description: Use when the project is stuck in a common agent failure mode such as missing docs, missing verify, profile mismatch, naming drift, oversized phases, doc-sync lag, sub-agent overlap, or insufficient evidence, and you need a safe recovery path.
---

# Failure Mode Playbooks

## Use When

- 문서가 아직 없어서 어디서 시작해야 할지 막힐 때
- verify 명령이 비어 있을 때
- profile mismatch가 의심될 때
- naming contract drift가 생겼을 때
- phase가 너무 커졌을 때
- doc-sync가 밀렸을 때
- 서브에이전트 owned path가 겹칠 때
- evidence가 부족한데 완료 선언이 나왔을 때

## Inputs

- current failure signal
- `docs/ref/PROJECT-PLAN.md`
- `docs/status/PROJECT-STATUS.md`
- relevant verify output

## Steps

1. signal을 아래 playbook 이름 중 하나에 매핑한다.
   - `no-docs-yet`
   - `verify-missing`
   - `profile-ambiguous`
   - `naming-contract-drift`
   - `phase-too-big`
   - `doc-sync-lag`
   - `subagent-overlap`
   - `evidence-insufficient`
2. likely cause를 짧게 적는다.
3. immediate action과 safe fallback을 고른다.
4. 꼭 갱신해야 할 문서와 다시 돌릴 verify를 적는다.
5. 필요한 경우 `PROJECT-STATUS.md`의 `Next Actions`로 승격한다.

## Outputs

- recovery steps
- required docs to update
- verify to re-run

## Verify

- playbook 이름이 실제 signal과 맞는다.
- recovery steps가 문서 갱신과 verify 재실행을 둘 다 포함한다.
- overlap이나 drift면 그대로 구현을 계속 밀지 않는다.

## Failure / Fallback

- signal이 둘 이상이면 가장 파괴적인 것부터 처리한다.
- 문서와 런타임 중 무엇이 truth인지 불명확하면 코드를 우선 읽고 문서를 따라가게 만든다.

## References

- 각 실패 모드별 복구 표는 [playbook-matrix.md](references/playbook-matrix.md)
