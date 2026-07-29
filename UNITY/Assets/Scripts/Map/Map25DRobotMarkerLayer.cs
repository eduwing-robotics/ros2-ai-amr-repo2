// Map25DRobotMarkerLayer.cs — 2.5D 뷰의 로봇 실시간 위치 마커(식별색 원판 + 실측 TB3 burger 모델, 폴백=원판+헤딩코).
// 2D MapMarkerLayer와 같은 pose 이벤트 구독, 3D 오브젝트로 표시.
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

        public Map25DRobotMarkerLayer(Transform parent, Camera billboardCam)
        {
            var robots = ControlRoomState.Instance?.Robots;
            if (robots != null && robots.Count > 0)
            {
                foreach (var r in robots)
                {
                    if (r == null || string.IsNullOrEmpty(r.robotId) || markers.ContainsKey(r.robotId))
                        continue;
                    markers[r.robotId] = new Marker(parent, ResolveColor(r), r.displayName, billboardCam);
                }
            }
            else
            {
                string robotId = ControlRoomState.Instance?.SelectedRobotId ?? "tb3_1";
                markers[robotId] = new Marker(parent, DefaultColor, robotId, billboardCam);
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

        // 로봇 1대 = 식별색 원판 + 실측 TB3 burger 모델(Resources/MuseumDecor/tb3_burger.obj, 미터 스케일).
        // 모델 없으면 기존 원판+헤딩코 폴백. 회전: ROS yaw(ccw) → Unity Y축 -yaw (yaw=0→+X/동쪽 검산 유지).
        sealed class Marker
        {
            const float DiscRadius = 0.12f, DiscHeight = 0.008f, NoseSize = 0.06f, NoseDist = 0.16f;
            const float NameplateHeight = 0.32f;
            static GameObject modelPrefab;
            static bool modelSearched;
            readonly Transform root;

            public Marker(Transform parent, Color color, string displayName, Camera billboardCam)
            {
                if (!modelSearched)
                {
                    modelPrefab = Resources.Load<GameObject>("MuseumDecor/tb3_burger");
                    modelSearched = true;
                }

                var rootGo = new GameObject("RobotMarker25D");
                rootGo.transform.SetParent(parent, false);
                root = rootGo.transform;

                var discGo = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                discGo.name = "Disc";
                discGo.transform.SetParent(root, false);
                discGo.transform.localPosition = new Vector3(0f, DiscHeight * 0.5f, 0f);
                discGo.transform.localScale = new Vector3(DiscRadius * 2f, DiscHeight * 0.5f, DiscRadius * 2f);
                discGo.GetComponent<Renderer>().sharedMaterial = MakeMat(color);
                DestroyCollider(discGo);

                if (modelPrefab != null)
                {
                    var model = Object.Instantiate(modelPrefab, root, false);
                    model.name = "Tb3Model";
                    var dark = MakeLit(new Color(0.13f, 0.13f, 0.14f));
                    foreach (var r in model.GetComponentsInChildren<Renderer>()) r.sharedMaterial = dark;
                    foreach (var c in model.GetComponentsInChildren<Collider>()) Object.Destroy(c);
                }
                else
                {
                    var noseGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    noseGo.name = "Nose";
                    noseGo.transform.SetParent(root, false);
                    noseGo.transform.localPosition = new Vector3(NoseDist, 0.05f, 0f);
                    noseGo.transform.localScale = Vector3.one * NoseSize;
                    noseGo.GetComponent<Renderer>().sharedMaterial = MakeMat(Color.white);
                    DestroyCollider(noseGo);
                }

                var nameGo = new GameObject("RobotNameplate");
                nameGo.transform.SetParent(root, false);
                nameGo.transform.localPosition = new Vector3(0f, NameplateHeight, 0f);
                nameGo.transform.localScale = Vector3.one * 0.12f;

                var name = nameGo.AddComponent<TextMesh>();
                name.text = string.IsNullOrWhiteSpace(displayName) ? "Robot" : displayName;
                name.anchor = TextAnchor.LowerCenter;
                name.alignment = TextAlignment.Center;
                name.fontSize = 36;
                name.characterSize = 0.4f;
                name.fontStyle = FontStyle.Bold;
                name.color = Color.white;

                var billboard = nameGo.AddComponent<Billboard>();
                billboard.target = billboardCam;

                root.gameObject.SetActive(false);
            }

            public void Set(float worldX, float worldY, float yaw)
            {
                root.localPosition = Map25DView.Offset + new Vector3(worldX, 0.003f, worldY);
                root.localRotation = Quaternion.Euler(0f, -yaw * Mathf.Rad2Deg, 0f);
                root.gameObject.SetActive(true);
            }

            static void DestroyCollider(GameObject go)
            {
                var col = go.GetComponent<Collider>();
                if (col != null) Object.Destroy(col);
            }

            static Material MakeMat(Color c)
            {
                var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
                return new Material(sh) { color = c, name = "rt_marker" }; // rt_ = Map25DView 파괴 시 정리 대상
            }

            static Material MakeLit(Color c)
            {
                var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "rt_marker_lit" };
                m.SetColor("_BaseColor", c);
                m.SetFloat("_Smoothness", 0.35f);
                return m;
            }
        }
    }
}
