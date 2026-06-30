// StaticMapLoader.cs — 저장맵 슬롯(StreamingAssets/Maps/<id>.png+.json)을 읽어 맵뷰에 공급.
// 로봇/ROS 연결과 무관(오프라인 내성). 슬롯 전환은 ControlRoomEvents.OnMapSlotSelected로 들어옴.
// 마지막 선택 슬롯을 PlayerPrefs에 영속 → 다음 실행에서 같은 맵으로 시작.
using System.IO;
using UnityEngine;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map
{
    public class StaticMapLoader : MonoBehaviour
    {
        public const string ActiveSlotPrefKey = "urhynix.map.activeSlotId";

        // (slotId, tex, w, h, res, originX, originY, originYaw). pinned 여부는 MapImageLayer가 slotId로 판단.
        public static event System.Action<string, Texture2D, int, int, float, float, float, float> OnStaticMapLoaded;
        public static Texture2D LatestMap { get; private set; }
        public static string LatestSlotId { get; private set; }
        public static int LatestWidth { get; private set; }
        public static int LatestHeight { get; private set; }
        public static float LatestResolution { get; private set; }
        public static float LatestOriginX { get; private set; }
        public static float LatestOriginY { get; private set; }
        public static float LatestOriginYaw { get; private set; }

        // 최종 fallback. arena_v* 슬롯이 하나도 없을 때만 사용(보통은 MapCatalog가 최신 버전을 동적 선택).
        [SerializeField] string defaultSlotId = "arena_v5";

        void OnEnable() => ControlRoomEvents.OnMapSlotSelected += OnSlotSelected;
        void OnDisable() => ControlRoomEvents.OnMapSlotSelected -= OnSlotSelected;

        void Start()
        {
            // 마지막 선택 우선. 없으면 운영 디폴트. "live"면 자동 모드라 정적 로드 생략.
            // arena_v5(동료 신규 SLAM 정확맵, 2026-06-26) 운영 복귀 — map5 임시핀 제거, LatestArenaSlot으로 복귀.
            string latest = MapCatalog.LatestArenaSlot(defaultSlotId);
            string slot = PlayerPrefs.GetString(ActiveSlotPrefKey, latest);
            // 삭제된 레거시 슬롯이 PlayerPrefs에 잔존하면(map5 등) 최신 슬롯으로 폴백 — 맵이 안 뜨는 상태 방지.
            if (slot != MapCatalog.LiveSlotId && !MapCatalog.HasSlot(slot)) slot = latest;
            if (slot == MapCatalog.LiveSlotId) slot = MapCatalog.HasSlot(latest) ? latest : slot;
            if (MapCatalog.HasSlot(slot)) Load(slot);
            else Debug.LogWarning($"[StaticMapLoader] 슬롯 없음: {slot} (StreamingAssets/Maps 확인)");
        }

        void OnSlotSelected(string slotId)
        {
            if (slotId == MapCatalog.LiveSlotId)
            {
                PlayerPrefs.SetString(ActiveSlotPrefKey, slotId); PlayerPrefs.Save();
                return; // 라이브 전환은 MapImageLayer가 핀 해제 처리
            }
            if (MapCatalog.HasSlot(slotId)) Load(slotId);
        }

        public void Load(string slotId)
        {
            string dir = MapCatalog.MapsDir;
            string png = Path.Combine(dir, slotId + ".png");
            string json = Path.Combine(dir, slotId + ".json");
            if (!File.Exists(png) || !File.Exists(json))
            {
                Debug.LogWarning($"[StaticMapLoader] 파일 없음: {png} / {json}");
                return;
            }
            var meta = JsonUtility.FromJson<MapConfigData>(File.ReadAllText(json))?.map;
            if (meta == null) { Debug.LogWarning($"[StaticMapLoader] 메타 파싱 실패: {json}"); return; }

            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point };
            if (!tex.LoadImage(File.ReadAllBytes(png))) { Debug.LogWarning($"[StaticMapLoader] PNG 디코드 실패: {png}"); return; }

            int widthCells = meta.widthPx > 0 ? meta.widthPx : tex.width;
            int heightCells = meta.heightPx > 0 ? meta.heightPx : tex.height;

            LatestMap = tex; LatestSlotId = slotId;
            LatestWidth = widthCells; LatestHeight = heightCells;
            LatestResolution = meta.resolution; LatestOriginX = meta.originX; LatestOriginY = meta.originY; LatestOriginYaw = 0f;
            PlayerPrefs.SetString(ActiveSlotPrefKey, slotId); PlayerPrefs.Save();

            OnStaticMapLoaded?.Invoke(slotId, tex, widthCells, heightCells, meta.resolution, meta.originX, meta.originY, 0f);
            Debug.Log($"[StaticMapLoader] 슬롯 '{slotId}' 로드 tex={tex.width}x{tex.height} map={widthCells}x{heightCells} origin({meta.originX},{meta.originY})");
        }
    }
}
