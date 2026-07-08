# Skill Harvest — 2026-07-08

> 자동 실행 (주간 skill-harvest). **첫 회차 = dry-run**: 파일 저장만, 슬랙 미발송.
> 명세: `.claude/automations/skill-harvest.md`

## ⚠️ 데이터 소스 한계 (이번 회차)

명세가 지정한 1차 입력이 이번 비대화형(스케줄) 실행에서 **접근 불가**였다:

| 지정 입력 | 상태 |
|---|---|
| `/Users/family/.codex/session_index.jsonl` | ❌ 연결 폴더(URHYNIX) 밖 → 읽기 불가 |
| `/Users/family/.codex/archived_sessions/*.jsonl` | ❌ 동일 |
| `/Users/family/.claude/projects/*/` | ❌ 동일 |

비대화형 실행이라 폴더 접근 승인(`request_cowork_directory`)을 받을 수 없어 위 경로들을 열지 못했다.
대신 **Cowork 세션 레지스트리**(`session_info.list_sessions`, 총 459개 중 최근 200개)를 대체 신호로 사용했다.

한계:
- 세션 레지스트리는 **타임스탬프를 노출하지 않아** 엄격한 "최근 7일" 윈도우를 확정할 수 없다. 아래 빈도는 "최근순 상위 200개 세션" 기준의 근사치다.
- 레지스트리는 URHYNIX 뿐 아니라 **Taillog·Mungmungfit·Vibehub 등 타 프로젝트**의 스케줄 자동화 실행을 다수 포함한다. URHYNIX 전용 코덱스/클로드 세션 신호는 이번에 확보하지 못했다.

→ 이번 결과는 **참고용 근사치**다. 정확한 하베스트를 위해서는 codex/claude 인덱스 경로를 URHYNIX 워크스페이스에 마운트하거나, 대화형 세션에서 `/skill-harvest`를 한 번 돌려 폴더 접근을 승인하는 것이 필요하다.

## 관측된 세션 분포 (상위 200개, 근사)

대부분이 **이미 스케줄된 자동화의 실행 로그**였다 (신규 수동 패턴 아님 → 제외 대상):

- Taillog orchestrator (morning/nightly/weekly/ai-data/daily-guard/doc-drift-guard) — 다수
- Vibehub (daily orchestrator·pipeline·autoresearch·drift-guard·dedup·editorial·media-publish·seo-audit·ingest·source-health·db-retention) — 다수
- Mungmungfit instagram (check/saturday/seed-gen) — 다수
- Daily recap / Daily journal loop / Daily coaching synthetic gen / Nightly vision labeling / Daily master harness / Weekly monday review / Clean downloads dmg / Skill harvest — 각 다수

이 항목들은 카테고리상 **콘텐츠 생성·요약·문서 드리프트·DB 유지보수**에 해당하나, 전부 **기존 스케줄 자동화가 이미 커버**하므로 후보에서 제외한다.

## 신규 후보 (2건, 잠정)

임계값(7일 3회)을 세션 레지스트리 근사 기준으로 충족하고, 기존 스킬/자동화에 없는 항목만.

### 1. automation-inventory (subagent)
- **카테고리**: 자동화 관리 / 스케줄 태스크 점검
- **빈도 (근사)**: 상위 200개 중 9+회
- **근거** (세션 제목):
  - "Automation task status" (×2)
  - "Automation scheduling setup"
  - "Automation folder prompts"
  - "Check automation folder contents"
  - "Configure scheduled orchestrator tasks"
  - "Set up daily and weekly automations"
  - "Find tasks to combine automation"
  - "Check automated scheduling system"
- **제안 위치**: `.claude/agents/automation-inventory.md`
- **핵심 동작**: 등록된 스케줄 태스크·`automations/*.md`·cron 전체를 한 화면에 인벤토리 → 중복/충돌/유휴(orphan) 자동화 탐지, 통합 후보 제안. 사용자가 반복적으로 수동 수행 중인 "자동화 현황 파악 + 정리" 작업을 대체.
- **예상 효과**: 자동화 상태 점검을 매번 새 세션으로 여는 대신 1커맨드로 요약. 중복 오케스트레이터 통합 판단 지원.
- **주의**: 기존 `task-intake-router`(신규 요청 라우팅)와 범위가 다름(이쪽은 기존 자동화 감사). 겹치지 않는지 채택 전 확인 필요.

### 2. telegram-history-consolidate (skill)
- **카테고리**: 콘텐츠/로그 통합 (Telegram 이력)
- **빈도 (근사)**: 상위 200개 중 3회
- **근거** (세션 제목):
  - "Telegram history consolidate" (×3, 각기 다른 세션 ID)
- **제안 위치**: `.claude/skills/telegram-history-consolidate/`
- **핵심 동작**: Telegram 대화 이력을 정형 포맷으로 수집·병합·중복 제거 후 아카이브. 템플릿 기반 결정적 워크플로우.
- **예상 효과**: 매번 수동으로 반복하던 이력 통합을 1스킬로. (단, URHYNIX 범위인지 타 프로젝트 작업인지 확인 필요 — 세션 cwd가 URHYNIX가 아님.)

## 이미 자동화된 영역 (중복 제외)

- **daily-recap** (요약) — `automations/daily-recap.md`
- **skill-harvest** (본 자동화) — `automations/skill-harvest.md`
- **urhynix-morning-orchestrator / urhynix-nightly-orchestrator** — `automations/`
- **문서 정합성/드리프트**: `doc-health-audit`, `doc-sync`, `doc-framework`, `stack-drift-guard`, `ip-drift-resync`, agents `doc-audit` — 이미 커버
- **보안 검토**: `secret-scan`, `edge-hardening` — 커버
- **PR/코드 리뷰**: `code-review-graph-ops`, `socratic-review`, `parallel-qa`, `evidence-review` — 커버
- **세션 인수인계**: `session-handoff`, `session-retro` — 커버
- **DB 마이그레이션/헬스**: `migration-manifest`, `supabase-db-health-ping`, `supabase-mcp` — 커버
- **설계 평가/콘텐츠 생성(로봇)**: `design-to-code`, `change-impact-map`, 다수의 `urhynix-*` 브링업 스킬 — 커버

## 다음 액션

- [ ] **데이터 소스 복구**: codex/claude 세션 인덱스를 하베스트가 읽을 수 있게 (a) URHYNIX 워크스페이스에 심볼릭/마운트, 또는 (b) 대화형에서 `/skill-harvest` 1회 실행해 폴더 접근 승인. → 다음 회차부터 정확한 7일 윈도우 집계 가능.
- [ ] 후보 1 (automation-inventory) 채택 여부 결정 — `task-intake-router`와 범위 중복 확인.
- [ ] 후보 2 (telegram-history-consolidate) 채택 여부 결정 — URHYNIX 범위 해당 여부 확인.
- [ ] 자동 생성 금지 규칙 준수: 채택 시 사용자가 수동으로 스킬 파일 생성.
- [ ] 슬랙 발송: **이번 회차 미발송** (첫 회차 dry-run 규칙). 사용자 OK 후 cron 활성화 시 채널 `C0B5Q43A27R`로 요약 전송.

---
*생성: 2026-07-08 · skill-harvest 자동 실행 · 대체 소스(session registry) 기반 근사치 · 슬랙 미발송(dry-run)*
