// RobotPoseEntry.cs — 시계열 로봇 pose 1건. Supabase `pose_logs` 1행과 1:1 매핑.
// SSOT: docs/ref/SCHEMA.md "Planned Extensions (SCRUM-23) pose_logs" 정본 컬럼 따름.
// 외부 의존 없는 순수 POCO — Vector2/3은 의도적으로 안 씀(직렬화 친화).
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class RobotPoseEntry
    {
        public string id;             // UUID PK
        public string session_id;     // UUID FK → session_meta
        public string robot_id;       // "tb3_1" (티원) / "tb3_2" (젠지)
        public DateTime ts;           // UTC 기록 시각
        public double x;              // meters
        public double y;              // meters
        public double theta;          // radians (yaw)
        public string source_topic;   // 예: "/tb3_1/pose"
        public string nav_mode;       // "patrol" / "dispatch" / "lidar_boost" / "manual"
    }
}
