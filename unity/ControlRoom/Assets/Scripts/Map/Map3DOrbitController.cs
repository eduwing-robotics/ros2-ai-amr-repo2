// Map3DOrbitController.cs — 2.5D 뷰 드래그 궤도 회전(yaw+pitch) + 휠 줌(radius). Map25DView가 카메라 1개당 1회 생성.
// 포인터 드래그 → yaw/pitch 갱신, 휠 → radius 갱신 → 구면좌표로 카메라 위치 재계산, LookAt(center)로 항상 중심 프레이밍.
using UnityEngine;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.Map
{
    public class Map3DOrbitController
    {
        const float DragSensitivity = 0.3f; // deg/px, ponytail 1차값 — 육안검증 후 조정
        const float DefaultMinPitch = 15f, DefaultMaxPitch = 80f;
        const float ZoomSensitivity = 0.1f; // radius 배율/휠틱, ponytail 1차값
        const float DefaultMinRadiusScale = 0.3f, DefaultMaxRadiusScale = 2.5f; // 최초 radius 대비 줌 범위

        readonly Camera cam;
        readonly Vector3 center;
        readonly float minRadius, maxRadius, minPitch, maxPitch;
        float radius, yaw, pitch;
        Vector2 lastPos;
        bool dragging;

        // minPitch/maxPitch/minRadiusScale/maxRadiusScale 생략 시 2.5D 스키매틱 뷰 기본 클램프값 유지.
        // 3D 점군처럼 완전 자유 회전이 필요하면 넓은 범위(예: -89~89, 0.1~6)를 명시.
        public Map3DOrbitController(Camera cam, Vector3 center, float radius, float startYaw, float startPitch,
            float minPitch = DefaultMinPitch, float maxPitch = DefaultMaxPitch,
            float minRadiusScale = DefaultMinRadiusScale, float maxRadiusScale = DefaultMaxRadiusScale)
        {
            this.cam = cam; this.center = center; this.radius = radius;
            this.minPitch = minPitch; this.maxPitch = maxPitch;
            minRadius = radius * minRadiusScale; maxRadius = radius * maxRadiusScale;
            yaw = startYaw; pitch = startPitch;
            Apply();
        }

        public void Attach(VisualElement container)
        {
            container.RegisterCallback<PointerDownEvent>(OnDown);
            container.RegisterCallback<PointerMoveEvent>(OnMove);
            container.RegisterCallback<PointerUpEvent>(OnUp);
            container.RegisterCallback<PointerLeaveEvent>(_ => dragging = false);
            container.RegisterCallback<WheelEvent>(OnWheel);
        }

        void OnWheel(WheelEvent e)
        {
            radius = Mathf.Clamp(radius * (1f + e.delta.y * ZoomSensitivity), minRadius, maxRadius);
            Apply();
            e.StopPropagation();
        }

        void OnDown(PointerDownEvent e)
        {
            if (e.button != 0) return;   // 좌클릭만 궤도 드래그 시작 — 우클릭은 소비 안 하고 다른 리스너(우클릭 메뉴)로 전파
            dragging = true; lastPos = e.position;
            (e.currentTarget as VisualElement)?.CapturePointer(e.pointerId);
        }

        void OnMove(PointerMoveEvent e)
        {
            if (!dragging) return;
            Vector2 pos = e.position;
            Vector2 delta = pos - lastPos;
            lastPos = pos;
            yaw += delta.x * DragSensitivity;
            pitch = Mathf.Clamp(pitch - delta.y * DragSensitivity, minPitch, maxPitch);
            Apply();
        }

        void OnUp(PointerUpEvent e)
        {
            dragging = false;
            (e.currentTarget as VisualElement)?.ReleasePointer(e.pointerId);
        }

        void Apply()
        {
            float yawRad = yaw * Mathf.Deg2Rad, pitchRad = pitch * Mathf.Deg2Rad;
            var offset = new Vector3(
                radius * Mathf.Cos(pitchRad) * Mathf.Sin(yawRad),
                radius * Mathf.Sin(pitchRad),
                radius * Mathf.Cos(pitchRad) * Mathf.Cos(yawRad));
            cam.transform.position = center + offset;
            cam.transform.LookAt(center);
        }
    }
}
