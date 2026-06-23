// MapImageLayer.cs — 라이브 SLAM 맵 텍스처를 map-frame에 채우는 레이어.
// MapSubscriber.OnMapUpdated 구독 → frame을 채우는 Image에 텍스처 할당 + viewport에 맵 메타 전달.
// frame이 맵 비율이라 StretchToFill로 채워도 왜곡 없음.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Map
{
    public class MapImageLayer
    {
        readonly MapViewport viewport;
        readonly Image image;

        public MapImageLayer(MapViewport viewport)
        {
            this.viewport = viewport;

            image = new Image { name = "map-image", scaleMode = ScaleMode.StretchToFill };
            image.style.position = Position.Absolute;
            image.style.left = 0; image.style.right = 0;
            image.style.top = 0;  image.style.bottom = 0;
            image.pickingMode = PickingMode.Ignore; // 클릭은 frame이 받음
            viewport.Frame.Add(image);

            MapSubscriber.OnMapUpdated += OnMapUpdated;
            if (MapSubscriber.LatestMap != null)
                OnMapUpdated(MapSubscriber.LatestMap, MapSubscriber.LatestWidth,
                    MapSubscriber.LatestHeight, MapSubscriber.LatestResolution,
                    MapSubscriber.LatestOriginX, MapSubscriber.LatestOriginY,
                    MapSubscriber.LatestOriginYaw);
        }

        void OnMapUpdated(Texture2D tex, int w, int h, float res, float ox, float oy, float oyaw)
        {
            image.image = tex;
            viewport.SetMap(w, h, res, ox, oy); // 메타 갱신 → frame 재배치
        }

        public void Dispose() => MapSubscriber.OnMapUpdated -= OnMapUpdated;
    }
}
