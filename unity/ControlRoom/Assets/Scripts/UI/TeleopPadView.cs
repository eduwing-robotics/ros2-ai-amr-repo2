// TeleopPadView.cs — 좌측 패널 수동 조종 D-pad.
// 버튼 누름/뗌에 따라 linear/angular Twist 명령을 ControlRoomEvents로 발행.
// 수동 모드일 때만 enable; 자동 모드에서는 비활성 표시.
// 버튼을 누른 채 패드 밖으로 나가도 정지 보장.
// Coded with OpenCode; high-cost model review recommended.
using System.Collections.Generic;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class TeleopPadView
    {
        readonly VisualElement card;
        readonly Dictionary<Button, bool> holding = new();

        const float LinearSpeed = 0.2f;
        const float AngularSpeed = 0.5f;

        public TeleopPadView(VisualElement root)
        {
            card = root.Q<VisualElement>("teleop-card");

            Bind(root.Q<Button>("btn-teleop-forward"), LinearSpeed, 0f, "전진");
            Bind(root.Q<Button>("btn-teleop-back"), -LinearSpeed, 0f, "후진");
            Bind(root.Q<Button>("btn-teleop-left"), 0f, AngularSpeed, "좌회전");
            Bind(root.Q<Button>("btn-teleop-right"), 0f, -AngularSpeed, "우회전");
            BindStop(root.Q<Button>("btn-teleop-stop"));

            ControlRoomEvents.OnModeChanged += OnModeChanged;
            OnModeChanged(ControlRoomState.Instance.Mode);
        }

        void Bind(Button btn, float linear, float angular, string label)
        {
            if (btn == null) return;
            holding[btn] = false;

            btn.RegisterCallback<PointerDownEvent>(_ =>
            {
                if (holding[btn]) return;
                holding[btn] = true;
                var robotId = ControlRoomState.Instance.SelectedRobotId;
                ControlRoomEvents.RaiseTeleopCmd(robotId, linear, angular, true);
                ControlRoomEvents.RaiseLogAdded("teleop", "INFO", $"수동 조종 {label}");
            });

            btn.RegisterCallback<PointerUpEvent>(_ =>
            {
                if (!holding[btn]) return;
                holding[btn] = false;
                Stop("버튼 해제");
            });

            btn.RegisterCallback<PointerLeaveEvent>(_ =>
            {
                if (!holding[btn]) return;
                holding[btn] = false;
                Stop("패드 이탈");
            });
        }

        void BindStop(Button btn)
        {
            if (btn == null) return;
            btn.clicked += () => Stop("정지 버튼");
        }

        void Stop(string reason)
        {
            var robotId = ControlRoomState.Instance.SelectedRobotId;
            ControlRoomEvents.RaiseTeleopCmd(robotId, 0f, 0f, false);
            ControlRoomEvents.RaiseLogAdded("teleop", "INFO", $"수동 조종 정지 ({reason})");
        }

        void OnModeChanged(string mode)
        {
            bool manual = mode == "manual";
            if (card != null)
            {
                card.EnableInClassList("disabled", !manual);
                foreach (var btn in card.Query<Button>().ToList())
                    btn.SetEnabled(manual);
            }

            if (!manual)
            {
                foreach (var btn in holding.Keys)
                    holding[btn] = false;
            }
        }
    }
}
