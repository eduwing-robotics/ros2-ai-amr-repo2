// ScenarioPanelView.cs — 좌측 패널의 시나리오 4종 버튼(화재/침입/소음/도난).
// 클릭 → ControlRoomEvents.RaiseScenarioTriggered → DemoScenarioService가 처리.
// Phase 2.5에서 모드/순회/특수모드/웨이포인트는 별도 View로 분리(SRP).
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class ScenarioPanelView
    {
        public ScenarioPanelView(VisualElement root)
        {
            Bind(root.Q<Button>("btn-scenario-fire"),     "fire");
            Bind(root.Q<Button>("btn-scenario-intruder"), "intruder");
            Bind(root.Q<Button>("btn-scenario-noise"),    "noise");
            Bind(root.Q<Button>("btn-scenario-theft"),    "theft");
        }

        void Bind(Button btn, string scenarioId)
        {
            if (btn == null) return;
            btn.clicked += () => ControlRoomEvents.RaiseScenarioTriggered(scenarioId);
        }
    }
}
