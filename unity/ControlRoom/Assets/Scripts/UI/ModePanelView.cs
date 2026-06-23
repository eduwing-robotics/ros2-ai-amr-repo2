// ModePanelView.cs — 좌측 패널의 모드 카드. 자동/수동 토글.
// 클릭 → ControlRoomState.SetMode + active 클래스 토글 + 로그 push.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class ModePanelView
    {
        readonly Button autoBtn;
        readonly Button manualBtn;

        public ModePanelView(VisualElement root)
        {
            autoBtn   = root.Q<Button>("btn-mode-auto");
            manualBtn = root.Q<Button>("btn-mode-manual");

            if (autoBtn   != null) autoBtn.clicked   += () => SetMode("auto");
            if (manualBtn != null) manualBtn.clicked += () => SetMode("manual");

            // 초기 active 스타일은 UXML이 박은 그대로 유지 (자동 기본 active).
        }

        void SetMode(string mode)
        {
            ControlRoomState.Instance.SetMode(mode);
            if (autoBtn != null)
            {
                if (mode == "auto") autoBtn.AddToClassList("active");
                else autoBtn.RemoveFromClassList("active");
            }
            if (manualBtn != null)
            {
                if (mode == "manual") manualBtn.AddToClassList("active");
                else manualBtn.RemoveFromClassList("active");
            }
            ControlRoomEvents.RaiseLogAdded("mode", "INFO", $"모드 전환: {mode}");
        }
    }
}
