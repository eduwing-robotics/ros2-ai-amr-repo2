// LogPanelView.cs — 이벤트 로그 리스트. ControlRoomEvents.OnLogAdded 구독.
// 최대 100줄 유지, 새 라인이 들어오면 자동 스크롤. WARN/ERROR는 색 클래스 부여.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class LogPanelView
    {
        const int MaxEntries = 100;

        readonly ScrollView scroll;
        readonly VisualElement list;

        public LogPanelView(VisualElement root)
        {
            scroll = root.Q<ScrollView>("log-panel");
            list   = root.Q<VisualElement>("log-list");
            ControlRoomEvents.OnLogAdded += AddLog;
        }

        void AddLog(string category, string level, string message)
        {
            if (list == null) return;

            var entry = new Label($"[{level}] [{category}] {message}");
            entry.AddToClassList("log-entry");
            if (level == "WARN")  entry.AddToClassList("log-entry-warn");
            if (level == "ERROR") entry.AddToClassList("log-entry-error");
            list.Add(entry);

            while (list.childCount > MaxEntries) list.RemoveAt(0);

            // 자동 스크롤 (다음 프레임에 적용)
            if (scroll != null)
            {
                scroll.schedule.Execute(() => scroll.scrollOffset = new UnityEngine.Vector2(0, float.MaxValue));
            }
        }
    }
}
