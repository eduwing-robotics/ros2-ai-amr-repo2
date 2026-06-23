-- demo_logs_rls.sql — 시연용 logs 테이블 + Unity anon 쓰기 RLS 정책 묶음
--
-- URHYNIX 박물관 디지털트윈경비로봇. Unity ControlRoom이 "직접 택배"(UnityWebRequest+PostgREST)
-- 방식으로 anon(publishable) 키로 직접 INSERT/SELECT 하기 위한 DB 준비.
-- 정본 스키마: docs/ref/SCHEMA.md. 적용 후 SCHEMA.md + DECISION-LOG.md 갱신 필수.
-- 실행: supabase db query --linked --file scripts/sql/demo_logs_rls.sql
--       (프로젝트가 paused면 먼저 Dashboard에서 Restore project)
-- 패턴 출처: scripts/sql/pose_logs.sql (anon_insert_pose / anon_select_pose).

-- ════════════════════════════════════════════════════════════════
-- 1) logs — UI 로그 라인 저장 (화면 로그창 = DB 일치 검증의 핵심)
-- ════════════════════════════════════════════════════════════════
create table if not exists public.logs (
  id         uuid        primary key default gen_random_uuid(),
  session_id uuid        references public.session_meta(session_id) on delete cascade,
  ts         timestamptz not null    default now(),
  level      text        not null    default 'INFO',   -- INFO / WARN / ERROR
  category   text        not null,                      -- system / dispatch / sensor / gemma / ...
  message    text        not null,
  source     text        not null    default 'ControlRoom'  -- ControlRoom / RobotPC
);

create index if not exists idx_logs_session_ts on public.logs (session_id, ts);
create index if not exists idx_logs_category    on public.logs (category, ts);

alter table public.logs enable row level security;

drop policy if exists "anon_insert_logs" on public.logs;
create policy "anon_insert_logs" on public.logs
  for insert to anon with check (true);

drop policy if exists "anon_select_logs" on public.logs;
create policy "anon_select_logs" on public.logs
  for select to anon using (true);

-- ════════════════════════════════════════════════════════════════
-- 2) dispatches — 맵 클릭 수동 출동을 기록할 수 있게 완화
--    수동 출동은 트리거 센서 이벤트가 없으므로 event_id를 nullable로.
--    reason/nav_mode 컬럼 추가(맵 액션 OnDispatchRequested의 reason 보존).
-- ════════════════════════════════════════════════════════════════
alter table public.dispatches alter column event_id drop not null;
alter table public.dispatches add column if not exists reason   text;
alter table public.dispatches add column if not exists nav_mode text;

-- ════════════════════════════════════════════════════════════════
-- 3) anon RLS 정책 — Unity가 직접 쓰는 테이블 (시연 한정 개방)
--    session_meta(세션 생성) / dispatches(출동) / events(센서 이벤트).
--    후속 단계에서 robot_id 일치 검증 등으로 조일 수 있음.
-- ════════════════════════════════════════════════════════════════

-- session_meta: Unity가 시연 회차마다 세션 생성 + 조회
alter table public.session_meta enable row level security;
drop policy if exists "anon_insert_session" on public.session_meta;
create policy "anon_insert_session" on public.session_meta
  for insert to anon with check (true);
drop policy if exists "anon_select_session" on public.session_meta;
create policy "anon_select_session" on public.session_meta
  for select to anon using (true);

-- dispatches: 맵 클릭 출동 기록 + 조회
alter table public.dispatches enable row level security;
drop policy if exists "anon_insert_dispatch" on public.dispatches;
create policy "anon_insert_dispatch" on public.dispatches
  for insert to anon with check (true);
drop policy if exists "anon_select_dispatch" on public.dispatches;
create policy "anon_select_dispatch" on public.dispatches
  for select to anon using (true);

-- events: 센서 감지 이벤트 기록 + 조회 (옵션 범위)
alter table public.events enable row level security;
drop policy if exists "anon_insert_event" on public.events;
create policy "anon_insert_event" on public.events
  for insert to anon with check (true);
drop policy if exists "anon_select_event" on public.events;
create policy "anon_select_event" on public.events
  for select to anon using (true);

-- ════════════════════════════════════════════════════════════════
-- 검증 쿼리 (적용 후 실행해 확인)
--   select count(*) from public.logs;
--   select tablename, policyname, cmd from pg_policies
--     where schemaname='public' order by tablename, cmd;
-- ════════════════════════════════════════════════════════════════
