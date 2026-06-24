// MapImageLayer.cs — 맵 텍스처를 map-frame에 채우는 레이어. 라이브 SLAM(/map)과 저장맵 슬롯을 모두 표시.
// 우선순위: 슬롯을 직접 고르면(pinned) 그 저장맵 고정. pinned 없으면 라이브가 정적(auto)보다 우선.
// frame이 맵 비율이라 StretchToFill로 채워도 왜곡 없음.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Map
{
    public class MapImageLayer
    {
        readonly MapViewport viewport;
        readonly Image image;

        bool liveReceived;
        string pinnedSlot;            // null이면 자동(라이브 우선), 값이 있으면 그 저장맵 고정
        Texture2D liveTex; int lw, lh; float lres, lox, loy;   // 마지막 라이브 맵 캐시(핀 해제 시 복귀용)

        public MapImageLayer(MapViewport viewport)
        {
            this.viewport = viewport;

            image = new Image { name = "map-image", scaleMode = ScaleMode.StretchToFill };
            image.style.position = Position.Absolute;
            image.style.left = 0; image.style.right = 0;
            image.style.top = 0;  image.style.bottom = 0;
            image.pickingMode = PickingMode.Ignore; // 클릭은 frame이 받음
            viewport.Frame.Add(image);

            MapSubscriber.OnMapUpdated += OnLiveMap;
            StaticMapLoader.OnStaticMapLoaded += OnStaticMap;
            ControlRoomEvents.OnMapSlotSelected += OnSlotSelected;

            // 초기 상태 복원: 라이브가 이미 있으면 라이브, 아니면 마지막 저장맵.
            if (MapSubscriber.LatestMap != null)
                OnLiveMap(MapSubscriber.LatestMap, MapSubscriber.LatestWidth, MapSubscriber.LatestHeight,
                    MapSubscriber.LatestResolution, MapSubscriber.LatestOriginX, MapSubscriber.LatestOriginY,
                    MapSubscriber.LatestOriginYaw);
            else if (StaticMapLoader.LatestMap != null)
                OnStaticMap(StaticMapLoader.LatestSlotId, StaticMapLoader.LatestMap,
                    StaticMapLoader.LatestWidth, StaticMapLoader.LatestHeight, StaticMapLoader.LatestResolution,
                    StaticMapLoader.LatestOriginX, StaticMapLoader.LatestOriginY, StaticMapLoader.LatestOriginYaw);
        }

        void OnLiveMap(Texture2D tex, int w, int h, float res, float ox, float oy, float oyaw)
        {
            liveReceived = true;
            liveTex = tex; lw = w; lh = h; lres = res; lox = ox; loy = oy;
            if (pinnedSlot == null) Render(tex, w, h, res, ox, oy);   // 핀 없으면 라이브 우선
        }

        void OnStaticMap(string slotId, Texture2D tex, int w, int h, float res, float ox, float oy, float oyaw)
        {
            // 사용자가 고른 슬롯이면 고정 표시; 자동 상태면 라이브가 아직 없을 때만 표시.
            if (pinnedSlot == slotId) Render(tex, w, h, res, ox, oy);
            else if (pinnedSlot == null && !liveReceived) Render(tex, w, h, res, ox, oy);
        }

        void OnSlotSelected(string slotId)
        {
            if (slotId == MapCatalog.LiveSlotId)
            {
                pinnedSlot = null;                                   // 핀 해제 → 라이브 복귀
                if (liveTex != null) Render(liveTex, lw, lh, lres, lox, loy);
                return;
            }
            pinnedSlot = slotId;
            // 이벤트 구독 순서 무관 보장: StaticMapLoader가 이미 이 슬롯을 로드해 뒀으면 즉시 렌더.
            // (StaticMapLoader.OnSlotSelected가 먼저 실행돼 OnStaticMap이 pinned 설정 전 무시된 경우 복구)
            if (StaticMapLoader.LatestSlotId == slotId && StaticMapLoader.LatestMap != null)
                Render(StaticMapLoader.LatestMap, StaticMapLoader.LatestWidth, StaticMapLoader.LatestHeight,
                    StaticMapLoader.LatestResolution, StaticMapLoader.LatestOriginX, StaticMapLoader.LatestOriginY);
            // 아직 미로드면 StaticMapLoader.Load가 OnStaticMap을 쏠 때 pinned==slotId라 렌더됨.
        }

        void Render(Texture2D tex, int w, int h, float res, float ox, float oy)
        {
            image.image = tex;
            viewport.SetMap(w, h, res, ox, oy); // 메타 갱신 → frame 재배치
        }

        public void Dispose()
        {
            MapSubscriber.OnMapUpdated -= OnLiveMap;
            StaticMapLoader.OnStaticMapLoaded -= OnStaticMap;
            ControlRoomEvents.OnMapSlotSelected -= OnSlotSelected;
        }
    }
}
