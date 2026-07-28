// opencode: 2026-06-29 - 대응 탭 View. Coded with OpenCode; high-cost model review recommended.
// ResponsePageView.cs — 대응 탭(위험등급 보드 + 출동현황 + 이벤트/출동 히스토리).
// EventRepository/DispatchRepository를 통해 Supabase에서 읽고, ControlRoomEvents로 실시간 반영.
// DB 비활성 시에도 graceful(empty) 동작.
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.UI
{
    public class ResponsePageView
    {
        const int EventLimit = 50;
        const int EvacuateDangerThreshold = 2; // 최근 이벤트 중 DANGER 누적이 이 값 이상이면 EVACUATE로 격상

        readonly MonoBehaviour host;
        readonly EventRepository eventRepo;
        readonly DispatchRepository dispatchRepo;

        readonly VisualElement page;
        readonly Label activeCountLabel;
        readonly Label totalCountLabel;
        readonly VisualElement activeList;
        readonly VisualElement eventList;
        readonly Button refreshBtn;
        readonly Dictionary<string, VisualElement> severityCards;

        int totalDispatchCount;
        bool refreshQueued;

        public ResponsePageView(MonoBehaviour host, VisualElement root)
        {
            this.host = host;
            var client = SupabaseDbService.Instance?.Client;
            eventRepo = new EventRepository(client);
            dispatchRepo = new DispatchRepository(client);

            page = root.Q<VisualElement>("response-page");
            if (page == null)
            {
                Debug.LogWarning("[ResponsePageView] response-page element not found — ResponsePage.uxml Instance 확인");
                return;
            }

            activeCountLabel = page.Q<Label>("dispatch-active-count");
            totalCountLabel = page.Q<Label>("dispatch-total-count");
            activeList = page.Q<VisualElement>("dispatch-active-items");
            eventList = page.Q<VisualElement>("event-history-items");
            refreshBtn = page.Q<Button>("btn-refresh-response");
            if (refreshBtn != null) refreshBtn.clicked += Refresh;

            severityCards = new Dictionary<string, VisualElement>
            {
                ["SAFE"] = page.Q<VisualElement>("severity-safe"),
                ["WATCH"] = page.Q<VisualElement>("severity-watch"),
                ["CHECK"] = page.Q<VisualElement>("severity-check"),
                ["DANGER"] = page.Q<VisualElement>("severity-danger"),
                ["EVACUATE"] = page.Q<VisualElement>("severity-evacuate")
            };

            ControlRoomEvents.OnAlert += OnAlert;
            ControlRoomEvents.OnDispatchRequested += OnDispatchRequested;
            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;

            Refresh();
        }

        void OnAlert(int severity, string message)
        {
            Refresh();
        }

        void OnDispatchRequested(string robotId, float x, float y, string reason, bool simulated)
        {
            Refresh();
        }

        void OnScenarioTriggered(string scenarioId)
        {
            Refresh();
        }

        // 같은 프레임에 OnAlert/OnDispatch/OnScenario가 몰려도 쿼리 묶음은 1회만 — 다음 프레임에 합쳐 실행.
        void Refresh()
        {
            if (host == null || refreshQueued) return;
            refreshQueued = true;
            host.StartCoroutine(RefreshNextFrame());
        }

        IEnumerator RefreshNextFrame()
        {
            yield return null;
            refreshQueued = false;
            host.StartCoroutine(LoadEvents());
            host.StartCoroutine(LoadActiveDispatches());
            host.StartCoroutine(LoadTotalDispatches());
        }

        IEnumerator LoadEvents()
        {
            yield return eventRepo.QueryRecent(EventLimit, (ok, rows) =>
            {
                RenderEvents(rows);
                UpdateSeverity(rows);
            });
        }

        IEnumerator LoadActiveDispatches()
        {
            yield return dispatchRepo.QueryActive((ok, rows) =>
            {
                RenderActiveDispatches(rows);
                if (activeCountLabel != null) activeCountLabel.text = rows.Count.ToString();
            });
        }

        IEnumerator LoadTotalDispatches()
        {
            yield return dispatchRepo.CountAll((ok, count) =>
            {
                if (ok) totalDispatchCount = count;
                if (totalCountLabel != null) totalCountLabel.text = totalDispatchCount.ToString();
            });
        }

        void RenderEvents(List<EventRow> rows)
        {
            if (eventList == null) return;
            eventList.Clear();
            foreach (var e in rows)
            {
                var entry = new Label($"[{SeverityName(e.severity)}] {e.robot_id ?? "-"} {e.event_type} @ {ShortTs(e.ts)}");
                entry.AddToClassList("response-list-item");
                entry.AddToClassList($"severity-{SeverityName(e.severity).ToLower()}");
                eventList.Add(entry);
            }
        }

        void RenderActiveDispatches(List<DispatchRow> rows)
        {
            if (activeList == null) return;
            activeList.Clear();
            foreach (var d in rows)
            {
                string reason = string.IsNullOrEmpty(d.reason) ? "출동" : d.reason;
                var entry = new Label($"{d.target_robot_id ?? "-"} → ({d.target_x:F2},{d.target_y:F2}) {reason} @ {ShortTs(d.dispatched_at)}");
                entry.AddToClassList("response-list-item");
                activeList.Add(entry);
            }
        }

        void UpdateSeverity(List<EventRow> rows)
        {
            foreach (var c in severityCards.Values)
                c?.RemoveFromClassList("active");

            // events.severity는 0~3(SAFE~DANGER)뿐 — EVACUATE(4)는 단일 이벤트로는 도달 불가.
            // ponytail: DANGER 이벤트가 임계치 이상 누적되면 EVACUATE로 격상한다.
            //   한계 = 단순 카운트(시간윈도우 무시). 업그레이드 경로 = event_type 가중치 또는 최근 N초 윈도우.
            string level = "SAFE";
            int dangerCount = 0;
            foreach (var e in rows)
            {
                string candidate = SeverityName(e.severity);
                if (candidate == "DANGER") dangerCount++;
                if (Rank(candidate) > Rank(level)) level = candidate;
            }
            if (dangerCount >= EvacuateDangerThreshold) level = "EVACUATE";

            if (severityCards.TryGetValue(level, out var card))
                card?.AddToClassList("active");
        }

        static string SeverityName(int severity)
        {
            switch (severity)
            {
                case 0: return "SAFE";
                case 1: return "WATCH";
                case 2: return "CHECK";
                case 3: return "DANGER";
                default: return "SAFE";
            }
        }

        static int Rank(string level)
        {
            switch (level)
            {
                case "SAFE": return 0;
                case "WATCH": return 1;
                case "CHECK": return 2;
                case "DANGER": return 3;
                case "EVACUATE": return 4;
                default: return 0;
            }
        }

        static string ShortTs(string ts)
        {
            if (string.IsNullOrEmpty(ts)) return "-";
            if (ts.Length > 16) return ts.Substring(0, 16).Replace('T', ' ');
            return ts;
        }
    }
}
