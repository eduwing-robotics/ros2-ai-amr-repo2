# Schema

> 디지털트윈경비로봇 — 이벤트/대응 로그 DB.
> 정본: 본 문서. `CONTRACT.md §2` 는 요약본. 변경 시 둘을 동시에 갱신한다.
> 저장소: **Supabase 프로젝트 `ueupkrxwybuuqxflstvg`** (region ap-northeast-1 Tokyo, org `uisuqsaynxoedcsuikqc`).
> 마이그레이션 적용 완료 (2026-05-28, Management API SQL endpoint 경유).
> 자세한 결정 흐름: `DECISION-LOG.md` 2026-05-28 "DB 선정 완료 — 신규 Supabase `ueupkrxwybuuqxflstvg`".
> 재검증(2026-06-18): `docs/evidence/2026-06-18-db-supabase-revalidation.md` — Supabase vs 직접 Postgres/TimescaleDB/SQLite 비교 후 Supabase 유지 + 로컬 SQLite 백업 안전판 권고.
> 키 운영: service_role JWT는 RPi `/etc/urhynix.env`에만 (commit 금지), publishable은 공개 가능.

## Current Applied Entities

```text
session_meta (1) ─── (N) events ─── (0..1) dispatches ─── (0..1) camera_captures
                                                                   │
                                                            (0..1) ai_labels (optional)
```

- 한 **세션**(시연 회차)은 다수 **이벤트**를 가진다.
- 한 **이벤트**는 최대 한 번의 **출동**으로 이어진다.
- 한 **출동**은 최대 한 번의 **카메라 확인**을 만든다.
- 2026-05-28 실제 Supabase REST 확인 기준 현재 적용 테이블은 `session_meta`, `events`, `dispatches`, `camera_captures` 4개다.
- **2026-06-02 추가**: `pose_logs` 적용 완료 (Supabase CLI `db query --linked --file scripts/sql/pose_logs.sql`). 인덱스 2종(`idx_pose_logs_session_robot`, `idx_pose_logs_mode`) + RLS 정책 2종(`anon_insert_pose`, `anon_select_pose`) 검증 PASS.
- **✅ 2026-06-18 적용 완료**: Unity "직접 택배"(UnityWebRequest+PostgREST anon) 쓰기 경로용 SQL `scripts/sql/demo_logs_rls.sql`. 내용 ① 신규 `logs` 테이블, ② `dispatches.event_id` NOT NULL → nullable 완화 + `reason`/`nav_mode` 컬럼(맵 클릭 수동출동 기록), ③ `session_meta`/`dispatches`/`events`/`logs` anon INSERT·SELECT RLS 정책 (10개 정책 검증 PASS). **적용**: `supabase db query --linked --file scripts/sql/demo_logs_rls.sql` 실행. **검증**: `logs` 테이블 생성 ✅, `dispatches.nav_mode`/`reason` 컬럼 추가 ✅, anon RLS 정책 10개 ✅. evidence: `docs/evidence/2026-06-18-unity-supabase-direct-write.md`.
- 사진/영상/사운드 메타데이터, 액자형 보호 대상 테이블은 아래 "Planned Extensions"이며 아직 실제 DB에 적용되지 않았다.

## Tables

### `session_meta` — 시연/순찰 세션 메타

| Column | Type | NULL | Default | 비고 |
|---|---|---|---|---|
| `session_id` | UUID PK | NO | `gen_random_uuid()` | 한 세션 ID |
| `started_at` | TIMESTAMPTZ | NO | `now()` | UTC |
| `ended_at` | TIMESTAMPTZ | YES | NULL | 종료 시점 |
| `scenario` | TEXT | NO | — | `night_patrol`/`intrusion`/`noise`/`fire_mock`/`mixed` |
| `notes` | TEXT | YES | NULL | 자유 메모 |
| `recorded_by` | TEXT | YES | NULL | 운영자 이름 |

Index: 없음 (PK 단독).

### `events` — 센서 감지 이벤트

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `id` | UUID PK | NO | SecurityEvent UUID |
| `session_id` | UUID FK → session_meta | NO | |
| `robot_id` | TEXT | NO | `tb3_1` / `tb3_2` |
| `ts` | TIMESTAMPTZ | NO | UTC ms |
| `event_type` | TEXT | NO | as-built: `pir` / `sound` (SCRUM-23 예정: `asset_seen` / `asset_missing`). 구 `dark`(LDR 폐기)·`noise`→`sound` |
| `severity` | SMALLINT | NO | 0~3 |
| `x` | DOUBLE PRECISION | NO | meters |
| `y` | DOUBLE PRECISION | NO | meters |
| `theta` | DOUBLE PRECISION | NO | radians |
| `raw_payload` | JSONB | YES | 센서 원본 값(임계값, ADC 값 등) |

Index:
- `idx_events_session` on `(session_id, ts)` — 세션별 시간순 조회
- `idx_events_type` on `(event_type)` — 시나리오별 집계
- `idx_events_robot` on `(robot_id, ts)`

