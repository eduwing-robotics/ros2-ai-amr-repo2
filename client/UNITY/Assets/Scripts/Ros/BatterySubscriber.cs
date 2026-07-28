// BatterySubscriber.cs — ROS2 BatteryState 구독 → voltage 기반 % 환산 → OnBatteryChanged 발화.
// Phase 2.7 듀얼: 인스턴스 1개당 robotId 1개 (tb3_1 티원 / tb3_2 젠지). topicName 비우면 TopicRegistry lookup.
// 함정: TurtleBot3 OpenCR 펌웨어가 percentage 필드를 잘못 채움(예: 117%) → voltage 선형 변환 사용.
// LiPo 3S 매핑: 12.6V=100% / 10.5V=0% (보수적, cutoff 직전 안전 마진).
// 끊김 감지 3중: (1) 토픽 timeout(기본 5초), (2) present=false, (3) voltage<5V 비정상.
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class BatterySubscriber : MonoBehaviour
    {
        [Header("Identity")]
        [Tooltip("robotId — \"tb3_1\" 티원 / \"tb3_2\" 젠지. default_robots.json과 1:1.")]
        public string robotId = "tb3_1";

        [Header("ROS Topic")]
        [Tooltip("비워두면 robotId 기준으로 TopicRegistry에서 lookup")]
        public string topicName = "";

        [Header("Display")]
        [Tooltip("로그 라벨용 표시명")]
        public string displayLabel = "티원";

        [Header("LiPo voltage range (V)")]
        [Tooltip("0% 기준 전압 (cutoff 직전 안전 마진)")]
        public float voltageEmpty = 10.5f;
        [Tooltip("100% 기준 전압 (만충)")]
        public float voltageFull  = 12.6f;

        [Header("Disconnect detection")]
        [Tooltip("메시지 미수신 N초 후 경고")]
        public float disconnectTimeoutSeconds = 5f;
        [Tooltip("OpenCR 펌웨어 비정상 하한")]
        public float voltageMinValid = 5.0f;

        bool subscribed;
        bool firstMessageLogged;
        float lastMessageTime = -1f;
        bool warnedDisconnect;
        bool warnedAbnormal;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.GetBatteryState(robotId);

            if (string.IsNullOrEmpty(topicName))
            {
                Debug.LogError($"[BatterySubscriber:{displayLabel}] topic resolve 실패 — robotId={robotId} 미등록");
                return;
            }

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<BatteryStateMsg>(topicName, OnBatteryMsg);
            subscribed = true;

            Debug.Log($"[BatterySubscriber:{displayLabel}] subscribed → {topicName} (robotId={robotId})");
        }

        void Update()
        {
            if (!subscribed || lastMessageTime < 0 || warnedDisconnect) return;
            if (Time.time - lastMessageTime > disconnectTimeoutSeconds)
            {
                warnedDisconnect = true;
                ControlRoomEvents.RaiseLogAdded(
                    "battery", "WARN",
                    $"⚠️ 배터리 토픽 끊김 {disconnectTimeoutSeconds:F0}초 이상 ({displayLabel} · {topicName})"
                );
            }
        }

        void OnBatteryMsg(BatteryStateMsg msg)
        {
            lastMessageTime = Time.time;

            if (warnedDisconnect)
            {
                warnedDisconnect = false;
                ControlRoomEvents.RaiseLogAdded(
                    "battery", "INFO",
                    $"🟢 배터리 토픽 복구 ({displayLabel})"
                );
            }

            float voltage = msg.voltage;
            bool present = msg.present;
            bool voltageBad = voltage < voltageMinValid;
            bool abnormal = !present || voltageBad;

            if (abnormal)
            {
                if (!warnedAbnormal)
                {
                    warnedAbnormal = true;
                    string why = !present
                        ? "present=false (배터리 분리)"
                        : $"voltage={voltage:F2}V 비정상";
                    ControlRoomEvents.RaiseLogAdded("battery", "WARN",
                        $"⚠️ 배터리 비정상 ({displayLabel}) — {why}");
                }
                return;
            }

            if (warnedAbnormal)
            {
                warnedAbnormal = false;
                ControlRoomEvents.RaiseLogAdded("battery", "INFO",
                    $"🟢 배터리 정상 회복 ({displayLabel}) — {voltage:F2}V");
            }

            float range = voltageFull - voltageEmpty;
            float pct = range > 0.01f
                ? Mathf.Clamp01((voltage - voltageEmpty) / range) * 100f
                : 0f;

            if (!firstMessageLogged)
            {
                firstMessageLogged = true;
                ControlRoomEvents.RaiseLogAdded(
                    "battery",
                    "INFO",
                    $"🔋 배터리 결선됨 ({displayLabel} · {topicName}) — {voltage:F2}V → {pct:F1}%"
                );
            }

            ControlRoomEvents.RaiseBatteryChanged(robotId, pct);
            ControlRoomState.Instance.SetSensorValue(robotId, "battery", pct);
        }
    }
}
