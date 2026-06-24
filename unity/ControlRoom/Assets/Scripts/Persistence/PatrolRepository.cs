// PatrolRepository.cs — 순찰 경로 로컬 영속(persistentDataPath/patrols/<mapId>.json). 로컬 우선 = Wi-Fi 무관.
// PatrolService 변경 시 자동 저장, 맵 슬롯 로드 시 그 맵의 경로 자동 복원(맵별 1경로). 끊겨도 안전.
// Supabase 동기화는 patrol_routes 테이블 적용 후 활성(scripts/sql/patrol_routes.sql) — 별도 단계.
using System.IO;
using UnityEngine;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Map;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Persistence
{
    public class PatrolRepository : MonoBehaviour
    {
        static string Dir => Path.Combine(Application.persistentDataPath, "patrols");
        bool loading;   // 자동 로드 중 자동 저장 재귀 방지

        void OnEnable()
        {
            ControlRoomEvents.OnPatrolChanged += AutoSave;
            StaticMapLoader.OnStaticMapLoaded += OnStaticLoaded;
        }

        void OnDisable()
        {
            ControlRoomEvents.OnPatrolChanged -= AutoSave;
            StaticMapLoader.OnStaticMapLoaded -= OnStaticLoaded;
        }

        void Start()
        {
            // 구독 전에 이미 맵이 로드됐으면 복원.
            if (StaticMapLoader.LatestMap != null) Load(StaticMapLoader.LatestSlotId);
        }

        void OnStaticLoaded(string slotId, Texture2D tex, int w, int h, float res, float ox, float oy, float oyaw)
            => Load(slotId);

        string CurrentMapId =>
            string.IsNullOrEmpty(StaticMapLoader.LatestSlotId) ? "default" : StaticMapLoader.LatestSlotId;

        void AutoSave()
        {
            if (loading) return;
            Save(CurrentMapId);
        }

        public void Save(string mapId)
        {
            try
            {
                Directory.CreateDirectory(Dir);
                var pts = PatrolService.Instance.Points;
                var arr = new PatrolPoint[pts.Count];
                for (int i = 0; i < pts.Count; i++) arr[i] = pts[i];
                var route = new PatrolRoute
                {
                    routeId = mapId, mapId = mapId,
                    robotId = ActiveRobotService.CurrentId, points = arr
                };
                File.WriteAllText(Path.Combine(Dir, mapId + ".json"), JsonUtility.ToJson(route, true));
            }
            catch (System.Exception e) { Debug.LogWarning($"[PatrolRepository] 저장 실패: {e.Message}"); }
        }

        public void Load(string mapId)
        {
            if (string.IsNullOrEmpty(mapId)) mapId = "default";
            string path = Path.Combine(Dir, mapId + ".json");
            loading = true;
            try
            {
                if (File.Exists(path))
                {
                    var route = JsonUtility.FromJson<PatrolRoute>(File.ReadAllText(path));
                    PatrolService.Instance.Replace(route?.points);
                }
                else PatrolService.Instance.Replace(null);   // 그 맵엔 경로 없음 → 비움
            }
            catch (System.Exception e) { Debug.LogWarning($"[PatrolRepository] 로드 실패: {e.Message}"); }
            finally { loading = false; }
        }
    }
}
