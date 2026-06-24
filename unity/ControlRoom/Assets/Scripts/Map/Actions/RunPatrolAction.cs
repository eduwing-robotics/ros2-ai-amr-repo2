// RunPatrolAction.cs — "순찰 시작": 현재 경로를 선택 로봇으로 실행 요청.
// PoseArray 발행(FollowWaypointsPublisher) → 로봇측 브리지가 Nav2 FollowWaypoints로 수행.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class RunPatrolAction : IMapAction
    {
        public string Id => "run_patrol";
        public string DisplayName => "▶ 순찰 시작";
        public bool AppliesTo(MapClickContext ctx)
            => PatrolService.Instance.Count > 0
               && !string.IsNullOrEmpty(ctx.selectedRobotId)
               && ActiveRobotService.Has(ActiveRobotService.CapPatrol);

        public void Execute(MapClickContext ctx)
            => ControlRoomEvents.RaisePatrolRunRequested(ctx.selectedRobotId);
    }
}
