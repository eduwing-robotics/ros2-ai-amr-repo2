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

        [SerializeField] string defaultSlotId = "arena";

        void OnEnable() => ControlRoomEvents.OnMapSlotSelected += OnSlotSelected;
        void OnDisable() => ControlRoomEvents.OnMapSlotSelected -= OnSlotSelected;

        void Start()
        {
            // 마지막 선택(없으면 기본). "live"면 자동 모드라 정적 로드는 생략(MapImageLayer가 라이브 대기).
            string slot = PlayerPrefs.GetString(ActiveSlotPrefKey, defaultSlotId);
            if (slot == MapCatalog.LiveSlotId) slot = MapCatalog.HasSlot(defaultSlotId) ? defaultSlotId : slot;
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

            LatestMap = tex; LatestSlotId = slotId;
            LatestWidth = tex.width; LatestHeight = tex.height;
            LatestResolution = meta.resolution; LatestOriginX = meta.originX; LatestOriginY = meta.originY; LatestOriginYaw = 0f;
            PlayerPrefs.SetString(ActiveSlotPrefKey, slotId); PlayerPrefs.Save();

            OnStaticMapLoaded?.Invoke(slotId, tex, tex.width, tex.height, meta.resolution, meta.originX, meta.originY, 0f);
            Debug.Log($"[StaticMapLoader] 슬롯 '{slotId}' 로드 {tex.width}x{tex.height} origin({meta.originX},{meta.originY})");
        }
    }
}
