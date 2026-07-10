// opencode: 2026-06-29 - Supabase logs 테이블 1행 매핑 DTO. Coded with OpenCode; high-cost model review recommended.
// LogRow.cs — public.logs 1행 POCO. JsonUtility 파싱용.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class LogRow
    {
        public string id;
        public string session_id;
        public string ts;       // ISO 8601 timestamptz
        public string level;    // INFO / WARN / ERROR
        public string category; // system / dispatch / sensor / gemma / audit / ...
        public string message;
        public string source;   // ControlRoom / RobotPC
    }

    [Serializable]
    public class LogRowArray { public LogRow[] rows; }
}
