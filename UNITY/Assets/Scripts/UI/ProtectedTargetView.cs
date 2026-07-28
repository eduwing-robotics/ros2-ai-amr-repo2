// ProtectedTargetView.cs — 우측 패널 보호대상 카드를 MapConfig 기반으로 동적 생성.
// 2026-06-30: frameA/B + objectA 하드코딩 제거 → office_base_map.json protectedTargets[] 기반.
using System.Collections.Generic;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.UI
{
    public class ProtectedTargetView
    {
        readonly VisualElement list;
        readonly Dictionary<string, Label> statusLabels = new();
        readonly Dictionary<string, VisualElement> dotElements = new();

        public ProtectedTargetView(VisualElement root)
        {
            list = root.Q<VisualElement>("protected-target-list");
            Rebuild();

            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;
            ControlRoomEvents.OnRobotChanged      += OnRobotChanged;
        }

        void Rebuild()
        {
            list?.Clear();
            statusLabels.Clear();
            dotElements.Clear();

            var targets = MapConfigService.Current?.protectedTargets;
            if (targets == null || targets.Length == 0)
            {
                list?.Add(new Label("등록된 보호대상이 없습니다.") { name = "target-empty" });
                return;
            }

            foreach (var t in targets)
            {
                var row = new VisualElement();
                row.AddToClassList("target-row");

                var dot = new VisualElement();
                dot.name = $"target-dot-{t.targetId}";
                dot.AddToClassList("target-dot");
                row.Add(dot);

                var nameLabel = new Label(t.displayName);
                nameLabel.AddToClassList("target-name");
                row.Add(nameLabel);

                var statusLabel = new Label(StatusText(t.status));
                statusLabel.name = $"target-status-{t.targetId}";
                statusLabel.AddToClassList("target-status");
                row.Add(statusLabel);

                list?.Add(row);
                statusLabels[t.targetId] = statusLabel;
                dotElements[t.targetId] = dot;
                ApplyStatus(t.targetId, t.status);
            }
        }

        void OnScenarioTriggered(string scenarioId)
        {
            if (scenarioId != "theft") return;
            // 데모 시나리오: 첫 번째 보호대상을 미확인 상태로 토글.
            foreach (var id in statusLabels.Keys)
            {
                ApplyStatus(id, "missing");
                break;
            }
        }

        void OnRobotChanged(string robotId) => Rebuild();

        void ApplyStatus(string targetId, string status)
        {
            if (!statusLabels.TryGetValue(targetId, out var label)) return;
            dotElements.TryGetValue(targetId, out var dot);

            label.text = StatusText(status);

            label.RemoveFromClassList("target-status-ok");
            label.RemoveFromClassList("target-status-warn");
            label.RemoveFromClassList("target-status-danger");
            dot?.RemoveFromClassList("target-ok");
            dot?.RemoveFromClassList("target-warn");
            dot?.RemoveFromClassList("target-danger");

            var cls = StatusToClass(status);
            label.AddToClassList($"target-status-{cls}");
            dot?.AddToClassList($"target-{cls}");
        }

        static string StatusText(string status) => status?.ToLower() switch
        {
            "safe"    => "확인됨",
            "check"   => "확인 필요",
            "missing" => "미확인",
            _         => status ?? "--"
        };

        static string StatusToClass(string status) => status?.ToLower() switch
        {
            "safe"    => "ok",
            "check"   => "warn",
            "missing" => "danger",
            _         => "ok"
        };
    }
}
