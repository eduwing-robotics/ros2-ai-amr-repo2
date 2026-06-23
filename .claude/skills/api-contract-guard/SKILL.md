---
name: api-contract-guard
description: 외부 API, 스키마, 모델명, 컬럼명을 코드에 직접 박기 전에 계약과 런타임을 검증하는 스킬
user_invocable: true
tags: [contract, schema, api, validation, safety]
trigger: "외부 계약값을 하드코딩하려 할 때"
version: 1
---

# API Contract Guard

## Use When

- 외부 API 응답 필드를 문자열로 직접 쓰려 할 때
- DB 컬럼/테이블명을 코드에서 정의하려 할 때
- 모델명, endpoint, 설정 키를 추정으로 넣으려 할 때

## Rules

1. 문서와 런타임 확인이 먼저다
2. 상수는 한 곳에 모은다
3. 버전 의존 로직은 이유를 남긴다
4. 계약값은 SSOT 문서와 맞춘다

## Steps

### Step 1: 외부 의존 목록 적기

- API 필드명
- 모델명
- DB 컬럼명
- env key

### Step 2: 런타임 또는 공식 계약으로 확인

- 실제 응답 보기
- schema file 보기
- migration 보기
- official doc 보기

### Step 3: 중앙화

- `config.*`
- `constants.*`
- generated types
- schema contract file

### Step 4: 버전 주석

버전/이유/향후 재검토 지점을 적는다.

## Verify

- [ ] 하드코딩 전 실제 계약을 확인했다
- [ ] 상수가 중앙화됐다
- [ ] 버전 의존성 이유가 남아 있다
- [ ] SSOT 문서와 이름이 일치한다

## Failure / Fallback

- 런타임 확인이 당장 안 되면: 최소 공식 문서/스키마를 근거로 남긴다
- generated types가 없으면: TODO로 두지 말고 생성 계획을 적는다
