// FeatureToggleListView.cs — 좌측 패널의 특수 모드 카드. 360°스캔/가속/SLAM 토글 3종.
// Phase 2.5는 정적 UXML 토글을 핸들링. Phase 3에서 default_features.json + FeatureRegistry 기반 자동 생성으로 교체.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class FeatureToggleListView
    {
        public FeatureToggleListView(VisualElement root)
        {
            Bind(root.Q<Toggle>("toggle-scan"),  "scan",  "360° 스캔");
            Bind(root.Q<Toggle>("toggle-turbo"), "turbo", "가속");
            Bind(root.Q<Toggle>("toggle-slam"),  "slam",  "SLAM");
        }

        void Bind(Toggle toggle, string featureId, string label)
        {
            if (toggle == null) return;
            toggle.RegisterValueChangedCallback(evt =>
            {
                var state = evt.newValue ? "ON" : "OFF";
                ControlRoomEvents.RaiseLogAdded("feature", "INFO", $"{label} {state}");
            });
        }
    }
}
