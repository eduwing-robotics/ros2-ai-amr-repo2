// MapConfigService.cs — Resources/MapConfig/office_base_map.json 1회 로드 → MapConfigData SSOT.
// PatrolService/ProtectedTargetView/MapView 등에서 실데이터로 fallback 받아 쓴다.
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Services
{
    public static class MapConfigService
    {
        const string ResourcePath = "MapConfig/office_base_map";

        public static MapConfigData Current { get; private set; }

        public static void LoadFromResources()
        {
            Current = null;
            var ta = Resources.Load<TextAsset>(ResourcePath);
            if (ta == null)
            {
                Debug.LogWarning($"[MapConfigService] '{ResourcePath}.json' 누락. MapConfig fallback 없이 실행.");
                return;
            }
            try
            {
                Current = JsonUtility.FromJson<MapConfigData>(ta.text);
                Debug.Log($"[MapConfigService] 로드: map={Current?.map?.displayName}, waypoints={(Current?.waypoints?.Length ?? 0)}, targets={(Current?.protectedTargets?.Length ?? 0)}");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[MapConfigService] 파싱 실패: {e.Message}");
            }
        }
    }
}
