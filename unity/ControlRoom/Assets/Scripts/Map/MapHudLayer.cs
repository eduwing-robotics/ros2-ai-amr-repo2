// MapHudLayer.cs — 맵 위 HUD: 방위(N), 스케일바, 좌표 readout. 남는 여백을 정보로 활용.
// 스케일바는 viewport 프레임 크기/해상도에 맞춰 길이 갱신. 좌표는 hover 시 SetCoordinate로 갱신(Phase 3).
using UnityEngine;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.Map
{
    public class MapHudLayer
    {
        readonly MapViewport viewport;
        readonly VisualElement scaleBar;
        readonly Label scaleLabel;
        readonly Label coordLabel;

        static readonly float[] NiceMeters = { 0.25f, 0.5f, 1f, 2f, 5f, 10f };

        public MapHudLayer(VisualElement container, MapViewport viewport)
        {
            this.viewport = viewport;

            // 방위 N (우상단)
            var north = MakePill("N ↑");
            north.style.top = 6; north.style.right = 6;
            container.Add(north);

            // 스케일바 (좌하단)
            var scaleWrap = new VisualElement { name = "map-scale", pickingMode = PickingMode.Ignore };
            scaleWrap.style.position = Position.Absolute;
            scaleWrap.style.left = 8; scaleWrap.style.bottom = 8;
            scaleWrap.style.alignItems = Align.Center;
            scaleBar = new VisualElement { pickingMode = PickingMode.Ignore };
            scaleBar.style.height = 3;
            scaleBar.style.backgroundColor = new Color(0.9f, 0.93f, 0.97f, 0.9f);
            scaleLabel = new Label("—") { name = "map-scale-label", pickingMode = PickingMode.Ignore };
            StylePill(scaleLabel);
            scaleWrap.Add(scaleBar);
            scaleWrap.Add(scaleLabel);
            container.Add(scaleWrap);

            // 좌표 readout (우하단)
            coordLabel = MakePill("x —  y —");
            coordLabel.style.bottom = 8; coordLabel.style.right = 6;
            container.Add(coordLabel);

            viewport.OnFrameChanged += UpdateScaleBar;
        }

        public void SetCoordinate(float x, float y)
            => coordLabel.text = $"x {x:0.00}  y {y:0.00}";

        public void ClearCoordinate() => coordLabel.text = "x —  y —";

        void UpdateScaleBar()
        {
            if (!viewport.HasMap || viewport.MapW <= 0f) return;
            float pxPerM = viewport.FrameWidth / viewport.MapW;
            if (pxPerM <= 0f) return;

            float meters = NiceMeters[0];
            foreach (var m in NiceMeters)
                if (m <= viewport.MapW * 0.4f) meters = m;

            scaleBar.style.width = meters * pxPerM;
            scaleLabel.text = meters >= 1f ? $"{meters:0.#} m" : $"{meters * 100f:0} cm";
        }

        static Label MakePill(string text)
        {
            var l = new Label(text) { pickingMode = PickingMode.Ignore };
            l.style.position = Position.Absolute;
            StylePill(l);
            return l;
        }

        static void StylePill(Label l)
        {
            l.style.color = new Color(0.92f, 0.95f, 0.98f, 1f);
            l.style.backgroundColor = new Color(0.10f, 0.12f, 0.16f, 0.66f);
            l.style.paddingLeft = 6; l.style.paddingRight = 6;
            l.style.paddingTop = 2; l.style.paddingBottom = 2;
            l.style.fontSize = 11;
            l.style.borderTopLeftRadius = 4; l.style.borderTopRightRadius = 4;
            l.style.borderBottomLeftRadius = 4; l.style.borderBottomRightRadius = 4;
            l.style.marginTop = 2;
        }
    }
}
