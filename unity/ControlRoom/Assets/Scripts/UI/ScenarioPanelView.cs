// opencode: 2026-06-30 - SituationConfig 기반 동적 버튼 생성 + demoMode 비활성화.
// ScenarioPanelView.cs — 좌측 패널의 위험상황 시나리오 버튼.
// 클릭 → ControlRoomEvents.RaiseScenarioTriggered → DemoScenarioService가 처리.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Simulation;

namespace URHYNIX.ControlRoom.UI
{
    public class ScenarioPanelView
    {
        const string SituationConfigPath = "SituationConfig/default_situations";

        public ScenarioPanelView(VisualElement root)
        {
            var container = root.Q<VisualElement>("scenario-button-list");
            if (container == null)
            {
                Debug.LogWarning("[ScenarioPanelView] scenario-button-list 컨테이너 없음");
                return;
            }
            container.Clear();

            var ta = Resources.Load<TextAsset>(SituationConfigPath);
            if (ta == null)
            {
                Debug.LogWarning($"[ScenarioPanelView] {SituationConfigPath}.json 없음");
                return;
            }
            var list = JsonUtility.FromJson<SituationInfoList>(ta.text);
            if (list?.situations == null) return;

            bool demoMode = DemoScenarioService.Instance != null && DemoScenarioService.Instance.demoMode;

            foreach (var s in list.situations)
            {
                if (s == null || string.IsNullOrEmpty(s.situationId)) continue;
                var btn = new Button(() => ControlRoomEvents.RaiseScenarioTriggered(s.situationId))
                {
                    text = string.IsNullOrEmpty(s.icon)
                        ? s.displayName
                        : $"{s.icon} {s.displayName}",
                    name = $"btn-scenario-{s.situationId}"
                };
                btn.AddToClassList("btn-scenario");
                if (!demoMode)
                {
                    btn.SetEnabled(false);
                    btn.tooltip = "실제 운영 모드에서는 시나리오 테스트를 사용할 수 없습니다";
                }
                container.Add(btn);
            }
        }
    }
}
