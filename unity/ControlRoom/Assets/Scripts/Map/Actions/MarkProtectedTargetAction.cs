// MarkProtectedTargetAction.cs — "보호대상 지정": 클릭 좌표를 보호대상으로(스캐폴딩, 영속화는 추후).
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class MarkProtectedTargetAction : IMapAction
    {
        public string Id => "mark_target";
        public string DisplayName => "🛡 보호대상 지정";
        public bool AppliesTo(MapClickContext ctx) => true;

        public void Execute(MapClickContext ctx)
        {
            // TODO: ProtectedTargetService.Add(x,y,name) + SSOT/Supabase 영속화 (후속 Phase).
            ControlRoomEvents.RaiseLogAdded("map", "INFO",
                $"보호대상 지정 예정: ({ctx.worldX:0.00}, {ctx.worldY:0.00})");
        }
    }
}
