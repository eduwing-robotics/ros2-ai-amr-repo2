// DbVerifyConsole.cs — "화면에 뜬 정보가 DB에도 저장됐나" 검증 콘솔. unityctl exec로 호출.
// 호출: unityctl exec --code 'URHYNIX.ControlRoom.App.DbVerifyConsole.Verify()'
// 즉시 메모리 상태(세션/대기버퍼/UI로그수) 반환 + DB 카운트(logs/pose_logs)·최근 pose는 비동기로 Debug.Log.
// SensorVerifyConsole 자매 — 시연 직전 표준 검증.
using System.Text;
using UnityEngine;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.App
{
    public static class DbVerifyConsole
    {
        // 즉시 메모리 상태 반환(동기) + DB 대조는 코루틴으로 Debug.Log.
        public static string Verify()
        {
            var sb = new StringBuilder();
            sb.AppendLine("=== DB Verify ===");
            sb.AppendLine($"active={SupabaseDbService.Active}");
            sb.AppendLine($"session={SupabaseDbService.SessionId}");
            sb.AppendLine($"uiLogCount(mem)={SupabaseDbService.UiLogCount}");
            sb.AppendLine($"pendingBuffer={SupabaseDbService.PendingCount}");

            var svc = SupabaseDbService.Instance;
            if (svc == null || !SupabaseDbService.Active)
            {
                sb.AppendLine("DB 비활성 — DB 대조 생략(메모리 상태만).");
                return sb.ToString();
            }
            svc.StartCoroutine(CompareWithDb());
            sb.AppendLine("DB 대조 쿼리 실행 중 → 결과는 Console(Debug.Log [DbVerify])에 출력됨.");
            return sb.ToString();
        }

        static System.Collections.IEnumerator CompareWithDb()
        {
            var client = SupabaseDbService.Instance.Client;
            string sid = SupabaseDbService.SessionId;

            int dbLogs = -1, dbPoses = -1;
            yield return client.Select($"logs?select=id&session_id=eq.{sid}", true,
                (ok, _, n) => { if (ok) dbLogs = n; });
            yield return client.Select($"pose_logs?select=id&session_id=eq.{sid}", true,
                (ok, _, n) => { if (ok) dbPoses = n; });

            string latest = "(none)";
            yield return client.Select($"pose_logs?session_id=eq.{sid}&order=ts.desc&limit=1&select=x,y,ts", false,
                (ok, body, _) => { if (ok && !string.IsNullOrEmpty(body) && body.Length > 2) latest = body; });

            int uiLogs = SupabaseDbService.UiLogCount;
            int pending = SupabaseDbService.PendingCount;
            string logVerdict = dbLogs < 0 ? "쿼리실패"
                : (dbLogs + pending >= uiLogs ? "OK(화면≈DB+버퍼)" : "MISMATCH(누락 의심)");

            Debug.Log(
                "[DbVerify] ───────────────\n" +
                $"[DbVerify] session   = {sid}\n" +
                $"[DbVerify] UI logs   = {uiLogs} (화면 발생)\n" +
                $"[DbVerify] DB logs   = {dbLogs} (저장됨)  + pending {pending}\n" +
                $"[DbVerify] DB poses  = {dbPoses}\n" +
                $"[DbVerify] latestPose= {latest}\n" +
                $"[DbVerify] verdict   = {logVerdict}\n" +
                "[DbVerify] ───────────────");
        }
    }
}
