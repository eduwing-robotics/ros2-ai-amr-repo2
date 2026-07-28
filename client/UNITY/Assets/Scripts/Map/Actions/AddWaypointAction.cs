// AddWaypointAction.cs — "순회지점 추가": 클릭 좌표를 순찰 경로에 추가(PatrolService). 영속화는 Phase 5.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class AddWaypointAction : IMapAction
    {
        public string Id => "add_waypoint";
        public string DisplayName => "➕ 순회지점 추가";
        public bool AppliesTo(MapClickContext ctx) => true;

        public void Execute(MapClickContext ctx)
        {
            PatrolService.Instance.Add(ctx.worldX, ctx.worldY);
            ControlRoomEvents.RaiseLogAdded("map", "INFO",
                $"순회지점 #{PatrolService.Instance.Count} 추가: ({ctx.worldX:0.00}, {ctx.worldY:0.00})");
        }
    }
}
