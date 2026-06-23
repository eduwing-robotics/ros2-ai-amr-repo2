// ControlRoomState.cs — 전역 싱글톤 상태. 선택 로봇/모드/세션/배터리/센서 last value.
// 변경은 setter 통해서만. 변경 시 ControlRoomEvents 발화.
// View는 본 state를 read-only로 참조 + 이벤트 구독.
using System.Collections.Generic;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.App
{
    public class ControlRoomState
    {
        public static ControlRoomState Instance { get; } = new ControlRoomState();
        private ControlRoomState() { }

        // 로봇 목록 (default_robots.json에서 로드)
        public List<RobotInfo> Robots { get; } = new List<RobotInfo>();

        // 현재 선택된 로봇 ID
        public string SelectedRobotId { get; private set; } = "tb3_1";
        public void SelectRobot(string robotId)
        {
            if (SelectedRobotId == robotId) return;
            SelectedRobotId = robotId;
            ControlRoomEvents.RaiseRobotChanged(robotId);
        }

        public RobotInfo GetSelectedRobot()
        {
            return Robots.Find(r => r.robotId == SelectedRobotId);
        }

        // 모드: auto / manual / scan / turbo
        public string Mode { get; private set; } = "auto";
        public void SetMode(string mode)
        {
            if (Mode == mode) return;
            Mode = mode;
            ControlRoomEvents.RaiseModeChanged(mode);
        }

        // 맵 뷰 모드: 2d / 3d
        public string MapViewMode { get; private set; } = "2d";
        public void SetMapViewMode(string mode)
        {
            if (MapViewMode == mode) return;
            MapViewMode = mode;
            ControlRoomEvents.RaiseMapViewModeChanged(mode);
        }

        // 세션 UUID (Supabase session_meta FK)
        public string SessionId { get; set; }

        // 배터리/센서 last value (robotId → sensorId → value)
        public Dictionary<string, Dictionary<string, float>> LastSensorValues { get; }
            = new Dictionary<string, Dictionary<string, float>>();

        public void SetSensorValue(string robotId, string sensorId, float value)
        {
            if (!LastSensorValues.TryGetValue(robotId, out var dict))
            {
                dict = new Dictionary<string, float>();
                LastSensorValues[robotId] = dict;
            }
            dict[sensorId] = value;
            ControlRoomEvents.RaiseSensorChanged(robotId, sensorId, value);
        }
    }
}
