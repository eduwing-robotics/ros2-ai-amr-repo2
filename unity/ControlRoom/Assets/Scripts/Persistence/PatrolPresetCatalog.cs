// PatrolPresetCatalog.cs — 맵별 검증된 순찰 프리셋(StreamingAssets/Maps/<mapId>.presets.json) 로더.
// scripts/patrol_presets.py가 거리변환(벽·장애물 클리어런스 ≥0.25m)으로 검증·생성한 좌표를
// 맵 패널 드롭다운에 노출 — 사용자가 벽/장애물에 붙여 찍어 주행 실패하는 문제의 안전 대안.
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Persistence
{
    [System.Serializable]
    public class PatrolPreset
    {
        public string name;
        public PatrolPoint[] points;
    }

    [System.Serializable]
    public class PatrolPresetFile
    {
        public PatrolPreset[] presets;
    }

    public static class PatrolPresetCatalog
    {
        public static List<PatrolPreset> Load(string mapId)
        {
            var result = new List<PatrolPreset>();
            if (string.IsNullOrEmpty(mapId)) return result;
            string path = Path.Combine(Application.streamingAssetsPath, "Maps", mapId + ".presets.json");
            try
            {
                if (!File.Exists(path)) return result;
                var file = JsonUtility.FromJson<PatrolPresetFile>(File.ReadAllText(path));
                if (file?.presets != null)
                    foreach (var p in file.presets)
                        if (p != null && p.points != null && p.points.Length > 0)
                            result.Add(p);
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"[PatrolPresetCatalog] 프리셋 로드 실패({path}): {e.Message}");
            }
            return result;
        }
    }
}