## Planned Extensions (SCRUM-23)

> 아래 구조는 박물관/미술관 액자 보호 요구를 위한 **확장 예정안**이다. 현재 Supabase에는 아직 없다. 적용 전 별도 migration SQL 작성 + 실제 DB 조회 검증이 필요하다.
> **`pose_logs`는 2026-06-02 적용 완료** — 표는 참고용으로 유지(Current Applied 항목과 동일 컬럼).

### `pose_logs` — 이동 좌표 로그 (✅ 2026-06-02 적용 완료)

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `id` | UUID PK | NO | |
| `session_id` | UUID FK → session_meta | NO | |
| `robot_id` | TEXT | NO | `tb3_1` / `tb3_2` |
| `ts` | TIMESTAMPTZ | NO | pose 기록 시각 |
| `x` | DOUBLE PRECISION | NO | meters |
| `y` | DOUBLE PRECISION | NO | meters |
| `theta` | DOUBLE PRECISION | NO | radians |
| `source_topic` | TEXT | YES | `/tb3_1/pose` 등 |
| `nav_mode` | TEXT | YES | `patrol` / `dispatch` / `lidar_boost` / `manual` |

Index:
- `idx_pose_logs_session_robot` on `(session_id, robot_id, ts)`
- `idx_pose_logs_mode` on `(nav_mode, ts)`

### `logs` — UI 로그 라인 (✅ 2026-06-18 적용 완료)

