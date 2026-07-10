// opencode: 2026-06-29 - 로봇 마커 기본색 토스 green500으로 변환. Coded with OpenCode; high-cost model review recommended.
// MapMarkerLayer.cs — 맵 위 로봇 방향 마커(벡터 화살표)들을 로봇별로 관리.
// 로봇별 /tb3_X/pose(RobotPoseFeed) → 로봇별 마커. 전역 /tf(RobotPoseSubscriber)는 per-robot pose가
// 없는 선택로봇에만 적용되는 fallback(비-ns 단일로봇 맵제작 호환). 색은 로봇 config(markerColor).
// 화살표는 Painter2D로 직접 그려 글꼴 글리프 의존 없이 어떤 크기·색도 또렷하게 정면을 표시한다.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Map
{
    public class MapMarkerLayer
    {
        static readonly Color DefaultColor = new Color(0f, 0.769f, 0.443f, 1f); // 토스 green500 #00C471

        readonly MapViewport viewport;
        readonly Dictionary<string, RobotMarker> markers = new Dictionary<string, RobotMarker>();

        public MapMarkerLayer(MapViewport viewport)
        {
            this.viewport = viewport;

            // 설정된 로봇마다 마커 1개(자기 색). 목록이 비면 기본색 단일 마커로 동작.
            var robots = ControlRoomState.Instance?.Robots;
            if (robots != null && robots.Count > 0)
            {
                foreach (var r in robots)
                {
                    if (r == null || string.IsNullOrEmpty(r.robotId) || markers.ContainsKey(r.robotId))
                        continue;
                    markers[r.robotId] = new RobotMarker(viewport, ResolveColor(r));
                }
            }
            else
            {
                markers[ControlRoomState.Instance?.SelectedRobotId ?? "tb3_1"]
                    = new RobotMarker(viewport, DefaultColor);
            }

            RobotPoseFeed.OnRobotPose += OnRobotPose;
            RobotPoseSubscriber.OnPoseUpdated += OnGlobalTfPose;
            viewport.OnFrameChanged += RepositionAll;

            // 초기 seed: 이미 전역 /tf pose가 있으면 선택로봇 마커에.
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
            if (markers.TryGetValue(robotId, out var m))
            {
                m.Set(x, y, yaw);
                Debug.Log($"[MapMarkerLayer] marker set {robotId}: ({x:F3}, {y:F3})");
            }
            else
            {
                Debug.LogWarning($"[MapMarkerLayer] marker not found for {robotId}");
            }
        }

        // 전역 /tf: per-robot pose가 없는 "선택 로봇"에만 적용(단일로봇 맵제작 호환).
        void OnGlobalTfPose(float x, float y, float yaw)
        {
            string sel = ControlRoomState.Instance?.SelectedRobotId;
            if (string.IsNullOrEmpty(sel) || RobotPoseFeed.LiveRobots.Contains(sel)) return;
            if (markers.TryGetValue(sel, out var m)) m.Set(x, y, yaw);
        }

        void RepositionAll()
        {
            foreach (var m in markers.Values) m.Reposition();
        }

        public void Dispose()
        {
            RobotPoseFeed.OnRobotPose -= OnRobotPose;
            RobotPoseSubscriber.OnPoseUpdated -= OnGlobalTfPose;
            viewport.OnFrameChanged -= RepositionAll;
        }

        // 로봇 1대의 화살표 마커. world pose → frame 픽셀 + yaw 회전.
        sealed class RobotMarker
        {
            const float Size = 26f;                       // 마커 박스(px)

            readonly MapViewport viewport;
            readonly VisualElement el;
            readonly Color color;

            bool hasPose;
            float poseX, poseY, poseYaw;

            public RobotMarker(MapViewport viewport, Color color)
            {
                this.viewport = viewport;
                this.color = color;

                el = new VisualElement { name = "robot-marker", pickingMode = PickingMode.Ignore };
                el.style.position = Position.Absolute;
                el.style.width = Size;
                el.style.height = Size;
                el.style.display = DisplayStyle.None;
                // 중심을 (left,top)에 맞추고 그 중심 기준으로 회전.
                el.style.transformOrigin = new TransformOrigin(Length.Percent(50), Length.Percent(50), 0);
                el.style.translate = new Translate(Length.Percent(-50), Length.Percent(-50));
                el.generateVisualContent += OnGenerateArrow;
                viewport.Frame.Add(el);
            }

            // 위쪽(정면=북쪽 기준)을 가리키는 화살촉. yaw 회전은 Reposition에서 적용.
            void OnGenerateArrow(MeshGenerationContext ctx)
            {
                var p = ctx.painter2D;
                p.BeginPath();
                p.MoveTo(new Vector2(Size * 0.50f, Size * 0.04f));  // tip(정면)
                p.LineTo(new Vector2(Size * 0.90f, Size * 0.94f));  // 우측 뒤
                p.LineTo(new Vector2(Size * 0.50f, Size * 0.68f));  // 뒤 노치(화살표 꼬리)
                p.LineTo(new Vector2(Size * 0.10f, Size * 0.94f));  // 좌측 뒤
                p.ClosePath();
                p.fillColor = color;
                p.Fill();
                p.strokeColor = new Color(0f, 0f, 0f, 0.55f);       // 밝은 맵에서 윤곽 대비
                p.lineWidth = 1.5f;
                p.Stroke();
            }

            public void Set(float x, float y, float yaw)
            {
                poseX = x; poseY = y; poseYaw = yaw; hasPose = true;
                Reposition();
            }

            public void Reposition()
            {
                if (!hasPose || !viewport.HasMap) return;
                float fw = viewport.FrameWidth, fh = viewport.FrameHeight;
                if (fw <= 0f || fh <= 0f) return;

                Vector2 px = MapCoordinateSystem.WorldToFramePx(
                    poseX, poseY, viewport.OriginX, viewport.OriginY,
                    viewport.MapW, viewport.MapH, fw, fh);

                el.style.display = DisplayStyle.Flex;
                el.style.left = px.x;   // translate(-50%)로 중심정렬
                el.style.top = px.y;
                // 화살촉(북쪽 기준)을 yaw(ccw, +x동쪽)에 맞춤: 화면 회전(cw+) = 90 - yawDeg.
                el.style.rotate = new Rotate(90f - poseYaw * Mathf.Rad2Deg);
            }
        }
    }
}
