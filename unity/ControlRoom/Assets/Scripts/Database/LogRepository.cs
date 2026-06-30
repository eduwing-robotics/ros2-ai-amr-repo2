// opencode: 2026-06-29 - Supabase logs 테이블 읽기 Repository. Coded with OpenCode; high-cost model review recommended.
// LogRepository.cs — public.logs 읽기 전용. 쓰기는 SupabaseDbService가 담당.
// 카테고리/레벨 필터 + 최근 N건 조회. 기록 탭 로그검색 백엔드.
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Database
{
    public class LogRepository
    {
        readonly SupabaseClient client;

        public LogRepository(SupabaseClient client)
        {
            this.client = client;
        }

        public IEnumerator Query(int limit, Action<bool, List<LogRow>> onResult,
                                 string category = null, string level = null)
        {
            if (client == null)
            {
                onResult?.Invoke(false, new List<LogRow>());
                yield break;
            }

            string q = $"logs?order=ts.desc&limit={limit}" +
                       "&select=id,session_id,ts,level,category,message,source";
            if (!string.IsNullOrEmpty(category)) q += $"&category=eq.{category}";
            if (!string.IsNullOrEmpty(level)) q += $"&level=eq.{level}";

            yield return client.Select(q, false, (ok, body, _) =>
            {
                if (!ok)
                {
                    onResult?.Invoke(false, new List<LogRow>());
                    return;
                }
                var arr = JsonUtility.FromJson<LogRowArray>(JsonHelper.WrapRows(body));
                var rows = arr?.rows ?? new LogRow[0];
                onResult?.Invoke(true, new List<LogRow>(rows));
            });
        }

        // 조건에 맞는 로그 건수(count=exact).
        public IEnumerator Count(Action<bool, int> onCount, string category = null, string level = null)
        {
            if (client == null)
            {
                onCount?.Invoke(false, 0);
                yield break;
            }

            string q = "logs?select=id";
            if (!string.IsNullOrEmpty(category)) q += $"&category=eq.{category}";
            if (!string.IsNullOrEmpty(level)) q += $"&level=eq.{level}";

            yield return client.Select(q, true, (ok, _, n) => onCount?.Invoke(ok, ok ? n : 0));
        }
    }
}