> Unity ControlRoom 화면 로그창의 모든 라인을 그대로 저장. "화면=DB 일치" 검증의 핵심 테이블.
> SQL: `scripts/sql/demo_logs_rls.sql`. RLS `anon_insert_logs`/`anon_select_logs`.

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `id` | UUID PK | NO | Unity(C#)가 생성 |
| `session_id` | UUID FK → session_meta | YES | 세션 전 로그 허용 위해 nullable |
| `ts` | TIMESTAMPTZ | NO | 발생 시각 |
| `level` | TEXT | NO | `INFO`/`WARN`/`ERROR` |
| `category` | TEXT | NO | `system`/`dispatch`/`sensor`/`gemma`/... |
| `message` | TEXT | NO | 로그 본문 |
| `source` | TEXT | NO | `ControlRoom`/`RobotPC` |

Index: `idx_logs_session_ts (session_id, ts)`, `idx_logs_category (category, ts)`

### `dispatches` — tb3_2 출동 기록

> 2026-06-18: 맵 클릭 수동출동(트리거 이벤트 없음) 기록 위해 `event_id` nullable로 완화, `reason`/`nav_mode` 컬럼 추가. SQL `scripts/sql/demo_logs_rls.sql`.

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `id` | UUID PK | NO | Dispatch UUID |
| `event_id` | UUID FK → events | YES | source 이벤트 (수동출동은 NULL, 2026-06-18 완화) |
| `reason` | TEXT | YES | 출동 사유 (`manual`/시나리오ID 등, 2026-06-18 추가) |
| `nav_mode` | TEXT | YES | `dispatch`/`patrol` 등 (2026-06-18 추가) |
| `target_robot_id` | TEXT | NO | 기본 `tb3_2` |
| `target_x` | DOUBLE PRECISION | NO | |
| `target_y` | DOUBLE PRECISION | NO | |
| `dispatched_at` | TIMESTAMPTZ | NO | 명령 발행 시각 |
| `arrived_at` | TIMESTAMPTZ | YES | nullable (도착 못 함 가능) |
| `response_time` | NUMERIC(6,2) | YES | seconds — `arrived_at - event.ts` 계산값 |
| `simulated` | BOOLEAN | NO | true=Unity 시뮬, false=실기 |

Index:
- `idx_dispatches_event` on `(event_id)`
- `idx_dispatches_session` join via events

### `camera_captures` — Pi Camera 확인 결과

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `id` | UUID PK | NO | |
| `dispatch_id` | UUID FK → dispatches | NO | |
| `robot_id` | TEXT | NO | 보통 `tb3_2` |
| `ts` | TIMESTAMPTZ | NO | |
| `image_path` | TEXT | NO | 로컬 경로 또는 Supabase Storage URL |
| `protected_asset_id` | TEXT | YES | 액자형 사진 타깃 또는 중요물품 ID |
| `result` | TEXT | NO | `confirmed`/`false_alarm`/`missed`/`unverified` |
| `ai_label` | TEXT | YES | M1 모델 결과 |
| `ai_confidence` | REAL | YES | 0~1 |
| `operator_note` | TEXT | YES | 운영자 코멘트 |

Index:
- `idx_captures_dispatch` on `(dispatch_id)`

### `media_artifacts` — 사진/영상/사운드 저장 메타데이터 (예정)

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `id` | UUID PK | NO | |
| `session_id` | UUID FK → session_meta | NO | |
| `event_id` | UUID FK → events | YES | 이벤트 연동 미디어 |
| `dispatch_id` | UUID FK → dispatches | YES | 출동 확인 미디어 |
| `robot_id` | TEXT | NO | |
| `ts` | TIMESTAMPTZ | NO | 캡처/녹음 시각 |
| `media_type` | TEXT | NO | `image` / `video` / `audio` |
| `storage_path` | TEXT | NO | Supabase Storage URL 또는 로컬 경로 |
| `duration_sec` | NUMERIC(6,2) | YES | 영상/사운드 길이 |
| `mime_type` | TEXT | YES | `image/jpeg`, `video/mp4`, `audio/wav` 등 |
| `metadata` | JSONB | YES | 해상도, 샘플레이트, 프레임 수, 파일 크기 |

Index:
- `idx_media_session` on `(session_id, ts)`
- `idx_media_event` on `(event_id)`
- `idx_media_type` on `(media_type, ts)`

### `protected_assets` — 박물관/미술관 보호 대상 (예정)

| Column | Type | NULL | 비고 |
|---|---|---|---|
| `asset_id` | TEXT PK | NO | 예: `frame_01` |
| `session_id` | UUID FK → session_meta | NO | 시연 세션별 등록 가능 |
| `name` | TEXT | NO | 액자/작품 이름 |
| `asset_type` | TEXT | NO | `photo_frame` / `object` |
| `x` | DOUBLE PRECISION | NO | 전시 위치 |
| `y` | DOUBLE PRECISION | NO | 전시 위치 |
| `marker_type` | TEXT | YES | `apriltag` / `qr` / `frame_color` / `manual` |
| `marker_value` | TEXT | YES | 태그 ID 또는 색상/라벨 |
| `expected_state` | TEXT | NO | `present` / `covered` / `unknown` |

Index:
- `idx_assets_session` on `(session_id, asset_id)`

## Migrations

- 초기 생성 SQL: `db/migrations/2026-05-27_init_security.sql` (4테이블 적용 완료)
- 박물관/미술관 보호 확장 SQL: `pose_logs`, `media_artifacts`, `protected_assets`, `camera_captures.protected_asset_id`, `events.event_type` check 확장(`asset_seen`, `asset_missing`) 추가 예정 (SCRUM-23)
- Supabase 사용 시 `supabase migration new` 워크플로 사용
- 모든 DDL 변경은 `CONTRACT.md` 동시 갱신 PR로

## Contracts

- ROS `SecurityEvent.id` ↔ `events.id` 동일 UUID
- ROS `Dispatch.id` ↔ `dispatches.id` 동일 UUID
- ROS `CameraConfirm.dispatch_id` ↔ `dispatches.id` 매칭
- `events.session_id`은 모든 후속 테이블에서 join 가능해야 한다 (직접 FK가 아니더라도 events 경유)
- `pose_logs`는 이벤트 전후 이동 경로 재구성을 위해 최소 1Hz 샘플링을 기본값으로 한다. `dark` 진입 시 `nav_mode='lidar_boost'`로 저장 빈도를 높일 수 있다.
- `camera_captures.protected_asset_id`와 `protected_assets.asset_id`는 액자형 사진 타깃 인식 결과를 연결한다.
- 원본 사진/영상/사운드는 DB에 bytea로 넣지 않는다. `media_artifacts.storage_path`만 정본으로 저장한다.

## 발표용 KPI 쿼리 (예시)

```sql
-- 시나리오별 평균 출동 시간 + 확인 성공률
SELECT
  s.scenario,
  COUNT(e.id) AS event_count,
  AVG(d.response_time) AS avg_response_sec,
  100.0 * SUM(CASE WHEN c.result = 'confirmed' THEN 1 ELSE 0 END) / NULLIF(COUNT(c.id), 0) AS confirm_rate
FROM session_meta s
JOIN events e ON e.session_id = s.session_id
LEFT JOIN dispatches d ON d.event_id = e.id
LEFT JOIN camera_captures c ON c.dispatch_id = d.id
GROUP BY s.scenario;
```

## Open Questions

- ~~DB 선정 미정 (2026-05-28, Day-1 차단)~~ → ✅ **해소 (2026-05-28)**: Supabase 프로젝트 `ueupkrxwybuuqxflstvg`로 잠금, 마이그레이션 적용·검증 완료. `DECISION-LOG.md` "DB 선정 완료" 참조.
- **RLS 정책 미정 (2026-05-28)** — 4 테이블 모두 RLS ON · 정책 0개. service_role 외부 접근만 가능. Unity·시연 대시보드에서 read-only SELECT가 필요해지면 anon용 SELECT policy를 추가할지 결정.
- AI 분류(`ai_label`)를 별도 `ai_labels` 테이블로 분리할지, `camera_captures` 인라인 컬럼으로 둘지 → S3 SCRUM-21 진행 시 결정.
- Supabase Storage vs 로컬 파일 시스템 — Pi 저장소 한계 + 발표 영상 백업 정책 고려.
- 실기 2대 운영 시 `dispatches.simulated=false` 조회를 추가 인덱스로 가속할지.
