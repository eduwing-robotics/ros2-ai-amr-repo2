---
name: daily-recap
purpose: URHYNIX 그날 작업 내용을 요약해 Slack 채널 C0B5Q43A27R로 전송
status: drafting
owner: 코워크 (Claude Code 별도 인스턴스가 이 문서를 참조해 스케줄 등록)
---

# URHYNIX Daily Recap → Slack

이 문서는 **코워크용 명세서**입니다. 코워크가 이 문서를 읽고 cron(또는 `schedule`/`CronCreate` 스킬)으로 자동 실행을 등록합니다.

## 트리거

- **스케줄**: 평일 22:00 KST → `0 22 * * 1-5`
- **수동 실행**: 사용자가 `/daily-recap` 슬래시 커맨드로 즉시 호출 가능
- **타임존**: Asia/Seoul

## 입력 (수집 단계)

| 출처 | 명령/경로 | 목적 |
|---|---|---|
| URHYNIX git 커밋 | `git -C /Users/family/jason/URHYNIX log --since="00:00" --pretty="%h %s"` | 오늘 커밋 목록 |
| 변경 통계 | `git -C /Users/family/jason/URHYNIX diff --shortstat HEAD@{1.day.ago} HEAD` | 라인 추가/삭제 |
| 일일 로그 | `cat /Users/family/jason/URHYNIX/docs/daily/$(date +%m-%d)*.md` (있으면) | 사용자가 직접 적은 로그 |
| Jira 진행 | `mcp__atlassian__searchJiraIssuesUsingJql` JQL: `project=SCRUM AND updated >= startOfDay()` | 오늘 변경된 이슈 |
| 결정 로그 | `tail -20 /Users/family/jason/URHYNIX/docs/status/DECISION-LOG.md` | 새 결정 |
| (선택) Codex 세션 | `grep -i urhynix /Users/family/.codex/session_index.jsonl \| tail -10` | URHYNIX 관련 세션 |

## 처리 (요약 단계)

수집한 데이터를 Claude/Codex가 다음 형식으로 요약합니다.

```markdown
## 📅 URHYNIX 데일리 — {YYYY-MM-DD}

**오늘 한 일**
- {commit 1줄 요약}
- {commit 2}
- {docs 변경 핵심}

**Jira 진행**
- SCRUM-{N}: {제목} → {상태 변화}

**결정 / 블로커**
- {새 결정 or 막힌 부분}

**내일 우선순위 (1~2개)**
1. {next action}
2. {next action}

> **한줄정리**: {모든 활동을 한 줄로 압축}
```

## 출력 (전송 단계)

- **도구**: `mcp__claude_ai_Slack__slack_send_message`
- **채널 ID**: `C0B5Q43A27R`
- **메시지 형식**: 위 마크다운을 슬랙 mrkdwn으로 변환 (헤더는 `*굵게*`, 리스트는 `•`)
- **첨부**: 변경 통계 + Jira 링크 블록

## 실패 처리

| 실패 케이스 | 대응 |
|---|---|
| 오늘 커밋이 0개 | "오늘은 활동이 없어요" 메시지 발송 (skip 금지 — 패턴 가시성 확보) |
| Slack MCP 응답 없음 | 메시지를 `docs/daily/{MM-DD}-recap-pending.md`로 로컬 저장 + 다음 실행에서 재시도 |
| Jira MCP 인증 만료 | Jira 섹션 생략하고 git/docs만으로 진행 |

## 코워크 등록 시 체크리스트

코워크가 이 문서를 참조해 자동화를 등록할 때 확인:

- [ ] cron 표현식 `0 22 * * 1-5` 등록 (또는 `schedule` 스킬 사용)
- [ ] `CronCreate` 시 `prompt`에 이 파일 경로 전달: `/Users/family/jason/URHYNIX/.claude/automations/daily-recap.md`
- [ ] 채널 ID `C0B5Q43A27R` 권한 (Bot이 채널에 초대되어 있는지)
- [ ] **⚠️ 필수 — 첫 회차는 반드시 dry-run**: cron 등록 직후 `RemoteTrigger`로 즉시 1회 실행 → 출력을 슬랙 대신 `docs/daily/{TODAY}-recap-preview.md`에 저장 → 주인님이 직접 보고 OK 하면 cron 활성화. 검증 없이 자동 발송 절대 금지.
- [ ] 등록 결과를 `docs/status/PROJECT-STATUS.md`의 **Automations** 섹션에 기록
- [ ] 첫 회차 결과 링크를 주인님(슬랙 DM 또는 콘솔)에게 보여주고 승인 대기

## 관련 파일

- 호환 자동화: `.claude/automations/skill-harvest.md` (주 1회 메타 스캔)
- 슬랙 채널 정책: `HARNESS-MANIFEST.yaml` 의 `slack` 섹션
- 메모리: `MEMORY.md` → "자동화는 문서 → 코워크 예약 패턴"
