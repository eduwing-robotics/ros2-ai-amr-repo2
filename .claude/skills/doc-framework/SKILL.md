---
name: doc-framework
description: 프로젝트 독립적 문서 관리 프레임워크를 이식할 때 사용하는 범용 스킬
user_invocable: true
tags: [documentation, ssot, bootstrap, governance]
trigger: "새 프로젝트에 문서 체계를 심거나, 기존 프로젝트 문서가 꼬였을 때"
version: 2
---

# Doc Framework

프로젝트의 언어, 프레임워크, 도메인과 무관하게 재사용 가능한 문서 운영 프레임워크다.

## Core Principles

1. 정본 1곳 원칙
2. Tier 기반 문서 읽기
3. change class 기반 문서 동기화
4. 구현과 문서 충돌 시 구현 우선

## Use When

- 새 프로젝트에 문서 체계를 처음 심을 때
- 문서가 점점 꼬이고 있을 때
- 어떤 문서가 정본인지 다시 잡아야 할 때
- 상태 문서가 오래 쌓여 current truth를 잃었을 때

## Inputs

- 프로젝트 루트 구조
- 현재 진입 문서 존재 여부
- 이미 있는 `docs/`, `ai-context/`, `.claude/` 구조
- 최근 변경 파일 또는 현재 작업 흐름

## Target Structure

```text
docs/
├── status/
│   ├── PROJECT-STATUS.md
│   └── DECISION-LOG.md
├── ref/
│   ├── ARCHITECTURE.md
│   ├── PRD.md
│   ├── SCHEMA.md
│   └── (도메인 ref)
└── archive/
    └── decisions-resolved.md
```

## Loading Tiers

| Tier | Purpose | Typical Files |
|---|---|---|
| 0 | runtime truth | code, logs, running app |
| 1 | entry + current state | `AGENTS.md`, `CLAUDE.md`, `PROJECT-STATUS.md` |
| 2 | structure + contract | `ARCHITECTURE.md`, `PRD.md`, `SCHEMA.md`, route/spec docs |
| 3 | reusable references | `templates/`, `patterns/`, examples, notes |

## Steps

### Step 1: 현재 문서 구조 진단

아래를 먼저 확인한다.

```bash
find docs -maxdepth 3 -type f 2>/dev/null | sort
find ai-context -maxdepth 2 -type f 2>/dev/null | sort
```

판단:
- entry 문서가 있는가
- status 문서가 current truth 역할을 하는가
- ref 문서가 구조/계약을 설명하는가
- 같은 사실이 여러 문서에 중복돼 있는가

### Step 2: 최소 정본 문서 잠금

프로젝트마다 최소한 아래 다섯 개는 있어야 한다.

1. `AGENTS.md` 또는 `CLAUDE.md`
2. `docs/status/PROJECT-STATUS.md`
3. `docs/status/DECISION-LOG.md`
4. `docs/ref/ARCHITECTURE.md`
5. `ai-context/START-HERE.md`

### Step 3: change class 표 만들기

프로젝트에 맞게 아래 표를 만든다.

```markdown
| 변경 영역 | 필수 갱신 | 조건부 갱신 |
|---|---|---|
| any code | PROJECT-STATUS.md | — |
| route/ui | ROUTE-SPECS.md | PRD.md |
| schema/model | SCHEMA.md | ARCHITECTURE.md |
| pipeline/worker | ARCHITECTURE.md | ops/ref docs |
| infra/config | ARCHITECTURE.md | deploy/env docs |
| boundary decision | DECISION-LOG.md | archive |
```

### Step 4: status 문서 규칙 고정

`PROJECT-STATUS.md` 규칙:
- current phase는 한 줄로 유지
- active tracks는 현재 진행 중 항목만
- done 항목은 날짜 포함
- next actions는 짧고 실행 가능해야 함

`DECISION-LOG.md` 규칙:
- pending 중심 유지
- 해결된 결정은 archive로 이동
- 구조/경계/원칙 변경만 기록

### Step 5: 운영 자산 연결

문서 프레임워크는 아래 운영 자산과 연결되면 안정적이다.

- `.claude/commands/doc-update.md`
- `.claude/skills/doc-sync/SKILL.md`
- `scripts/check-project.sh`
- `ai-context/START-HERE.md`

### Step 6: 검증 루프 연결

문서 체계는 검증 루프와 같이 잠겨야 한다.

- 무엇을 실행할지 `PROJECT-STATUS.md`에 적는다
- 작업 끝나면 `doc-sync`로 누락 문서 점검
- 회고 시 오래된 규칙을 승격/폐기한다

## Outputs

- 문서 계층 정리
- 최소 정본 문서 세트 확보
- change class 매핑 초안
- 문서/검증/회고 루프 연결

## Verify

- [ ] entry 문서가 존재한다
- [ ] `docs/status`와 `docs/ref` 구조가 구분돼 있다
- [ ] current truth를 보는 문서가 명확하다
- [ ] change class 표가 존재한다
- [ ] 문서 동기화 절차가 `doc-update` 또는 `doc-sync`로 연결돼 있다
- [ ] 중복 사실이 줄어들었다

## Failure / Fallback

- 문서가 너무 많아 정리가 막히면: entry/status/ref 3축만 먼저 살린다
- 어떤 문서가 정본인지 모르겠으면: 구현과 실행 결과를 먼저 확인한다
- 프로젝트가 아주 작으면: `SCHEMA.md` 같은 문서는 나중으로 미룬다
- 팀이 문서에 저항이 크면: `PROJECT-STATUS.md`와 `ARCHITECTURE.md` 두 개만 먼저 잠근다
