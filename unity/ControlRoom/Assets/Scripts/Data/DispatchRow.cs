// opencode: 2026-06-29 - Supabase dispatches 테이블 1행 매핑 DTO. Coded with OpenCode; high-cost model review recommended.
// DispatchRow.cs — public.dispatches 1행 POCO. JsonUtility 파싱용.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class DispatchRow
    {
        public string id;
        public string event_id;
        public string target_robot_id;
        public double target_x;
        public double target_y;
        public string dispatched_at; // ISO 8601 timestamptz
        public string arrived_at;    // null 가능
        public string response_time; // null 가능 (numeric)
        public bool simulated;
        public string reason;
        public string nav_mode;
    }

    [Serializable]
    public class DispatchRowArray { public DispatchRow[] rows; }
}
