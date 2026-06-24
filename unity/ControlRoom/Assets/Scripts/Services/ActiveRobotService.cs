// ActiveRobotService.cs — 활성(선택) 로봇의 역할 능력(capability) 조회 SSOT.
// 선택 상태 자체는 ControlRoomState.SelectedRobotId가 보유(역할 교환 = 탭 전환). 여기선 capability만 판정.
// capabilities 미설정이면 하위호환으로 모두 허용. 젠지/티원 둘 다 "patrol" 보유 → 순찰 상호교환.
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Services
{
    public static class ActiveRobotService
    {
        public const string CapPatrol = "patrol";
        public const string CapSensor = "sensor";
        public const string CapVision = "vision";
        public const string CapSlam = "slam";

        public static RobotInfo Current => ControlRoomState.Instance.GetSelectedRobot();
        public static string CurrentId => ControlRoomState.Instance.SelectedRobotId;

        public static bool Has(string capability)
        {
            var caps = Current?.capabilities;
            if (caps == null || caps.Length == 0) return true;   // 미설정 → 하위호환 허용
            foreach (var c in caps) if (c == capability) return true;
            return false;
        }
    }
}
