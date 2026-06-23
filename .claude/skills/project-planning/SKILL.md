---
name: project-planning
description: 새 프로젝트나 큰 기능 착수 전에 파일, 스킬, phase, 검증 계약까지 잠그는 실행 계약형 planning 스킬
user_invocable: true
tags: [planning, strategy, startup, roadmap, architecture]
trigger: "프로젝트를 처음 계획하거나 구현 전에 decision-complete plan이 필요할 때"
version: 2
---

# Project Planning

구현 전에 "무엇을 만들고 어떤 파일과 계약과 스킬을 어떤 순서로 쓸지"를 잠그는 스킬이다.

## Use When

- 새 프로젝트를 시작하기 전
- 큰 기능을 구현하기 전
- 요구사항은 있는데 file map, phase, 검증 경로가 흐릴 때
- 다음 구현자가 그대로 이어받을 수 있는 planning contract가 필요할 때

## Inputs

- 프로젝트명 또는 기능명
- 한 줄 문제 정의
- 목표 사용자
- 원하는 결과물
- stack
- target files 또는 후보 경로
- constraints
- unknowns
- verification command candidates

## Steps

### Step 1: Problem / Goal / Non-Goal을 분리한다

먼저 아래를 분리해서 적는다.

- Problem: 지금 무엇이 불편하거나 비어 있는가
- Goal: 이 작업이 끝나면 무엇이 가능해져야 하는가
- Non-Goal: 이번 phase에서 하지 않을 것은 무엇인가

`docs/ref/PRD.md`와 `docs/ref/PROJECT-PLAN.md`를 함께 연다.

### Step 2: Naming Contract를 잠근다

최소한 아래를 적는다.

- 핵심 entity 이름
- route 또는 API path
- table/schema 이름
- env var 이름
- 쓰지 않을 애매한 이름

계약명이 흔들리면 구현보다 먼저 `socratic-review` 또는 `api-contract-guard`로 보정한다.

### Step 3: File Map과 Folder Boundary를 적는다

`PROJECT-PLAN.md`의 `File Map`은 아래 종류를 명시한다.

- `create:` 새로 만들 파일
- `modify:` 수정할 기존 파일
- `keep:` 유지하되 계속 참조할 파일
- `candidate:` 경로는 미정이지만 경계는 알고 있는 파일

파일 경계 규칙은 `references/file-map-naming-rules.md`를 따른다.

### Step 4: Skill Routing을 적는다

적어도 아래 흐름 중 현재 작업에 필요한 스킬을 명시한다.

- `project-planning`
- `socratic-review`
- `project-bootstrap`
- `big-task`
- `api-contract-guard`
- `doc-sync`
- `session-retro`

정리 기준은 `references/canonical-skill-routing.md`를 따른다.

### Step 5: Phase Plan을 작성한다

각 phase마다 아래를 모두 채운다.

- `Goal:`
- `Files:`
- `Skills:`
- `Verification:`
- `Doc Sync:`
- `Exit Criteria:`
- `Decision Gates:`

상세 구조는 `references/plan-template.md`를 기준으로 쓴다.

### Step 6: Assumptions / Risks / Dependencies / Success Metrics를 잠근다

각 항목은 최소 1개 이상 적는다.

- Assumptions: 계획이 기대는 전제
- Risks: 실패 가능성, 일정/기술 위험
- Dependencies: 외부 API, 데이터, 승인, 사람
- Success Metrics: 사람이 확인 가능한 완료 기준

### Step 7: Planning Self-Review를 한다

아래 질문을 통과해야 한다.

- MVP와 later가 섞였는가
- 계약명이 추측인가
- 파일 경계가 모호한가
- phase별 verification / doc sync / exit criteria가 비어 있는가
- 다음 구현자가 어디서 시작해야 하는지 보이는가

상세 질문은 `references/planning-self-review.md`를 따른다.

### Step 8: 운영 문서에 반영한다

최소 산출물:

- `docs/ref/PRD.md`
- `docs/ref/PROJECT-PLAN.md`
- `docs/status/PROJECT-STATUS.md`
- 필요 시 `docs/status/DECISION-LOG.md`

구현 orchestration은 이후 `big-task`로 넘긴다.

## Not Done Until

- file path가 없는 plan은 완료가 아니다
- skill routing이 없는 plan은 완료가 아니다
- phase별 verify / doc sync / exit criteria가 비어 있으면 완료가 아니다
- placeholder가 남아 있으면 완료가 아니다

## Outputs

- 문제/목표/비목표가 구분된 `PRD.md`
- file map, skill routing, phase contract가 들어간 `PROJECT-PLAN.md`
- 현재 phase와 next actions가 반영된 `PROJECT-STATUS.md`
- 필요 시 주요 선택 근거가 적힌 `DECISION-LOG.md`

## Verify

- [ ] `PROJECT-PLAN.md`에 필수 heading이 모두 있다
- [ ] `Naming Contract`, `File Map`, `Skill Routing`이 명시되어 있다
- [ ] phase가 1개 이상 있고 각 phase에 `Files`, `Skills`, `Verification`, `Doc Sync`, `Exit Criteria`, `Decision Gates`가 있다
- [ ] placeholder가 남아 있지 않다
- [ ] `bash scripts/check-planning.sh` 또는 `bash scripts/check-project.sh`가 통과한다

## Failure / Fallback

- 정보가 부족하면: Discovery phase만 먼저 작성하고 미확정 항목을 `Open Questions`로 보낸다
- 범위가 너무 크면: MVP와 later backlog를 강제로 분리한다
- 계약명이 불확실하면: `socratic-review` 후 Naming Contract를 다시 잠근다
- 검증 명령이 아직 없으면: 최소 `bash scripts/check-project.sh`를 먼저 적고 이후 스택별 검증을 추가한다
