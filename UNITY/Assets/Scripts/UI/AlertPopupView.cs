// AlertPopupView.cs — 위험 경보 모달. ControlRoomEvents.OnAlert로 표시, 확인 버튼으로 닫음.
// .visible 클래스 토글로 표시/숨김 (Tokens/Style에 정의된 display 룰).
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class AlertPopupView
    {
        readonly VisualElement popup;
        readonly Label messageLabel;
        readonly Button dismissBtn;

        public AlertPopupView(VisualElement root)
        {
            popup        = root.Q<VisualElement>("alert-popup");
            messageLabel = root.Q<Label>("alert-popup-message");
            dismissBtn   = root.Q<Button>("btn-alert-dismiss");

            if (dismissBtn != null) dismissBtn.clicked += Hide;

            ControlRoomEvents.OnAlert += Show;
        }

        void Show(int severity, string message)
        {
            if (popup == null) return;
            if (messageLabel != null) messageLabel.text = $"⚠ {message}";
            popup.AddToClassList("visible");
        }

        void Hide()
        {
            popup?.RemoveFromClassList("visible");
        }
    }
}
