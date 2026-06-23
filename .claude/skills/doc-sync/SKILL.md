---
name: doc-sync
description: 코드 변경 후 어떤 문서를 같이 고쳐야 하는지 change class 기준으로 좁혀주는 점검 스킬
user_invocable: true
tags: [documentation, drift, post-edit, ssot]
trigger: "코드 변경 후 문서 누락이 걱정될 때"
version: 1
---

# Doc Sync

문서를 많이 쓰게 만들기보다, 꼭 고쳐야 할 문서를 빠르게 찾는 데 목적이 있다.

## Use When

- 코드 변경 직후
- 큰 작업 마무리 전
- `/self-review` 전에
- "PROJECT-STATUS만 고치면 되나?"가 헷갈릴 때

## Inputs

- working tree 변경사항
- staged 변경사항
- 새로 추가된 파일
- 프로젝트의 SSOT 문서 세트

## Steps

### Step 1: 변경 파일 수집

```bash
git diff --name-only HEAD
git diff --name-only --cached
git status --porcelain
```

### Step 2: trivial 변경 필터

아래만 바뀌면 문서 갱신이 불필요할 수 있다.

- 오탈자/포맷팅
- 테스트 fixture/log/generated 파일
- 주석만 수정

단, 동작이나 경계가 바뀌면 trivial이 아니다.

### Step 3: change class 분류

| Class | Example | Must Update | Maybe Update |
|---|---|---|---|
| route/surface | page, route, endpoint | `PROJECT-STATUS.md`, route/spec docs | `PRD.md`, `ARCHITECTURE.md` |
| schema/model | DB, types, contracts | `SCHEMA.md`, `PROJECT-STATUS.md` | `DECISION-LOG.md` |
| pipeline/flow | workers, jobs, orchestration | `PROJECT-STATUS.md`, `ARCHITECTURE.md` | ops docs |
| automation/prompt | automation, skills, hooks | `PROJECT-STATUS.md`, ops docs | `AGENTS.md` |
| design/token | UI, CSS, tokens | `PROJECT-STATUS.md` | design or route docs |
| config/infra | env, build, CI | infra docs or `ARCHITECTURE.md` | `DECISION-LOG.md` |

### Step 4: 필수 문서 누락 판정

각 문서에 대해 아래 중 하나를 판정한다.

- `updated`
- `not needed`
- `missing`

`missing`이면 이유와 섹션 힌트를 같이 적는다.

### Step 5: companion checks 제안

| 상황 | Companion Check |
|---|---|
| UI/route 변경 | visual smoke, UI audit |
| schema/contract 변경 | contract test, typecheck |
| automation/hook 변경 | related script run |
| 큰 변경 | self-review |

## Output Format

```markdown
## Doc Sync Report

### Change classes
- route/surface
- design/token

### Must update
| 문서 | 이유 | 상태 | 섹션 힌트 |
|---|---|---|---|
| docs/status/PROJECT-STATUS.md | 현재 동작 변화 반영 | missing | Active Tracks |
| docs/ref/ARCHITECTURE.md | 구조 경계 변경 | updated | Layers |

### Companion checks
- npm run build
- visual smoke

### Verdict
- ⚠️ 1 doc needs update
```

## Verify

- [ ] 변경 파일이 모두 최소 한 class에 분류되었다
- [ ] 필수 문서 누락 여부가 판정되었다
- [ ] `PROJECT-STATUS.md` 필요 여부가 검토되었다
- [ ] 구조/원칙 변경 시 `DECISION-LOG.md` 필요 여부가 검토되었다

## Failure / Fallback

- class가 애매하면 가장 가까운 두 class에 모두 걸친다
- 시간이 없으면 최소 `PROJECT-STATUS.md`만 우선 맞춘다
- 문서가 아직 없으면 `doc-framework`를 먼저 실행한다
