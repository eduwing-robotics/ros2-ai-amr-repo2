# URHYNIX Agent Entry

## Loading Order

1. `AGENTS.md`
2. `AGENT.md`
3. `CLAUDE.md`
4. `ai-context/START-HERE.md`
5. `docs/status/PROJECT-STATUS.md`
6. `docs/ref/TECH-INDEX.md`
7. `docs/ref/PROJECT-PLAN.md`
8. `docs/ref/STACK-PROFILES.md`
9. `docs/ref/ARCHITECTURE.md`
10. `.claude/skills/README.md`
11. 필요 시 `docs/ref/tech/*.md`, `docs/ref/PRD.md`, `docs/ref/SCHEMA.md`

## Rules

1. 수정 전에 파일을 읽는다.
2. 변경 목적을 먼저 적는다.
3. 구현 후 검증한다.
4. 문서 동기화를 같이 끝낸다.
5. 파괴적 조작은 명시 요청 없이 하지 않는다.
6. 파일이 300줄에 가까워지면 분리를 검토한다.
7. 역할 경계가 생기는 새 폴더면 로컬 `AGENTS.md` 또는 `CLAUDE.md` 추가를 검토한다.
8. 새 요청은 가능하면 `/intake` 또는 `task-intake-router`부터 시작한다.
9. 완료 전 `Evidence Status`를 갱신한다.
