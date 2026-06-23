# DB 선택 재검증 자료조사 — Supabase 유지 (2026-06-18)

> "Supabase vs 직접 운영 PostgreSQL vs 더 나은 대안" 질문에 대한 재검증 기록.
> 결론: 기존 Supabase 선택(2026-05-28 결정)이 요구사항에 부합 → 유지. 로컬 SQLite 백업 안전판 권고.
> 조사: 하이쿠 서브에이전트(프로젝트 문서 6종 정독) + 메인(Opus) 종합. 결정 주체: 주인님.

## 1. 배경 — 이미 결정된 사안의 재검증

DB는 **2026-05-28에 Supabase(`ueupkrxwybuuqxflstvg`)로 결정·마이그레이션 완료**됐다(`SCHEMA.md:5-7`). 본 조사는 신규 선정이 아니라 "그 선택이 맞았는가"를 프로젝트 데이터 요구사항 기준으로 재검증한 것이다.

### 핵심 개념 교정 — "Supabase vs 파이썬 PostgreSQL"은 대립이 아니다
- **Supabase = 매니지드 PostgreSQL** 그 자체. 내부에 실제 Postgres가 돈다. 거기에 Realtime(실시간 push) + Auth + 자동 REST API + 웹 대시보드를 얹은 것.
- **"직접 운영 PostgreSQL + 파이썬(psycopg/SQLAlchemy)"** = 실시간 push·인증·백업·대시보드를 전부 직접 구현해야 함.
- 즉 **Supabase를 쓰면서 파이썬으로 붙는 것이 현 아키텍처** (로봇 RPi가 파이썬으로 Supabase에 insert). 양자택일이 아님.

## 2. 프로젝트 데이터 요구사항 (조사로 추출)

| 항목 | 내용 | 근거 |
|------|------|------|
| 저장 데이터 | 센서 이벤트(dark/PIR/noise/온도/화재) + 로봇 좌표(`pose_logs`) + 출동/카메라 확인 + 미디어 메타 + 세션 메타 | `SCHEMA.md:25-156` |
| 쓰기 패턴 | 센서 이벤트 단발(burst 아님), `pose_logs` 1~10Hz(boost 시), 디스패치/카메라 이벤트당 1회 | `SCHEMA.md`, `CONTRACT.md:28-67` |
| 읽기 패턴 | 실시간(Unity 관제 push 중심) + 배치(발표용 KPI 쿼리) | `SCHEMA.md:174-188` |
| 환경 제약 | 팀 와이파이 AP isolation·IP drift, 발표 시연 중심(클라우드 의존 낮음) | `DECISION-CURRENT.md:74-76` |

## 3. 선택지 비교

| 항목 | Supabase (현재) | 직접 PostgreSQL | TimescaleDB | SQLite | Firebase |
|---|---|---|---|---|---|
| 센서 시계열 적합성 | ◎ TIMESTAMPTZ+JSONB | ◎ | ◎◎ 시계열 특화 | ○ | ○ |
| 실시간 push | ◎ Realtime API | △ LISTEN/NOTIFY 자작 | ○ | ✕ 폴링만 | ◎◎ built-in |
| 무선격리/오프라인 | △ 인터넷 필요 | ◎ 로컬망 | ◎ 로컬망 | ◎◎ 오프라인 | ✕ 인터넷 필수 |
| 발표 간편성 | ◎ 웹 대시보드 | ○ Grafana 필요 | ○ Grafana 필요 | △ 스크립트 | ◎ |
| KPI 집계 쿼리 | ◎ 표준 SQL | ◎ | ◎◎ | ○ | ✕ 복잡쿼리 약함 |
| 셋업/운영 부담 | ◎◎ 관리형·자동백업 | △ 자체관리·백업필수 | △ 자체관리 | ◎◎ 파일 하나 | ◎ Google 관리 |
| 비용 | ◎ free tier 충분 | ◎◎ 무료 self-host | ◎◎ 무료 | ◎◎ 무료 | ○ tier 제한 |

## 4. 결론 및 권고

**Supabase 유지 (선택이 맞았음).** 근거:
1. **Realtime API** — Unity 관제가 이벤트/포즈를 폴링 없이 push 수신.
2. **RLS 권한 분리** — `service_role`(로봇 쓰기) vs `anon`(Unity 읽기). 키는 RPi `/etc/urhynix.env`에만.
3. **발표 친화** — 웹 대시보드·공유 링크로 즉석 시각화.
4. **Free tier로 충분** — 5개 테이블 + `pose_logs` 규모(세션당 최대 ~36k행).

### 리스크 + 안전판
- **리스크**: 클라우드 의존 → 발표장 와이파이 끊기면 멈춤(`urhynix-team-wifi-isolation-direct-link` 환경 고질병).
- **권고 1 (안전판)**: 로봇 로컬에 **SQLite 백업 로거 병렬 운영** → 클라우드 장애 시 데이터 유실 0. (Unity 실시간 표시는 여전히 Supabase 담당, SQLite는 보험)
- **권고 2 (미래)**: `pose_logs` 조회가 느려지면 그때 **TimescaleDB** 마이그레이션 검토. 지금은 과설계 → 보류.

## 5. 근거 파일

- `docs/ref/SCHEMA.md:5-7,21-22,174-193` — DB 선정·마이그레이션·KPI·RLS
- `docs/ref/CONTRACT.md:28-67` — 보안 이벤트 토픽/메시지
- `docs/ref/ARCHITECTURE.md:3-46` — DB Writer 노드/저장소
- `docs/status/DECISION-CURRENT.md:9-17,74-76` — 센서 교체·무선 단일화
- 메모리 `urhynix-team-wifi-isolation-direct-link` — AP isolation 환경
