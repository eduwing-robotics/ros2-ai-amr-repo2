// MapConfigData.cs — office_base_map.json 전체 직렬화 컨테이너.
// 맵 메타 + waypoint + 보호대상을 1파일 안에 묶는다. JsonUtility 호환.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class MapConfigData
    {
        public MapMeta map;
        public WaypointInfo[] waypoints;
        public ProtectedTargetInfo[] protectedTargets;
    }

    [Serializable]
    public class MapMeta
    {
        public string mapId;          // "office_base" / "museum_floor1"
        public string displayName;    // "박물관 1층"
        public float originX;         // ROS 맵 origin (m)
        public float originY;
        public float resolution;      // m/pixel (Nav2 호환)
        public int widthPx;
        public int heightPx;
        public float displayRotationDeg; // 라이브 맵 표시 보정각(시계+). SLAM 원점↔실제 경기장 정렬.
    }

    [Serializable]
    public class WaypointInfo
    {
        public string waypointId;     // "wp_1" / "wp_2"
        public string displayName;    // "1번 지점" / "충전소"
        public float x;
        public float y;
        public float theta;
        public bool isChargingDock;   // 충전소 여부 (한 맵에 1개만 true 권장)
    }
}
