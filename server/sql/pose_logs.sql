-- pose_logs.sql — 이동 좌표 로그 테이블 + 인덱스 + RLS 정책
--
-- URHYNIX 박물관 시연 디지털트윈경비로봇 SCRUM-23 Planned Extension 첫 적용.
-- SCHEMA 정본: docs/ref/SCHEMA.md `pose_logs` 표.
-- 실행: Supabase Dashboard SQL Editor 또는 Management API SQL endpoint.
-- 적용 완료 후 docs/ref/SCHEMA.md의 "Planned Extensions" → "Current Applied"로 옮기고
-- docs/status/DECISION-LOG.md에 적용 일자/검증 행을 박는다.

create table if not exists public.pose_logs (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references public.session_meta(session_id) on delete cascade,
  robot_id     text not null check (robot_id in ('tb3_1', 'tb3_2')),
  ts           timestamptz not null default now(),
  x            double precision not null,
  y            double precision not null,
  theta        double precision not null,
  source_topic text,
  nav_mode     text check (nav_mode in ('patrol', 'dispatch', 'lidar_boost', 'manual'))
);

create index if not exists idx_pose_logs_session_robot
  on public.pose_logs (session_id, robot_id, ts);

create index if not exists idx_pose_logs_mode
  on public.pose_logs (nav_mode, ts);

-- Row Level Security
alter table public.pose_logs enable row level security;

-- 정책 A: anon이 INSERT 가능 (로봇 PC pose_logger.py 용).
--         박물관 시연 한정으로 제약 없이 허용. 후속 단계에서 robot_id 일치 검증 추가 가능.
drop policy if exists "anon_insert_pose" on public.pose_logs;
create policy "anon_insert_pose"
  on public.pose_logs
  for insert
  to anon
  with check (true);

-- 정책 B: anon이 SELECT 가능 (Unity 관제 read 경로).
drop policy if exists "anon_select_pose" on public.pose_logs;
create policy "anon_select_pose"
  on public.pose_logs
  for select
  to anon
  using (true);

-- 정책 C: anon이 UPDATE/DELETE 불가 — 명시적 정책 없으므로 기본 거부 유지.
--         관리자 작업은 service_role 키로만 (Supabase Dashboard 또는 backend proxy).

-- 검증 SQL (수동 실행):
-- select count(*) from public.pose_logs;                                     -- 0
-- insert into public.pose_logs (session_id, robot_id, x, y, theta)
--   values ('<existing_session_uuid>', 'tb3_1', 0, 0, 0);
-- select * from public.pose_logs order by ts desc limit 1;                   -- 방금 박은 행
