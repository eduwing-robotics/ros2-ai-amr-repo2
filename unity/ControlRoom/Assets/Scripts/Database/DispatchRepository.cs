// opencode: 2026-06-29 - Supabase dispatches 테이블 읽기 Repository. Coded with OpenCode; high-cost model review recommended.
// DispatchRepository.cs — public.dispatches 읽기 전용. 쓰기는 SupabaseDbService가 담당.
// QueryRecent(최근 출동) + QueryActive(도착 기록 없는 진행 중 출동).
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Database
{
    public class DispatchRepository
    {
        readonly SupabaseClient client;

        public DispatchRepository(SupabaseClient client)
        {
            this.client = client;
        }

        public IEnumerator QueryRecent(int limit, Action<bool, List<DispatchRow>> onResult,
                                       string robotId = null)
        {
            if (client == null)
            {
                onResult?.Invoke(false, new List<DispatchRow>());
                yield break;
            }

            string q = $"dispatches?order=dispatched_at.desc&limit={limit}" +
                       "&select=id,event_id,target_robot_id,target_x,target_y,dispatched_at,arrived_at,response_time,simulated,reason,nav_mode";
            if (!string.IsNullOrEmpty(robotId)) q += $"&target_robot_id=eq.{robotId}";

            yield return client.Select(q, false, (ok, body, _) =>
            {
                if (!ok)
                {
                    onResult?.Invoke(false, new List<DispatchRow>());
                    return;
                }
                var arr = JsonUtility.FromJson<DispatchRowArray>(JsonHelper.WrapRows(body));
                var rows = arr?.rows ?? new DispatchRow[0];
                onResult?.Invoke(true, new List<DispatchRow>(rows));
            });
        }

        // 전체 출동 건수(count=exact). limit 기반 rows.Count는 cap에 막히므로 Content-Range count를 쓴다.
        public IEnumerator CountAll(Action<bool, int> onCount, string robotId = null)
        {
            if (client == null)
            {
                onCount?.Invoke(false, 0);
                yield break;
            }

            string q = "dispatches?select=id";
            if (!string.IsNullOrEmpty(robotId)) q += $"&target_robot_id=eq.{robotId}";

            yield return client.Select(q, true, (ok, _, n) => onCount?.Invoke(ok, ok ? n : 0));
        }

        public IEnumerator QueryActive(Action<bool, List<DispatchRow>> onResult, string robotId = null)
        {
            if (client == null)
            {
                onResult?.Invoke(false, new List<DispatchRow>());
                yield break;
            }

            string q = "dispatches?arrived_at=is.null&order=dispatched_at.desc" +
                       "&select=id,event_id,target_robot_id,target_x,target_y,dispatched_at,arrived_at,response_time,simulated,reason,nav_mode";
            if (!string.IsNullOrEmpty(robotId)) q += $"&target_robot_id=eq.{robotId}";

            yield return client.Select(q, false, (ok, body, _) =>
            {
                if (!ok)
                {
                    onResult?.Invoke(false, new List<DispatchRow>());
                    return;
                }
                var arr = JsonUtility.FromJson<DispatchRowArray>(JsonHelper.WrapRows(body));
                var rows = arr?.rows ?? new DispatchRow[0];
                onResult?.Invoke(true, new List<DispatchRow>(rows));
            });
        }

        // 평균 응답시간(초). response_time이 null인 행은 제외.
        public IEnumerator AvgResponseTime(Action<bool, double> onResult)
        {
            if (client == null)
            {
                onResult?.Invoke(false, 0);
                yield break;
            }

            string q = "dispatches?select=response_time.avg()&response_time=not.is.null";
            yield return client.Select(q, false, (ok, body, _) =>
            {
                if (!ok)
                {
                    onResult?.Invoke(false, 0);
                    return;
                }
                var arr = JsonUtility.FromJson<AvgResultArray>(JsonHelper.WrapRows(body));
                double avg = arr?.rows?.Length > 0 ? arr.rows[0].avg : 0;
                onResult?.Invoke(true, avg);
            });
        }

        [Serializable]
        class AvgResult { public double avg; }

        [Serializable]
        class AvgResultArray { public AvgResult[] rows; }
    }
}
