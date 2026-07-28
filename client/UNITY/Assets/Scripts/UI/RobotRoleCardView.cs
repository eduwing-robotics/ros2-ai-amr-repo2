// RobotRoleCardView.cs — 좌측 패널 로봇 역할 카드.
// 선택 로봇의 displayName, 역할 뱃지, 연결 상태를 표시.
// 색상은 USS 클래스(.vision/.sensor/.unknown)로 제어, C#은 클래스 토글만 담당.
// Coded with OpenCode; high-cost model review recommended.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.UI
{
    public class RobotRoleCardView
    {
        readonly VisualElement icon;
        readonly Label nameLabel;
        readonly Label statusLabel;
        readonly Label badge;

        public RobotRoleCardView(VisualElement root)
        {
            icon = root.Q<VisualElement>("robot-role-icon");
            nameLabel = root.Q<Label>("robot-role-name");
            statusLabel = root.Q<Label>("robot-role-status");
            badge = root.Q<Label>("robot-role-badge");

            ControlRoomEvents.OnRobotChanged += OnRobotChanged;
            ControlRoomEvents.OnRobotConnectivity += OnConnectivity;
            OnRobotChanged(ControlRoomState.Instance.SelectedRobotId);
        }

        void OnRobotChanged(string robotId)
        {
            var robot = ControlRoomState.Instance.GetSelectedRobot();
            if (robot == null)
            {
                SetUnknown();
                return;
            }

            if (nameLabel != null) nameLabel.text = robot.displayName;
            // 실제 연결 상태: RobotPoseFeed 신호 수신 여부(RobotConnectivityMonitor)로 판정.
            if (statusLabel != null)
                statusLabel.text = RobotConnectivityMonitor.IsOnline(robot.robotId) ? "온라인" : "오프라인";
            if (badge != null)
            {
                badge.text = robot.role switch
                {
                    "vision" => "비전 로봇",
                    "sensor" => "센서/확인 로봇",
                    _ => robot.role
                };
            }

            SetRoleClass(robot.role);
        }

        // 선택 중인 로봇의 연결 상태가 바뀔 때만 라벨 갱신(다른 로봇 이벤트는 무시).
        void OnConnectivity(string robotId, bool isOnline)
        {
            if (robotId != ControlRoomState.Instance.SelectedRobotId) return;
            if (statusLabel != null) statusLabel.text = isOnline ? "온라인" : "오프라인";
        }

        void SetUnknown()
        {
            if (nameLabel != null) nameLabel.text = "--";
            if (statusLabel != null) statusLabel.text = "연결 대기";
            if (badge != null) badge.text = "미선택";
            SetRoleClass("unknown");
        }

        void SetRoleClass(string role)
        {
            icon?.RemoveFromClassList("vision");
            icon?.RemoveFromClassList("sensor");
            icon?.RemoveFromClassList("unknown");
            badge?.RemoveFromClassList("vision");
            badge?.RemoveFromClassList("sensor");
            badge?.RemoveFromClassList("unknown");

            string cls = role switch
            {
                "vision" => "vision",
                "sensor" => "sensor",
                _ => "unknown"
            };
            icon?.AddToClassList(cls);
            badge?.AddToClassList(cls);
        }
    }
}
