# Automation — URHYNIX 평일 18:00 SSOT 동기화

> **자동화 ID**: `urhynix-weekday-sync`
> **스케줄**: **평일(월~금) 18:00 KST** (`0 18 * * 1-5`)
> **작업 디렉토리**: `/Users/family/jason/URHYNIX`
> **트리거**: Codex automation (자동) · `bash docs/ref/run-weekday-sync.sh`(수동)
> **버전**: v1 · 2026-05-29 작성 (회의록 `3932161` 기반)

이 문서는 codex/Claude Code AI가 평일 18:00에 읽어 그대로 실행하는 **자동화 spec + prompt 본문**이다. 사람도 동일 절차로 수동 실행 가능.

---

## 1. 목적

| # | 항목 |
|---|---|
| 1 | **Confluence 회의록**(folder `524373`)의 오늘자 page를 읽어 멤버별 진척·결정·블로커 추출 |
| 2 | **Jira board 1**(SCRUM project) 진행 상태 조회 + 회의록과 매칭 |
| 3 | **Confluence SSOT 정본 3페이지**를 회의록 내용으로 갱신 (폴더 `1081377`은 *pageId가 아니라 folderId*라 descendant/ancestor 기반 자동화가 흔히 깨질 수 있음 → known pageId 직접 타겟팅) |
| 4 | **로컬 SSOT** (`docs/status/`, `docs/ref/`)를 동시 갱신 |
| 5 | `dev-plan` HTML 7페이지 + 번들 재빌드 |
| 6 | `docs/evidence/sync/YYYY-MM-DD-weekday-sync.md`에 작업 리포트 생성 |

---

## 2. 대상 자원 (cloudId, IDs, URLs)

### Atlassian
- **cloudId**: `bcd4e713-8205-46c8-81dc-f4cc7f2efb9e` (또는 `jason1127.atlassian.net`)
- **Confluence Space**: SCRUM (`spaceId=98307`)

### Jira
- **Project key**: SCRUM
- **Board**: <https://jason1127.atlassian.net/jira/software/projects/SCRUM/boards/1>
- **Epic**: `SCRUM-7` (18 child cards SCRUM-8 ~ SCRUM-25)

### Confluence 회의록 폴더 (input, `524373`)
- <https://jason1127.atlassian.net/wiki/spaces/SCRUM/folder/524373>
- 자동 검색: `parent = "524373" AND type = page AND title = "YYYY/MM/DD"`
- 알려진 page: `753701`(5/26) · `1048633`(5/27) · `2883585`(5/28) · `3932161`(5/29)

### Confluence SSOT 폴더 (output, `1081377`)
- <https://jason1127.atlassian.net/wiki/spaces/SCRUM/folder/1081377>
- 자동 검색: `ancestor = "1081377" AND type = page`
- 알려진 page:
  - **`327681`** — 기획안 (UR HYNIX) — 정본 SSOT
  - **`3112961`** — 사용자 요구사항 정의서 (라이브 페이지)
  - **`2555905`** — 기능 요구사항 정의서

### 로컬 SSOT (working_dir 상대 경로)
- `docs/status/HANDOFF.md`, `PROJECT-STATUS.md`, `DECISION-LOG.md`
- `docs/ref/PRD.md`, `PROJECT-PLAN.md`, `ARCHITECTURE.md`, `CONTRACT.md`, `SCHEMA.md`, `JIRA-MAP.md`, `STACK-PROFILES.md`
- `docs/dev-plan*.html` + `docs/dev-plan-bundle.html` (빌더: `docs/whiteboards/build_bundle.py`)

---

## 3. 절차 (AI가 따라할 순서)

### Step 0 — 사전 조건

