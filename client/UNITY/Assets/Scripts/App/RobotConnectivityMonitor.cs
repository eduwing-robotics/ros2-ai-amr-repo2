// RobotConnectivityMonitor.cs — 로봇별 신호 수신(RobotPoseFeed.OnRobotPose)을 추적해
// 마지막 신호 후 OnlineTimeout 이내면 온라인, 넘으면 오프라인으로 판정. 상태 변화 시 OnRobotConnectivity 발화.
// 로봇 전원이 꺼지면 pose가 끊겨 자동으로 오프라인 표시(RobotRoleCardView의 하드코딩 "온라인" 대체).
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.App
{
    public class RobotConnectivityMonitor : MonoBehaviour
    {
        const float OnlineTimeout = 3f;   // 마지막 신호 후 이 시간(초) 지나면 오프라인.

        static readonly Dictionary<string, float> lastSeen = new Dictionary<string, float>();
        static readonly Dictionary<string, bool> online = new Dictionary<string, bool>();

        // 선택 로봇이 바뀔 때 RobotRoleCardView가 현재 상태를 즉시 조회.
        public static bool IsOnline(string robotId) =>
            !string.IsNullOrEmpty(robotId) && online.TryGetValue(robotId, out var v) && v;

        void OnEnable() => RobotPoseFeed.OnRobotPose += OnPose;
        void OnDisable() => RobotPoseFeed.OnRobotPose -= OnPose;

        void OnPose(string robotId, float x, float y, float yaw) => lastSeen[robotId] = Time.time;

        void Update()
        {
            var robots = ControlRoomState.Instance.Robots;
            if (robots == null) return;
            foreach (var r in robots)
            {
                if (r == null || string.IsNullOrEmpty(r.robotId)) continue;
                string id = r.robotId;
                bool nowOnline = lastSeen.TryGetValue(id, out var t) && (Time.time - t) <= OnlineTimeout;
                bool was = online.TryGetValue(id, out var o) && o;
                if (nowOnline != was)
                {
                    online[id] = nowOnline;
                    ControlRoomEvents.RaiseRobotConnectivity(id, nowOnline);
                }
            }
        }

        void OnDestroy() { lastSeen.Clear(); online.Clear(); }
    }
}
