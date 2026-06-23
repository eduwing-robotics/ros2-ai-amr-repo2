// SensorCardListView.cs — 우측 패널 센서 카드 4종(인체감지/소음/온도/레이저). as-built 2026-06-18.
// OnSensorChanged 이벤트로 갱신. PIR/소음/레이저는 전이 발행(latching X), 온도는 1Hz 연속.
// PIR(pir): 0/1 → 감지!/감지 안 됨 + USS sensor-ok/danger. 소음(sound): swing 값 + 임계 60 색 토글.
// 온도(temp): raw 값 텍스트(°C 보정 후속). 레이저(laser): 수신부 미결선 → "미결선" disabled 고정.
// Phase 3에서 default_sensors.json + SensorRegistry 기반 자동 생성으로 swap.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class SensorCardListView
    {
        readonly Label pirValue;
        readonly Label soundValue;
        readonly Label tempValue;
        readonly Label laserValue;

        const int SoundThreshold = 60;

        public SensorCardListView(VisualElement root)
        {
            pirValue   = root.Q<Label>("sensor-pir-value");
            soundValue = root.Q<Label>("sensor-sound-value");
            tempValue  = root.Q<Label>("sensor-temp-value");
            laserValue = root.Q<Label>("sensor-laser-value");

            // 레이저는 수신부 미결선 → 항상 비활성 표시.
            SetSensorState(laserValue, "미결선", "sensor-disabled");

            ControlRoomEvents.OnSensorChanged    += OnSensorChanged;
            ControlRoomEvents.OnRobotChanged     += OnRobotChanged;
            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;
        }

        bool IsCurrent(string robotId) =>
            robotId == ControlRoomState.Instance.SelectedRobotId;

        void OnSensorChanged(string robotId, string sensorId, float value)
        {
            if (!IsCurrent(robotId)) return;
            switch (sensorId)
            {
                case "pir":
                    bool detected = value >= 0.5f;
                    SetSensorState(pirValue,
                        detected ? "감지!" : "감지 안 됨",
                        detected ? "sensor-danger" : "sensor-ok");
                    break;
                case "sound":
                    bool noisy = value >= SoundThreshold;
                    SetSensorState(soundValue,
                        noisy ? $"소음 감지! (swing={value:F0})" : $"조용함 (swing={value:F0})",
                        noisy ? "sensor-danger" : "sensor-ok");
                    break;
                case "temp":
                    if (tempValue != null) tempValue.text = $"raw {value:F0}";
                    break;
                case "laser":
                    // 수신부 미결선 — 값과 무관하게 비활성 고정.
                    SetSensorState(laserValue, "미결선", "sensor-disabled");
                    break;
            }
        }

        void OnRobotChanged(string robotId)
        {
            // 탭 전환 시 State 캐시에서 즉시 redraw — Subscriber는 두 로봇 모두 항상 sub중.
            // 메시지 도착 대기 없이 마지막 알려진 값 그대로 표시.
            var s = ControlRoomState.Instance;
            if (s != null && s.LastSensorValues != null
                && s.LastSensorValues.TryGetValue(robotId, out var dict))
            {
                if (dict.TryGetValue("pir",   out var p)) OnSensorChanged(robotId, "pir",   p);
                else SetSensorState(pirValue, "감지 안 됨", "sensor-ok");

                if (dict.TryGetValue("sound", out var n)) OnSensorChanged(robotId, "sound", n);
                else SetSensorState(soundValue, "--", "sensor-ok");

                if (dict.TryGetValue("temp",  out var t) && tempValue != null) tempValue.text = $"raw {t:F0}";
                else if (tempValue != null) tempValue.text = "--";
            }
            else
            {
                // State 비었음 → 전체 reset
                SetSensorState(pirValue,  "감지 안 됨", "sensor-ok");
                SetSensorState(soundValue, "--", "sensor-ok");
                if (tempValue != null) tempValue.text = "--";
            }

            // 레이저는 로봇과 무관하게 항상 미결선 비활성.
            SetSensorState(laserValue, "미결선", "sensor-disabled");
        }

        void OnScenarioTriggered(string scenarioId)
        {
            switch (scenarioId)
            {
                case "intruder": SetSensorState(pirValue, "감지!", "sensor-danger"); break;
            }
        }

        void SetSensorState(Label label, string text, string statusClass)
        {
            if (label == null) return;
            label.text = text;
            label.RemoveFromClassList("sensor-ok");
            label.RemoveFromClassList("sensor-warn");
            label.RemoveFromClassList("sensor-danger");
            label.RemoveFromClassList("sensor-disabled");
            label.AddToClassList(statusClass);
        }
    }
}
