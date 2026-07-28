// opencode: 2026-06-29 - onSelected 콜백 추가로 4탭 페이지 상태 연동 지원. Coded with OpenCode; high-cost model review recommended.
// PanelTabView.cs — UXML에 선언된 탭 버튼과 페이지를 이름 배열로 연결하는 작은 공용 View.
// 좌/우/하단 패널 전환만 담당하고, 각 페이지 내부 로직은 기존 View가 그대로 보유한다.
using System;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.UI
{
    public class PanelTabView
    {
        readonly Button[] tabs;
        readonly VisualElement[] pages;
        readonly Action<int> onSelected;

        public PanelTabView(VisualElement root, string[] tabNames, string[] pageNames, int activeIndex = 0, Action<int> onSelected = null)
        {
            this.onSelected = onSelected;
            int count = tabNames.Length < pageNames.Length ? tabNames.Length : pageNames.Length;
            tabs = new Button[count];
            pages = new VisualElement[count];

            for (int i = 0; i < count; i++)
            {
                int index = i;
                tabs[i] = root.Q<Button>(tabNames[i]);
                pages[i] = root.Q<VisualElement>(pageNames[i]);
                if (tabs[i] != null) tabs[i].clicked += () => Select(index);
            }

            Select(activeIndex);
        }

        void Select(int activeIndex)
        {
            for (int i = 0; i < tabs.Length; i++)
            {
                bool active = i == activeIndex;
                tabs[i]?.EnableInClassList("active", active);
                pages[i]?.EnableInClassList("hidden", !active);
            }
            onSelected?.Invoke(activeIndex);
        }
    }
}
