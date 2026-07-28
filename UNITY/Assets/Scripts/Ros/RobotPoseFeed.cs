// RobotPoseFeed.cs — 로봇별 /tb3_X/pose(PoseStamped, map프레임) 구독 → 로봇별 마커 이벤트.
// 듀얼로봇 런타임(네임스페이스 bringup)에서 각 로봇이 자기 pose를 발행하면 로봇별로 구분 표시한다.
// 전역 /tf(RobotPoseSubscriber)는 비-ns 단일로봇 맵제작용 fallback으로 공존한다(LiveRobots로 양보 판정).
using System;
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Map;
// 멀티 endpoint: 각 로봇 pose를 그 로봇 전용 ROSConnection(RosConnectionManager)에서 구독.
// AP isolation으로 cross-host가 막혀도 동작(각 로봇 endpoint에 Unity가 직접 TCP 연결).

namespace URHYNIX.ControlRoom.Ros
{
    public class RobotPoseFeed : MonoBehaviour
    {
        // (robotId, x, y, yaw rad) — map 프레임 기준 로봇 pose.
        public static event Action<string, float, float, float> OnRobotPose;

        // per-robot pose를 한 번이라도 받은 로봇 — 전역 /tf fallback이 양보할 대상.
        public static readonly HashSet<string> LiveRobots = new HashSet<string>();

        // (구독한 ROSConnection, topic) — robotId별로 다른 endpoint일 수 있어 함께 보관(Unsubscribe용).
        readonly List<(ROSConnection ros, string topic)> subs = new List<(ROSConnection, string)>();

        void Start()
        {
            var mgr = RosConnectionManager.GetOrCreate();
            var shared = ROSConnection.GetOrCreateInstance();   // endpointRobotId(보통 젠지)와 동일 IP면 재사용
            foreach (var r in ControlRoomState.Instance.Robots)
            {
                if (r == null || string.IsNullOrEmpty(r.robotId)) continue;
                string topic = !string.IsNullOrEmpty(r.poseTopic)
                    ? r.poseTopic : TopicRegistry.GetPose(r.robotId);
                if (string.IsNullOrEmpty(topic)) continue;

                var conn = mgr.GetForRobot(r, shared);           // 로봇 전용 endpoint(.84/.250)
                if (conn == null) continue;

                string id = r.robotId;                           // 클로저 캡처용 로컬
                conn.Subscribe<PoseStampedMsg>(topic, msg => OnPose(id, msg));
                subs.Add((conn, topic));
                Debug.Log($"[RobotPoseFeed] subscribed → {topic} ({id}) via {conn.RosIPAddress}");
            }
        }

    void OnPose(string robotId, PoseStampedMsg msg)
    {
        var p = msg.pose.position;
        var q = msg.pose.orientation;
        float yaw = MapCoordinateSystem.QuaternionToYaw(
            (float)q.x, (float)q.y, (float)q.z, (float)q.w);
        LiveRobots.Add(robotId);
        OnRobotPose?.Invoke(robotId, (float)p.x, (float)p.y, yaw);
        Debug.Log($"[RobotPoseFeed] pose received {robotId}: ({p.x:F3}, {p.y:F3}, yaw{yaw:F2})");
    }

        void OnDestroy()
        {
            foreach (var (ros, topic) in subs)
            {
                if (ros == null) continue;
                try { ros.Unsubscribe(topic); }
                catch { /* 종료 순서상 ROS 이미 정리 가능 */ }
            }
            subs.Clear();
            LiveRobots.Clear();
        }
    }
}
