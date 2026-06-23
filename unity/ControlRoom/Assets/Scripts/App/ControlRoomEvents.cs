// ControlRoomEvents.cs — UI ↔ App ↔ Sim ↔ ROS 이벤트 라우터.
// 모든 도메인 간 통신은 본 라우터의 이벤트로만. 직접 참조 금지.
// Phase 5 진입 시 ROS subscriber/publisher도 동일 이벤트 발화/구독.
using System;

namespace URHYNIX.ControlRoom.App
{
    public static class ControlRoomEvents
    {
        // 로봇 선택 변경 (robotId)
        public static event Action<string> OnRobotChanged;
        public static void RaiseRobotChanged(string robotId) => OnRobotChanged?.Invoke(robotId);

        // 시나리오 트리거 (scenarioId: "fire" / "intruder" / "noise" / "theft")
        public static event Action<string> OnScenarioTriggered;
        public static void RaiseScenarioTriggered(string scenarioId) => OnScenarioTriggered?.Invoke(scenarioId);

        // 로그 라인 추가 (category, level, message)
        public static event Action<string, string, string> OnLogAdded;
        public static void RaiseLogAdded(string category, string level, string message) =>
            OnLogAdded?.Invoke(category, level, message);

        // 배터리 변화 (robotId, percent 0~100)
        public static event Action<string, float> OnBatteryChanged;
        public static void RaiseBatteryChanged(string robotId, float percent) =>
            OnBatteryChanged?.Invoke(robotId, percent);

        // 센서값 변화 (robotId, sensorId, value)
        public static event Action<string, string, float> OnSensorChanged;
        public static void RaiseSensorChanged(string robotId, string sensorId, float value) =>
            OnSensorChanged?.Invoke(robotId, sensorId, value);

        // 모드 변경 ("auto" / "manual" / "scan" / "turbo")
        public static event Action<string> OnModeChanged;
        public static void RaiseModeChanged(string mode) => OnModeChanged?.Invoke(mode);

        // 위험 경보 (severity: 0~3, message)
        public static event Action<int, string> OnAlert;
        public static void RaiseAlert(int severity, string message) => OnAlert?.Invoke(severity, message);

        // 맵 뷰 모드 변경 ("2d" / "3d")
        public static event Action<string> OnMapViewModeChanged;
        public static void RaiseMapViewModeChanged(string mode) => OnMapViewModeChanged?.Invoke(mode);

        // 좌표 출동 요청 (robotId, worldX, worldY, reason). 맵 우클릭 액션 → Robot/Ros가 소비.
        public static event Action<string, float, float, string> OnDispatchRequested;
        public static void RaiseDispatchRequested(string robotId, float x, float y, string reason) =>
            OnDispatchRequested?.Invoke(robotId, x, y, reason);
    }
}
