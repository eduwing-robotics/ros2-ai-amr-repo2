// PatrolRoute.cs — 순찰 경로 데이터(순수 POCO). PatrolPoint 순서 목록 + 맵/로봇 메타. JSON 직렬화 가능.
// map 프레임 좌표(m). Phase 5에서 PatrolRepository가 로컬/Supabase로 영속.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class PatrolPoint
    {
        public int seq;      // 1-based 순서
        public float x;      // map 프레임 X (m)
        public float y;      // map 프레임 Y (m)
        public float theta;  // yaw (rad), 0이면 미지정
    }

    [Serializable]
    public class PatrolRoute
    {
        public string routeId;
        public string mapId;
        public string robotId;
        public PatrolPoint[] points;
    }
}
