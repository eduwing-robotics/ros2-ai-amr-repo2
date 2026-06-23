// PirSubscriber.cs — ROS2 /sensors/pir (std_msgs/Bool) 구독 → 감지!/정상 토글.
// Phase 2.8 듀얼: 인스턴스 1개당 robotId 1개 (현재 tb3_2 젠지만 결선). topicName 비우면 TopicRegistry lookup.
// arduino_bridge: [MOTION] → Bool true / [CLEAR] → Bool false. 변화 시에만 발행(latching X).
// 함정: 가만히 있으면 메시지 안 옴 — Unity Start 직후 UI는 "정상" 기본 상태 유지.
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class PirSubscriber : MonoBehaviour
    {
        [Header("Identity")]
        [Tooltip("robotId — \"tb3_2\" 젠지만 현재 결선. default_robots.json과 1:1.")]
        public string robotId = "tb3_2";

        [Header("ROS Topic")]
        [Tooltip("비워두면 robotId 기준으로 TopicRegistry에서 lookup")]
        public string topicName = "";

        [Header("Display")]
        [Tooltip("로그 라벨용 표시명")]
        public string displayLabel = "젠지PIR";

        bool subscribed;
        bool firstMessageLogged;
        bool lastState;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.GetPirState(robotId);

            if (string.IsNullOrEmpty(topicName))
            {
                Debug.LogError($"[PirSubscriber:{displayLabel}] topic resolve 실패 — robotId={robotId} 미등록");
                return;
            }

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<BoolMsg>(topicName, OnPirMsg);
            subscribed = true;

            Debug.Log($"[PirSubscriber:{displayLabel}] subscribed → {topicName} (robotId={robotId})");
        }

        void OnPirMsg(BoolMsg msg)
        {
            bool detected = msg.data;

            if (!firstMessageLogged)
            {
                firstMessageLogged = true;
                ControlRoomEvents.RaiseLogAdded(
                    "sensor",
                    "INFO",
                    $"🚨 PIR 결선됨 ({displayLabel} · {topicName}) — 첫 상태 {(detected ? "감지!" : "정상")}"
                );
            }
            else if (detected != lastState)
            {
                ControlRoomEvents.RaiseLogAdded(
                    "sensor",
                    detected ? "WARN" : "INFO",
                    detected
                        ? $"🚨 PIR 감지! ({displayLabel})"
                        : $"🟢 PIR 정상 복귀 ({displayLabel})"
                );
            }

            lastState = detected;

            // sensorId="pir" — SensorCardListView가 pir 케이스로 감지!/정상 + USS 색 토글.
            ControlRoomState.Instance.SetSensorValue(robotId, "pir", detected ? 1f : 0f);
        }
    }
}
