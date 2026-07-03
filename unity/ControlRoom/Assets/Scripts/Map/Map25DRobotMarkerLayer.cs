// Map25DRobotMarkerLayer.cs — 2.5D 뷰의 로봇 실시간 위치 마커(원판+헤딩코). 2D MapMarkerLayer와 같은 pose 이벤트 구독, 3D 오브젝트로 표시.
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Map
{
    public class Map25DRobotMarkerLayer
    {
        static readonly Color DefaultColor = new Color(0f, 0.769f, 0.443f, 1f); // 토스 green500

        readonly Dictionary<string, Marker> markers = new Dictionary<string, Marker>();

        public Map25DRobotMarkerLayer(Transform parent)
        {
            var robots = ControlRoomState.Instance?.Robots;
            if (robots != null && robots.Count > 0)
            {
                foreach (var r in robots)
                {
                    if (r == null || string.IsNullOrEmpty(r.robotId) || markers.ContainsKey(r.robotId))
                        continue;
                    markers[r.robotId] = new Marker(parent, ResolveColor(r));
                }
            }
            else
            {
                markers[ControlRoomState.Instance?.SelectedRobotId ?? "tb3_1"] = new Marker(parent, DefaultColor);
            }

            RobotPoseFeed.OnRobotPose += OnRobotPose;
            RobotPoseSubscriber.OnPoseUpdated += OnGlobalTfPose;

            if (RobotPoseSubscriber.HasPose)
                OnGlobalTfPose(RobotPoseSubscriber.X, RobotPoseSubscriber.Y, RobotPoseSubscriber.Yaw);
        }

        static Color ResolveColor(RobotInfo robot)
            => (robot != null && !string.IsNullOrEmpty(robot.markerColor)
                && ColorUtility.TryParseHtmlString(robot.markerColor, out var c))
               ? c : DefaultColor;

        // 로봇별 pose: 해당 로봇 마커만 갱신.
        void OnRobotPose(string robotId, float x, float y, float yaw)
        {
            if (markers.TryGetValue(robotId, out var m)) m.Set(x, y, yaw);
        }

        // 전역 /tf: per-robot pose가 없는 "선택 로봇"에만 적용(단일로봇 맵제작 호환) — 2D MapMarkerLayer와 동일 정책.
        void OnGlobalTfPose(float x, float y, float yaw)
        {
            string sel = ControlRoomState.Instance?.SelectedRobotId;
            if (string.IsNullOrEmpty(sel) || RobotPoseFeed.LiveRobots.Contains(sel)) return;
            if (markers.TryGetValue(sel, out var m)) m.Set(x, y, yaw);
        }

        public void Dispose()
        {
            RobotPoseFeed.OnRobotPose -= OnRobotPose;
            RobotPoseSubscriber.OnPoseUpdated -= OnGlobalTfPose;
        }

        // 로봇 1대 = 몸통(원판, Cylinder) + 헤딩 코(Cube). 회전행렬 없이 코 위치를 삼각함수로 직접 배치해
        // Quaternion/Euler 부호 실수를 원천 차단(오푸스 검산: yaw=0→+X/동쪽, yaw=90°→+Z/북쪽, ROS 컨벤션과 일치).
        sealed class Marker
        {
            const float BodyRadius = 0.12f, BodyHeight = 0.04f, NoseSize = 0.06f, NoseDist = 0.16f, Y = 0.05f;
            readonly Transform body, nose;

            public Marker(Transform parent, Color color)
            {
                var bodyGo = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                bodyGo.name = "RobotMarker25D_Body";
                bodyGo.transform.SetParent(parent, false);
                bodyGo.transform.localScale = new Vector3(BodyRadius * 2f, BodyHeight * 0.5f, BodyRadius * 2f);
                bodyGo.GetComponent<Renderer>().sharedMaterial = MakeMat(color);
                DestroyCollider(bodyGo);
                body = bodyGo.transform;

                var noseGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
                noseGo.name = "RobotMarker25D_Nose";
                noseGo.transform.SetParent(parent, false);
                noseGo.transform.localScale = Vector3.one * NoseSize;
                noseGo.GetComponent<Renderer>().sharedMaterial = MakeMat(Color.white);
                DestroyCollider(noseGo);
                nose = noseGo.transform;

                body.gameObject.SetActive(false);
                nose.gameObject.SetActive(false);
            }

            public void Set(float worldX, float worldY, float yaw)
            {
                Vector3 c = Map25DView.Offset + new Vector3(worldX, Y, worldY);
                body.localPosition = c;
                nose.localPosition = c + new Vector3(Mathf.Cos(yaw), 0f, Mathf.Sin(yaw)) * NoseDist;
                body.gameObject.SetActive(true);
                nose.gameObject.SetActive(true);
            }

            static void DestroyCollider(GameObject go)
            {
                var col = go.GetComponent<Collider>();
                if (col != null) Object.Destroy(col);
            }

            static Material MakeMat(Color c)
            {
                var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
                return new Material(sh) { color = c };
            }
        }
    }
}
