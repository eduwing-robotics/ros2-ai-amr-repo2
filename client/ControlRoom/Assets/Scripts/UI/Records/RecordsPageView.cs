// opencode: 2026-06-30 - 기록 탭 coordinator. Coded with OpenCode; high-cost model review recommended.
// RecordsPageView.cs — 기록 탭(page-records) coordinator.
// 3서브탭(로그/이벤트·출동/KPI)을 IRecordsSubtab 구현체로 분리하고, 이벤트 발생 시 현재 서브탭만 Refresh.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.UI.Records
{
    public class RecordsPageView
    {
        readonly MonoBehaviour host;
        readonly IRecordsSubtab[] subtabs;
        readonly PanelTabView subtab;
        int currentSubtabIndex;
        bool refreshQueued;

        public RecordsPageView(MonoBehaviour host, VisualElement root)
        {
            this.host = host;
            var client = SupabaseDbService.Instance?.Client;
            var logRepo = new LogRepository(client);
            var eventRepo = new EventRepository(client);
            var dispatchRepo = new DispatchRepository(client);

            var page = root.Q<VisualElement>("records-page");
            if (page == null)
            {
                Debug.LogWarning("[RecordsPageView] records-page element not found — RecordsPage.uxml Instance 확인");
                return;
            }

            var chipRow = page.Q<VisualElement>("records-chip-row");
            var logsList = page.Q<VisualElement>("records-logs-list");
            var eventsList = page.Q<VisualElement>("records-events-list");
            var kpiEventCount = page.Q<Label>("kpi-events-count");
            var kpiDispatchCount = page.Q<Label>("kpi-dispatch-count");
            var kpiAvgResponse = page.Q<Label>("kpi-avg-response");
            var kpiAuditCount = page.Q<Label>("kpi-audit-count");

            subtabs = new IRecordsSubtab[3];
            subtabs[0] = new RecordsLogSubtab(host, logRepo, chipRow, logsList);
            subtabs[1] = new RecordsTimelineSubtab(host, eventRepo, dispatchRepo, chipRow, eventsList);
            subtabs[2] = new RecordsKpiSubtab(host, eventRepo, dispatchRepo, logRepo,
                chipRow, kpiEventCount, kpiDispatchCount, kpiAvgResponse, kpiAuditCount);

            subtab = new PanelTabView(page,
                new[] { "btn-records-logs", "btn-records-events", "btn-records-kpi" },
                new[] { "records-logs-page", "records-events-page", "records-kpi-page" },
                activeIndex: 0,
                onSelected: OnSubtabChanged);

            ControlRoomEvents.OnAlert += OnAlert;
            ControlRoomEvents.OnDispatchRequested += OnDispatchRequested;
            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;
            // 초기 칩/로드는 PanelTabView 생성자의 Select(0) → OnSubtabChanged(0)이 수행.
        }

        void OnSubtabChanged(int idx)
        {
            currentSubtabIndex = idx;
            subtabs[idx]?.Build();
            subtabs[idx]?.Load();
        }

        void OnAlert(int severity, string message) => Refresh();
        void OnDispatchRequested(string robotId, float x, float y, string reason, bool simulated) => Refresh();
        void OnScenarioTriggered(string scenarioId) => Refresh();

        void Refresh()
        {
            if (host == null || refreshQueued) return;
            refreshQueued = true;
            host.StartCoroutine(RefreshNextFrame());
        }

        System.Collections.IEnumerator RefreshNextFrame()
        {
            yield return null;
            refreshQueued = false;
            subtabs[currentSubtabIndex]?.Refresh();
        }
    }
}
