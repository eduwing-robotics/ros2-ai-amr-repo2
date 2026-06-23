// SoundSubscriber.cs — ROS2 /sensors/sound (std_msgs/Int32, AO swing 0~) 구독 → 소음 swing 표시.
// Phase 2.8 듀얼: 인스턴스 1개당 robotId 1개 (현재 tb3_2 젠지만 결선). topicName 비우면 TopicRegistry lookup.
// arduino_bridge_quad: [SOUND] DETECTED/quiet (swing=N) → swing 정수. 임계 60. 상태 전이 시에만 발행(latching X).
// 함정: 조용하면 메시지 안 옴 — Unity Start 직후 UI는 기본 상태 유지. disconnect-timeout 없음(전이 발행).
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Std;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class SoundSubscriber : MonoBehaviour
    {
        [Header("Identity")]
        [Tooltip("robotId — \"tb3_2\" 젠지만 현재 결선. default_robots.json과 1:1.")]
        public string robotId = "tb3_2";

        [Header("ROS Topic")]
        [Tooltip("비워두면 robotId 기준으로 TopicRegistry에서 lookup")]
        public string topicName = "";

        [Header("Display")]
        [Tooltip("로그 라벨용 표시명")]
        public string displayLabel = "젠지소음";

        [Header("감지 임계 (swing)")]
        [Tooltip("이 swing 이상이면 소음 감지 (펌웨어 SOUND_TH=60)")]
        public int soundThreshold = 60;

        bool subscribed;
        bool firstMessageLogged;
        bool lastDetected;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.GetSound(robotId);

            if (string.IsNullOrEmpty(topicName))
            {
                Debug.LogError($"[SoundSubscriber:{displayLabel}] topic resolve 실패 — robotId={robotId} 미등록");
                return;
            }

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<Int32Msg>(topicName, OnSoundMsg);
            subscribed = true;

            Debug.Log($"[SoundSubscriber:{displayLabel}] subscribed → {topicName} (robotId={robotId})");
        }

        void OnSoundMsg(Int32Msg msg)
        {
            int swing = msg.data;
            bool detected = swing >= soundThreshold;

            if (!firstMessageLogged)
            {
                firstMessageLogged = true;
                ControlRoomEvents.RaiseLogAdded(
                    "sensor", "INFO",
                    $"🔊 소음 결선됨 ({displayLabel} · {topicName}) — 첫 swing={swing} {(detected ? "감지!" : "조용")}"
                );
            }
            else if (detected != lastDetected)
            {
                ControlRoomEvents.RaiseLogAdded(
                    "sensor",
                    detected ? "WARN" : "INFO",
                    detected
                        ? $"🔊 소음 감지! ({displayLabel} · swing={swing})"
                        : $"🟢 소음 정상 복귀 ({displayLabel})"
                );
            }

            lastDetected = detected;

            // sensorId="sound" — SensorCardListView가 swing 값 + 임계 색 토글.
            ControlRoomState.Instance.SetSensorValue(robotId, "sound", swing);
        }
    }
}
