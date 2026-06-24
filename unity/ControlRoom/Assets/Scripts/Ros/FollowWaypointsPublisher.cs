// FollowWaypointsPublisher.cs — 순찰 경로(PatrolService)를 geometry_msgs/PoseArray로
// /<robotId>/patrol_waypoints 에 발행. ROS-TCP-Connector는 ROS2 액션을 미지원하므로,
// 로봇측 브리지(scripts/patrol_waypoints_bridge.py)가 이 PoseArray를 받아 Nav2 FollowWaypoints로 실행한다.
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Ros
{
    public class FollowWaypointsPublisher : MonoBehaviour
    {
        public string frameId = "map";

        ROSConnection ros;
        readonly HashSet<string> registered = new HashSet<string>();

        void Start()
        {
            ros = ROSConnection.GetOrCreateInstance();
            ControlRoomEvents.OnPatrolRunRequested += OnRun;
            Debug.Log("[FollowWaypointsPublisher] ready");
        }

        void OnRun(string robotId)
        {
            if (string.IsNullOrEmpty(robotId)) return;
            var pts = PatrolService.Instance.Points;
            if (pts.Count == 0)
            {
                ControlRoomEvents.RaiseLogAdded("patrol", "WARN", "순찰 시작 실패: 웨이포인트 0개");
                return;
            }

            string topic = TopicRegistry.GetPatrolWaypoints(robotId);
            if (string.IsNullOrEmpty(topic)) return;
            if (!registered.Contains(topic)) { ros.RegisterPublisher<PoseArrayMsg>(topic); registered.Add(topic); }

            var poses = new PoseMsg[pts.Count];
            for (int i = 0; i < pts.Count; i++)
            {
                float qz = Mathf.Sin(pts[i].theta * 0.5f);
                float qw = Mathf.Cos(pts[i].theta * 0.5f);
                poses[i] = new PoseMsg
                {
                    position = new PointMsg(pts[i].x, pts[i].y, 0),
                    orientation = new QuaternionMsg(0, 0, qz, qw)
                };
            }
            var msg = new PoseArrayMsg
            {
                header = new RosMessageTypes.Std.HeaderMsg { frame_id = frameId },
                poses = poses
            };
            ros.Publish(topic, msg);
            ControlRoomEvents.RaiseLogAdded("patrol", "INFO",
                $"순찰 시작: {robotId} ← {pts.Count}개 지점 → {topic}");
            Debug.Log($"[FollowWaypointsPublisher] → {topic} ({pts.Count} poses)");
        }

        void OnDestroy() => ControlRoomEvents.OnPatrolRunRequested -= OnRun;
    }
}
