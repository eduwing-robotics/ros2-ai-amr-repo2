// Map3DView.cs — sdf 벽을 3D로 띄우고 천장뷰 ortho 카메라를 RenderTexture로 렌더 → UI Toolkit container3D 배경.
// 메인 UI 씬과 안 겹치게 3D 콘텐츠를 먼 오프셋(Offset)에 둔다(전용 레이어 추가 없이 격리).
// MapPanelView가 3D 첫 진입 시 1회 Build, 탭 전환마다 SetActive로 카메라만 토글.
using System.IO;
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public class Map3DView : MonoBehaviour
    {
        static readonly Vector3 Offset = new Vector3(10000f, 0f, 10000f); // 메인 씬 밖

        public RenderTexture Texture { get; private set; }
        Camera cam;
        bool built;

        // 슬롯 메타(StaticMapLoader 값)로 1회 빌드. slotId의 .sdf가 있으면 벽, 없으면 바닥만.
        public bool Build(string slotId, float originX, float originY, int mapW, int mapH, float res)
        {
            if (built) return Texture != null;
            built = true;

            Texture = new RenderTexture(720, 720, 16) { name = "Map3D_RT" };
            float wm = Mathf.Max(0.5f, mapW * res), hm = Mathf.Max(0.5f, mapH * res); // 맵 실치수(m)
            Vector3 center = Offset + new Vector3(originX + wm * 0.5f, 0f, originY + hm * 0.5f);

            var wallMat = MakeMat(new Color(0.10f, 0.10f, 0.12f));

            // 벽 (sdf)
            var walls = new GameObject("Map3D_Walls").transform;
            walls.SetParent(transform, false);
            walls.localPosition = Offset;
            string sdf = Path.Combine(Application.streamingAssetsPath, "Maps", slotId + ".sdf");
            int n = File.Exists(sdf) ? SdfWallSpawner.Spawn(File.ReadAllText(sdf), walls, wallMat) : 0;

            // 바닥
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Map3D_Floor";
            floor.transform.SetParent(transform, false);
            floor.transform.localPosition = center;
            floor.transform.localScale = new Vector3(wm / 10f, 1f, hm / 10f); // Plane 기본 10m
            floor.GetComponent<Renderer>().sharedMaterial = MakeMat(new Color(0.85f, 0.85f, 0.82f));
            DestroyCollider(floor);

            // 천장뷰 ortho 카메라
            var camGo = new GameObject("Map3D_Cam");
            camGo.transform.SetParent(transform, false);
            cam = camGo.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = Mathf.Max(wm, hm) * 0.6f + 0.3f;
            cam.transform.position = center + new Vector3(0f, 6f, 0f);
            cam.transform.rotation = Quaternion.Euler(90f, 0f, 0f); // 수직 하향
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.125f, 0.149f, 0.196f);
            cam.targetTexture = Texture;
            cam.nearClipPlane = 0.1f;
            cam.farClipPlane = 30f;

            // 조명
            var sun = new GameObject("Map3D_Sun");
            sun.transform.SetParent(transform, false);
            var l = sun.AddComponent<Light>();
            l.type = LightType.Directional;
            l.intensity = 1.1f;
            sun.transform.rotation = Quaternion.Euler(55f, -30f, 0f);

            Debug.Log($"[Map3DView] {slotId} 빌드: 벽 {n}개, 맵 {wm:F1}×{hm:F1}m");
            SetActive(false);
            return true;
        }

        // 카메라만 토글 — 비활성 시 RT 렌더 정지(매 프레임 비용 0).
        public void SetActive(bool on)
        {
            if (cam != null) cam.enabled = on;
        }

        static Material MakeMat(Color c)
        {
            var sh = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var m = new Material(sh) { color = c };
            return m;
        }

        static void DestroyCollider(GameObject go)
        {
            var col = go.GetComponent<Collider>();
            if (col != null) Destroy(col);
        }
    }
}
