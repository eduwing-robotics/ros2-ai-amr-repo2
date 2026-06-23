// HardwarePanelView.cs — 우측 패널 하드웨어 카드. 선택된 로봇의 표시명/모델/호스트.
// OnRobotChanged 이벤트 구독 → 탭 전환 시 정보 갱신.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class HardwarePanelView
    {
        readonly Label hardwareInfoLabel;

        public HardwarePanelView(VisualElement root)
        {
            hardwareInfoLabel = root.Q<Label>("hardware-info-label");

            ControlRoomEvents.OnRobotChanged += OnRobotChanged;
            OnRobotChanged(ControlRoomState.Instance.SelectedRobotId);
        }

        void OnRobotChanged(string robotId)
        {
            if (hardwareInfoLabel == null) return;
            var info = ControlRoomState.Instance.GetSelectedRobot();
            hardwareInfoLabel.text = info != null
                ? $"{info.displayName} / {info.model}\n{info.hostAddress}"
                : "(로봇 정보 로드 안 됨)";
        }
    }
}
