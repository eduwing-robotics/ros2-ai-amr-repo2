// MapViewport.cs — 컨테이너 안에 "map-frame"(맵 비율로 잠긴 사각형)을 만들고 중앙배치·재계산.
// frame이 곧 맵 사각형이라 내부 letterbox가 없고, 마커/클릭 좌표가 frame 기준으로 단순해진다.
// 맵 메타(원점/해상도/셀수)를 보관해 좌표 변환의 단일 출처 역할을 한다.
using System;
using UnityEngine;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.Map
{
    public class MapViewport
    {
        readonly VisualElement container;

        public VisualElement Frame { get; }

        // 맵 메타 (MapSubscriber에서 주입)
        public int WidthCells { get; private set; }
        public int HeightCells { get; private set; }
        public float Resolution { get; private set; }
        public float OriginX { get; private set; }
        public float OriginY { get; private set; }
        public bool HasMap { get; private set; }

        public float MapW => WidthCells * Resolution;   // 실제 가로(m)
        public float MapH => HeightCells * Resolution;  // 실제 세로(m)
        public float FrameWidth => Frame.resolvedStyle.width;
        public float FrameHeight => Frame.resolvedStyle.height;

        // frame 크기/위치가 갱신될 때마다 발생 (마커/HUD가 재배치용으로 구독).
        public event Action OnFrameChanged;

        // 맵 표시 회전(도, 시계방향+). SLAM 원점과 실제 경기장 정렬 보정용.
        public float RotationDeg { get; private set; }

        public MapViewport(VisualElement container)
        {
            this.container = container;
            Frame = new VisualElement { name = "map-frame", pickingMode = PickingMode.Position };
            Frame.style.position = Position.Absolute;
            Frame.style.overflow = Overflow.Hidden;
            Frame.style.transformOrigin = new TransformOrigin(Length.Percent(50), Length.Percent(50), 0);
            container.Add(Frame);
            container.RegisterCallback<GeometryChangedEvent>(_ => Relayout());
        }

        // 프레임 전체(맵 이미지 + 마커)를 중심 기준으로 회전. 마커도 함께 돌아 위치 정합 유지.
        public void SetRotation(float deg)
        {
            RotationDeg = deg;
            Frame.style.rotate = new Rotate(deg);
        }

        public void AddRotation(float delta) => SetRotation(RotationDeg + delta);

        // MapSubscriber.OnMapUpdated에서 호출 — 맵 메타 갱신 후 재배치.
        public void SetMap(int widthCells, int heightCells, float resolution, float originX, float originY)
        {
            WidthCells = widthCells;
            HeightCells = heightCells;
            Resolution = resolution;
            OriginX = originX;
            OriginY = originY;
            HasMap = widthCells > 0 && heightCells > 0 && resolution > 0f;
            Relayout();
        }

        // 컨테이너 크기/맵 비율에 맞춰 frame을 최대 크기로 중앙배치.
        void Relayout()
        {
            float cw = container.resolvedStyle.width;
            float ch = container.resolvedStyle.height;
            if (cw <= 0f || ch <= 0f || !HasMap || MapW <= 0f || MapH <= 0f) return;

            float mapAspect = MapW / MapH;
            float containerAspect = cw / ch;
            float fw, fh;
            if (containerAspect > mapAspect) { fh = ch; fw = ch * mapAspect; } // 세로 제한
            else                             { fw = cw; fh = cw / mapAspect; } // 가로 제한

            Frame.style.width = fw;
            Frame.style.height = fh;
            Frame.style.left = (cw - fw) * 0.5f;
            Frame.style.top = (ch - fh) * 0.5f;

            OnFrameChanged?.Invoke();
        }
    }
}
