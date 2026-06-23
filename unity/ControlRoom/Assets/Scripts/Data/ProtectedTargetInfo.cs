// ProtectedTargetInfo.cs — 보호대상(액자/작품/중요물품) POCO. office_base_map.json의 protectedTargets 1행.
// 박물관 시연 핵심 — 상태(safe/check/missing)는 시나리오에서 갱신.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class ProtectedTargetInfo
    {
        public string targetId;       // "frame_a" / "frame_b" / "vase_1"
        public string displayName;    // "액자 A" / "액자 B" / "도자기"
        public string targetType;     // "frame" / "art" / "object"
        public float x;               // 맵 좌표 (m, ROS 기준)
        public float y;
        public float theta;           // 방향 (rad)
        public string status;         // "safe" / "check" / "missing"
        public string iconName;       // IconNames 상수와 매핑
        public string lastSeenAt;     // ISO8601 timestamp 문자열 (마지막 확인 시각, 미확인 시 "")
    }

    [Serializable]
    public class ProtectedTargetInfoList
    {
        public ProtectedTargetInfo[] protectedTargets;
    }
}
