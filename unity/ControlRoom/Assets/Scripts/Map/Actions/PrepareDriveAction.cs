// PrepareDriveAction.cs — "주행준비": 선택 로봇의 충전독 주행준비 6단계를 원버튼 트리거.
// Bool 발행(PrepareDrivePublisher) → 로봇측 readyd.py가 ~/t1_drive_ready.sh(bringup→AMCL→nav2 lifecycle
// →검증)를 1회 실행. 순찰 시작과 달리 웨이포인트가 없어도 적용(주행 준비는 경로와 독립).
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class PrepareDriveAction : IMapAction
    {
        public string Id => "prepare_drive";
        public string DisplayName => "🔧 주행준비";
        public bool AppliesTo(MapClickContext ctx)
            => !string.IsNullOrEmpty(ctx.selectedRobotId)
               && ActiveRobotService.Has(ActiveRobotService.CapPatrol);

        public void Execute(MapClickContext ctx)
            => ControlRoomEvents.RaisePrepareDriveRequested(ctx.selectedRobotId);
    }
}
