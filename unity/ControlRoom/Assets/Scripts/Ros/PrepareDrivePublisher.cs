// PrepareDrivePublisher.cs — "주행준비" 요청(OnPrepareDriveRequested)을 std_msgs/Bool로
// /<robotId>/prepare_drive 에 발행 → 로봇측 readyd.py가 ~/t1_drive_ready.sh를 1회 실행한다.
// 동시에 /<robotId>/drive_ready_status(String)를 구독해 6단계 진행상황을 관제 로그로 중계한다.
// FollowWaypointsPublisher의 형제 — 발행 경로/연결(GetOrCreateInstance)을 동일하게 따른다.
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class PrepareDrivePublisher : MonoBehaviour
    {
        ROSConnection ros;
        readonly HashSet<string> pubRegistered = new HashSet<string>();
        readonly HashSet<string> subRegistered = new HashSet<string>();

        void Start()
        {
            ros = ROSConnection.GetOrCreateInstance();
            ControlRoomEvents.OnPrepareDriveRequested += OnRequest;
            Debug.Log("[PrepareDrivePublisher] ready");
        }

        void OnRequest(string robotId)
        {
            if (string.IsNullOrEmpty(robotId)) return;

            string topic = TopicRegistry.GetPrepareDrive(robotId);
            if (string.IsNullOrEmpty(topic)) return;
            if (!pubRegistered.Contains(topic)) { ros.RegisterPublisher<BoolMsg>(topic); pubRegistered.Add(topic); }

            // 진행상황 구독은 로봇당 1회만(재요청 시 중복 구독 방지).
            string statusTopic = TopicRegistry.GetDriveReadyStatus(robotId);
            if (!string.IsNullOrEmpty(statusTopic) && !subRegistered.Contains(statusTopic))
            {
                ros.Subscribe<StringMsg>(statusTopic, OnStatus);
                subRegistered.Add(statusTopic);
            }

            ros.Publish(topic, new BoolMsg { data = true });
            ControlRoomEvents.RaiseLogAdded("drive", "INFO", $"주행준비 요청 → {robotId} ({topic})");
            Debug.Log($"[PrepareDrivePublisher] → {topic} (true)");
        }

        void OnStatus(StringMsg msg)
        {
            if (string.IsNullOrEmpty(msg.data)) return;
            string level = msg.data.Contains("FAIL") ? "WARN" : "INFO";
            ControlRoomEvents.RaiseLogAdded("drive", level, $"주행준비: {msg.data}");
        }

        void OnDestroy() => ControlRoomEvents.OnPrepareDriveRequested -= OnRequest;
    }
}
