-- patrol_routes.sql — 순찰 경로 저장 테이블 + anon RLS.
-- Unity ControlRoom 맵 웨이포인트 에디터(MWE)의 경로를 맵별로 보존. 로컬 우선 + 이 테이블로 동기화.
-- 적용: supabase db query --linked --file scripts/sql/patrol_routes.sql
-- 정책: Unity는 anon + RLS로 INSERT/SELECT만. service_role 미반입.

create table if not exists public.patrol_routes (
  id          uuid primary key default gen_random_uuid(),
  route_id    text not null,                 -- 보통 map_id (맵별 1경로)
  map_id      text not null,                 -- 슬롯 id (arena 등)
  robot_id    text not null,                 -- tb3_1 / tb3_2
  points      jsonb not null,                -- [{seq,x,y,theta}, ...] (map 프레임 m/rad)
  updated_at  timestamptz not null default now()
);

create index if not exists idx_patrol_routes_map on public.patrol_routes (map_id, updated_at desc);

alter table public.patrol_routes enable row level security;

-- anon 읽기 허용
drop policy if exists anon_select_patrol on public.patrol_routes;
create policy anon_select_patrol on public.patrol_routes
  for select to anon using (true);

-- anon 쓰기 허용(시연 환경 — 운영 시 좁히기)
drop policy if exists anon_insert_patrol on public.patrol_routes;
create policy anon_insert_patrol on public.patrol_routes
  for insert to anon with check (true);
