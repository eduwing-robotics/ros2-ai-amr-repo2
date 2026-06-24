// RemoveWaypointAction.cs — "마지막 순회지점 제거"(우클릭 메뉴). 레퍼런스 우클릭=undo 대응.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class RemoveWaypointAction : IMapAction
    {
        public string Id => "remove_waypoint";
        public string DisplayName => "➖ 마지막 지점 제거";
        public bool AppliesTo(MapClickContext ctx) => PatrolService.Instance.Count > 0;

        public void Execute(MapClickContext ctx)
        {
            PatrolService.Instance.RemoveLast();
            ControlRoomEvents.RaiseLogAdded("map", "INFO",
                $"마지막 순회지점 제거 (남음 {PatrolService.Instance.Count})");
        }
    }
}
