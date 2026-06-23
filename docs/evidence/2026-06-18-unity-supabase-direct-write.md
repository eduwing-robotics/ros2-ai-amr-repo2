# Unity ControlRoom → Supabase "직접 택배" 쓰기 구현 (2026-06-18)

> 목표: 시연 중 ① UI 로그 저장 ② 맵 클릭 좌표 지정→출동 기록 ③ 로봇 이동좌표 추적을 DB에 영속,
> 끊김 없이("직접 택배" UnityWebRequest+PostgREST anon) + 오프라인 안전판 + "화면=DB" 검증.
> 결정: 연동방식 = UnityWebRequest 직접(주인님 선택). SDK(supabase-csharp) 미채택(가벼움/끊김방지 우선).

## 1. 배경 / 갭

- DB(Supabase `ueupkrxwybuuqxflstvg`)·스키마·Unity stub은 이미 존재. 빈 곳은 ① Unity 실제 HTTP 쓰기 0줄 ② `logs` 테이블 부재 + `events`/`dispatches` anon RLS 0개 ③ 끊김방지·검증 장치 부재.
- 조사: 하이쿠 서브에이전트가 supabase-csharp SDK+Realtime 권고했으나, "유니티가 주로 쓰기" + "끊김 없는 시연" + 메모리 룰(가벼운 대안 먼저)에 따라 **UnityWebRequest 직접**으로 결정.
- **2026-06-18 업데이트**: Supabase 프로젝트 `ueupkrxwybuuqxflstvg`는 paused가 아니라 **복구되어 LIVE** (HTTP 200, Tokyo, service 접속 정상). 이전 evidence의 "paused/NXDOMAIN" 서술은 2026-06-18 이전의 상태이며 현재 정정됨.

## 2. 구현 산출물

### DB SQL (⏳ 적용 대기)
- `scripts/sql/demo_logs_rls.sql` — `logs` 테이블 신규 + `dispatches.event_id` nullable 완화(+`reason`/`nav_mode`) + `session_meta`/`dispatches`/`events`/`logs` anon INSERT·SELECT RLS. 패턴은 `pose_logs.sql` 복제.

### Unity 코드 (✅ 컴파일 PASS)
- `Database/SupabaseSettings.cs` — `Resources/SupabaseConfig/supabase.json` 로드. 없거나 service_role 감지 시 graceful 비활성.
- `Database/SupabaseClient.cs` — UnityWebRequest INSERT(POST)/SELECT(GET). apikey+Bearer 헤더, `Prefer:return=minimal`, count=exact 지원. 코루틴 반환(비차단).
- `Database/SupabaseDbService.cs` — 단일 라이터. `OnLogAdded`→logs, `OnDispatchRequested`→dispatches, `RobotPoseSubscriber.OnPoseUpdated`→pose_logs(Hz throttle+최소이동). **내구성 큐**: 클라이언트 UUID 생성 → FIFO 드레인(세션 먼저) → 실패 시 디스크 버퍼(`urhynix_db_buffer.jsonl`) 영속+자동 재시도, 4xx는 드롭(큐 막힘 방지).
- `Database/PoseLogRepository.cs` — NotImplemented 스텁 → 클라이언트 기반 read 헬퍼(coroutine)로 교체.
- `App/DbVerifyConsole.cs` — `unityctl exec`용 검증 콘솔. UI로그수(mem) vs DB logs수(+버퍼) + DB pose수 + 최근 pose 대조, verdict 출력.
- `App/ControlRoomApp.cs` — `CreateDbService()`로 부착(씬 YAML 비의존, DB 비활성이어도 안전).
- `Resources/SupabaseConfig/supabase.json`(.gitignore) + `supabase.example.json`(커밋) + `.gitignore` 항목.

## 3. 끊김 방지(시연) 설계 근거

| 위험 | 대응 |
|---|---|
| 네트워크가 메인스레드 블록 | UnityWebRequest 코루틴, 전부 fire-and-forget 큐잉 |
| pose 매프레임 폭증 | `poseWriteHz`(기본 2Hz) + `poseMinMoveMeters`(정지 시 스킵) throttle |
| DB 다운/와이파이 끊김(=오늘 paused 상황) | 디스크 버퍼 영속 + 복구 시 FIFO 자동 flush, UUID 클라생성으로 FK 보존 |
| 잘못된 row가 큐 영구 차단 | 4xx 응답은 드롭, 네트워크/5xx/429만 재시도 |

## 4. 검증 상태

| 항목 | 상태 | 근거 |
|---|---|---|
| Unity 컴파일 | ✅ PASS | `unityctl check` `scriptCompilationFailed:false`, 6파일 import(.meta 생성) 후 CompileScripts 이벤트 확인. (주의: 포커스 없으면 IPC refresh stale — `osascript activate`로 강제 import 후 재검증함) |
| DB SQL 적용 | ✅ PASS | `supabase db query --linked --file scripts/sql/demo_logs_rls.sql` 적용 완료. 검증: `logs` 테이블 생성 ✅, `dispatches.nav_mode`/`reason` 컬럼 추가 ✅, anon RLS 정책 10개(5테이블 × insert/select) ✅. |
| REST 쓰기 스모크 | ✅ PASS | curl anon 왕복 검증: `pose_logs` INSERT(201)→SELECT(200), `logs` INSERT(201)→SELECT(200), `session_meta` INSERT(201) 모두 성공. |
| Play 모드 end-to-end | ⚠️ 부분 PASS | Play 재시작 후 `SupabaseDbService.active=True` + 세션 생성됨(session_meta INSERT 동작). UI 로그 7건이 `logs` 테이블에 실제 기록됨(`DbVerifyConsole.Verify()` + DB 직조회). **미해결**: `pose_logs` 0건 — RobotPoseSubscriber가 /tf map프레임 못 받음(TF 체인/ROS 연결/센서 fake 여부 다음 추적). 블로커 아님(session_meta+logs만 필수). |

## 5. 다음 진입 (2026-06-18 완료 상태)

1. ✅ Supabase 프로젝트 복구 완료 (LIVE 확인).
2. ✅ `supabase db query --linked --file scripts/sql/demo_logs_rls.sql` 적용 완료.
3. ✅ curl anon 스모크 PASS: `session_meta`/`logs`/`pose_logs` INSERT(201)→SELECT(200).
4. ✅ Unity Play end-to-end 부분 PASS: session_meta + logs 기록 확인. pose_logs는 /tf map 프레임 미수신으로 0건 (다음 세션 TF 체인 추적).
5. ✅ SCHEMA.md "적용 대기"→"적용 완료", DECISION-LOG/PROJECT-STATUS 갱신 완료.

**남은 과제**: `pose_logs` 미기록 원인 추적 (RobotPoseSubscriber → /tf map 프레임 수신 또는 TF 체인 확인).

## 6. 보안

- anon(publishable) 키만 클라이언트 반입(`sb_publishable_...`, SCHEMA.md가 "공개 가능"으로 명시). service_role 미반입. 설정 파일은 `.gitignore` 차단.
