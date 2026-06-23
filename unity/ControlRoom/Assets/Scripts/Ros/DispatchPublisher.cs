// DispatchPublisher.cs — ControlRoomEvents.OnDispatchRequested 구독 → /goal_pose(Nav2)로 PoseStamped 발행.
// Nav2 미가동 시에도 발행은 무해(로봇이 받으면 자율주행 목표). map 프레임 좌표로 보낸다.
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class DispatchPublisher : MonoBehaviour
    {
        public string topicName = "";   // 비우면 TopicRegistry.GoalPose
        public string frameId = "map";

        ROSConnection ros;
        bool registered;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName)) topicName = TopicRegistry.GoalPose;
            ros = ROSConnection.GetOrCreateInstance();
            ros.RegisterPublisher<PoseStampedMsg>(topicName);
            registered = true;
            ControlRoomEvents.OnDispatchRequested += OnDispatch;
            Debug.Log($"[DispatchPublisher] ready → {topicName}");
        }

        void OnDispatch(string robotId, float x, float y, string reason)
        {
            if (!registered) return;
            var msg = new PoseStampedMsg
            {
                header = new RosMessageTypes.Std.HeaderMsg { frame_id = frameId },
                pose = new PoseMsg
                {
                    position = new PointMsg(x, y, 0),
                    orientation = new QuaternionMsg(0, 0, 0, 1)
                }
            };
            ros.Publish(topicName, msg);
            Debug.Log($"[DispatchPublisher] → {topicName} ({x:0.00},{y:0.00}) reason={reason} robot={robotId}");
        }

        void OnDestroy() => ControlRoomEvents.OnDispatchRequested -= OnDispatch;
    }
}
