// WaypointListView.cs — 좌측 패널의 순회 지점 5개 더미 버튼.
// 클릭 → selected 클래스 토글 + 로그 push. Phase 3에서 office_base_map.json 기반으로 swap.
using System.Collections.Generic;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class WaypointListView
    {
        readonly List<Button> buttons = new();
        Button selected;

        public WaypointListView(VisualElement root)
        {
            for (int i = 1; i <= 5; i++)
            {
                var btn = root.Q<Button>($"wp-{i}");
                if (btn == null) continue;
                var captured = btn;
                btn.clicked += () => OnSelect(captured);
                buttons.Add(btn);
            }
        }

        void OnSelect(Button btn)
        {
            selected?.RemoveFromClassList("selected");
            selected = btn;
            btn.AddToClassList("selected");
            ControlRoomEvents.RaiseLogAdded("waypoint", "INFO", $"웨이포인트 선택: {btn.text}");
        }
    }
}
