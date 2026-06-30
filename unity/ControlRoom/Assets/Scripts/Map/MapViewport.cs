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

        // 줌/팬 (Frame transform). rotate와 같은 인프라라 클릭 WorldToLocal이 자동 역산.
        public float Zoom { get; private set; } = 1f;
        public float PanX { get; private set; }
        public float PanY { get; private set; }
        const float MinZoom = 1f, MaxZoom = 6f;

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
            RotationDeg = deg % 360f;   // 360°=0° 정규화 (회전 누적 시 한 바퀴 깔끔 처리)
            Frame.style.rotate = new Rotate(RotationDeg);
        }

        public void AddRotation(float delta) => SetRotation(RotationDeg + delta);

        // 커서 고정 줌: pivot(프레임-로컬 px)이 줌 후에도 같은 화면점에 남도록 pan 보정.
        // center-origin scale이라 화면점 = F + pan + center + (p-center)*zoom → pan += (p-center)*(old-new).
        public void SetZoom(float targetZoom, Vector2 pivotFrameLocal)
        {
            float clamped = Mathf.Clamp(targetZoom, MinZoom, MaxZoom);
            if (Mathf.Approximately(clamped, Zoom)) return;
            float cx = FrameWidth * 0.5f, cy = FrameHeight * 0.5f;
            PanX += (pivotFrameLocal.x - cx) * (Zoom - clamped);
            PanY += (pivotFrameLocal.y - cy) * (Zoom - clamped);
            Zoom = clamped;
            ClampPan();
            ApplyTransform();
        }

        public void Pan(float dx, float dy)
        {
            PanX += dx; PanY += dy;
            ClampPan();
            ApplyTransform();
        }

        public void ResetView()
        {
            Zoom = 1f; PanX = 0f; PanY = 0f;
            ApplyTransform();
        }

        // 줌인 상태에서 맵이 container 밖으로 과도 이탈하지 않게 pan 제한.
        void ClampPan()
        {
            float mx = FrameWidth * (Zoom - 1f) * 0.5f;
            float my = FrameHeight * (Zoom - 1f) * 0.5f;
            PanX = Mathf.Clamp(PanX, -mx, mx);
            PanY = Mathf.Clamp(PanY, -my, my);
        }

        void ApplyTransform()
        {
            Frame.style.scale = new Scale(new Vector2(Zoom, Zoom));
            Frame.style.translate = new Translate(PanX, PanY);
            OnFrameChanged?.Invoke();   // 마커 reposition + 스케일바 갱신
        }

        // MapSubscriber.OnMapUpdated에서 호출 — 맵 메타 갱신 후 재배치.
        public void SetMap(int widthCells, int heightCells, float resolution, float originX, float originY)
        {
            WidthCells = widthCells;
            HeightCells = heightCells;
            Resolution = resolution;
            OriginX = originX;
            OriginY = originY;
            HasMap = widthCells > 0 && heightCells > 0 && resolution > 0f;
            ResetView();   // 새 맵이면 줌/팬 초기화
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
