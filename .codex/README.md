# .codex Ops Pack

이 디렉토리는 Codex 기준 운영 자산 모음이다.

## Defaults

- `hooks.json`: post-edit reminder 연결
- `hooks/`: 짧은 검증 리마인더
- `README.md`: Codex 전용 운영 메모

## Agent Layer

- task 분류는 `task-intake-router`
- 병렬 조사 전에는 `change-impact-map`
- 완료 선언 전에는 `evidence-review`
- 세션 종료 전에는 `session-handoff`

## Sub-Agent Packet

- `Task`
- `Why delegated`
- `Owned paths`
- `Expected artifact`
- `Verify`
- `Return format`
- `Model hint`

## Safe Defaults

- cheap model: 검색, 로그 triage, 문서 inventory
- stronger model: cross-file synthesis, 설계 비교, tricky bug
- evidence 없는 완료 보고 금지
