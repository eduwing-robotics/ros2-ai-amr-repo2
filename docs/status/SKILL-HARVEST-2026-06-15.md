# Skill Harvest — 2026-06-15

> 자동 실행 (주간 수확). **DRY-RUN 회차**: 파일로만 저장, 슬랙 미발송 (명세 체크리스트 §코워크 등록 시 준수).
> 윈도우: 2026-06-08 ~ 2026-06-15 (최근 7일).
> 직전 회차: `SKILL-HARVEST-2026-06-04.md` (3건 후보 제안, 아직 채택 전).

## ⚠️ 데이터 소스 한계 (이번 회차)

직전 회차와 동일하게, 명세가 지정한 1차 입력 소스가 이번 실행 환경에서 **도달 불가**였습니다. 투명하게 기록합니다.

| 소스 | 경로 | 상태 |
|---|---|---|
| Codex 세션 인덱스 | `/Users/family/.codex/session_index.jsonl` | ❌ 연결 폴더 밖 — 읽기 불가 (bash 샌드박스/Read 툴 모두) |
| Codex archived | `/Users/family/.codex/archived_sessions/*.jsonl` | ❌ 동일 |
| Claude transcripts | `/Users/family/.claude/projects/*/` | ❌ 동일 |
| 기존 스킬/자동화 | `URHYNIX/.claude/{skills,agents,automations}/` | ✅ 도달 가능 |
| 로컬 세션 목록 | `session_info` MCP (437개 세션, 최신순) | ✅ 대체 소스로 사용 |

스케줄 실행이라 사용자에게 폴더 접근 승인을 요청할 수 없어, `~/.codex` 대신 **`session_info` MCP의 세션 제목**을 카테고리 신호로 사용했습니다. 세션 목록에는 타임스탬프가 없어 7일 윈도우는 "최신순 상위 ~200개"로 근사했습니다. **이 한계는 2회 연속 재발**했으므로, 다음 정식 회차 전 `~/.codex`를 연결 폴더로 추가하는 것을 강력 권고합니다 (아래 다음 액션 참조).

## 카테고리 빈도 (도달 가능 신호 기준, 상위 ~200 세션)

대부분의 최근 세션은 **이미 스케줄된 자동화 실행**(Taillog/Vibehub/Mungmungfit/Nightly vision labeling/Daily journal·recap·media·coaching 등)이라 후보에서 제외됩니다. 수동·반복으로 보이는 클러스터만 집계:

| 카테고리 | 빈도(근사) | 후보? | 직전 회차 대비 |
|---|---|---|---|
| 자동화 운영/관리 (상태 점검·스케줄 설정·폴더 확인·태스크 통합) | ~10+ | ✅ (미커버) | 지속 (7→10+) |
| 다운로드/디스크 정리 ("Clean downloads dmg") | ~10 | ✅ (미커버, URHYNIX 비특화) | 지속 (4→10) |
| 텔레그램 히스토리 통합 ("Telegram history consolidate") | ~5 | ✅ (미커버) | **신규** (1→5, 임계값 첫 돌파) |
| 콘텐츠/시각화 생성 (RC카 조립·배선, 로봇 부트캠프 슬라이드) | ~3 | ✅ (부분 커버) | 지속 (3→3) |
| GitHub 스킬 동기화 ("Github skill sync") | 2 | ❌ (<3) | 관찰 중 |
| 로컬 LLM 전환 검토 (런타임/대체 자동화 질문) | 2~3 | ⚠️ 경계값 | 신규 관찰 |
| 기타 단발 (MVP 학습·문서 우선순위·Claude Design 사용법) | — | ❌ | — |

## 신규 후보 (1건)

### 1. telegram-history-consolidate (skill)
- **카테고리**: 텔레그램 히스토리 통합
- **빈도**: 7일간 ~5회 (임계값 3회 첫 돌파)
- **근거** (세션 제목, session_info MCP):
  - "Telegram history consolidate" (5개 세션, 최신순 상위~중위에 반복 등장)
