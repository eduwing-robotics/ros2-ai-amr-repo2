---
name: code-review-graph-ops
description: docs-heavy 또는 cross-cutting 코드베이스에서 그래프 기반으로 영향 범위를 좁히는 스킬
user_invocable: true
tags: [graph, impact-analysis, review, refactor]
trigger: "중간 이상 규모 변경 전, 영향 범위가 넓고 텍스트 검색만으로 노이즈가 많을 때"
version: 1
---

# Code Review Graph Ops

## Use When

- cross-module 변경 전
- docs-heavy repo에서 `rg` 결과가 너무 넓을 때
- refactor 전 테스트 범위를 좁히고 싶을 때

## Rules

1. text lookup은 `rg`
2. impact lookup은 graph
3. 둘 다 필요하면 섞어서 쓴다

## Steps

### Step 1: graph 도구 존재 확인

```bash
code-review-graph status
```

### Step 2: ignore 범위 조정

보통 제외:
- docs
- build/dist
- caches
- generated output

포함:
- `src/**`
- `tests/**`

### Step 3: build 또는 update

```bash
code-review-graph build
code-review-graph update
```

### Step 4: 영향 파일 좁히기

graph로 관련 파일 세트를 좁힌 뒤, 그 안에서 `rg`로 실제 symbol/command를 찾는다.

## Verify

- [ ] graph가 실제 authored files를 포함한다
- [ ] docs/build noise가 줄었다
- [ ] 관련 파일 집합을 좁힌 뒤 text lookup을 수행했다

## Failure / Fallback

- graph 도구가 없으면: `rg` + 수동 영향 맵으로 대체
- 결과가 너무 넓거나 비면: ignore와 build 상태를 다시 본다
