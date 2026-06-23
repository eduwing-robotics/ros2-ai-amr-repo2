# Database Supabase Tech Ref

Supabase/Postgres, schema, RLS, storage, DB writer 작업의 빠른 진입점이다.

## Read First

1. `docs/ref/TECH-INDEX.md`
2. `docs/ref/SCHEMA.md`
3. `docs/ref/CONTRACT.md`
4. `db/migrations/2026-05-27_init_security.sql`
5. `docs/status/PROJECT-STATUS.md` Evidence Status for current/applied table truth

## Current Truth

- Supabase URL: `https://ueupkrxwybuuqxflstvg.supabase.co`.
- Current tables: `session_meta`, `events`, `dispatches`, `camera_captures`.
- Planned SCRUM-23 tables: `pose_logs`, `media_artifacts`, `protected_assets`.
- Unity client must not include `service_role`.
- Robot PC ROS2/Python writer is the main write path; Unity uses anon/RLS and restricted human action writes.

## Verify

- Migration truth: compare `SCHEMA.md` with `db/migrations/2026-05-27_init_security.sql`.
- Runtime truth: Supabase REST or SQL confirms current table availability.
- Insert smoke: robot or service writer can create an `events` row.
- RLS smoke: anon key is blocked or allowed according to the intended policy.

