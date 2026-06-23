// CameraStreamSubscriber.cs — ROS2 CompressedImage 토픽 구독 → JPEG decode → 정적 이벤트로 Texture + robotId 전달.
// Phase 2.7 듀얼: 인스턴스 1개당 robotId 1개 (tb3_1 티원 / tb3_2 젠지). topicName 비우면 TopicRegistry에서 lookup.
// View 측은 OnFrameUpdated 이벤트만 구독 — robotId로 필터링해서 활성 패널만 갱신.
using System;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Ros
{
    public class CameraStreamSubscriber : MonoBehaviour
    {
        [Header("Identity")]
        [Tooltip("robotId — \"tb3_1\" 티원 / \"tb3_2\" 젠지. default_robots.json과 1:1.")]
        public string robotId = "tb3_2";

        [Header("ROS Topic")]
        [Tooltip("비워두면 robotId 기준으로 TopicRegistry에서 lookup")]
        public string topicName = "";

        [Header("Display")]
        [Tooltip("로그/UI 라벨에 표시할 이름")]
        public string displayLabel = "젠지";

        // View가 구독하는 정적 이벤트. (robotId, currentFrame, hz)
        public static event Action<string, Texture2D, float> OnFrameUpdated;

        Texture2D streamTexture;
        int frameCount;
        float lastHzCheck;
        float currentHz;
        bool subscribed;
        bool firstFrameLogged;

        void Start()
        {
            streamTexture = new Texture2D(2, 2, TextureFormat.RGB24, false);

            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.GetCameraCompressed(robotId);

            if (string.IsNullOrEmpty(topicName))
            {
                Debug.LogError($"[CameraStreamSubscriber:{displayLabel}] topic resolve 실패 — robotId={robotId} 미등록");
                return;
            }

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<CompressedImageMsg>(topicName, OnImageReceived);
            subscribed = true;
            lastHzCheck = Time.time;

            Debug.Log($"[CameraStreamSubscriber:{displayLabel}] subscribed → {topicName} (robotId={robotId})");
        }

        void OnImageReceived(CompressedImageMsg msg)
        {
            if (streamTexture == null) return;
            if (streamTexture.LoadImage(msg.data))
            {
                frameCount++;
                if (!firstFrameLogged)
                {
                    firstFrameLogged = true;
                    ControlRoomEvents.RaiseLogAdded(
                        "camera",
                        "INFO",
                        $"🟢 Pi Camera 연결됨 ({displayLabel} · {topicName})"
                    );
                }
                OnFrameUpdated?.Invoke(robotId, streamTexture, currentHz);
            }
        }

        void Update()
        {
            if (!subscribed) return;
            float dt = Time.time - lastHzCheck;
            if (dt >= 1.0f)
            {
                currentHz = frameCount / dt;
                frameCount = 0;
                lastHzCheck = Time.time;
            }
        }

        void OnDestroy()
        {
            if (streamTexture != null) Destroy(streamTexture);
        }
    }
}
