// SensorVerifyConsole.cs — Phase 2 검증 콘솔. unityctl exec로 호출하는 영구 자산.
// SensorRegistry.All 동적 순회 → 새 센서 추가 시 코드 0줄로 자동 포함.
// 호출: unityctl exec --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()'
// 보조: SwitchTo("tb3_2") / DumpRos() (토픽 매핑 확인)
// 2026-06-30: 하드코딩 sensor 라벨 ID 제거 → sensor-value-{sensorId} convention 적용.
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Ros;
using URHYNIX.ControlRoom.Sensors;

namespace URHYNIX.ControlRoom.App
{
    public static class SensorVerifyConsole
    {
        // battery는 탭마다 1개, 센서 카드 아님.
        const string BatteryLabelId = "battery-percent-label";

        public static string SwitchTo(string robotId)
        {
            ControlRoomState.Instance.SelectRobot(robotId);
            return $"selected -> {robotId}";
        }

        public static string Dump()
        {
            var s = ControlRoomState.Instance;
            var doc = UnityEngine.Object.FindObjectOfType<UIDocument>();
            var root = doc?.rootVisualElement;

            var sb = new StringBuilder();
            sb.AppendLine($"selected={s?.SelectedRobotId}");
            sb.AppendLine($"robots={(s?.Robots != null ? s.Robots.Count : 0)}");

            if (s?.Robots != null)
            {
                foreach (var r in s.Robots)
                {
                    sb.Append($"  [state {r.robotId} {r.displayName}] ");
                    if (s.LastSensorValues.TryGetValue(r.robotId, out var dict))
                    {
                        foreach (var kv in dict)
                            sb.Append($"{kv.Key}={kv.Value:F1} ");
                    }
                    else sb.Append("(empty)");
                    sb.AppendLine();
                }
            }

            var registry = new SensorRegistry();
            registry.LoadFromResources();

            sb.AppendLine("--- UI labels (현재 탭 기준) ---");
            var batteryLabel = root?.Q<Label>(BatteryLabelId);
            sb.AppendLine($"  battery  -> {BatteryLabelId,-22} = '{batteryLabel?.text ?? "(no label)"}'");

            foreach (var sensor in registry.All)
            {
                string labelId = $"sensor-value-{sensor.sensorId}";
                var label = root?.Q<Label>(labelId);
                string text = label?.text ?? "(no label)";
                string classes = label != null ? string.Join("|", label.GetClasses()) : "";
                sb.AppendLine($"  {sensor.sensorId,-8} -> {labelId,-22} = '{text}' [{classes}]");
            }
            return sb.ToString();
        }

        public static string DumpRos()
        {
            var sb = new StringBuilder();
            sb.AppendLine("--- TopicRegistry 매핑 ---");
            foreach (var rid in new[] { "tb3_1", "tb3_2" })
            {
                sb.AppendLine($"  [{rid}]");
                sb.AppendLine($"    battery_state = {TopicRegistry.GetBatteryState(rid) ?? "(null)"}");
                sb.AppendLine($"    camera        = {TopicRegistry.GetCameraCompressed(rid) ?? "(null)"}");
                sb.AppendLine($"    pir           = {TopicRegistry.GetPirState(rid) ?? "(null)"}");
                sb.AppendLine($"    sound         = {TopicRegistry.GetSound(rid) ?? "(null)"}");
                sb.AppendLine($"    temp          = {TopicRegistry.GetTemp(rid) ?? "(null)"}");
                sb.AppendLine($"    laser         = {TopicRegistry.GetLaser(rid) ?? "(null)"}");
            }
            return sb.ToString();
        }

        public static string DumpUiLayout()
        {
            var doc = UnityEngine.Object.FindObjectOfType<UIDocument>();
            var root = doc?.rootVisualElement;
            if (root == null) return "UIDocument/rootVisualElement 없음";

            var sb = new StringBuilder();
            foreach (var name in new[]
            {
                "body", "center-panel", "center-map-slot", "map-panel", "map-2d-container", "map-frame",
                "center-bottom-slot", "camera-log-row", "bottom-panel-camera", "camera-panel", "camera-image"
            })
            {
                var e = root.Q<VisualElement>(name);
                if (e == null)
                {
                    sb.AppendLine($"{name}: null");
                    continue;
                }

                var r = e.resolvedStyle;
                sb.AppendLine($"{name}: {r.width:0.0}x{r.height:0.0} display={r.display}");
            }
            return sb.ToString();
        }
    }
}
