# .claude Ops Pack

이 디렉토리는 Claude Code 기준 운영 자산 모음이다.

## Structure

```text
.claude/
├── settings.json
├── README.md
├── commands/
├── automations/
├── hooks/
└── skills/
```

## Defaults

- `commands/`: 수동 실행용 작업 절차
- `automations/`: 반복 작업 프롬프트 자산
- `hooks/`: 편집 후 빠른 리마인더/검증
- `skills/`: 반복되는 운영 패턴의 실행형 문서
- agent layer: intake, impact, handoff, evidence, drift

## Skill Categories

- 문서/운영: `doc-framework`, `doc-sync`, `session-retro`, `big-task`
- 시작/구조화: `project-bootstrap`, `migration-manifest`
- 설계/검토: `design-to-code`, `socratic-review`, `task-intake-router`, `profile-recommendation`
- 품질/검증: `parallel-qa`, `change-impact-map`, `evidence-review`, `stack-drift-guard`
- 계약/안전: `api-contract-guard`, `code-review-graph-ops`
- 복구/이관: `failure-mode-playbooks`, `session-handoff`

## Command Shortcuts

- `/intake`
- `/impact-map`
- `/profile-recommend`
- `/evidence-review`
- `/handoff`

## Sub-Agent Packet

- `Task`
- `Why delegated`
- `Owned paths`
- `Expected artifact`
- `Verify`
- `Return format`
- `Model hint`

## Recommended Session Order

1. 루트 `AGENTS.md`
2. 루트 `CLAUDE.md`
3. `docs/status/PROJECT-STATUS.md`
4. `skills/README.md`
5. 필요 시 `/intake` 또는 `task-intake-router`
6. 작업 관련 `skills/*/SKILL.md`
