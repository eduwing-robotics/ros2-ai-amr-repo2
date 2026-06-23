---
name: urhynix-morning-orchestrator
purpose: 매일 아침 URHYNIX 상태를 점검하고 그날 작업할 컨텍스트를 정리
status: planned
owner: 코워크
schedule: "0 8 * * 1-5"  # 평일 08:00 KST
lock: docs/status/.morning-orchestrator.lock
based_on: TaillogToss/taillog-morning-orchestrator (구조 차용)
---

# URHYNIX Morning Orchestrator

평일 아침 8시, 그날 작업 시작 전 상태 점검·드리프트 감지·일일 컨텍스트 준비.

## 공통 원칙 (MUST)

- lock 존재 + running이면 즉시 종료: "모닝 오케스트레이터 이미 실행 중"
- lock 없으면 시작 시 `{"status":"running","started_at":"<ISO>"}` 생성, 종료 시 해제
- lock 해제 실패 시 `{"status":"released","released_at":"<ISO>"}` 덮어쓰기
- DRY_RUN=true면 각 TASK도 DRY_RUN=true로 전달 (슬랙 발송 X, 파일 저장만)
- 각 TASK 결과(변경 없음 / 완료 / 오류)를 RESULTS 배열에 기록
- 하나 실패해도 다음 TASK 진행

## TASK 목록 (순서 고정)

### TASK 1: 전일 드리프트 점검

직접 실행:
1. `git -C /Users/family/jason/URHYNIX log --since="yesterday" --until="now" --name-only --pretty=format:""` 실행
2. 변경된 파일이 `docs/status/PROJECT-STATUS.md`의 현재 단계와 일치하는지 확인
3. 변경된 코드/문서 vs `docs/status/DECISION-LOG.md` 최신 결정 정합성 확인
4. 불일치 시 `docs/status/DRIFT-REPORT.md` 에 append

성공/실패 출력:
- 드리프트 없음: "TASK 1: 변경 없음"
- 드리프트 있음: "TASK 1: drift N건 → docs/status/DRIFT-REPORT.md"

### TASK 2: doc-audit 서브에이전트 호출 (월요일만)

월요일에만 실행 (다른 요일은 skip).

```
Agent(subagent_type="general-purpose", model="opus",
      description="URHYNIX 주간 문서 정합성 점검",
      prompt=".claude/agents/doc-audit.md 의 절차대로 6종 표준 문서 크로스 검증. 결과는 docs/status/DOC-AUDIT-{YYYY-MM-DD}.md 저장")
```

### TASK 3: secret-scan 빠른 점검

```bash
bash /Users/family/jason/URHYNIX/.claude/skills/secret-scan/scan.sh
```

발견 시: 슬랙 채널 `C0B5Q43A27R`에 경고 메시지 즉시 발송 (DRY_RUN=false일 때만).

### TASK 4: Jira 진행 상황 요약

MCP `mcp__atlassian__searchJiraIssuesUsingJql`:
- JQL: `project = SCRUM AND sprint in openSprints() AND status != Done`
- 결과: 오늘 활성 이슈 목록 (3건 이내로)
- 출력: `docs/daily/$(date +%m-%d)/morning-jira-snapshot.md` 저장

### TASK 5: 종합 보고 (선택)

5건 모두 끝나면 짧은 1줄 요약을 슬랙으로 (DRY_RUN=false 시):
```
🌅 URHYNIX 모닝 ({YYYY-MM-DD})
드리프트 {N}건 · Jira {오픈}개 · 시크릿 {0/N}건
```

## 코워크 등록 시 체크리스트

- [ ] cron `0 8 * * 1-5` (평일 08시 KST)
- [ ] 첫 회차 dry-run (DRY_RUN=true 환경변수)
- [ ] 주인님 컨펌 후 활성화
- [ ] 결과를 `docs/status/MORNING-ORCHESTRATOR-LOG.md` 에 누적

## 한줄정리
하루 시작 전 5단계 점검(드리프트→문서감사→시크릿→Jira→슬랙요약)을 자동 수행, 실패해도 멈추지 않고 다음 단계로 진행.
