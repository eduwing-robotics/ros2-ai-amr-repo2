---
name: socratic-review
description: 큰 설계 결정을 질문 기반으로 검증하는 스킬
user_invocable: true
tags: [review, planning, architecture, validation]
trigger: "큰 설계 결정 전, 리팩터링 착수 전"
version: 1
---

# Socratic Review

## Use When

- 새 기능 설계 직후
- 리팩터링 전에 방향이 맞는지 확인할 때
- PR이 커질 것 같을 때
- 선택지가 두 개 이상일 때

## Rules

1. 한 번에 최대 3개 질문
2. 질문 번호 누적
3. 대안을 반드시 1개 이상 검토
4. 결론은 `DECISION-LOG.md`에 기록

## Steps

1. Context 질문 3개를 먼저 던져 목표와 영향 범위를 고정한다.
2. Alternatives 질문 3개로 다른 접근과 기각 이유를 드러낸다.
3. Edge Cases 질문 3개로 실패 시나리오와 롤백 비용을 점검한다.
4. 답변에서 남은 불확실성을 risk 목록으로 따로 적는다.
5. 최종 결론, 기각한 대안, 검증 기준을 `DECISION-LOG.md`에 남긴다.

### Context Questions

- Q1 목적은 무엇인가
- Q2 영향 범위는 어디까지인가
- Q3 가장 위험한 지점은 어디인가

### Alternatives Questions

- Q4 다른 접근은 무엇인가
- Q5 왜 그 대안을 고르지 않았나
- Q6 이 설계의 가장 큰 단점은 무엇인가

### Edge Case Questions

- Q7 실패 시나리오는 무엇인가
- Q8 되돌리기 어려운 결정은 무엇인가
- Q9 검증 전략은 무엇인가

## Outputs

- 질문/답변 세트
- 선택한 설계와 기각한 대안
- 검증 기준
- decision log entry

## Verify

- [ ] 최소 9개 이상 질문이 오갔다
- [ ] 대안이 최소 1개 검토되었다
- [ ] 최종 결정과 이유가 기록되었다
- [ ] 검증 기준이 명시되었다

## Failure / Fallback

- 시간이 없으면: Context 3개 + 검증 기준 1개만 먼저 한다
- 답이 불확실하면: 그 불확실성 자체를 risk로 기록한다
