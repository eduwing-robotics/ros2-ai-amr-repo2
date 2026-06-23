// RobotInfo.cs — 로봇 메타 정보 POCO. default_robots.json 1행과 1:1 매핑.
// Unity/ROS API 의존 없이 순수 데이터만. JSON 직렬화 친화.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class RobotInfo
    {
        public string robotId;        // "tb3_1" / "tb3_2"
        public string displayName;    // "티원" / "젠지"
        public string role;           // "vision" / "sensor"
        public string model;          // "TurtleBot3 Burger"
        public string hostAddress;    // mDNS 또는 IP (예: "urhynix-robot.local", "t1@192.168.0.250")
        public string cameraTopic;    // 예: "/tb3_1/camera/color/image_raw/compressed"
        public string poseTopic;      // 예: "/tb3_1/pose"
        public string iconName;       // IconNames.TurtlebotBadge 등
    }

    [Serializable]
    public class RobotInfoList
    {
        public RobotInfo[] robots;
    }
}
