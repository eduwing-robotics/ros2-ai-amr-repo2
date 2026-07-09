// PrepareDrivePublisher.cs — 주행준비/재시딩 트리거를 std_msgs/Bool로 발행하는 관제측 발행기.
//   OnPrepareDriveRequested → /<robotId>/prepare_drive → 로봇 readyd가 ~/t1_drive_ready.sh(6단계) 실행.
//   OnReseedRequested       → /<robotId>/reseed        → 로봇 readyd가 ~/_dock_reseed.sh(충전독 재시딩) 실행.
// 두 요청 모두 /<robotId>/drive_ready_status(String)를 구독해 진행상황을 관제 로그로 중계한다(상태 토픽 공유).
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
            ControlRoomEvents.OnPrepareDriveRequested += OnPrepare;
            ControlRoomEvents.OnReseedRequested += OnReseed;
            Debug.Log("[PrepareDrivePublisher] ready");
        }

        void OnPrepare(string robotId) => Trigger(robotId, TopicRegistry.GetPrepareDrive(robotId), "주행준비");
        void OnReseed(string robotId)  => Trigger(robotId, TopicRegistry.GetReseed(robotId), "충전독 재시딩");

        void Trigger(string robotId, string topic, string label)
        {
            if (string.IsNullOrEmpty(robotId) || string.IsNullOrEmpty(topic)) return;
            if (!pubRegistered.Contains(topic)) { ros.RegisterPublisher<BoolMsg>(topic); pubRegistered.Add(topic); }
            EnsureStatusSub(robotId);
            ros.Publish(topic, new BoolMsg { data = true });
            ControlRoomEvents.RaiseLogAdded("drive", "INFO", $"{label} 요청 → {robotId} ({topic})");
            Debug.Log($"[PrepareDrivePublisher] → {topic} (true)");
        }

        // drive_ready_status 구독은 로봇당 1회만(재요청 시 중복 구독 방지). 주행준비/재시딩 공용.
        void EnsureStatusSub(string robotId)
        {
            string statusTopic = TopicRegistry.GetDriveReadyStatus(robotId);
            if (!string.IsNullOrEmpty(statusTopic) && !subRegistered.Contains(statusTopic))
            {
                ros.Subscribe<StringMsg>(statusTopic, OnStatus);
                subRegistered.Add(statusTopic);
            }
        }

        // readyd 메시지는 자체 설명적("시작: …", "DRIVE-READY: PASS", "FAIL: …")이라 그대로 로그.
        void OnStatus(StringMsg msg)
        {
            if (string.IsNullOrEmpty(msg.data)) return;
            string level = msg.data.Contains("FAIL") ? "WARN" : "INFO";
            ControlRoomEvents.RaiseLogAdded("drive", level, msg.data);
        }

        void OnDestroy()
        {
            ControlRoomEvents.OnPrepareDriveRequested -= OnPrepare;
            ControlRoomEvents.OnReseedRequested -= OnReseed;
        }
    }
}
