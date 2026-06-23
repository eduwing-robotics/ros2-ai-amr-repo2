// AddWaypointAction.cs — "순회지점 추가": 클릭 좌표를 새 웨이포인트로(스캐폴딩, 영속화는 추후).
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class AddWaypointAction : IMapAction
    {
        public string Id => "add_waypoint";
        public string DisplayName => "➕ 순회지점 추가";
        public bool AppliesTo(MapClickContext ctx) => true;

        public void Execute(MapClickContext ctx)
        {
            // TODO: WaypointService.Add(x,y) + SSOT/Supabase 영속화 (후속 Phase).
            ControlRoomEvents.RaiseLogAdded("map", "INFO",
                $"순회지점 추가 예정: ({ctx.worldX:0.00}, {ctx.worldY:0.00})");
        }
    }
}
