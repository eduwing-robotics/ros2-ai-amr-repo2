// ProtectedTargetView.cs — 우측 패널 보호대상 카드. 액자 A/B + 중요품 A 더미.
// OnScenarioTriggered("theft") 발화 시 보호대상 1개를 "미확인" 상태로 토글 (fake interaction).
// Phase 3에서 office_base_map.json의 protectedTargets[] 기반 자동 생성으로 swap.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class ProtectedTargetView
    {
        readonly Label frameAStatus;
        readonly Label frameBStatus;
        readonly Label objectAStatus;

        public ProtectedTargetView(VisualElement root)
        {
            frameAStatus  = root.Q<Label>("target-frame-a-status");
            frameBStatus  = root.Q<Label>("target-frame-b-status");
            objectAStatus = root.Q<Label>("target-object-a-status");

            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;
            ControlRoomEvents.OnRobotChanged      += OnRobotChanged;
        }

        void OnScenarioTriggered(string scenarioId)
        {
            if (scenarioId != "theft") return;
            // 도난 시나리오: 중요품 A를 미확인으로 토글 (시연 인상용 fake)
            SetStatus(objectAStatus, "미확인", "target-status-danger");
        }

        void OnRobotChanged(string robotId)
        {
            // 탭 전환 시 보호대상 상태 reset (시나리오 초기화)
            SetStatus(frameAStatus,  "확인됨", "target-status-ok");
            SetStatus(frameBStatus,  "확인됨", "target-status-ok");
            SetStatus(objectAStatus, "확인됨", "target-status-ok");
        }

        void SetStatus(Label label, string text, string statusClass)
        {
            if (label == null) return;
            label.text = text;
            label.RemoveFromClassList("target-status-ok");
            label.RemoveFromClassList("target-status-warn");
            label.RemoveFromClassList("target-status-danger");
            label.AddToClassList(statusClass);
        }
    }
}
