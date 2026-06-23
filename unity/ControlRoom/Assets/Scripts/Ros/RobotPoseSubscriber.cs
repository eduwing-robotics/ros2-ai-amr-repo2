// RobotPoseSubscriber.cs — /tf(TFMessage) 구독 → map 프레임 기준 로봇 pose(x,y,yaw) 산출.
// tf 트리를 누적해 target(base_footprint)부터 root(map)까지 체인을 합성한다(cartographer map→odom 보정 반영).
// CameraStreamSubscriber/MapSubscriber와 동일 패턴 — MonoBehaviour + static 이벤트.
using System;
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Tf2;
using URHYNIX.ControlRoom.Map;

namespace URHYNIX.ControlRoom.Ros
{
    public class RobotPoseSubscriber : MonoBehaviour
    {
        [Header("ROS / Frames")]
        public string topicName = "";          // 비우면 TopicRegistry.Tf
        public string rootFrame = "map";
        public string[] targetFrames = { "base_footprint", "base_link" };

        // (x, y, yaw rad) — map 프레임 기준 로봇 pose.
        public static event Action<float, float, float> OnPoseUpdated;
        public static bool HasPose { get; private set; }
        public static float X { get; private set; }
        public static float Y { get; private set; }
        public static float Yaw { get; private set; }

        // child_frame_id → (parent, x, y, yaw) : child의 parent프레임 pose
        readonly Dictionary<string, (string parent, float x, float y, float yaw)> tf
            = new Dictionary<string, (string, float, float, float)>();

        bool subscribed;
        bool firstLogged;

        void Start()
        {
            if (string.IsNullOrEmpty(topicName)) topicName = TopicRegistry.Tf;
            ROSConnection.GetOrCreateInstance().Subscribe<TFMessageMsg>(topicName, OnTf);
            subscribed = true;
            Debug.Log($"[RobotPoseSubscriber] subscribed → {topicName} (root={rootFrame})");
        }

        void OnTf(TFMessageMsg msg)
        {
            if (msg.transforms == null) return;
            foreach (var t in msg.transforms)
            {
                var tr = t.transform.translation;
                var q = t.transform.rotation;
                float yaw = MapCoordinateSystem.QuaternionToYaw(
                    (float)q.x, (float)q.y, (float)q.z, (float)q.w);
                tf[t.child_frame_id] = (t.header.frame_id, (float)tr.x, (float)tr.y, yaw);
            }

            foreach (var target in targetFrames)
                if (TryResolve(target, out float x, out float y, out float yw))
                {
                    X = x; Y = y; Yaw = yw; HasPose = true;
                    if (!firstLogged) { firstLogged = true; Debug.Log($"[RobotPoseSubscriber] 🟢 first pose {x:0.00},{y:0.00} yaw{yw:0.00}"); }
                    OnPoseUpdated?.Invoke(x, y, yw);
                    return;
                }
        }

        // target → root 체인을 합성. 체인이 root까지 닿으면 true.
        bool TryResolve(string target, out float x, out float y, out float yaw)
        {
            x = y = yaw = 0f;
            string cur = target;
            int guard = 0;
            while (cur != rootFrame && tf.TryGetValue(cur, out var e) && guard++ < 32)
            {
                (x, y, yaw) = MapCoordinateSystem.ComposePose(e.x, e.y, e.yaw, x, y, yaw);
                cur = e.parent;
            }
            return cur == rootFrame;
        }

        void OnDestroy()
        {
            if (subscribed)
            {
                try { ROSConnection.GetOrCreateInstance().Unsubscribe(topicName); }
                catch { /* 종료 순서상 ROS 이미 정리 가능 */ }
            }
        }
    }
}
