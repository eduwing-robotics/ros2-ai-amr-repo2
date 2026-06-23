---
name: project-bootstrap
description: 새 프로젝트 시작 시 최소 골격과 진입 문서를 빠르게 잠그는 스킬
user_invocable: true
tags: [bootstrap, scaffold, startup, docs]
trigger: "새 프로젝트를 시작하거나 기존 프로젝트를 하네스 구조로 옮길 때"
version: 5
---

# Project Bootstrap

새 프로젝트의 "코드 이전에 필요한 운영 골격"을 잠그는 스킬이다.

## First Files

1. `AGENTS.md`
2. `CLAUDE.md`
3. `ai-context/START-HERE.md`
4. `docs/status/PROJECT-STATUS.md`
5. `docs/status/DECISION-LOG.md`
6. `docs/ref/ARCHITECTURE.md`
7. `docs/ref/PRD.md`
8. `docs/ref/PROJECT-PLAN.md`
9. `docs/ref/STACK-PROFILES.md`

## Rule

- 구현보다 먼저 목적, 구조, 검증 경로를 잠근다.

## Use When

- 새 저장소를 처음 만들 때
- hackathon / MVP / 새 side project 시작 시
- 기존 저장소에 AI 협업 구조를 심고 싶을 때

## Inputs

- 프로젝트명
- 새 프로젝트 위치
- 한 줄 설명
- 첫 검증 명령 후보
- 필요 시 stack profile 이름

## Fast Path

템플릿 전체 루트에서:

```bash
bash scripts/bootstrap-project.sh <project-name> <destination-path>
```

예:

```bash
bash scripts/bootstrap-project.sh dogcoach-v2 /tmp/dogcoach-v2
```

stack-aware 예:

```bash
bash scripts/bootstrap-project.sh dogcoach-v2 /tmp/dogcoach-v2 --stack-profile "Next.js + FastAPI + Supabase"
```

## Steps

### Step 1: scaffold 복사

`scaffold/project-root/`를 새 프로젝트 루트에 복사한다.

복사 후 최소 구조:

```text
project-root/
├── AGENTS.md
├── CLAUDE.md
├── ai-context/
├── docs/
├── .claude/
├── .codex/
├── .obsidian/
└── scripts/
```

### Step 2: 이름과 날짜 치환

`bootstrap-project.sh`는 아래 placeholder를 치환한다.

- `URHYNIX`
- `2026-05-26`

`--stack-profile`이 있으면 `STACK-PROFILES.md`에서 해당 profile starter를 읽어

- `PROJECT-PLAN.md`
- `ARCHITECTURE.md`
- `PROJECT-STATUS.md`
- 필요 시 `PRD.md`

초안을 profile-aware하게 채운다.

수동 복사했다면 직접 바꾼다.

### Step 3: entry 문서 잠금

반드시 먼저 채우는 파일:

1. `AGENTS.md` — 읽기 순서와 규칙
2. `CLAUDE.md` — 짧은 진입점
3. `ai-context/START-HERE.md` — 현재 초점

### Step 4: status 문서 잠금

`PROJECT-STATUS.md`에 아래를 적는다.

- current phase
- active tracks
- 첫 검증 명령
- next actions

`DECISION-LOG.md`에는 초기 구조 채택 이유를 남긴다.

### Step 5: 구조 문서 잠금

`ARCHITECTURE.md`에는 최소한 아래를 적는다.

- 시스템 overview
- 레이어
- 외부 의존성
- repo boundary

`PRD.md`에는 goal/scope/non-goal을 적는다.

`STACK-PROFILES.md`에서 가장 가까운 starter profile을 고른다.

`PROJECT-PLAN.md`에는 최소한 아래를 적는다.

- phases
- assumptions
- risks
- dependencies
- verification
- exit criteria
- intake verdict
- impact map summary
- sub-agent opportunities

`PROJECT-STATUS.md`에는 추가로 아래를 적는다.

- current sub-agent work
- handoff capsule
- evidence status

### Step 6: 운영 자산 최소 연결

- `.claude/settings.json`
- `.codex/hooks.json`
- `.obsidian/templates.json`
- `scripts/check-project.sh`

### Step 7: 첫 검증 실행

새 프로젝트 루트에서:

```bash
bash scripts/check-project.sh
```

그 다음 스택별 검증 명령을 `PROJECT-STATUS.md`에 추가한다.

## Outputs

- 실행 가능한 프로젝트 골격
- AI 진입 문서
- 최소 상태/구조 문서
- 계획 문서
- stack profile reference
- 첫 검증 경로

## Verify

- [ ] `AGENTS.md`, `CLAUDE.md`, `START-HERE.md`가 존재한다
- [ ] `PROJECT-STATUS.md`에 current phase와 검증 명령이 있다
- [ ] `ARCHITECTURE.md`, `PRD.md`, `PROJECT-PLAN.md`, `STACK-PROFILES.md`가 존재한다
- [ ] `.claude`, `.codex`, `.obsidian` 최소 구조가 존재한다
- [ ] `bash scripts/check-project.sh`가 통과한다

## Failure / Fallback

- 프로젝트명이 아직 불확실하면 placeholder 상태로 먼저 부트스트랩한다
- docs를 다 채우기 부담되면 `AGENTS`, `PROJECT-STATUS`, `ARCHITECTURE` 세 개만 먼저 잠근다
- Obsidian을 안 쓰면 `.obsidian`은 남겨두되 최소 설정만 유지한다
