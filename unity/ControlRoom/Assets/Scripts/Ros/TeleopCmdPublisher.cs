// TeleopCmdPublisher.cs — 수동 조종 D-pad 명령(OnTeleopCmd)을 geometry_msgs/TwistStamped로
// /<robotId>/cmd_vel 에 발행. TurtleBot3 HW가 Nav2 비경유로 직접 구동.
// ⚠ TwistStamped 사용(TurtleBot3 Jazzy 실기. CONTRACT.md의 Twist 표기는 드리프트 — UI-WIRING-CONTRACT 참조).
// FollowWaypointsPublisher와 동일 패턴(이벤트 구독 → robotId별 토픽 RegisterPublisher 1회 → Publish).
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Geometry;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class TeleopCmdPublisher : MonoBehaviour
    {
        ROSConnection ros;
        readonly HashSet<string> registered = new HashSet<string>();

        void Start()
        {
            ros = ROSConnection.GetOrCreateInstance();
            ControlRoomEvents.OnTeleopCmd += OnCmd;
            Debug.Log("[TeleopCmdPublisher] ready");
        }

        // linear m/s, angular rad/s. 뗄 때는 (0,0,false)로 정지 명령이 그대로 발행됨.
        void OnCmd(string robotId, float linear, float angular, bool isPressed)
        {
            string topic = TopicRegistry.GetCmdVel(robotId);
            if (string.IsNullOrEmpty(topic)) return;
            if (!registered.Contains(topic)) { ros.RegisterPublisher<TwistStampedMsg>(topic); registered.Add(topic); }

            var msg = new TwistStampedMsg
            {
                header = new RosMessageTypes.Std.HeaderMsg { frame_id = "" },
                twist = new TwistMsg
                {
                    linear = new Vector3Msg(linear, 0, 0),
                    angular = new Vector3Msg(0, 0, angular)
                }
            };
            ros.Publish(topic, msg);
        }

        void OnDestroy() => ControlRoomEvents.OnTeleopCmd -= OnCmd;
    }
}
