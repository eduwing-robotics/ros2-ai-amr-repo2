// opencode: 2026-06-29 - Supabase events 테이블 읽기 Repository. Coded with OpenCode; high-cost model review recommended.
// EventRepository.cs — public.events 읽기 전용. 쓰기는 SupabaseDbService가 담당.
// SupabaseClient.Select 코루틴 래퍼. DB 비활성 시 onResult(false, empty) graceful.
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Database
{
    public class EventRepository
    {
        readonly SupabaseClient client;

        public EventRepository(SupabaseClient client)
        {
            this.client = client;
        }

        public IEnumerator QueryRecent(int limit, Action<bool, List<EventRow>> onResult,
                                       string robotId = null, int? minSeverity = null)
        {
            if (client == null)
            {
                onResult?.Invoke(false, new List<EventRow>());
                yield break;
            }

            // raw_payload(JSONB)는 의도적으로 제외 — JsonUtility가 객체를 string 필드에 못 담아 행 파싱이 깨진다.
            // 현재 화면에서 미사용. 필요해지면 별도 jsonb 전용 조회로 분리.
            string q = $"events?order=ts.desc&limit={limit}" +
                       "&select=id,session_id,robot_id,ts,event_type,severity,x,y,theta";
            if (!string.IsNullOrEmpty(robotId)) q += $"&robot_id=eq.{robotId}";
            if (minSeverity.HasValue) q += $"&severity=gte.{minSeverity.Value}";

            yield return client.Select(q, false, (ok, body, _) =>
            {
                if (!ok)
                {
                    onResult?.Invoke(false, new List<EventRow>());
                    return;
                }
                var arr = JsonUtility.FromJson<EventRowArray>(JsonHelper.WrapRows(body));
                var rows = arr?.rows ?? new EventRow[0];
                onResult?.Invoke(true, new List<EventRow>(rows));
            });
        }

        // 전체 이벤트 건수(count=exact).
        public IEnumerator CountAll(Action<bool, int> onCount, string robotId = null)
        {
            if (client == null)
            {
                onCount?.Invoke(false, 0);
                yield break;
            }

            string q = "events?select=id";
            if (!string.IsNullOrEmpty(robotId)) q += $"&robot_id=eq.{robotId}";

            yield return client.Select(q, true, (ok, _, n) => onCount?.Invoke(ok, ok ? n : 0));
        }
    }
}
