---
name: design-to-code
description: 화면 설계에서 route/API/구조 문서까지 연결하는 범용 스킬
user_invocable: true
tags: [design, ui, route-map, frontend, planning]
trigger: "새 화면 설계, 리디자인, 프론트엔드 구조화가 필요할 때"
version: 1
---

# Design To Code

## Use When

- 새 프로젝트의 UI를 처음 설계할 때
- 화면을 추가하거나 리디자인할 때
- 프론트 라우트와 백엔드 계약을 같이 정렬해야 할 때

## Core Principles

1. 시안 먼저, 코드 나중
2. 화면 목록과 유저 플로우를 먼저 잠근다
3. route/API 매핑을 문서로 남긴다
4. 디자인 토큰은 SSOT로 둔다

## Steps

### Step 1: 화면 목록 작성

```markdown
| ID | Screen | User Flow | Priority |
|---|---|---|---|
| S-001 | Login | entry -> auth -> dashboard | P0 |
```

### Step 2: 시안 또는 와이어프레임 확보

- Stitch
- Figma
- 손그림 스캔
- 텍스트 스케치

중요한 건 "코드 전에 화면을 보게 만드는 것"이다.

### Step 3: 디자인 결정 기록

`docs/ref/DESIGN-DECISIONS.md` 또는 비슷한 문서에 기록:

- layout
- navigation
- typography
- color/tokens
- adopt/reject 이유

### Step 4: route map 작성

```markdown
| Screen ID | Front Route | API | Method | Notes |
|---|---|---|---|---|
| S-001 | /login | /api/auth/login | POST | email/password |
```

권장 위치:
- `docs/ref/ROUTE-MAP.md`

### Step 5: 폴더 구조 생성

라우트맵 기준으로 파일 구조를 만든다.

### Step 6: 토큰 잠금

색, spacing, radius, type scale은 하드코딩보다 `tokens` 파일에 둔다.

## Outputs

- screen inventory
- design decisions
- route map
- folder structure plan
- token source

## Verify

- [ ] 모든 핵심 화면이 ID와 함께 정리되었다
- [ ] 시안/와이어프레임이 최소 1개 이상 있다
- [ ] route/API 매핑 문서가 있다
- [ ] token SSOT 위치가 정해졌다
- [ ] 폴더 구조가 route map과 연결된다

## Failure / Fallback

- 디자인 도구가 없으면: 텍스트 와이어프레임으로 시작
- 화면이 너무 많으면: P0 3~5개만 먼저 잠근다
- API가 아직 없으면: `stub`로 표시하고 route 중심으로 먼저 진행
