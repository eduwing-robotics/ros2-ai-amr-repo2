# Skill Harvest — 2026-06-04

> 자동 실행 (주간 수확). **DRY-RUN 회차**: 파일로만 저장, 슬랙 미발송 (명세 체크리스트 §코워크 등록 시 준수).
> 윈도우: 2026-05-28 ~ 2026-06-04 (최근 7일).

## ⚠️ 데이터 소스 한계 (이번 회차)

명세가 지정한 1차 입력 소스가 이번 실행 환경에서 **도달 불가**였습니다. 투명하게 기록합니다.

| 소스 | 경로 | 상태 |
|---|---|---|
| Codex 세션 인덱스 | `/Users/family/.codex/session_index.jsonl` | ❌ 연결 폴더 밖 — 읽기 불가 (샌드박스/파일툴 모두) |
| Codex archived | `/Users/family/.codex/archived_sessions/*.jsonl` | ❌ 동일 |
| Claude transcripts | `/Users/family/.claude/projects/*/` | ❌ 동일 |
| 기존 스킬/자동화 | `URHYNIX/.claude/{skills,agents,automations}/` | ✅ 도달 가능 |
| 로컬 세션 목록 | `session_info` MCP (405개 세션, 최신순) | ✅ 대체 소스로 사용 |

스케줄 실행이라 사용자에게 폴더 접근 승인을 요청할 수 없어, `~/.codex` 대신 **`session_info` MCP의 세션 제목**을 카테고리 신호로 사용했습니다. 세션 목록에는 타임스탬프가 없어 7일 윈도우는 "최신순 상위 ~90개"로 근사했습니다. 다음 정식 회차에서는 `~/.codex` 폴더를 연결 폴더로 추가하면 정밀도가 올라갑니다.

## 카테고리 빈도 (도달 가능 신호 기준, 상위 ~90 세션)

대부분의 최근 세션은 **이미 스케줄된 자동화 실행**이라 후보에서 제외됩니다 (아래 "이미 자동화된 영역"). 수동·반복으로 보이는 클러스터만 집계:

| 카테고리 | 빈도 | 후보? |
|---|---|---|
| 자동화 운영/관리 (상태 점검·폴더 확인·태스크 통합·스케줄 설정) | 7 | ✅ (미커버) |
| 다운로드/디스크 정리 ("Clean downloads dmg") | 4 | ✅ (미커버, 단 URHYNIX 비특화) |
| 콘텐츠/시각화 생성 (RC카 조립·배선 가이드, 로봇 부트캠프 슬라이드) | 3 | ✅ (부분 커버) |
| 텔레그램 히스토리 통합 | 1 | ❌ (<3) |
| 기타 단발 | — | ❌ |

## 신규 후보 (3건)

### 1. automation-audit (subagent)
- **카테고리**: 자동화 운영/관리
- **빈도**: 7일간 ~7회
- **근거** (세션 제목, session_info MCP):
  - "Automation task status" (x2)
  - "Automation scheduling setup"
  - "Automation folder prompts"
  - "Check automation folder contents"
  - "Find tasks to combine automation"
  - "Configure scheduled orchestrator tasks"
- **제안 위치**: `.claude/agents/automation-audit.md`
- **핵심 동작**: `~/.codex/automations` + `URHYNIX/.claude/automations` 전수 스캔 → 중복/충돌 cron 탐지, 통합 후보 제시, 스케줄 표 1장 출력. 점점 늘어나는 스케줄 태스크(Taillog/Vibehub/Mungmungfit/daily-recap 등)를 한 화면에서 감사.
- **예상 효과**: 매주 반복되는 "어떤 자동화가 돌고 있고 겹치나" 수동 점검을 1콜로 대체.

### 2. downloads-tidy (skill)
- **카테고리**: 디스크/다운로드 정리
- **빈도**: 7일간 ~4회 ("Clean downloads dmg")
- **근거**:
  - "Clean downloads dmg" (4개 세션, 최신순 상위권에 반복 등장)
- **제안 위치**: `.claude/skills/downloads-tidy/SKILL.md`
- **핵심 동작**: Downloads 폴더에서 `.dmg`/설치 잔여물/중복 다운로드를 규칙 기반으로 식별 → 용량 보고 → 사용자 확인 후 정리. 결정적·템플릿형이라 subagent보다 skill 적합.
- **예상 효과**: 반복되는 수동 정리를 표준 워크플로우로. **주의**: URHYNIX 프로젝트 비특화(범용 OS 작업)라, 프로젝트 스킬보다 사용자 전역 스킬(`~/.codex/skills`)로 두는 편이 맞을 수 있음.

### 3. assembly-visual-guide (skill)
- **카테고리**: 콘텐츠/시각화 생성
- **빈도**: 7일간 ~3회
- **근거**:
  - "Visualize RC car assembly and wiring"
  - "Create RC car assembly visualization guide"
  - "Create presentation slides for robot bootcamp project"
- **제안 위치**: `.claude/skills/assembly-visual-guide/SKILL.md`
- **핵심 동작**: 하드웨어 부품/배선 명세 → 조립·배선 시각 가이드(HTML/SVG) + 부트캠프용 슬라이드 일관 포맷 생성. 기존 `design-to-code`/`unity-camera-panel`과 인접하지만 "물리 조립/배선 설명도"는 미커버.
- **예상 효과**: TurtleBot/RC 하드웨어 설명 자료 제작을 표준화. 기존 시각 보드 자산(`docs/whiteboards/*`)과 스타일 통일 가능.

## 이미 자동화된 영역 (중복 제외)

- **daily-recap** → `.claude/automations/daily-recap.md` ("Daily recap" 세션)
- **morning/nightly orchestrator** → `.claude/automations/urhynix-{morning,nightly}-orchestrator.md`
- **타 프로젝트 스케줄 자동화** (URHYNIX 무관, 제외): Taillog (morning/nightly/weekly/ai-data/daily-guard), Vibehub (daily orchestrator/autoresearch/seo audit/editorial/drift guard/auto publish/ingest), Mungmungfit instagram (check/seed gen/saturday), Nightly vision labeling, Daily coaching synthetic gen, Daily journal loop, Weekly monday review, Daily master harness
- **문서 정합성** → 기존 `doc-audit` (agent), `doc-sync`/`doc-framework` (skill)
- **PR/코드 리뷰** → `code-review-graph-ops`, `socratic-review`
- **보안 검토** → `secret-scan`, `edge-hardening`
- **테스트 트리아지** → `parallel-qa`
- **DB 마이그레이션** → `migration-manifest`
- **설계 평가** → `socratic-review`, `change-impact-map`

## 다음 액션

- [ ] 후보 1 (automation-audit) 채택 여부 결정 — 가장 신호 강함(7회), URHYNIX 자산 직접 활용
- [ ] 후보 2 (downloads-tidy) 채택 시 전역 스킬로 둘지 결정 (프로젝트 비특화)
- [ ] 후보 3 (assembly-visual-guide) 채택 여부 결정
- [ ] **다음 정식 회차 전제**: `~/.codex` 폴더를 연결 폴더로 추가 → codex 세션 인덱스 정밀 스캔 복구
- [ ] 채택 시 사용자가 수동으로 스킬 파일 생성 (자동 생성 금지 — 명세 룰)
- [ ] cron 활성화 전 본 dry-run 결과 사용자 컨펌

---
*자동 생성: skill-harvest (dry-run). 후보는 제안일 뿐 — 채택은 사용자 컨펌 후.*
