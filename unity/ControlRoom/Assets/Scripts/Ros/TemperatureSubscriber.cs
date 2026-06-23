// TemperatureSubscriber.cs — ROS2 /sensors/temp (std_msgs/Int32, PP-A017 A0 raw 0~1023) 구독 → raw 표시.
// Phase 2.8 듀얼: 인스턴스 1개당 robotId 1개 (현재 tb3_2 젠지만 결선). topicName 비우면 TopicRegistry lookup.
// arduino_bridge_quad: [TEMP] A0 raw=N → raw 정수, 1초 주기 연속 발행. °C 2점 보정은 후속(현재 raw 표시).
// NTC 특성상 raw↓ = 온도↑. 1Hz 연속 발행이라 Update()에서 disconnect-timeout 끊김 감지 유효.
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class TemperatureSubscriber : MonoBehaviour
    {
        [Header("Identity")]
        [Tooltip("robotId — \"tb3_2\" 젠지만 현재 결선. default_robots.json과 1:1.")]
        public string robotId = "tb3_2";

        [Header("ROS Topic")]
        [Tooltip("비워두면 robotId 기준으로 TopicRegistry에서 lookup")]
        public string topicName = "";

        [Header("Display")]
        [Tooltip("로그 라벨용 표시명")]
        public string displayLabel = "젠지온도";

        [Header("Disconnect detection")]
        [Tooltip("메시지 미수신 N초 후 경고 (온도는 1Hz 연속 발행)")]
        public float disconnectTimeoutSeconds = 5f;

        bool subscribed;
        bool firstMessageLogged;
        float lastMessageTime = -1f;
        bool warnedDisconnect;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.GetTemp(robotId);

            if (string.IsNullOrEmpty(topicName))
            {
                Debug.LogError($"[TemperatureSubscriber:{displayLabel}] topic resolve 실패 — robotId={robotId} 미등록");
                return;
            }

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<Int32Msg>(topicName, OnTempMsg);
            subscribed = true;

            Debug.Log($"[TemperatureSubscriber:{displayLabel}] subscribed → {topicName} (robotId={robotId})");
        }

        void Update()
        {
            if (!subscribed || lastMessageTime < 0 || warnedDisconnect) return;
            if (Time.time - lastMessageTime > disconnectTimeoutSeconds)
            {
                warnedDisconnect = true;
                ControlRoomEvents.RaiseLogAdded(
                    "sensor", "WARN",
                    $"⚠️ 온도 토픽 끊김 {disconnectTimeoutSeconds:F0}초 이상 ({displayLabel} · {topicName})"
                );
            }
        }

        void OnTempMsg(Int32Msg msg)
        {
            lastMessageTime = Time.time;

            if (warnedDisconnect)
            {
                warnedDisconnect = false;
                ControlRoomEvents.RaiseLogAdded(
                    "sensor", "INFO",
                    $"🟢 온도 토픽 복구 ({displayLabel})"
                );
            }

            int raw = msg.data;

            if (!firstMessageLogged)
            {
                firstMessageLogged = true;
                ControlRoomEvents.RaiseLogAdded(
                    "sensor", "INFO",
                    $"🌡️ 온도 결선됨 ({displayLabel} · {topicName}) — raw={raw} (보정 전)"
                );
            }

            // sensorId="temp" — SensorCardListView가 raw 텍스트로 표시 (°C 보정 후속).
            ControlRoomState.Instance.SetSensorValue(robotId, "temp", raw);
        }
    }
}
