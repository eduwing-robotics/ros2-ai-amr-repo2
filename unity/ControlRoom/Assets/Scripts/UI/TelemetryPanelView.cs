// TelemetryPanelView.cs — 우측 패널 배터리 게이지. 탭 전환 즉시 해당 로봇의 last value로 재표시.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class TelemetryPanelView
    {
        readonly Label batteryPercentLabel;
        readonly VisualElement batteryBarFill;

        public TelemetryPanelView(VisualElement root)
        {
            batteryPercentLabel = root.Q<Label>("battery-percent-label");
            batteryBarFill      = root.Q<VisualElement>("battery-bar-fill");

            ControlRoomEvents.OnBatteryChanged += OnBatteryChanged;
            ControlRoomEvents.OnRobotChanged   += OnRobotChanged;
            OnRobotChanged(ControlRoomState.Instance.SelectedRobotId);
        }

        bool IsCurrent(string robotId) =>
            robotId == ControlRoomState.Instance.SelectedRobotId;

        void OnBatteryChanged(string robotId, float percent)
        {
            if (!IsCurrent(robotId)) return;
            Apply(percent);
        }

        void OnRobotChanged(string robotId)
        {
            if (ControlRoomState.Instance.LastSensorValues.TryGetValue(robotId, out var dict)
                && dict.TryGetValue("battery", out var v))
                Apply(v);
            else
                Reset();
        }

        void Apply(float percent)
        {
            if (batteryPercentLabel != null) batteryPercentLabel.text = $"{percent:F1} %";
            if (batteryBarFill != null)
                batteryBarFill.style.width = Length.Percent(UnityEngine.Mathf.Clamp(percent, 0f, 100f));
        }

        void Reset()
        {
            if (batteryPercentLabel != null) batteryPercentLabel.text = "-- %";
            if (batteryBarFill != null)
                batteryBarFill.style.width = Length.Percent(0f);
        }
    }
}
