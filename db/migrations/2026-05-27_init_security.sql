-- URHYNIX 디지털트윈경비로봇 — 초기 보안 스키마
-- SSOT: docs/ref/SCHEMA.md
-- 결정: docs/status/DECISION-LOG.md 2026-05-28 "DB 선정 — mungmungfit 프로젝트 재용도"
-- 대상: Supabase project ueupkrxwybuuqxflstvg (public schema, region ap-northeast-1 Tokyo)
-- 적용 도구: Supabase Management API SQL endpoint (token: $SUPABASE_ACCESS_TOKEN)
--           POST https://api.supabase.com/v1/projects/{ref}/database/query
-- 이전 시도(oucgzkbqrzbwxxffmmqt = mungmungfit)는 egress quota 초과로 폐기됨.

create extension if not exists pgcrypto;

-- ────────────────────────────────────────────────────────────────
-- 1) session_meta — 시연/순찰 세션 메타
-- ────────────────────────────────────────────────────────────────
create table public.session_meta (
  session_id  uuid        primary key default gen_random_uuid(),
  started_at  timestamptz not null    default now(),
  ended_at    timestamptz,
  scenario    text        not null    check (scenario in ('night_patrol','intrusion','noise','fire_mock','mixed')),
  notes       text,
  recorded_by text
);

-- ────────────────────────────────────────────────────────────────
-- 2) events — 센서 감지 이벤트
-- ────────────────────────────────────────────────────────────────
create table public.events (
  id           uuid              primary key default gen_random_uuid(),
  session_id   uuid              not null    references public.session_meta(session_id) on delete cascade,
  robot_id     text              not null    check (robot_id in ('tb3_1','tb3_2')),
  ts           timestamptz       not null    default now(),
  event_type   text              not null    check (event_type in ('dark','pir','noise','fire')),
  severity     smallint          not null    check (severity between 0 and 3),
  x            double precision  not null,
  y            double precision  not null,
  theta        double precision  not null,
  raw_payload  jsonb
);
create index idx_events_session on public.events(session_id, ts);
create index idx_events_type    on public.events(event_type);
create index idx_events_robot   on public.events(robot_id, ts);

-- ────────────────────────────────────────────────────────────────
-- 3) dispatches — tb3_2 출동 기록
-- ────────────────────────────────────────────────────────────────
create table public.dispatches (
  id              uuid             primary key default gen_random_uuid(),
  event_id        uuid             not null    references public.events(id) on delete cascade,
  target_robot_id text             not null    default 'tb3_2',
  target_x        double precision not null,
  target_y        double precision not null,
  dispatched_at   timestamptz      not null    default now(),
  arrived_at      timestamptz,
  response_time   numeric(6,2),
  simulated       boolean          not null    default true
);
create index idx_dispatches_event on public.dispatches(event_id);

-- ────────────────────────────────────────────────────────────────
-- 4) camera_captures — Pi Camera 확인 결과
-- ────────────────────────────────────────────────────────────────
create table public.camera_captures (
  id            uuid        primary key default gen_random_uuid(),
  dispatch_id   uuid        not null    references public.dispatches(id) on delete cascade,
  robot_id      text        not null    default 'tb3_2',
  ts            timestamptz not null    default now(),
  image_path    text        not null,
  result        text        not null    check (result in ('confirmed','false_alarm','missed','unverified')),
  ai_label      text,
  ai_confidence real                    check (ai_confidence between 0 and 1),
  operator_note text
);
create index idx_captures_dispatch on public.camera_captures(dispatch_id);

-- ────────────────────────────────────────────────────────────────
-- 시연/Day-1 PIR 검증용 seed 세션 1건 (events.session_id FK 만족)
-- 고정 UUID로 두어 arduino_bridge.py에서 그대로 참조 가능
-- ────────────────────────────────────────────────────────────────
insert into public.session_meta (session_id, scenario, recorded_by, notes)
values ('00000000-0000-0000-0000-000000000001', 'intrusion', 'urhynix-day1', 'Day-1 PIR smoke session')
on conflict (session_id) do nothing;