- **제안 위치**: `.claude/skills/telegram-history-consolidate/SKILL.md` (단, URHYNIX 비특화일 경우 전역 `~/.codex/skills`가 적절)
- **핵심 동작**: 텔레그램 대화/내보내기 데이터를 수집 → 중복·잡음 제거 → 날짜·주제별로 정규화된 단일 아카이브로 통합, 표준 포맷 출력. 결정적·템플릿형이라 subagent보다 skill 적합.
- **예상 효과**: 매주 반복되는 수동 통합 작업을 1콜 워크플로우로 표준화.
- **주의**: 세션 제목만으로 판단 — 실제 입력 소스/포맷은 transcript 확인이 필요(현재 도달 불가). 채택 전 1회 transcript 검증 권장.

## 이월 후보 (직전 회차 제안 — 아직 미채택, 신호 지속/강화)

직전 `2026-06-04` 회차에서 제안된 3건은 채택 전 상태이며, 이번 윈도우에서도 신호가 유지 또는 강화되었습니다. 중복 제안을 피하기 위해 상태만 갱신합니다.

| 후보 | 타입 | 이번 빈도 | 상태 |
|---|---|---|---|
| `automation-audit` | subagent | ~10+ (강화) | **재확인** — 가장 강한 신호. 우선 채택 권고. |
| `downloads-tidy` | skill | ~10 (강화) | **재확인** — 단 URHYNIX 비특화, 전역 스킬 권고. |
| `assembly-visual-guide` | skill | ~3 (유지) | 유지 — 임계값 충족 지속. |

상세 카드는 `SKILL-HARVEST-2026-06-04.md` §신규 후보 1~3 참조.

## 이미 자동화된 영역 (중복 제외)

- **daily-recap** → `.claude/automations/daily-recap.md`
- **morning/nightly orchestrator** → `.claude/automations/urhynix-{morning,nightly}-orchestrator.md`
- **타 프로젝트 스케줄 자동화** (URHYNIX 무관, 제외): Taillog (morning/nightly/weekly/ai-data/daily-guard/doc-drift-guard), Vibehub (daily orchestrator/pipeline/autoresearch/seo audit/editorial/drift guard/dedup guard/auto publish/ingest/db retention/source health/media publish/self critique), Mungmungfit instagram (check/seed gen/saturday), Nightly vision labeling, Daily coaching synthetic gen, Daily journal loop, Daily media publish, Daily master harness, Weekly monday/harness review
- **문서 정합성** → `doc-audit` (agent), `doc-sync`/`doc-framework` (skill)
- **PR/코드 리뷰** → `code-review-graph-ops`, `socratic-review`
- **보안 검토** → `secret-scan`, `edge-hardening`
- **테스트 트리아지** → `parallel-qa`
- **DB 마이그레이션** → `migration-manifest`
- **설계 평가** → `socratic-review`, `change-impact-map`

## 다음 액션

- [ ] **신규** 후보 1 (telegram-history-consolidate) 채택 여부 결정 — transcript 1회 검증 후
- [ ] 이월 후보 1 (automation-audit) 채택 여부 결정 — **2주 연속 최강 신호**, 우선순위 최상
- [ ] 이월 후보 2 (downloads-tidy) 전역 vs 프로젝트 스킬 배치 결정
- [ ] 이월 후보 3 (assembly-visual-guide) 채택 여부 결정
- [ ] **⚠️ 데이터 소스 복구 (2회 연속 차단)**: `~/.codex`(또는 상위 `/Users/family`)를 Cowork 연결 폴더로 추가 → codex 세션 인덱스/archived/transcript 정밀 스캔 복구. 미복구 시 본 수확은 세션 제목 근사에 계속 의존.
- [ ] 채택 시 사용자가 수동으로 스킬 파일 생성 (자동 생성 금지 — 명세 룰)
- [ ] 슬랙 알림(`C0B5Q43A27R`)은 이번 회차 **미발송** (dry-run 정책 + 무인 실행 시 write 액션 보류). cron 정식 활성화 및 사용자 컨펌 후 발송 전환.

---
*자동 생성: skill-harvest (dry-run, 무인 스케줄 실행). 후보는 제안일 뿐 — 채택은 사용자 컨펌 후. 슬랙 미발송.*
