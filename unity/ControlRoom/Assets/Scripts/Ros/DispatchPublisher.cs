// DispatchPublisher.cs — ControlRoomEvents.OnDispatchRequested 구독 → /<robotId>/goal_pose로 PoseStamped 발행.
// 로봇측 patrol_waypoints_bridge.py가 robotId별 goal_pose를 받아 Nav2 goToPose로 실행한다.
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class DispatchPublisher : MonoBehaviour
    {
        public string topicName = "";   // 비우면 TopicRegistry.GetGoalPose(robotId)
        public string frameId = "map";

        ROSConnection ros;
        readonly HashSet<string> registered = new HashSet<string>();

        void Start()
        {
            ros = ROSConnection.GetOrCreateInstance();
            ControlRoomEvents.OnDispatchRequested += OnDispatch;
            Debug.Log("[DispatchPublisher] ready");
        }

        void OnDispatch(string robotId, float x, float y, string reason)
        {
            string topic = string.IsNullOrEmpty(topicName) ? TopicRegistry.GetGoalPose(robotId) : topicName;
            if (string.IsNullOrEmpty(topic)) return;
            if (!registered.Contains(topic))
            {
                ros.RegisterPublisher<PoseStampedMsg>(topic);
                registered.Add(topic);
            }

            var msg = new PoseStampedMsg
            {
                header = new RosMessageTypes.Std.HeaderMsg { frame_id = frameId },
                pose = new PoseMsg
                {
                    position = new PointMsg(x, y, 0),
                    orientation = new QuaternionMsg(0, 0, 0, 1)
                }
            };
            ros.Publish(topic, msg);
            Debug.Log($"[DispatchPublisher] → {topic} ({x:0.00},{y:0.00}) reason={reason} robot={robotId}");
        }

        void OnDestroy() => ControlRoomEvents.OnDispatchRequested -= OnDispatch;
    }
}
