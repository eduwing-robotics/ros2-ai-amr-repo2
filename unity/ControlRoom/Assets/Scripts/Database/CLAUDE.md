# Assets/Scripts/Database/

> Supabase 제한 권한 클라이언트. service_role 키 절대 미반입.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `SupabaseClient.cs` | REST/Edge Function 클라이언트 (anon key + UniTask) |
| `RobotConfigRepository.cs` | 로봇/기능/센서 설정 조회 |
| `ProtectedTargetRepository.cs` | 보호대상 저장/조회 |
| `SessionRepository.cs` | `session_meta` 저장/조회 |
| `EventRepository.cs` | `events` 저장/조회 |
| `DispatchRepository.cs` | `dispatches` 저장/조회 |
| `CameraRepository.cs` | `camera_captures` 저장/조회 |
| `PoseLogRepository.cs` ✅ | `pose_logs` read 헬퍼 (coroutine) |
| `SupabaseSettings.cs` ✅ | `Resources/SupabaseConfig/supabase.json` 로드 (anon 키, graceful 비활성) |
| `SupabaseClient.cs` ✅ | UnityWebRequest REST 클라이언트 (INSERT/SELECT, "직접 택배") |
| `SupabaseDbService.cs` ✅ | 단일 DB 라이터 — 이벤트→insert, throttle, 내구성 큐+오프라인 버퍼 |

## 권한 정책 (중요)

- **Unity = read + 제한 INSERT만**. `dispatches`(출동), `session_meta`(사람 액션)만 쓰기.
- **service_role 키 절대 미반입**. anon key는 `Resources/SupabaseConfig.local.asset` (`.gitignore`).
- 민감 작업(전원 종료/RLS 우회)은 Supabase **Edge Function** 호출만.
- **주 쓰기 주체는 로봇 PC** (Python ROS2 노드 + anon + RLS).

## Supabase 진입점

- URL: `https://ueupkrxwybuuqxflstvg.supabase.co`
- 연동: **"직접 택배" = UnityWebRequest + PostgREST** (무패키지, 2026-06-18 결정). supabase-csharp SDK 미채택 — 가벼움/끊김방지 우선. 멀티화면 실시간 공유가 필요해지면 그때 Realtime SDK 재검토.
- 비동기: 코루틴(`StartCoroutine`). 모든 쓰기는 fire-and-forget 큐잉(`SupabaseDbService`).
- 설정: `Resources/SupabaseConfig/supabase.json`(.gitignore) — `supabase.example.json` 복사해 생성.

## 관련 스킬

- `supabase-mcp` — TaillogToss 운영 스킬, URHYNIX에 적용 시 schema/migration 참고 가능.
- `secret-scan` — 커밋 전 키 노출 점검.
