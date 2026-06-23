---
name: parallel-qa
description: E2E QA 시나리오를 그룹으로 나눠 빠르게 검증하는 스킬
user_invocable: true
tags: [qa, e2e, browser, regression, verification]
trigger: "데모 전, 회귀 테스트 전, 수동 QA 시간이 부족할 때"
version: 1
---

# Parallel QA

## Use When

- MVP/데모 직전
- 버그 수정 후 회귀 확인
- 페이지가 많아 수동 QA가 오래 걸릴 때

## Steps

### Step 1: 시나리오 목록 작성

우선순위별로 정리:

- P0 blocker
- P1 core flows
- P2 edge flows

### Step 2: 그룹핑

- 페이지 단위
- 기능 단위
- 5개 이하 그룹 권장

### Step 3: 세션 분리

브라우저 세션/테스트 프로세스를 분리해 충돌을 줄인다.

### Step 4: 관통 테스트 추가

개별 TC 외에 end-to-end 한 줄 관통 시나리오 1개는 꼭 둔다.

예:
- 로그인 -> 생성 -> 저장 -> 확인

### Step 5: 결과 요약

```markdown
TC-01: PASS
TC-02: FAIL - reason
```

## Verify

- [ ] P0 시나리오가 먼저 정의됐다
- [ ] 시나리오가 그룹으로 나뉘었다
- [ ] 관통 테스트 1개 이상 있다
- [ ] pass/fail 이유가 남는다

## Failure / Fallback

- 병렬 실행이 불안정하면: 그룹만 유지하고 순차 실행한다
- 브라우저보다 API가 안정적이면: 일부는 API 테스트로 내린다
