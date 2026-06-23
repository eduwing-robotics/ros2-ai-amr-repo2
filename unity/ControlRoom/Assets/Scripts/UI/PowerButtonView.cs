// PowerButtonView.cs — 상단바 우측 전원 버튼. 클릭 시 경고 로그만 (실 종료는 Phase 5+ 안전 게이트).
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class PowerButtonView
    {
        readonly Button btnPower;

        public PowerButtonView(VisualElement root)
        {
            btnPower = root.Q<Button>("btn-power");
            if (btnPower != null) btnPower.clicked += OnClicked;
        }

        void OnClicked()
        {
            ControlRoomEvents.RaiseLogAdded("power", "WARN", "전원 버튼 클릭 — 실 종료는 Phase 5+ 안전 게이트 통과 후");
        }
    }
}
