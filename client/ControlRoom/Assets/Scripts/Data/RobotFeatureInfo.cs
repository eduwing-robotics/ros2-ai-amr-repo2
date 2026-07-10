// RobotFeatureInfo.cs — 로봇 기능 토글 메타 POCO. default_features.json 1행과 1:1 매핑.
// 자율주행/SLAM/스캔/가속/카메라 같은 켜고 끌 수 있는 기능 정의.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class RobotFeatureInfo
    {
        public string featureId;       // "scan_360" / "boost" / "slam" / "camera_feed"
        public string displayName;     // "360° 스캔" / "가속" / "SLAM" / "카메라"
        public bool isActive;          // 초기 활성 여부 (JSON 기본값, 런타임 토글 가능)
        public string commandTopic;    // 예: "/tb3_1/feature/scan_360" (Phase 5에서 사용)
        public string iconName;        // IconNames 상수와 매핑
        public string robotId;         // 어느 로봇 소속인지 (""이면 전체 로봇 공통)
    }

    [Serializable]
    public class RobotFeatureInfoList
    {
        public RobotFeatureInfo[] features;
    }
}
