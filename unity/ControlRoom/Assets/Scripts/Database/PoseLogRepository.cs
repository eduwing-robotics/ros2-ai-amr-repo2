// PoseLogRepository.cs — Supabase `pose_logs` read 헬퍼 (coroutine + callback).
// "직접 택배"(UnityWebRequest) 클라이언트 위 얇은 래퍼. 주 쓰기는 SupabaseDbService가 담당.
// 코루틴 스타일로 통일(Task 아님) — 호출부가 MonoBehaviour.StartCoroutine으로 돌림.
// service_role 키 절대 미반입. anon key + RLS(anon_select_pose) 경로만.
using System;
using System.Collections;

namespace URHYNIX.ControlRoom.Database
{
    public class PoseLogRepository
    {
        readonly SupabaseClient client;

        public PoseLogRepository(SupabaseClient client)
        {
            this.client = client;
        }

        // 세션별 시간순 pose 조회. onResult(success, rawJson). 파싱은 호출부 책임.
        // SCHEMA index: idx_pose_logs_session_robot on (session_id, robot_id, ts).
        public IEnumerator QueryBySession(string sessionId, Action<bool, string> onResult,
                                          string robotId = null, int limit = 1000)
        {
            string q = $"pose_logs?session_id=eq.{sessionId}&order=ts.asc&limit={limit}" +
                       "&select=id,robot_id,ts,x,y,theta,source_topic,nav_mode";
            if (!string.IsNullOrEmpty(robotId)) q += $"&robot_id=eq.{robotId}";
            yield return client.Select(q, false, (ok, body, _) => onResult?.Invoke(ok, body));
        }

        // 모드별 pose 조회 (시연 시 patrol/dispatch 구간 분석). idx_pose_logs_mode 활용.
        public IEnumerator QueryByNavMode(string navMode, Action<bool, string> onResult, int limit = 1000)
        {
            string q = $"pose_logs?nav_mode=eq.{navMode}&order=ts.desc&limit={limit}" +
                       "&select=id,robot_id,ts,x,y,theta,nav_mode";
            yield return client.Select(q, false, (ok, body, _) => onResult?.Invoke(ok, body));
        }

        // 세션 pose 총개수 (count=exact). onCount(success, count).
        public IEnumerator CountBySession(string sessionId, Action<bool, int> onCount)
        {
            yield return client.Select($"pose_logs?select=id&session_id=eq.{sessionId}", true,
                (ok, _, n) => onCount?.Invoke(ok, n));
        }
    }
}
