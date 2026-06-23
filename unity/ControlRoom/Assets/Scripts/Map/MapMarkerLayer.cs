// MapMarkerLayer.cs — 맵 위 로봇 화살표 마커. RobotPoseSubscriber.OnPoseUpdated 구독.
// world pose → frame 픽셀(MapCoordinateSystem) 위치 + yaw→화살표 회전. frame 재배치 시 함께 갱신.
// 향후 웨이포인트/보호대상 마커도 이 레이어 패턴으로 확장.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Map
{
    public class MapMarkerLayer
    {
        readonly MapViewport viewport;
        readonly Label arrow;

        bool hasPose;
        float poseX, poseY, poseYaw;

        public MapMarkerLayer(MapViewport viewport)
        {
            this.viewport = viewport;

            arrow = new Label("▲") { name = "robot-marker", pickingMode = PickingMode.Ignore };
            arrow.style.position = Position.Absolute;
            arrow.style.fontSize = 18;
            arrow.style.color = new Color(0.20f, 0.85f, 0.55f, 1f); // 로봇 강조색
            arrow.style.unityTextAlign = TextAnchor.MiddleCenter;
            arrow.style.display = DisplayStyle.None;
            // 중심을 (left,top)에 정확히 맞추고 그 중심을 기준으로 회전 (글리프 박스 크기 무관).
            arrow.style.transformOrigin = new TransformOrigin(Length.Percent(50), Length.Percent(50), 0);
            arrow.style.translate = new Translate(Length.Percent(-50), Length.Percent(-50));
            viewport.Frame.Add(arrow);

            RobotPoseSubscriber.OnPoseUpdated += OnPose;
            viewport.OnFrameChanged += Reposition;
            if (RobotPoseSubscriber.HasPose)
                OnPose(RobotPoseSubscriber.X, RobotPoseSubscriber.Y, RobotPoseSubscriber.Yaw);
        }

        void OnPose(float x, float y, float yaw)
        {
            poseX = x; poseY = y; poseYaw = yaw; hasPose = true;
            Reposition();
        }

        void Reposition()
        {
            if (!hasPose || !viewport.HasMap) return;
            float fw = viewport.FrameWidth, fh = viewport.FrameHeight;
            if (fw <= 0f || fh <= 0f) return;

            Vector2 px = MapCoordinateSystem.WorldToFramePx(
                poseX, poseY, viewport.OriginX, viewport.OriginY,
                viewport.MapW, viewport.MapH, fw, fh);

            arrow.style.display = DisplayStyle.Flex;
            arrow.style.left = px.x;   // translate(-50%)로 중심정렬
            arrow.style.top = px.y;
            // ▲(북쪽 기준)을 yaw(ccw, +x동쪽)에 맞춤: 화면 회전(cw+) = 90 - yawDeg.
            arrow.style.rotate = new Rotate(90f - poseYaw * Mathf.Rad2Deg);
        }

        public void Dispose()
        {
            RobotPoseSubscriber.OnPoseUpdated -= OnPose;
            viewport.OnFrameChanged -= Reposition;
        }
    }
}
