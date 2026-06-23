// DispatchHereAction.cs — "이 위치로 출동": 선택 로봇을 클릭 좌표로 보내는 수동 출동.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class DispatchHereAction : IMapAction
    {
        public string Id => "dispatch_here";
        public string DisplayName => "📍 이 위치로 출동";
        public bool AppliesTo(MapClickContext ctx) => !string.IsNullOrEmpty(ctx.selectedRobotId);

        public void Execute(MapClickContext ctx)
        {
            ControlRoomEvents.RaiseLogAdded("dispatch", "INFO",
                $"출동 명령: {ctx.selectedRobotId} → ({ctx.worldX:0.00}, {ctx.worldY:0.00})");
            ControlRoomEvents.RaiseDispatchRequested(ctx.selectedRobotId, ctx.worldX, ctx.worldY, "manual");
        }
    }
}
