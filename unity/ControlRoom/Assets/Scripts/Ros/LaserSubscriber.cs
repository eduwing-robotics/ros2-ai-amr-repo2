// LaserSubscriber.cs — ROS2 /sensors/laser (std_msgs/Bool) 구독 → 레이저 송신부 상태 로그.
// Phase 2.8 듀얼: 인스턴스 1개당 robotId 1개 (현재 tb3_2 젠지만 결선). topicName 비우면 TopicRegistry lookup.
// arduino_bridge_quad: 레이저는 PIR 종속 송신 actuator(ON/OFF=PIR). 수신부 납땜문제로 미결선 → 빔차단 감지 불가.
// → UI 카드는 "미결선" 비활성 표시가 기본. 값은 로그/디버그용으로만 보관.
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class LaserSubscriber : MonoBehaviour
    {
        [Header("Identity")]
        [Tooltip("robotId — \"tb3_2\" 젠지만 현재 결선. default_robots.json과 1:1.")]
        public string robotId = "tb3_2";

        [Header("ROS Topic")]
        [Tooltip("비워두면 robotId 기준으로 TopicRegistry에서 lookup")]
        public string topicName = "";

        [Header("Display")]
        [Tooltip("로그 라벨용 표시명")]
        public string displayLabel = "젠지레이저";

        bool subscribed;
        bool firstMessageLogged;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.GetLaser(robotId);

            if (string.IsNullOrEmpty(topicName))
            {
                Debug.LogError($"[LaserSubscriber:{displayLabel}] topic resolve 실패 — robotId={robotId} 미등록");
                return;
            }

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<BoolMsg>(topicName, OnLaserMsg);
            subscribed = true;

            Debug.Log($"[LaserSubscriber:{displayLabel}] subscribed → {topicName} (robotId={robotId})");
        }

        void OnLaserMsg(BoolMsg msg)
        {
            bool on = msg.data;

            if (!firstMessageLogged)
            {
                firstMessageLogged = true;
                ControlRoomEvents.RaiseLogAdded(
                    "sensor", "INFO",
                    $"🔦 레이저 송신부 결선됨 ({displayLabel} · {topicName}) — 수신부 미결선(빔차단 감지 불가)"
                );
            }

            // sensorId="laser" — UI는 "미결선" 비활성 고정. 값은 디버그용.
            ControlRoomState.Instance.SetSensorValue(robotId, "laser", on ? 1f : 0f);
        }
    }
}
