// QuickActionView.cs — 좌측 패널 퀵 액션 4종 버튼.
// 즉시정지 / 충전소복귀 / ArUco주차 / 주행잠금을 ControlRoomEvents로 발행.
// Coded with OpenCode; high-cost model review recommended.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Design;

namespace URHYNIX.ControlRoom.UI
{
    public class QuickActionView
    {
        public QuickActionView(VisualElement root)
        {
            Bind(root.Q<Button>("btn-quick-stop"), QuickActionIds.Stop, "즉시정지");
            Bind(root.Q<Button>("btn-quick-home"), QuickActionIds.ReturnHome, "충전소복귀");
            Bind(root.Q<Button>("btn-quick-park"), QuickActionIds.ArucoPark, "ArUco주차");
            Bind(root.Q<Button>("btn-quick-lock"), QuickActionIds.LockDrive, "주행잠금");
        }

        void Bind(Button btn, string actionId, string label)
        {
            if (btn == null) return;
            btn.clicked += () =>
            {
                var robotId = ControlRoomState.Instance.SelectedRobotId;
                ControlRoomEvents.RaiseQuickAction(robotId, actionId);
                ControlRoomEvents.RaiseLogAdded("quick", "INFO", $"퀵 액션: {label} ({robotId})");
            };
        }
    }
}
