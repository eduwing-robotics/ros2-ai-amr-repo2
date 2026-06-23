// MapContextMenuView.cs — 우클릭 시 커서 위치에 뜨는 플로팅 메뉴(AlertPopup 패턴: absolute + 표시/숨김).
// 액션 목록을 버튼으로 바인딩, 선택 시 실행 후 닫힘. 바깥 클릭(scrim)으로도 닫힘.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Map.Actions;

namespace URHYNIX.ControlRoom.Map
{
    public class MapContextMenuView
    {
        readonly VisualElement root;
        readonly VisualElement scrim;
        readonly VisualElement menu;

        public MapContextMenuView(VisualElement root)
        {
            this.root = root;

            scrim = new VisualElement { name = "map-ctx-scrim" };
            scrim.style.position = Position.Absolute;
            scrim.style.left = 0; scrim.style.right = 0; scrim.style.top = 0; scrim.style.bottom = 0;
            scrim.style.display = DisplayStyle.None;
            scrim.RegisterCallback<PointerDownEvent>(_ => Close());
            root.Add(scrim);

            menu = new VisualElement { name = "map-ctx-menu" };
            menu.style.position = Position.Absolute;
            menu.style.minWidth = 160;
            menu.style.paddingTop = 4; menu.style.paddingBottom = 4;
            menu.style.backgroundColor = new Color(0.12f, 0.14f, 0.18f, 0.98f);
            menu.style.borderTopLeftRadius = 6; menu.style.borderTopRightRadius = 6;
            menu.style.borderBottomLeftRadius = 6; menu.style.borderBottomRightRadius = 6;
            SetBorder(menu, new Color(1f, 1f, 1f, 0.12f));
            menu.style.display = DisplayStyle.None;
            root.Add(menu);
        }

        public void Open(MapClickContext ctx, IEnumerable<IMapAction> actions)
        {
            menu.Clear();
            var header = new Label($"({ctx.worldX:0.00}, {ctx.worldY:0.00})");
            header.style.color = new Color(0.6f, 0.66f, 0.75f, 1f);
            header.style.fontSize = 10;
            header.style.paddingLeft = 10; header.style.paddingRight = 10;
            header.style.paddingBottom = 2;
            menu.Add(header);

            foreach (var a in actions)
            {
                var item = new Button(() => { a.Execute(ctx); Close(); }) { text = a.DisplayName };
                StyleItem(item);
                menu.Add(item);
            }

            float maxX = root.resolvedStyle.width - 170f;
            float maxY = root.resolvedStyle.height - 160f;
            menu.style.left = Mathf.Min(ctx.screenX, maxX > 0 ? maxX : ctx.screenX);
            menu.style.top  = Mathf.Min(ctx.screenY, maxY > 0 ? maxY : ctx.screenY);
            scrim.style.display = DisplayStyle.Flex;
            menu.style.display = DisplayStyle.Flex;
            menu.BringToFront();
        }

        public void Close()
        {
            scrim.style.display = DisplayStyle.None;
            menu.style.display = DisplayStyle.None;
        }

        static void StyleItem(Button b)
        {
            b.style.backgroundColor = Color.clear;
            b.style.color = new Color(0.92f, 0.95f, 0.98f, 1f);
            b.style.unityTextAlign = TextAnchor.MiddleLeft;
            b.style.fontSize = 12;
            b.style.paddingLeft = 10; b.style.paddingRight = 10;
            b.style.paddingTop = 5; b.style.paddingBottom = 5;
            b.style.marginTop = 0; b.style.marginBottom = 0;
            b.style.marginLeft = 0; b.style.marginRight = 0;
            b.style.borderTopWidth = 0; b.style.borderBottomWidth = 0;
            b.style.borderLeftWidth = 0; b.style.borderRightWidth = 0;
        }

        static void SetBorder(VisualElement e, Color c)
        {
            e.style.borderTopWidth = 1; e.style.borderBottomWidth = 1;
            e.style.borderLeftWidth = 1; e.style.borderRightWidth = 1;
            e.style.borderTopColor = c; e.style.borderBottomColor = c;
            e.style.borderLeftColor = c; e.style.borderRightColor = c;
        }
    }
}
