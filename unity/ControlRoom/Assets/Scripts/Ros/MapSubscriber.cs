// MapSubscriber.cs — ROS2 nav_msgs/OccupancyGrid(/map) 구독 → Texture2D 변환 → 정적 이벤트로 전달.
// 2026-06-16 라이브 맵뷰(경로 B): SLAM cartographer가 발행하는 /map을 ControlRoom MapPanel에 1:1 렌더.
// 셀값 규약: -1 unknown(회색) / 0 free(흰색) / 100 occupied(검정). 맵 크기 변하면 텍스처 재생성.
// CameraStreamSubscriber와 동일 패턴 — MonoBehaviour 1개 + static 이벤트, View는 이벤트만 구독.
using System;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Nav;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Map;

namespace URHYNIX.ControlRoom.Ros
{
    public class MapSubscriber : MonoBehaviour
    {
        [Header("ROS Topic")]
        [Tooltip("비워두면 TopicRegistry.Map(/map) 사용")]
        public string topicName = "";

        [Header("Display")]
        public string displayLabel = "SLAM 맵";

        // View가 구독하는 정적 이벤트. (tex, widthCells, heightCells, res m/cell, originX, originY, originYaw)
        public static event Action<Texture2D, int, int, float, float, float, float> OnMapUpdated;

        // 가장 최근 텍스처/메타 — 늦게 붙는 View가 즉시 그릴 수 있게 보관.
        public static Texture2D LatestMap { get; private set; }
        public static int LatestWidth { get; private set; }
        public static int LatestHeight { get; private set; }
        public static float LatestResolution { get; private set; }
        public static float LatestOriginX { get; private set; }
        public static float LatestOriginY { get; private set; }
        public static float LatestOriginYaw { get; private set; }

        Texture2D mapTexture;
        bool subscribed;
        bool firstMapLogged;
        Color32[] pixels;

        // 셀값 → 색 (Color32). unknown은 반투명 회색으로 배경과 구분.
        static readonly Color32 ColFree     = new Color32(235, 238, 242, 255); // 빈 공간
        static readonly Color32 ColOccupied = new Color32(20, 24, 30, 255);    // 벽/장애물
        static readonly Color32 ColUnknown  = new Color32(60, 66, 76, 120);    // 미관측

        void Start()
        {
            if (string.IsNullOrEmpty(topicName))
                topicName = TopicRegistry.Map;

            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<OccupancyGridMsg>(topicName, OnMapReceived);
            subscribed = true;

            Debug.Log($"[MapSubscriber:{displayLabel}] subscribed → {topicName}");
        }

        void OnMapReceived(OccupancyGridMsg msg)
        {
            int w = (int)msg.info.width;
            int h = (int)msg.info.height;
            if (w <= 0 || h <= 0) return;

            // 맵 크기 변화 시(또는 최초) 텍스처/버퍼 재생성.
            if (mapTexture == null || mapTexture.width != w || mapTexture.height != h)
            {
                if (mapTexture != null) Destroy(mapTexture);
                mapTexture = new Texture2D(w, h, TextureFormat.RGBA32, false)
                {
                    filterMode = FilterMode.Point,   // 셀 경계 또렷하게
                    wrapMode = TextureWrapMode.Clamp
                };
                pixels = new Color32[w * h];
            }

            var data = msg.data; // sbyte[] row-major, 원점=좌하단(ROS). Texture2D y=0도 하단 → 그대로 매핑.
            int n = Math.Min(data.Length, w * h);
            for (int i = 0; i < n; i++)
            {
                sbyte v = data[i];
                pixels[i] = v < 0 ? ColUnknown : (v >= 65 ? ColOccupied : ColFree);
            }

            mapTexture.SetPixels32(pixels);
            mapTexture.Apply(false);

            var o = msg.info.origin;
            float ox = (float)o.position.x;
            float oy = (float)o.position.y;
            float oyaw = MapCoordinateSystem.QuaternionToYaw(
                (float)o.orientation.x, (float)o.orientation.y,
                (float)o.orientation.z, (float)o.orientation.w);

            LatestMap = mapTexture;
            LatestWidth = w;
            LatestHeight = h;
            LatestResolution = msg.info.resolution;
            LatestOriginX = ox;
            LatestOriginY = oy;
            LatestOriginYaw = oyaw;

            if (!firstMapLogged)
            {
                firstMapLogged = true;
                Debug.Log($"[MapSubscriber:{displayLabel}] 🟢 first /map frame {w}×{h} @ {msg.info.resolution:0.###}m");
                ControlRoomEvents.RaiseLogAdded(
                    "map", "INFO",
                    $"🟢 SLAM 맵 수신 시작 ({displayLabel} · {topicName} · {w}×{h} @ {msg.info.resolution:0.###}m)"
                );
            }

            OnMapUpdated?.Invoke(mapTexture, w, h, msg.info.resolution, ox, oy, oyaw);
        }

        void OnDestroy()
        {
            if (subscribed)
            {
                try { ROSConnection.GetOrCreateInstance().Unsubscribe(topicName); }
                catch { /* 종료 순서상 ROS 이미 정리됐을 수 있음 */ }
            }
            if (mapTexture != null) Destroy(mapTexture);
            if (LatestMap == mapTexture) LatestMap = null;
        }
    }
}