```bash
cd /Users/family/jason/URHYNIX
# 주의: repo에 생성 산출물(untracked)이 많으면 무조건 중단될 수 있음.
# 자동화는 "핵심 SSOT( docs/status, docs/ref )에 tracked 변경이 이미 있는 경우"만 중단 권장.
git status --short  # dirty면 자동화 중단(운영 정책에 따라 조정)
date +%Y-%m-%d      # 오늘 날짜 캡처 (Asia/Seoul)
```

### Step 1 — 오늘 회의록 page 식별

```
TODAY = $(date "+%Y/%m/%d")  # 예: "2026/05/29"

mcp__codex_apps__atlassian_rovo._searchconfluenceusingcql
  cloudId: "bcd4e713-8205-46c8-81dc-f4cc7f2efb9e"
  cql: `parent = "524373" AND title = "${TODAY}" AND type = page`
  limit: 5
```

- **결과 0건**: 회의록 미작성. **자동화 종료** + `docs/evidence/sync/YYYY-MM-DD-weekday-sync-skipped.md`에 "회의록 없음" 한 줄 기록.
- **결과 1건**: page ID 추출 → Step 2

### Step 2 — 회의록 본문 읽기 + 분류

```
mcp__codex_apps__atlassian_rovo._getconfluencepage
  cloudId, pageId: <today_page_id>
  contentFormat: "markdown"
```

본문을 다음 4 카테고리로 분류:

| 카테고리 | 패턴 |
|---|---|
| (a) 결정 | "결정", "확정", "잠금", "전환", "채택" 등 |
| (b) 진척 | "성공", "통과", "완료", "검증", "측정" 등 |
| (c) 블로커 | "실패", "한계", "막힘", "이슈", "오류" 등 |
| (d) 다음 액션 | "예정", "필요", "다음", "권장" 등 |

각 항목에 **멤버 태그** (김주영·김선일·임현찬·박태진) + **관련 SCRUM ID** 매핑.

### Step 3 — Jira board 상태 조회

```
mcp__codex_apps__atlassian_rovo._searchjiraissuesusingjql
  cloudId, jql: `project = SCRUM ORDER BY updated DESC`
  fields: ["summary", "status", "assignee", "updated"]
  limit: 30
```

회의록의 (b) 진척과 각 SCRUM-N 매칭 → 영향받는 ticket 식별 + 본문 갱신 필요 여부 판단.

### Step 4 — 로컬 SSOT 갱신 (보수적)

| 파일 | 갱신 트리거 | 액션 |
|---|---|---|
| `docs/status/DECISION-LOG.md` | (a) 결정 ≥1건 | 오늘 날짜 섹션에 결정 항목 append (결정/근거/영향) |
| `docs/status/PROJECT-STATUS.md` | (b) 진척 ≥1건 | Evidence Status 표에 행 추가 |
| `docs/status/HANDOFF.md` | (a)+(c)+(d) | Top 1 + 미해결 이슈 + 자산 표 갱신 |
| `docs/ref/PRD.md` | 컨셉/범위 (a) | 영향받는 섹션만 patch |
| `docs/ref/ARCHITECTURE.md` | 인터페이스/적층 (a) | 영향받는 다이어그램만 |
| `docs/ref/CONTRACT.md` | 토픽/스키마 (a) | 영향받는 표만 |
| `docs/ref/SCHEMA.md` | DB 컬럼 (a) | 영향받는 테이블만 |
| `docs/ref/JIRA-MAP.md` | Jira ticket (b) 진척 | 상태/담당자 columns 갱신 |

**원칙**: section 단위 patch만. 파일 전체 덮어쓰기 금지.

### Step 5 — Confluence SSOT 폴더(1081377) 갱신

**권장(보수적, 파괴적 rewrite 회피)**: 정본 페이지 본문을 직접 patch하지 말고, **footer comment로 일일 델타만** 남긴다.

```
mcp__codex_apps__atlassian_rovo._createconfluencefootercomment
  cloudId: "bcd4e713-8205-46c8-81dc-f4cc7f2efb9e"
  pageId: "<SSOT_page_id>"
  body: "<YYYY-MM-DD 회의록 기반 (결정/진척/블로커/다음 액션) 델타>"
```

