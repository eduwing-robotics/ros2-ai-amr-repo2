// opencode: 2026-06-29 - Supabase events 테이블 1행 매핑 DTO. Coded with OpenCode; high-cost model review recommended.
// EventRow.cs — public.events 1행 POCO. JsonUtility 파싱용.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class EventRow
    {
        public string id;
        public string session_id;
        public string robot_id;
        public string ts;          // ISO 8601 timestamptz
        public string event_type;  // dark / pir / noise / fire
        public int severity;       // 0~3
        public double x;
        public double y;
        public double theta;
        // raw_payload(JSONB)는 현재 조회에서 제외(JsonUtility 객체→string 파싱 불가). 필요 시 jsonb 전용 조회로 채운다.
        public string raw_payload;
    }

    [Serializable]
    public class EventRowArray { public EventRow[] rows; }
}
