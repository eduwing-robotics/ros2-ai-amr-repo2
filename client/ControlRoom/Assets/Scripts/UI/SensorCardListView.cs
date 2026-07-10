// SensorCardListView.cs — 우측 패널 센서 카드를 default_sensors.json + SensorRegistry 기반으로 동적 생성.
// 로봇 변경 시 카드 재구성; 센서값 이벤트로 실시간 갱신. disabled 센서는 "미결선" 고정.
// 2026-06-30: 4개 하드코딩 라벨 제거 → 동적 생성.
using System.Collections.Generic;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Sensors;

namespace URHYNIX.ControlRoom.UI
{
    public class SensorCardListView
    {
        readonly VisualElement list;
        readonly SensorRegistry registry = new SensorRegistry();
        readonly Dictionary<string, Label> valueLabels = new();
        readonly Dictionary<string, SensorInfo> sensorInfos = new();

        public SensorCardListView(VisualElement root)
        {
            list = root.Q<VisualElement>("sensor-card-list");
            registry.LoadFromResources();

            Rebuild();

            ControlRoomEvents.OnSensorChanged    += OnSensorChanged;
            ControlRoomEvents.OnRobotChanged     += OnRobotChanged;
            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;
        }

        void Rebuild()
        {
            list?.Clear();
            valueLabels.Clear();
            sensorInfos.Clear();

            var robotId = ControlRoomState.Instance.SelectedRobotId;
            var sensors = registry.GetSensorsForRobot(robotId);
            if (sensors.Count == 0)
            {
                list?.Add(new Label("이 로봇에 등록된 센서가 없습니다.") { name = "sensor-empty" });
                return;
            }

            foreach (var s in sensors)
            {
                var row = new VisualElement();
                row.AddToClassList("sensor-row");

                var nameLabel = new Label(s.displayName);
                nameLabel.AddToClassList("sensor-name");
                row.Add(nameLabel);

                var valueLabel = new Label("--");
                valueLabel.name = $"sensor-value-{s.sensorId}";
                valueLabel.AddToClassList("sensor-value");
                row.Add(valueLabel);

                list?.Add(row);
                valueLabels[s.sensorId] = valueLabel;
                sensorInfos[s.sensorId] = s;

                if (s.disabled)
                    SetSensorState(valueLabel, "미결선", "sensor-disabled");
                else
                    ApplyDefault(valueLabel, s);
            }

            // State 캐시가 있으면 즉시 반영.
            ApplyCachedValues();
        }

        void ApplyCachedValues()
        {
            var robotId = ControlRoomState.Instance.SelectedRobotId;
            if (ControlRoomState.Instance.LastSensorValues.TryGetValue(robotId, out var dict))
            {
                foreach (var kv in dict)
                    if (valueLabels.TryGetValue(kv.Key, out var label) && !sensorInfos[kv.Key].disabled)
                        UpdateValue(sensorInfos[kv.Key], kv.Value);
            }
        }

        void OnSensorChanged(string robotId, string sensorId, float value)
        {
            if (robotId != ControlRoomState.Instance.SelectedRobotId) return;
            if (!valueLabels.TryGetValue(sensorId, out var label)) return;
            if (!sensorInfos.TryGetValue(sensorId, out var info) || info.disabled) return;
            UpdateValue(info, value);
        }

        void UpdateValue(SensorInfo info, float value)
        {
            if (!valueLabels.TryGetValue(info.sensorId, out var label)) return;
            switch (info.sensorType)
            {
                case "boolean":
                    bool on = value >= info.warningThreshold;
                    SetSensorState(label,
                        on ? "감지!" : "감지 안 됨",
                        on ? "sensor-danger" : "sensor-ok");
                    break;
                case "analog":
                default:
                    bool warn = info.warningThreshold > 0f && value >= info.warningThreshold;
                    string suffix = string.IsNullOrEmpty(info.unit) ? "" : $" {info.unit}";
                    SetSensorState(label,
                        warn ? $"{info.displayName} 감지! ({value:F0}{suffix})" : $"{value:F0}{suffix}",
                        warn ? "sensor-danger" : "sensor-ok");
                    break;
            }
        }

        void ApplyDefault(Label label, SensorInfo info)
        {
            switch (info.sensorId)
            {
                case "pir": SetSensorState(label, "감지 안 됨", "sensor-ok"); break;
                default:    SetSensorState(label, "--", "sensor-ok"); break;
            }
        }

        void OnRobotChanged(string robotId) => Rebuild();

        void OnScenarioTriggered(string scenarioId)
        {
            if (scenarioId != "intruder") return;
            if (valueLabels.TryGetValue("pir", out var label) &&
                sensorInfos.TryGetValue("pir", out var info) && !info.disabled)
                SetSensorState(label, "감지!", "sensor-danger");
        }

        static void SetSensorState(Label label, string text, string statusClass)
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
