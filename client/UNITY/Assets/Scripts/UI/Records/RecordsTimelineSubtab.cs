// RecordsTimelineSubtab.cs — 기록 탭 > 이벤트/출동 서브탭.
// events + dispatches를 시간순으로 머지해 타임라인 카드로 렌더한다.
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.UI.Records
{
    public class RecordsTimelineSubtab : IRecordsSubtab
    {
        const int Limit = 50;

        readonly MonoBehaviour host;
        readonly EventRepository eventRepo;
        readonly DispatchRepository dispatchRepo;
        readonly VisualElement chipRow;
        readonly VisualElement eventsList;

        Button activeTimelineChip;
        string currentTimelineFilter = "all";

        public RecordsTimelineSubtab(MonoBehaviour host,
                                     EventRepository eventRepo,
                                     DispatchRepository dispatchRepo,
                                     VisualElement chipRow,
                                     VisualElement eventsList)
        {
            this.host = host;
            this.eventRepo = eventRepo;
            this.dispatchRepo = dispatchRepo;
            this.chipRow = chipRow;
            this.eventsList = eventsList;
        }

        public void Build()
        {
            if (chipRow == null) return;
            chipRow.Clear();
            activeTimelineChip = null;
            currentTimelineFilter = "all";

            AddTimelineChip("전체", "all", active: true);
            AddTimelineChip("이벤트", "event");
            AddTimelineChip("출동", "dispatch");
        }

        public void Load() => InternalLoad();
        public void Refresh() => InternalLoad();

        void InternalLoad()
        {
            if (host == null) return;
            host.StartCoroutine(LoadTimelineCo());
        }

        IEnumerator LoadTimelineCo()
        {
            var events = new List<EventRow>();
            var dispatches = new List<DispatchRow>();
            bool eventsOk = false, dispatchesOk = false;

            yield return eventRepo.QueryRecent(Limit, (ok, rows) =>
            {
                eventsOk = ok;
                events = rows ?? events;
            });
            yield return dispatchRepo.QueryRecent(Limit, (ok, rows) =>
            {
                dispatchesOk = ok;
                dispatches = rows ?? dispatches;
            });

            if (!eventsOk && !dispatchesOk)
            {
                RenderTimeline(new List<TimelineItem>());
                yield break;
            }

            var items = new List<TimelineItem>();
            foreach (var e in events)
                items.Add(MakeEventItem(e));
            foreach (var d in dispatches)
                items.Add(MakeDispatchItem(d));

            items.Sort((a, b) => RecordsRenderHelpers.CompareTs(b.ts, a.ts));

            if (currentTimelineFilter != "all")
                items = items.Where(i => i.type == currentTimelineFilter).ToList();

            RenderTimeline(items);
        }

        void AddTimelineChip(string label, string value, bool active = false)
        {
            var btn = RecordsChipBar.MakeChip(label, active);
            btn.clicked += () =>
            {
                if (activeTimelineChip == btn) return;
                RecordsChipBar.SetSingleChip(ref activeTimelineChip, btn, true);
                currentTimelineFilter = value;
                foreach (var other in chipRow.Query<Button>().ToList().Where(b => b != btn))
                    other.RemoveFromClassList("active");
                Refresh();
            };
            if (active)
            {
                activeTimelineChip = btn;
                currentTimelineFilter = value;
            }
            chipRow.Add(btn);
        }

        void RenderTimeline(List<TimelineItem> items)
        {
            if (eventsList == null) return;
            eventsList.Clear();
            if (items == null || items.Count == 0)
            {
                eventsList.Add(RecordsRenderHelpers.MakeEmpty("이벤트/출동 기록이 없습니다."));
                return;
            }
            foreach (var item in items)
                eventsList.Add(RecordsRenderHelpers.MakeTimelineCard(item));
        }

        static TimelineItem MakeEventItem(EventRow e)
        {
            string sev = RecordsRenderHelpers.SeverityName(e.severity);
            return new TimelineItem
            {
                type = "event",
                title = $"[{sev}] {e.robot_id ?? "-"} {e.event_type}",
                subtitle = $"위치 ({e.x:F2}, {e.y:F2})",
                ts = e.ts,
                stripeClass = $"severity-{sev.ToLower()}"
            };
        }

        static TimelineItem MakeDispatchItem(DispatchRow d)
        {
            string reason = string.IsNullOrEmpty(d.reason) ? "출동" : d.reason;
            return new TimelineItem
            {
                type = "dispatch",
                title = $"{d.target_robot_id ?? "-"} → {reason}",
                subtitle = $"목표 ({d.target_x:F2}, {d.target_y:F2})",
                ts = d.dispatched_at,
                stripeClass = "dispatch"
            };
        }
    }
}
