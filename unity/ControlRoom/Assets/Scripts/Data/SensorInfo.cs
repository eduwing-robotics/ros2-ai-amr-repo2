// SensorInfo.cs — 센서 메타 정보 POCO. default_sensors.json 1행과 1:1 매핑.
// 외부 의존 없는 순수 데이터. JSON 직렬화 친화 (JsonUtility).
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class SensorInfo
    {
        public string sensorId;          // "pir" / "sound" / "temp" / "laser" (as-built 4센서, 2026-06-18)
        public string displayName;       // "인체감지" / "소음" / "온도" / "레이저"
        public string sensorType;        // "analog" / "digital" / "boolean"
        public string unit;              // "" / "swing" / "raw" / ""
        public string topicName;         // 예: "/sensors/temp" (root namespace, arduino_bridge_quad.py 발행)
        public float warningThreshold;   // 경고 임계값 (sensorType=boolean이면 0/1, sound는 swing 60)
        public string iconName;          // IconNames 상수와 매핑
        public string robotId;           // 어느 로봇 소속인지 ("tb3_1" / "tb3_2")
    }

    [Serializable]
    public class SensorInfoList
    {
        public SensorInfo[] sensors;
    }
}
