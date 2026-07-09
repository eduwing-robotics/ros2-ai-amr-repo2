// StopPatrolAction.cs — "순찰 정지": 무한 순찰을 멈추고 독 복귀주차 요청.
// Bool 발행(FollowWaypointsPublisher) → 로봇측 bridge가 현재 랩 마무리 후 복귀주차하고 종료.
// "▶ 순찰 시작"이 무한 연속 순찰이므로 이 정지 버튼과 짝을 이룬다.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class StopPatrolAction : IMapAction
    {
        public string Id => "stop_patrol";
        public string DisplayName => "■ 순찰 정지";
        public bool AppliesTo(MapClickContext ctx)
            => !string.IsNullOrEmpty(ctx.selectedRobotId)
               && ActiveRobotService.Has(ActiveRobotService.CapPatrol);

        public void Execute(MapClickContext ctx)
            => ControlRoomEvents.RaisePatrolStopRequested(ctx.selectedRobotId);
    }
}
