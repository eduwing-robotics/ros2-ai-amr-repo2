// SupabaseDbService.cs — ControlRoom 이벤트를 Supabase로 흘려보내는 단일 DB 라이터.
// "직접 택배"(UnityWebRequest) + 내구성 큐(오프라인 버퍼/디스크 영속/자동 재시도).
// 설계 원칙(시연 끊김 0):
//   1) 모든 쓰기는 fire-and-forget 큐잉 → UI/ROS 메인스레드 절대 비차단.
//   2) UUID는 클라이언트(C#)가 생성 → 오프라인 버퍼를 순서대로 flush해도 FK 충족.
//   3) pose는 throttle(Hz)+최소이동거리로 큐 폭증 방지.
//   4) DB 다운/와이파이 끊김 시 디스크 버퍼에 쌓였다가 복구되면 자동 송신.
// service_role 키 절대 미반입. anon RLS 경로만.
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Database
{
    public class SupabaseDbService : MonoBehaviour
    {
        public static SupabaseDbService Instance { get; private set; }

        SupabaseSettings settings;
        SupabaseClient client;
        string sessionId;
        bool active;

        readonly List<(string table, string body)> queue = new List<(string, string)>();
        readonly object qlock = new object();
        string bufferPath;
        bool dirty;

        // pose throttle 상태
        float lastPoseTime;
        float lastX, lastY;
        bool hasLastPose;

        // 검증 콘솔용 카운터
        public static int UiLogCount { get; private set; }
        public static string SessionId => Instance != null ? Instance.sessionId : null;
        public static int PendingCount { get { if (Instance == null) return 0; lock (Instance.qlock) return Instance.queue.Count; } }
        public static bool Active => Instance != null && Instance.active;
        public SupabaseClient Client => client;

        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        void Awake()
        {
            if (Instance != null) { Destroy(gameObject); return; }
            Instance = this;

            settings = SupabaseSettings.Load();
            if (settings == null || !settings.enabled)
            {
                Debug.LogWarning("[SupabaseDbService] 비활성(설정 없음/disabled) — 앱은 DB 없이 동작.");
                return;
            }

            client = new SupabaseClient(settings.url, settings.anonKey);
            sessionId = Guid.NewGuid().ToString();
            bufferPath = Path.Combine(Application.persistentDataPath, "urhynix_db_buffer.jsonl");
            active = true;

            LoadBuffer();
            EnqueueSession();   // 세션 row 먼저(자식 row들의 FK 대상)

            ControlRoomEvents.OnLogAdded += OnLogAdded;
            ControlRoomEvents.OnDispatchRequested += OnDispatchRequested;
            RobotPoseSubscriber.OnPoseUpdated += OnPoseUpdated;

            StartCoroutine(DrainLoop());
            StartCoroutine(FlushBufferLoop());
            Debug.Log($"[SupabaseDbService] 🟢 활성 session={sessionId} buffered={queue.Count}");
        }

        void OnDestroy()
        {
            if (Instance != this) return;
            ControlRoomEvents.OnLogAdded -= OnLogAdded;
            ControlRoomEvents.OnDispatchRequested -= OnDispatchRequested;
            RobotPoseSubscriber.OnPoseUpdated -= OnPoseUpdated;
            if (active) PersistBuffer();
        }

        void OnApplicationQuit() { if (active) PersistBuffer(); }

        // ── 이벤트 핸들러 (모두 메인스레드: 가벼운 큐잉만) ──────────────

        void OnLogAdded(string category, string level, string message)
        {
            UiLogCount++;
            if (!active) return;
            string body = "{" +
                $"\"id\":\"{Guid.NewGuid()}\"," +
                $"\"session_id\":\"{sessionId}\"," +
                $"\"ts\":\"{NowIso()}\"," +
                $"\"level\":\"{Esc(level)}\"," +
                $"\"category\":\"{Esc(category)}\"," +
                $"\"message\":\"{Esc(message)}\"," +
                "\"source\":\"ControlRoom\"}";
            Enqueue("logs", body);
        }

        void OnDispatchRequested(string robotId, float x, float y, string reason)
        {
            if (!active) return;
            string rid = string.IsNullOrEmpty(robotId) ? settings.defaultRobotId : robotId;
            string body = "{" +
                $"\"id\":\"{Guid.NewGuid()}\"," +
                $"\"target_robot_id\":\"{Esc(rid)}\"," +
                $"\"target_x\":{Num(x)},\"target_y\":{Num(y)}," +
                $"\"dispatched_at\":\"{NowIso()}\"," +
                "\"simulated\":true," +
                $"\"reason\":\"{Esc(reason)}\"," +
                "\"nav_mode\":\"dispatch\"}";
            Enqueue("dispatches", body);
        }

        void OnPoseUpdated(float x, float y, float yaw)
        {
            if (!active) return;
            float now = Time.unscaledTime;
            float minDt = settings.poseWriteHz > 0 ? 1f / settings.poseWriteHz : 0.5f;
            if (hasLastPose)
            {
                if (now - lastPoseTime < minDt) return;                       // Hz throttle
                float dx = x - lastX, dy = y - lastY;
                if (dx * dx + dy * dy < settings.poseMinMoveMeters * settings.poseMinMoveMeters) return; // 정지 시 스킵
            }
            lastPoseTime = now; lastX = x; lastY = y; hasLastPose = true;

            string body = "{" +
                $"\"id\":\"{Guid.NewGuid()}\"," +
                $"\"session_id\":\"{sessionId}\"," +
                $"\"robot_id\":\"{Esc(settings.defaultRobotId)}\"," +
                $"\"ts\":\"{NowIso()}\"," +
                $"\"x\":{Num(x)},\"y\":{Num(y)},\"theta\":{Num(yaw)}," +
                "\"source_topic\":\"/tf\",\"nav_mode\":\"patrol\"}";
            Enqueue("pose_logs", body);
        }

        // ── 큐 / 드레인 / 버퍼 ────────────────────────────────────────

        void EnqueueSession()
        {
            string sc = settings.scenario;
            // session_meta.scenario CHECK 위반 방지(허용값만).
            if (sc != "night_patrol" && sc != "intrusion" && sc != "noise" && sc != "fire_mock" && sc != "mixed")
                sc = "mixed";
            string body = "{" +
                $"\"session_id\":\"{sessionId}\"," +
                $"\"scenario\":\"{sc}\"," +
                $"\"started_at\":\"{NowIso()}\"," +
                "\"recorded_by\":\"ControlRoom\"," +
                "\"notes\":\"Unity ControlRoom 시연 세션\"}";
            Enqueue("session_meta", body);
        }

        void Enqueue(string table, string body)
        {
            lock (qlock) { queue.Add((table, body)); dirty = true; }
        }

        // FIFO 드레인 — 순서 보장(session_meta → 자식). 영구실패(4xx)는 드롭, 일시실패는 유지 재시도.
        IEnumerator DrainLoop()
        {
            var shortWait = new WaitForSeconds(0.15f);
            var backoff = new WaitForSeconds(3f);
            while (true)
            {
                (string table, string body) item;
                lock (qlock)
                {
                    if (queue.Count == 0) { item = (null, null); }
                    else item = queue[0];
                }
                if (item.table == null) { yield return shortWait; continue; }

                bool done = false, ok = false; int code = 0;
                yield return client.Insert(item.table, item.body, (s, e) =>
                {
                    ok = s; done = true;
                    if (!s) { code = ParseLeadingInt(e); Debug.LogWarning($"[SupabaseDbService] {item.table} 실패: {e}"); }
                });

                if (ok)
                {
                    lock (qlock) { if (queue.Count > 0) queue.RemoveAt(0); dirty = true; }
                }
                else if (code >= 400 && code < 500 && code != 429)
                {
                    // 영구 실패(잘못된 row/정책) → 큐 막힘 방지 위해 드롭
                    Debug.LogWarning($"[SupabaseDbService] {item.table} 영구실패({code}) 드롭");
                    lock (qlock) { if (queue.Count > 0) queue.RemoveAt(0); dirty = true; }
                }
                else
                {
                    // 네트워크/타임아웃/5xx/429/일시정지 → 유지하고 백오프 후 재시도
                    yield return backoff;
                }
            }
        }

        IEnumerator FlushBufferLoop()
        {
            var wait = new WaitForSeconds(1f);
            while (true)
            {
                yield return wait;
                if (dirty) { PersistBuffer(); dirty = false; }
            }
        }

        void PersistBuffer()
        {
            try
            {
                var sb = new StringBuilder();
                lock (qlock)
                    foreach (var it in queue) sb.Append(it.table).Append('\t').Append(it.body).Append('\n');
                File.WriteAllText(bufferPath, sb.ToString());
            }
            catch (Exception e) { Debug.LogWarning($"[SupabaseDbService] 버퍼 저장 실패: {e.Message}"); }
        }

        void LoadBuffer()
        {
            try
            {
                if (!File.Exists(bufferPath)) return;
                foreach (var line in File.ReadAllLines(bufferPath))
                {
                    int tab = line.IndexOf('\t');
                    if (tab <= 0) continue;
                    queue.Add((line.Substring(0, tab), line.Substring(tab + 1)));
                }
                Debug.Log($"[SupabaseDbService] 디스크 버퍼 {queue.Count}건 복구");
            }
            catch (Exception e) { Debug.LogWarning($"[SupabaseDbService] 버퍼 로드 실패: {e.Message}"); }
        }

        // ── 헬퍼 ──────────────────────────────────────────────────────
        static string NowIso() => DateTime.UtcNow.ToString("o");
        static string Num(float v) => ((double)v).ToString("R", Inv);
        static int ParseLeadingInt(string s)
        {
            if (string.IsNullOrEmpty(s)) return 0;
            int i = 0; while (i < s.Length && char.IsDigit(s[i])) i++;
            return i > 0 && int.TryParse(s.Substring(0, i), out int n) ? n : 0;
        }
        static string Esc(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            var sb = new StringBuilder(s.Length + 8);
            foreach (char c in s)
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default: sb.Append(c); break;
                }
            return sb.ToString();
        }
    }
}
