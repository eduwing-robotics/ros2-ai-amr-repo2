// MapCoordinateSystem.cs — 맵 좌표 변환 SSOT (순수 static, UI 비의존).
// world(m) ↔ 정규화(u,v) ↔ frame 픽셀(UI 좌상단 원점) 변환 + 쿼터니언→yaw.
// map-frame이 곧 맵 사각형이므로 letterbox 보정 없이 frame 크기만으로 변환된다.
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public static class MapCoordinateSystem
    {
        // OccupancyGrid orientation(쿼터니언) → yaw(rad). REP-103 z축 회전.
        public static float QuaternionToYaw(float x, float y, float z, float w)
            => Mathf.Atan2(2f * (w * z + x * y), 1f - 2f * (y * y + z * z));

        // 2D 강체 합성: a=B의 A프레임 pose, b=C의 B프레임 pose → C의 A프레임 pose.
        // tf 체인(map→odom ∘ odom→base) 누적에 사용.
        public static (float x, float y, float yaw) ComposePose(
            float ax, float ay, float ayaw, float bx, float by, float byaw)
        {
            float c = Mathf.Cos(ayaw), s = Mathf.Sin(ayaw);
            return (ax + c * bx - s * by, ay + s * bx + c * by, ayaw + byaw);
        }

        // world(m) → 정규화 (u: +x동쪽, v: +y북쪽, 0~1). mapW/mapH = 셀수×해상도(m).
        public static Vector2 WorldToNormalized(float worldX, float worldY,
            float originX, float originY, float mapW, float mapH)
        {
            float u = mapW > 0f ? (worldX - originX) / mapW : 0f;
            float v = mapH > 0f ? (worldY - originY) / mapH : 0f;
            return new Vector2(u, v);
        }

        // 정규화 → frame 픽셀 (UI 좌상단 원점, y 아래로 증가 → v 반전).
        public static Vector2 NormalizedToFramePx(Vector2 uv, float frameW, float frameH)
            => new Vector2(uv.x * frameW, (1f - uv.y) * frameH);

        // frame 픽셀 → 정규화 (역변환).
        public static Vector2 FramePxToNormalized(Vector2 px, float frameW, float frameH)
            => new Vector2(frameW > 0f ? px.x / frameW : 0f,
                           frameH > 0f ? 1f - px.y / frameH : 0f);

        // 정규화 → world(m).
        public static Vector2 NormalizedToWorld(Vector2 uv,
            float originX, float originY, float mapW, float mapH)
            => new Vector2(originX + uv.x * mapW, originY + uv.y * mapH);

        // 편의: world → frame 픽셀.
        public static Vector2 WorldToFramePx(float worldX, float worldY,
            float originX, float originY, float mapW, float mapH, float frameW, float frameH)
            => NormalizedToFramePx(
                WorldToNormalized(worldX, worldY, originX, originY, mapW, mapH), frameW, frameH);

        // 편의: frame 픽셀 → world.
        public static Vector2 FramePxToWorld(Vector2 px,
            float originX, float originY, float mapW, float mapH, float frameW, float frameH)
            => NormalizedToWorld(
                FramePxToNormalized(px, frameW, frameH), originX, originY, mapW, mapH);
    }
}
