# scripts/sql/

> URHYNIX Supabase migration SQL 모음. 적용 결과는 `docs/ref/SCHEMA.md`로 반영.

## 실행 경로

| 경로 | 언제 |
|---|---|
| Supabase Dashboard → SQL Editor → 붙여넣기 → Run | 사람이 직접, 1회성 |
| Management API SQL endpoint (`SUPABASE_ACCESS_TOKEN` 사용) | 자동화 또는 RPi에서 |
| Supabase MCP (`supabase-mcp` 스킬) | 후속, 적용 흔적까지 자동 수집 |

## 적용 순서

1. SQL 파일에 `-- 실행 일자: YYYY-MM-DD` 주석 박기.
2. Dashboard 또는 Management API로 실행.
3. 검증 SQL(파일 하단 주석)로 결과 확인.
4. `docs/ref/SCHEMA.md` "Planned Extensions" → "Current Applied"로 표 이동.
5. `docs/status/DECISION-LOG.md`에 적용 일자/검증 결과 한 줄.

## 명명 규칙

- `<table_name>.sql` — 테이블 1개 신설.
- `<YYYYMMDD>_<purpose>.sql` — 복합 migration 또는 정책 변경.
- DROP / dangerous migration은 별도 파일로 분리 + 사람 리뷰 강제.

## 보안

- 본 폴더는 SQL 텍스트만. **service_role 키, anon key 절대 박지 않음**.
- 키는 RPi `/etc/urhynix.env` 또는 Mac `~/.tb3rc`. 환경변수로만 전달.

## 현재 파일

| 파일 | 상태 |
|---|---|
| `pose_logs.sql` | ✅ 2026-06-02 적용 완료 (Supabase CLI `db query --linked`). 검증: 인덱스 3종 + RLS 정책 2종 + count=0. |
| `demo_logs_rls.sql` | ✅ 2026-06-18 적용 완료 (supabase db query --linked). 검증: logs 테이블 + dispatches nav_mode/reason 컬럼 + anon 정책 10개(5테이블 × insert/select). REST anon 왕복 PASS(pose_logs/logs insert/select 201→200). |
