// Map25DView.cs — sdf 벽을 3D로 띄우고 자유 궤도(드래그 yaw+pitch) 카메라를 RenderTexture로 렌더 → UI Toolkit container25D 배경.
// 메인 UI 씬과 안 겹치게 3D 콘텐츠를 먼 오프셋(Offset)에 둔다(전용 레이어 추가 없이 격리).
// MapPanelView가 2.5D 첫 진입 시 1회 Build, 탭 전환마다 SetActive로 카메라만 토글.
// 진짜 "3D"(RTAB-Map 점군)는 별도 클래스로 후속 도입 예정 — 이름 충돌 방지 위해 이 클래스는 2.5D 전용으로 리네임됨(구 Map3DView).
using System.IO;
using UnityEngine;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.Map
{
    public class Map25DView : MonoBehaviour
    {
        public static readonly Vector3 Offset = new Vector3(10000f, 0f, 10000f); // 메인 씬 밖 — Map25DInteractionController/RobotMarkerLayer가 world↔map 좌표 역산에도 씀
        const float StartYaw = 225f, StartPitch = 50f; // ponytail: 남서 대각선 위 1차 기본값, 육안검증 후 조정

        public RenderTexture Texture { get; private set; }
        public Camera Cam => cam;
        Camera cam;
        Map3DOrbitController orbit;
        Map25DRobotMarkerLayer robotMarkers;
        Map25DPatrolMarkerLayer patrolMarkers;
        bool built;

        // 슬롯 메타(StaticMapLoader 값)로 1회 빌드. slotId의 .sdf가 있으면 벽, 없으면 바닥만.
        public bool Build(string slotId, float originX, float originY, int mapW, int mapH, float res)
        {
            if (built) return Texture != null;
            built = true;

            Texture = new RenderTexture(720, 720, 16) { name = "Map25D_RT" };
            float wm = Mathf.Max(0.5f, mapW * res), hm = Mathf.Max(0.5f, mapH * res); // 맵 실치수(m)
            Vector3 center = Offset + new Vector3(originX + wm * 0.5f, 0f, originY + hm * 0.5f);

            var wallMat = MakeMat(new Color(0.10f, 0.10f, 0.12f));

            // 벽 (sdf)
            var walls = new GameObject("Map25D_Walls").transform;
            walls.SetParent(transform, false);
            walls.localPosition = Offset;
            string sdf = Path.Combine(Application.streamingAssetsPath, "Maps", slotId + ".sdf");
            int n = File.Exists(sdf) ? SdfWallSpawner.Spawn(File.ReadAllText(sdf), walls, wallMat) : 0;

            // 바닥
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Map25D_Floor";
            floor.transform.SetParent(transform, false);
            floor.transform.localPosition = center;
            floor.transform.localScale = new Vector3(wm / 10f, 1f, hm / 10f); // Plane 기본 10m
            floor.GetComponent<Renderer>().sharedMaterial = MakeMat(new Color(0.85f, 0.85f, 0.82f));
            DestroyCollider(floor);

            // 자유 궤도(perspective) 카메라 — 클릭 가능한 마커 오버레이가 없는 배경 렌더라 ortho 강제 안 함.
            var camGo = new GameObject("Map25D_Cam");
            camGo.transform.SetParent(transform, false);
            cam = camGo.AddComponent<Camera>();
            cam.orthographic = false;
            cam.fieldOfView = 55f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.125f, 0.149f, 0.196f);
            cam.targetTexture = Texture;
            cam.nearClipPlane = 0.1f;
            cam.farClipPlane = 30f;
            cam.cullingMask = ~(1 << 9); // Map3DPointCloudView가 같은 Offset을 쓰므로 그쪽 전용 레이어(9)만 제외

            float radius = Mathf.Max(wm, hm) * 1.0f; // ponytail: 1차 프레이밍 값, 육안검증 후 조정
            orbit = new Map3DOrbitController(cam, center, radius, StartYaw, StartPitch);

            Debug.Log($"[Map25DView] {slotId} 빌드: 벽 {n}개, 맵 {wm:F1}×{hm:F1}m");
            robotMarkers = new Map25DRobotMarkerLayer(transform);
            patrolMarkers = new Map25DPatrolMarkerLayer(transform, billboardCam: cam);
            SetActive(false);
            return true;
        }

        void OnDestroy()
        {
            robotMarkers?.Dispose();
            patrolMarkers?.Dispose();
        }

        // container에 드래그 입력을 붙인다. MapPanelView.EnsureMap25D()에서 1회만 호출.
        public void AttachOrbitControl(VisualElement container) => orbit?.Attach(container);

        // 카메라만 토글 — 비활성 시 RT 렌더 정지(매 프레임 비용 0).
        public void SetActive(bool on)
        {
            if (cam != null) cam.enabled = on;
        }

        // Unlit — 조명/노출 설정에 안 흔들리는 평면 색상(스키마틱 맵뷰라 사실적 셰이딩 불필요, 흰색 뜸 방지).
        static Material MakeMat(Color c)
        {
            var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
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
