// PatrolMarkerLayer.cs — 순찰 웨이포인트 마커(번호 원형) + 순서 연결선.
// PatrolService.OnPatrolChanged / frame 변경 시 갱신. 선은 generateVisualContent(Painter2D),
// 번호는 Label 풀로 그린다. 좌표 변환은 MapCoordinateSystem(SSOT) 위임.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map
{
    public class PatrolMarkerLayer
    {
        readonly MapViewport viewport;
        readonly VisualElement lineCanvas;
        readonly List<Label> labelPool = new List<Label>();
        readonly List<Vector2> px = new List<Vector2>();   // DrawLines가 사용하는 frame 픽셀

        static readonly Color LineColor = new Color(0.95f, 0.45f, 0.20f, 0.95f);
        static readonly Color DotColor = new Color(0.95f, 0.45f, 0.20f, 1f);

        public PatrolMarkerLayer(MapViewport viewport)
        {
            this.viewport = viewport;

            lineCanvas = new VisualElement { name = "patrol-lines", pickingMode = PickingMode.Ignore };
            lineCanvas.style.position = Position.Absolute;
            lineCanvas.style.left = 0; lineCanvas.style.right = 0;
            lineCanvas.style.top = 0; lineCanvas.style.bottom = 0;
            lineCanvas.generateVisualContent += DrawLines;
            viewport.Frame.Add(lineCanvas);

            ControlRoomEvents.OnPatrolChanged += Refresh;
            viewport.OnFrameChanged += Refresh;
            Refresh();
        }

        void Refresh()
        {
            var pts = PatrolService.Instance.Points;
            px.Clear();
            if (viewport.HasMap && viewport.FrameWidth > 0f && viewport.FrameHeight > 0f)
            {
                foreach (var p in pts)
                    px.Add(MapCoordinateSystem.WorldToFramePx(p.x, p.y,
                        viewport.OriginX, viewport.OriginY, viewport.MapW, viewport.MapH,
                        viewport.FrameWidth, viewport.FrameHeight));
            }

            EnsureLabels(px.Count);
            for (int i = 0; i < labelPool.Count; i++)
            {
                var lbl = labelPool[i];
                if (i < px.Count)
                {
                    lbl.text = (i + 1).ToString();
                    lbl.style.left = px[i].x;
                    lbl.style.top = px[i].y;
                    lbl.style.display = DisplayStyle.Flex;
                }
                else lbl.style.display = DisplayStyle.None;
            }

            lineCanvas.MarkDirtyRepaint();
        }

        void EnsureLabels(int n)
        {
            while (labelPool.Count < n)
            {
                var lbl = new Label { pickingMode = PickingMode.Ignore };
                lbl.style.position = Position.Absolute;
                lbl.style.fontSize = 11;
                lbl.style.color = Color.white;
                lbl.style.backgroundColor = DotColor;
                lbl.style.unityTextAlign = TextAnchor.MiddleCenter;
                lbl.style.minWidth = 18; lbl.style.height = 18;
                lbl.style.borderTopLeftRadius = 9; lbl.style.borderTopRightRadius = 9;
                lbl.style.borderBottomLeftRadius = 9; lbl.style.borderBottomRightRadius = 9;
                lbl.style.paddingLeft = 0; lbl.style.paddingRight = 0;
                lbl.style.transformOrigin = new TransformOrigin(Length.Percent(50), Length.Percent(50), 0);
                lbl.style.translate = new Translate(Length.Percent(-50), Length.Percent(-50));
                viewport.Frame.Add(lbl);
                labelPool.Add(lbl);
            }
        }

        void DrawLines(MeshGenerationContext mgc)
        {
            if (px.Count < 2) return;
            var p = mgc.painter2D;
            p.lineWidth = 2f;
            p.strokeColor = LineColor;
            p.BeginPath();
            p.MoveTo(px[0]);
            for (int i = 1; i < px.Count; i++) p.LineTo(px[i]);
            p.Stroke();
        }

        public void Dispose()
        {
            ControlRoomEvents.OnPatrolChanged -= Refresh;
            viewport.OnFrameChanged -= Refresh;
        }
    }
}
