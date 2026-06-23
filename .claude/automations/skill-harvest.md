---
name: skill-harvest
purpose: Codex/Claude 세션 인덱스를 스캔해 반복되는 수동 작업을 새 스킬·서브에이전트 후보로 추출
status: planned
owner: 코워크 (주 1회 실행)
---

# Skill Harvest — 반복 워크플로우 자동 수확

이 문서는 **메타 자동화** 명세입니다. 사용자가 수동으로 반복하는 작업을 자동 감지해 "스킬화 후보"로 제안합니다.

## 트리거

- **스케줄**: 매주 일요일 22:00 KST → `0 22 * * 0`
- **수동 실행**: `/skill-harvest`
- **임계값**: 같은 카테고리의 요청이 1주에 3회 이상 → 후보로 등록

## 입력

| 출처 | 경로 | 추출 정보 |
|---|---|---|
| Codex 세션 인덱스 | `/Users/family/.codex/session_index.jsonl` | 최근 7일치 세션 제목/요약 |
| Codex archived | `/Users/family/.codex/archived_sessions/*.jsonl` | 샘플링 (최근 30개) |
| Claude transcripts | `/Users/family/.claude/projects/*/` (jsonl) | URHYNIX 관련 세션 |
| 기존 스킬 목록 | `/Users/family/.codex/skills/`, `/Users/family/jason/URHYNIX/.claude/skills/` | 이미 자동화된 영역 (중복 제외) |
| 기존 자동화 | `/Users/family/.codex/automations/`, `URHYNIX/.claude/automations/` | 자동화 커버리지 |

## 처리

1. **카테고리 분류** (LLM): 각 세션을 다음 카테고리 중 하나로 매핑
   - CI 실패 분석 / PR 리뷰 / 체인지로그 / 문서 업데이트 / 릴리즈 준비 / 디버깅 / 테스트 트리아지
   - 보안 검토 / 성능 분석 / 설계 평가 / 콘텐츠 생성 / DB 마이그레이션
   - 기타 (자유 텍스트)

2. **빈도 집계**: 카테고리별 7일치 카운트

3. **중복 제거**: 이미 `.claude/skills/` 또는 `.codex/skills/` 또는 `automations/`에 있는 카테고리 제외

4. **타입 결정**:
   - **skill**: 한 화면/한 워크플로우 단위, 템플릿 기반, 결정적 (예: `secret-scan`, `schema-tidy`)
   - **subagent**: 다중 단계 조사·판단·복합 분석 (예: `doc-audit`, `qa-validator`, `arch-reviewer`)

5. **후보 카드 생성**: 카테고리당 1개의 후보 카드 (이름/설명/근거 인용/타입/예상 효과)

## 출력

- **파일**: `docs/status/SKILL-HARVEST-{YYYY-MM-DD}.md` (덮어쓰기 금지, 누적)
- **슬랙 알림**: 후보 카드 요약을 채널 `C0B5Q43A27R`로 전송 (선택)

### 출력 형식

```markdown
# Skill Harvest — {YYYY-MM-DD}

## 신규 후보 ({N}건)

### 1. doc-audit (subagent)
- **카테고리**: 문서 정합성 점검
- **빈도**: 7일간 5회
- **근거**:
  - "PRD/ARCH 정합성 점검해줘" (2026-05-22)
  - "문서 검토하고 다음 개발 순서 정리" (2026-05-24)
  - ...
- **제안 위치**: `.claude/agents/doc-audit.md`
- **핵심 동작**: PRD/ARCH/STATUS/DECISION-LOG 크로스 검증, 드리프트 보고

### 2. ...

## 이미 자동화된 영역 (중복 제외)
- daily-recap (요약 작업)
- ...

## 다음 액션
- [ ] 후보 1번 (doc-audit) 채택 여부 결정
- [ ] 사용자에게 컨펌 요청 (슬랙 1메시지)
```

## 코워크 등록 시 체크리스트

- [ ] cron 등록 `0 22 * * 0` (일요일 22시)
- [ ] `CronCreate` prompt에 이 파일 경로 전달
- [ ] **⚠️ 필수 — 첫 회차는 반드시 dry-run**: 출력은 파일로만 저장(`docs/status/SKILL-HARVEST-{YYYY-MM-DD}.md`), 슬랙 미발송. 주인님이 직접 보고 OK 하면 cron 활성화.
- [ ] 사용자가 후보 검토 → 채택 시 수동으로 스킬 파일 생성
   - 자동 생성은 일단 하지 않음 (룰: 자동화는 문서 → 사람 컨펌 → 적용)

## 한계 / 주의

- LLM 분류는 noisy할 수 있음 → 임계값 3회로 너무 자주 후보 뜨지 않도록
- Codex archived_sessions가 215개 이상 → 매주 전체 스캔이 아닌 7일치 윈도우만
- 새 스킬을 자동 생성하지는 않는다 (제안만). 사용자가 채택해야 실제 파일 생성
