// SituationDispatchAction.cs — SSOT(default_situations.json) 상황을 좌표 출동 액션으로 노출.
// 예: 화재 좌표 우클릭 → 경보 + 선택 로봇 출동. 상황 정의는 SSOT가 주도(코드 무수정 확장).
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class SituationDispatchAction : IMapAction
    {
        readonly SituationInfo s;
        public SituationDispatchAction(SituationInfo situation) { s = situation; }

        public string Id => "situation_" + s.situationId;
        public string DisplayName =>
            string.IsNullOrEmpty(s.icon) ? $"{s.displayName} 출동" : $"{s.icon} {s.displayName} 출동";
        public bool AppliesTo(MapClickContext ctx) => !string.IsNullOrEmpty(ctx.selectedRobotId);

        public void Execute(MapClickContext ctx)
        {
            ControlRoomEvents.RaiseAlert(s.severity,
                $"{s.displayName} 발생 — ({ctx.worldX:0.00}, {ctx.worldY:0.00}) 출동");
            ControlRoomEvents.RaiseLogAdded("dispatch", "WARN",
                $"{s.displayName} 출동: {ctx.selectedRobotId} → ({ctx.worldX:0.00}, {ctx.worldY:0.00})");
            ControlRoomEvents.RaiseDispatchRequested(ctx.selectedRobotId, ctx.worldX, ctx.worldY, s.situationId);
        }
    }
}
