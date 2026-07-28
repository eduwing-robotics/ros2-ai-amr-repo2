// RobotTabView.cs — 상단바 좌측의 로봇 탭(티원/젠지) 전환.
// 클릭 → ControlRoomState.SelectRobot → OnRobotChanged 이벤트 → active 토글.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class RobotTabView
    {
        readonly Button tabRobot1;
        readonly Button tabRobot2;

        public RobotTabView(VisualElement root)
        {
            tabRobot1 = root.Q<Button>("tab-tb3_1");
            tabRobot2 = root.Q<Button>("tab-tb3_2");

            if (tabRobot1 != null) tabRobot1.clicked += () => Select("tb3_1");
            if (tabRobot2 != null) tabRobot2.clicked += () => Select("tb3_2");

            ControlRoomEvents.OnRobotChanged += SyncActiveTab;
            SyncActiveTab(ControlRoomState.Instance.SelectedRobotId);
        }

        void Select(string robotId)
        {
            ControlRoomState.Instance.SelectRobot(robotId);
        }

        void SyncActiveTab(string robotId)
        {
            tabRobot1?.RemoveFromClassList("active");
            tabRobot2?.RemoveFromClassList("active");
            if (robotId == "tb3_1") tabRobot1?.AddToClassList("active");
            if (robotId == "tb3_2") tabRobot2?.AddToClassList("active");
        }
    }
}
