# File Map Naming Rules

`File Map`은 repo-relative 경로를 기본으로 쓴다.

## Prefix Rules

- `create:` 새로 만들 파일
- `modify:` 이미 존재하는 파일
- `keep:` 유지하면서 계속 참조할 파일
- `existing:` 수정 여부와 상관없이 현재 존재해야 하는 파일
- `candidate:` 경로는 미정이지만 경계는 아는 경우

## Good

- `create: candidate:apps/web/app/dashboard/page.tsx`
- `modify: docs/ref/PRD.md`
- `existing: backend/AGENTS.md`

## Bad

- `new dashboard file`
- `change backend things`
- `maybe somewhere in src`

## Boundary Reminder

아래 경계가 새로 생기면 로컬 `AGENTS.md` 또는 `CLAUDE.md`를 검토한다.

- `src/features/*`
- `workers/*`
- `integrations/*`