**직접 본문 patch 모드(선택, 위험)**는 아래 선행조건을 만족할 때만:
- (1) 대상 page ADF를 안정적으로 fetch할 수 있고(truncation 없음),
- (2) patch 범위를 `AUTO-SYNC` 마크로 명확히 제한하고,
- (3) update 후 버전 증가 검증이 가능할 때.

※ 참고: Codex Atlassian Rovo 도구의 `getConfluencePage`는 `markdown`/`adf`만 지원하는 경우가 있어(`html` round-trip 가정이 깨짐) 본문 patch는 실패 가능성이 높다.

매핑 가이드:
- 회의록 (a) 결정 → `327681` 기획안 또는 `2555905` 기능 요구사항
- 회의록 (b) 진척 (사용자 요구) → `3112961` 사용자 요구사항 정의서
- 회의록 (b) 진척 (시스템 기능) → `2555905` 기능 요구사항 정의서

### Step 6 — dev-plan HTML 번들 재빌드

```bash
python3 docs/whiteboards/build_bundle.py
ls -lh docs/dev-plan-bundle.html  # 약 465KB
python3 -c "
from html.parser import HTMLParser
import glob
for f in sorted(glob.glob('docs/dev-plan*.html')):
    HTMLParser().feed(open(f).read())
print('All HTML OK')
"
```

### Step 7 — 작업 리포트 생성

`docs/evidence/sync/YYYY-MM-DD-weekday-sync.md`에 다음 spec으로 작성:

```markdown
# Weekday Sync — YYYY-MM-DD

- 실행 시각: HH:MM KST
- 실행 주체: codex automation `urhynix-weekday-sync` (또는 manual)
- 회의록: page <id> (parent 524373) — title YYYY/MM/DD

## 회의록 추출 요약
(a) 결정 N건 / (b) 진척 N건 / (c) 블로커 N건 / (d) 다음 액션 N건

## 갱신 결과

### 로컬 SSOT (git diff 요약)
- docs/status/DECISION-LOG.md — +N 결정
- docs/status/PROJECT-STATUS.md — +N Evidence rows
- ...

### Confluence (1081377)
| page ID | title | version (before → after) | 변경 섹션 |
|---|---|---|---|
| 327681 | 기획안 | v12 → v13 | 카메라 인식 + 매핑 한계 |
| 3112961 | 사용자 요구사항 정의서 | vN → vN+1 | ... |
| 2555905 | 기능 요구사항 정의서 | v5 → v6 | YOLO 4 클래스 + Pi 카메라 토픽 |

### Jira (board 1)
| SCRUM-N | 변경 |
|---|---|
| SCRUM-19 | Pi 카메라 토픽 검증 진척 본문 추가 |

## 검증
- [ ] HTML 파싱 OK
- [ ] git status: M N files
- [ ] Confluence 3 pages updated, version 증가 확인
- [ ] Jira ticket M개 본문 갱신

## 사용자 액션
- [ ] git diff 검토 후 commit
- [ ] (선택) Slack 채널 `C0B5Q43A27R`에 회의록 요약 발송
```

---

## 4. 안전 가이드 (절대 지킴)

| 원칙 | 상세 |
|---|---|
| ❌ 자동 commit/push 금지 | 사람이 git diff 검토 후 수동 commit |
| ❌ Confluence 전체 덮어쓰기 금지 | section 단위 patch만 (`<!-- AUTO-SYNC -->` 마크) |
| ✅ 기본 모드는 델타 코멘트 | 본문 rewrite 대신 footer comment로 델타 기록(안전/감사 추적 용이) |
| ❌ Slack/이메일 자동 발송 금지 | 사용자가 명시 허용 시만 |
| ❌ 비밀 정보 commit 금지 | `service_role` JWT, Slack 토큰, Jira API 토큰 등 |
| ✅ 모든 변경 추적 | `docs/evidence/sync/` 리포트에 기록 |
| ✅ 실패 시 rollback | git stash 또는 직전 commit으로 복원 |
| ✅ 회의록 없으면 즉시 종료 | 빈 스캔 금지 |

