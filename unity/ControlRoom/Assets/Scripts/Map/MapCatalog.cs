// MapCatalog.cs — StreamingAssets/Maps 의 맵 슬롯(<id>.png + <id>.json)을 열거.
// 런타임 슬롯 전환 드롭다운의 목록 소스. 새 슬롯을 폴더에 넣으면 자동 인식(재빌드 불필요).
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public static class MapCatalog
    {
        public const string LiveSlotId = "live";   // 라이브 SLAM(/map) 가상 슬롯
        public const string LiveLabel = "라이브(SLAM)";

        public static string MapsDir => Path.Combine(Application.streamingAssetsPath, "Maps");

        // .png와 .json이 모두 있는 슬롯 id 목록(정렬). 파일 없으면 빈 목록.
        public static List<string> SlotIds()
        {
            var ids = new List<string>();
            if (!Directory.Exists(MapsDir)) return ids;
            foreach (var json in Directory.GetFiles(MapsDir, "*.json"))
            {
                var id = Path.GetFileNameWithoutExtension(json);
                if (File.Exists(Path.Combine(MapsDir, id + ".png"))) ids.Add(id);
            }
            ids.Sort();
            return ids;
        }

        public static bool HasSlot(string id)
            => !string.IsNullOrEmpty(id) && id != LiveSlotId
               && File.Exists(Path.Combine(MapsDir, id + ".png"))
               && File.Exists(Path.Combine(MapsDir, id + ".json"));
    }
}
