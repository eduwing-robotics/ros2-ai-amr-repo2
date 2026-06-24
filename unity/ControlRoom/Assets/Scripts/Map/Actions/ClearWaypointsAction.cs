// ClearWaypointsAction.cs — "순회지점 전체삭제"(우클릭 메뉴). 레퍼런스 deleteAll 버튼 대응.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class ClearWaypointsAction : IMapAction
    {
        public string Id => "clear_waypoints";
        public string DisplayName => "🗑 순회지점 전체삭제";
        public bool AppliesTo(MapClickContext ctx) => PatrolService.Instance.Count > 0;

        public void Execute(MapClickContext ctx)
        {
            int n = PatrolService.Instance.Count;
            PatrolService.Instance.Clear();
            ControlRoomEvents.RaiseLogAdded("map", "INFO", $"순회지점 전체삭제 ({n}개)");
        }
    }
}
