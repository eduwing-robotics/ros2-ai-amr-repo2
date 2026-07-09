// ReseedAction.cs — "충전독 재시딩": 선택 로봇의 AMCL을 저장맵 충전독 고정좌표로 재시딩(위치만 재선언).
// Bool 발행(PrepareDrivePublisher) → 로봇측 readyd가 ~/_dock_reseed.sh 1회 실행. 주행준비 6단계와 달리
// bringup/nav2를 건드리지 않음(이미 기동된 상태 전제) — 손으로 옮겼다 독에 되돌린 뒤 위치만 맞출 때.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class ReseedAction : IMapAction
    {
        public string Id => "reseed_dock";
        public string DisplayName => "🎯 충전독 재시딩";
        public bool AppliesTo(MapClickContext ctx)
            => !string.IsNullOrEmpty(ctx.selectedRobotId)
               && ActiveRobotService.Has(ActiveRobotService.CapPatrol)
               && RobotConnectivityMonitor.IsOnline(ctx.selectedRobotId); // 죽은 로봇에 가짜 재시딩 방지(AMCL 기동 전제)

        public void Execute(MapClickContext ctx)
            => ControlRoomEvents.RaiseReseedRequested(ctx.selectedRobotId);
    }
}
