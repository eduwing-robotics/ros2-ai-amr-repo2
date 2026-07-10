// RecordsRenderHelpers.cs — 기록 탭 카드 렌더링 + 시간 포맷 공통 헬퍼.
using System;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.UI.Records
{
    public static class RecordsRenderHelpers
    {
        public static VisualElement MakeLogCard(LogRow r)
        {
            string stripeClass = r.level switch
            {
                "ERROR" => "level-error",
                "WARN" => "level-warn",
                _ => "level-info"
            };
            var card = new VisualElement();
            card.AddToClassList("records-card");

            var stripe = new VisualElement();
            stripe.AddToClassList("records-card-stripe");
            stripe.AddToClassList(stripeClass);
            card.Add(stripe);

            var content = new VisualElement();
            content.AddToClassList("records-card-content");

            var title = new Label($"[{r.level}] {r.category} {(string.IsNullOrEmpty(r.source) ? "" : $"· {r.source}")}");
            title.AddToClassList("records-card-title");
            content.Add(title);

            var msg = new Label(r.message ?? "-");
            msg.AddToClassList("records-card-subtitle");
            content.Add(msg);

            var ts = new Label(ShortTs(r.ts));
            ts.AddToClassList("records-card-ts");
            content.Add(ts);

            card.Add(content);
            return card;
        }

        public static VisualElement MakeTimelineCard(TimelineItem item)
        {
            var card = new VisualElement();
            card.AddToClassList("records-card");

            var stripe = new VisualElement();
            stripe.AddToClassList("records-card-stripe");
            stripe.AddToClassList(item.stripeClass);
            card.Add(stripe);

            var content = new VisualElement();
            content.AddToClassList("records-card-content");

            var title = new Label(item.title);
            title.AddToClassList("records-card-title");
            content.Add(title);

            var sub = new Label(item.subtitle);
            sub.AddToClassList("records-card-subtitle");
            content.Add(sub);

            var ts = new Label(ShortTs(item.ts));
            ts.AddToClassList("records-card-ts");
            content.Add(ts);

            card.Add(content);
            return card;
        }

        public static Label MakeEmpty(string message)
        {
            var lbl = new Label(message);
            lbl.AddToClassList("home-activity-empty");
            return lbl;
        }

        public static string ShortTs(string ts)
        {
            if (string.IsNullOrEmpty(ts)) return "-";
            if (ts.Length > 16) return ts.Substring(0, 16).Replace('T', ' ');
            return ts;
        }

        public static int CompareTs(string a, string b)
        {
            if (DateTime.TryParse(a, out var da) && DateTime.TryParse(b, out var db))
                return da.CompareTo(db);
            return string.Compare(a, b);
        }

        public static string SeverityName(int severity)
        {
            return severity switch
            {
                0 => "SAFE",
                1 => "WATCH",
                2 => "CHECK",
                3 => "DANGER",
                _ => "SAFE"
            };
        }
    }

    public class TimelineItem
    {
        public string type;
        public string title;
        public string subtitle;
        public string ts;
        public string stripeClass;
    }
}
