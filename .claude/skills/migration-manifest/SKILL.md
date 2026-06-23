---
name: migration-manifest
description: 마이그레이션이나 대규모 리팩터링을 parity ID와 wave로 관리하는 스킬
user_invocable: true
tags: [migration, refactor, parity, waves, tracking]
trigger: "앱 이전, 대규모 구조 변경, 메이저 업그레이드"
version: 1
---

# Migration Manifest

## Use When

- A -> B 스택 이전
- 큰 폴더/아키텍처 재편
- 메이저 버전 업그레이드

## Rules

1. 모든 기능에 parity ID 부여
2. wave 순서 정의
3. 상태 추적
4. 원본과 대상을 명확히 분리

## Steps

### Step 1: 기능 인벤토리

현재 앱의 화면/기능/API를 나열한다.

### Step 2: parity ID 부여

예:
- `AUTH-001`
- `DASH-001`
- `SET-001`

### Step 3: wave 분류

- W0 foundation
- W1 core
- W2 features
- W3 polish

### Step 4: manifest 작성

권장 파일:
- `docs/migration-manifest.yaml`

### Step 5: wave 단위 실행 + 검증

각 item:
- pending
- in-progress
- done
- verified

## Verify

- [ ] 모든 핵심 기능에 ID가 있다
- [ ] wave가 의존성을 반영한다
- [ ] 현재 wave 상태를 추적할 수 있다
- [ ] 누락 기능을 대조할 수 있다

## Failure / Fallback

- 원본 접근이 어려우면: 스크린샷/문서 기반으로 시작
- 기능이 너무 많으면: P0 핵심 기능만 먼저 manifest화한다
