// SupabaseClient.cs — "직접 택배" REST 클라이언트 (UnityWebRequest + PostgREST).
// 무패키지/빌트인. anon(publishable) 키로 INSERT(POST)/SELECT(GET)만. service_role 미반입.
// 코루틴 반환만 함(스스로 실행 안 함) — MonoBehaviour인 SupabaseDbService가 StartCoroutine으로 돌림.
// 메인스레드 비차단: UnityWebRequest.SendWebRequest()는 프레임을 막지 않음 → 시연 끊김 없음.
using System;
using UnityEngine;
using UnityEngine.Networking;

namespace URHYNIX.ControlRoom.Database
{
    public class SupabaseClient
    {
        public string Url { get; }
        public string AnonKey { get; }

        const int TimeoutSec = 8;   // 응답 없으면 8초 후 실패 처리(버퍼로 되돌림)

        public SupabaseClient(string url, string anonKey)
        {
            Url = url.TrimEnd('/');
            AnonKey = anonKey;
        }

        // 단건/다건 INSERT. body는 JSON 객체 또는 배열 문자열.
        // onDone(success, errorOrEmpty). 실패 시 호출부가 버퍼에 되돌림.
        public System.Collections.IEnumerator Insert(string table, string jsonBody, Action<bool, string> onDone)
        {
            string url = $"{Url}/rest/v1/{table}";
            using (var req = new UnityWebRequest(url, "POST"))
            {
                byte[] bytes = System.Text.Encoding.UTF8.GetBytes(jsonBody);
                req.uploadHandler = new UploadHandlerRaw(bytes);
                req.downloadHandler = new DownloadHandlerBuffer();
                ApplyHeaders(req);
                req.SetRequestHeader("Content-Type", "application/json");
                req.SetRequestHeader("Prefer", "return=minimal");   // 응답 본문 최소화 → 빠름
                req.timeout = TimeoutSec;

                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success)
                    onDone?.Invoke(true, "");
                else
                    onDone?.Invoke(false, $"{(int)req.responseCode} {req.error} {Trim(req.downloadHandler?.text)}");
            }
        }

        // SELECT. query 예: "logs?select=id&session_id=eq.<uuid>&order=ts.desc&limit=1".
        // wantCount=true면 Prefer:count=exact + onDone에 Content-Range의 총개수 파싱해 넘김(count out).
        public System.Collections.IEnumerator Select(string query, bool wantCount, Action<bool, string, int> onDone)
        {
            string url = $"{Url}/rest/v1/{query}";
            using (var req = UnityWebRequest.Get(url))
            {
                ApplyHeaders(req);
                if (wantCount) req.SetRequestHeader("Prefer", "count=exact");
                req.timeout = TimeoutSec;

                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success)
                {
                    int count = -1;
                    if (wantCount)
                    {
                        // Content-Range: "0-9/42" → 42
                        var cr = req.GetResponseHeader("Content-Range") ?? req.GetResponseHeader("content-range");
                        if (!string.IsNullOrEmpty(cr))
                        {
                            int slash = cr.LastIndexOf('/');
                            if (slash >= 0 && int.TryParse(cr.Substring(slash + 1), out int n)) count = n;
                        }
                    }
                    onDone?.Invoke(true, req.downloadHandler.text, count);
                }
                else
                {
                    onDone?.Invoke(false, $"{(int)req.responseCode} {req.error}", -1);
                }
            }
        }

        void ApplyHeaders(UnityWebRequest req)
        {
            req.SetRequestHeader("apikey", AnonKey);
            req.SetRequestHeader("Authorization", "Bearer " + AnonKey);
        }

        static string Trim(string s) => string.IsNullOrEmpty(s) ? "" : (s.Length > 200 ? s.Substring(0, 200) : s);
    }
}