---

## 5. 트러블슈팅

| 증상 | 원인 | 해법 |
|---|---|---|
| 오늘 회의록 page 없음 | 멤버가 미작성 | 자동화 종료 + skipped 리포트 |
| Atlassian API timeout | rate limit | 5분 후 재시도, 안 되면 manual |
| Confluence 갱신 409 conflict | 동시 편집 | 최신 version fetch 후 retry |
| HTML 파싱 실패 | `build_bundle.py` 오류 | 직전 commit으로 rollback + 본문 검사 |
| git status dirty | 사용자 작업 중 | 자동화 중단 + 사용자에게 알림 |
| 분류 모호 | 회의록 자유 형식 | (a)~(d) 모두 미분류로 두고 사람 검토 요청 |
| Jira board 응답 빈 | 권한 또는 JQL 오류 | JQL 단순화 후 재시도 |

---

## 6. 수동 트리거 (사람이 즉시 실행하고 싶을 때)

### Option A — Claude Code/Codex에 prompt로 전달
```
Read /Users/family/jason/URHYNIX/docs/ref/AUTOMATION-WEEKDAY-SYNC.md
Execute the procedure for today (Asia/Seoul). Stop and ask if unclear.
```

### Option B — 단계별 명령으로 분해
```bash
cd /Users/family/jason/URHYNIX
# 1. 회의록 ID 확인
TODAY=$(date "+%Y/%m/%d")
# (Atlassian MCP로 CQL 검색)

# 2. 절차 따라 실행
# 3. 결과 검증
git status --short docs/
ls docs/evidence/sync/$(date "+%Y-%m-%d")-*
```

---

## 7. 첫 실행 evidence (2026-05-29)

이 spec의 첫 실전 대상은 **2026-05-29 회의록 page `3932161`** — 본 자동화 spec 작성과 동시에 수동 실행됨.

| 항목 | 결과 |
|---|---|
| 회의록 추출 | 김주영 (매핑) + 박태진 (UR) + 임현찬 (카메라+YOLO) |
| 핵심 발견 | "라이다 높이 > 가벽 높이" 진단 정정 |
| 로컬 SSOT 갱신 | DECISION-LOG +2, PROJECT-STATUS +2 행, HANDOFF Top 1 정정, eval.md 정정 |
| Confluence 갱신 | (예정) 327681 v13 / 3112961 / 2555905 v6 |
| Jira 갱신 | (예정) SCRUM-10/16/19 본문 정정 |

---

## 8. 관련 결정

- `docs/status/DECISION-LOG.md` 2026-05-28 "매일 18:00 Confluence 회의록 기반 SSOT 자동화 예약" — 이 문서가 그 결정의 spec 본문
- `docs/status/DECISION-LOG.md` 2026-05-29 "매핑 실패 진단 정정" — 첫 실전 evidence
- `.claude/skills/decision-broadcast/SKILL.md` — 결정 1건 → 5채널 broadcast (이 자동화는 회의록 1건 → SSOT 폴더 일괄, 다른 흐름)
- `.claude/skills/ssot-board-sync/SKILL.md` — 로컬 SSOT ↔ HTML 동기화 (Step 6에서 위임)

---

## 한줄정리

평일 18:00에 codex/Claude가 이 문서를 prompt로 받아 **회의록 (folder 524373) → SSOT 폴더 (1081377) + Jira board 1 + 로컬 SSOT + dev-plan 번들** 4곳을 한 번에 동기화한다. 자동 commit/push 금지 — 사람이 git diff 검토 후 결정.
