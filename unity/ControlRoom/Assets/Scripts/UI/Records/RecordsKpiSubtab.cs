// RecordsKpiSubtab.cs — 기록 탭 > KPI 서브탭.
// 이벤트 수 · 출동 수 · 평균 응답시간 · 감사로그 수를 비동기로 로드한다.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.UI.Records
{
    public class RecordsKpiSubtab : IRecordsSubtab
    {
        readonly MonoBehaviour host;
        readonly EventRepository eventRepo;
        readonly DispatchRepository dispatchRepo;
        readonly LogRepository logRepo;
        readonly VisualElement chipRow;
        readonly Label kpiEventCount;
        readonly Label kpiDispatchCount;
        readonly Label kpiAvgResponse;
        readonly Label kpiAuditCount;

        public RecordsKpiSubtab(MonoBehaviour host,
                                EventRepository eventRepo,
                                DispatchRepository dispatchRepo,
                                LogRepository logRepo,
                                VisualElement chipRow,
                                Label kpiEventCount,
                                Label kpiDispatchCount,
                                Label kpiAvgResponse,
                                Label kpiAuditCount)
        {
            this.host = host;
            this.eventRepo = eventRepo;
            this.dispatchRepo = dispatchRepo;
            this.logRepo = logRepo;
            this.chipRow = chipRow;
            this.kpiEventCount = kpiEventCount;
            this.kpiDispatchCount = kpiDispatchCount;
            this.kpiAvgResponse = kpiAvgResponse;
            this.kpiAuditCount = kpiAuditCount;
        }

        public void Build()
        {
            if (chipRow == null) return;
            chipRow.Clear();
            var refresh = new Button(() => Load()) { text = "새로고침" };
            refresh.AddToClassList("records-chip");
            chipRow.Add(refresh);
        }

        public void Load() => InternalLoad();
        public void Refresh() => InternalLoad();

        void InternalLoad()
        {
            if (host == null) return;
            host.StartCoroutine(eventRepo.CountAll((ok, count) =>
                SetText(kpiEventCount, ok ? count.ToString() : "-")));
            host.StartCoroutine(dispatchRepo.CountAll((ok, count) =>
                SetText(kpiDispatchCount, ok ? count.ToString() : "-")));
            host.StartCoroutine(dispatchRepo.AvgResponseTime((ok, avg) =>
                SetText(kpiAvgResponse, ok ? $"{avg:F1}s" : "-")));
            host.StartCoroutine(logRepo.Count((ok, count) =>
                SetText(kpiAuditCount, ok ? count.ToString() : "-"), category: "audit"));
        }

        static void SetText(Label label, string text)
        {
            if (label != null) label.text = text;
        }
    }
}
