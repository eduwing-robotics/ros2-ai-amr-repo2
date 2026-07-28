// WaypointListView.cs — 좌측 패널의 순회 지점 목록을 PatrolService SSOT 기반으로 동적 생성.
// 2026-06-30: wp-1~wp-5 하드코딩 버튼 제거 → PatrolService.Points 변화 시 자동 재구성.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.UI
{
    public class WaypointListView
    {
        readonly VisualElement list;
        Button selected;

        public WaypointListView(VisualElement root)
        {
            list = root.Q<VisualElement>("waypoint-list");

            Rebuild();
            ControlRoomEvents.OnPatrolChanged += Rebuild;
        }

        void Rebuild()
        {
            list?.Clear();
            selected = null;

            var points = PatrolService.Instance.Points;
            if (points.Count == 0)
            {
                list?.Add(new Label("등록된 순회 지점이 없습니다.") { name = "waypoint-empty" });
                return;
            }

            for (int i = 0; i < points.Count; i++)
            {
                var pt = points[i];
                var btn = new Button();
                btn.text = $"#{pt.seq} ({pt.x:0.0}, {pt.y:0.0})";
                btn.name = $"wp-{pt.seq}";
                btn.AddToClassList("btn-waypoint");
                var captured = btn;
                btn.clicked += () => OnSelect(captured);
                list?.Add(btn);
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
