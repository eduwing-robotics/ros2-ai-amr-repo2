# Assets/Scripts/Persistence/

> 저장·복원 책임. 로컬 우선(끊겨도 안전) + (단계화) Supabase 동기화.

## 파일

| 파일 | 책임 |
|---|---|
| `PatrolRepository.cs` | 순찰 경로 로컬 영속(persistentDataPath/patrols/<mapId>.json), 맵별 자동 저장/복원 |

## 규칙

- **로컬 우선**: 변경 즉시 로컬 기록(네트워크 대기 금지). Wi-Fi 끊겨도 손실 없음.
- Supabase 동기화는 fire-and-forget(실패해도 UI 무영향). `patrol_routes` 테이블은 `scripts/sql/patrol_routes.sql` 적용 후 활성.
- service_role 키 미반입. anon + RLS(`Database/SupabaseClient`) 경유.
- 런타임 사용자 데이터는 Assets 밖 `persistentDataPath`에 기록(빌드 후 쓰기 가능).
