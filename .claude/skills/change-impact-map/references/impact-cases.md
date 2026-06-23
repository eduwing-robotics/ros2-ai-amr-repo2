# Impact Cases

## Route Rename

- core paths: `apps/web/app/...`, `backend/app/api/...`
- companion docs: `docs/ref/PROJECT-PLAN.md`, `docs/ref/ARCHITECTURE.md`
- verify matrix: route smoke, project check

## Env Var Rename

- core paths: `.env.example`, runtime config, deploy docs
- companion docs: `PROJECT-PLAN`, `ARCHITECTURE`, `PROJECT-STATUS`
- verify matrix: config load, project check

## Schema Rename

- core paths: API layer, persistence layer, migration docs
- companion docs: `PRD`, `PROJECT-PLAN`, `ARCHITECTURE`
- verify matrix: migration/test/check-project
