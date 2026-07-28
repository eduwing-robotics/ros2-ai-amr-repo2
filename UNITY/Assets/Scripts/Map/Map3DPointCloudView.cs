// Map3DPointCloudView.cs — RTAB-Map 점군(jp.keijiro.pcx로 임포트된 Mesh 프리팹)을
// 자유 궤도 카메라로 RenderTexture 렌더 → "3D" 탭 배경(보기 전용). Map25DView와 동일 패턴, 벽 대신 점군 인스턴스화.
// 좌표계는 arena_shared 2D맵/2.5D와 동일하게 정렬(map-frame 미터 단위)해서 기존 웨이포인트 마커가 같은 자리에 뜬다.
// 2026-07-03: 우클릭 좌표 찍기는 점군이 성겨서 클릭 판정이 불안정해 제외 — 좌표 입력은 2D/2.5D 전용, 3D는 시각 참고용.
using UnityEngine;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.Map
{
    public class Map3DPointCloudView : MonoBehaviour
    {
        // 2026-07-03 arena_shared2 캡처 세션의 map<->odom SE2 변환(scripts/extract_transform.py로 도출,
        // amcl_pose(map frame) vs /tb3_1/odom을 같은 시각에 비교). 새 점군을 다시 캡처하면 재계산 필요.
        const float Theta = 0.18670f, Tx = 0.0252f, Ty = 1.4068f;

        // Map25DView와 같은 Offset(map-frame 정렬)을 쓰면서도 같은 카메라에 서로 안 잡히게 분리하는 전용 레이어.
        public const int CloudLayer = 9;

        public RenderTexture Texture { get; private set; }
        public Camera Cam => cam;
        Camera cam;
        Map3DOrbitController orbit;
        Map25DPatrolMarkerLayer patrolMarkers;
        bool built;

        // resourcePath 예: "PointClouds/arena_shared_room" (확장자 제외, Resources.Load 경로)
        public bool Build(string resourcePath)
        {
            if (built) return Texture != null;
            built = true;

            var prefab = Resources.Load<GameObject>(resourcePath);
            if (prefab == null)
            {
                Debug.LogWarning($"[Map3DPointCloudView] 점군 리소스 없음: {resourcePath}");
                return false;
            }

            Texture = new RenderTexture(720, 720, 16) { name = "Map3DCloud_RT" };

            var cloud = Instantiate(prefab, transform);
            cloud.name = "Map3D_Cloud";
            cloud.transform.localPosition = Map25DView.Offset;
            cloud.transform.localRotation = Quaternion.identity; // 정렬은 정점 자체를 미리 변환(아래)해서 회전 불필요
            SetLayerRecursively(cloud, CloudLayer);

            // Pcx "Default Point" 머티리얼의 _PointSize(0.05=5cm)가 우리 점군 밀도(방 2m권에 17만점) 대비 커서
            // 점들이 서로 겹쳐 매끈한 덩어리로 보임 — 인스턴스 머티리얼로 복제해 점 크기 축소 + 색조(_Tint 50%회색) 복원.
            var renderer = cloud.GetComponentInChildren<MeshRenderer>();
            if (renderer != null)
            {
                var mat = renderer.material; // sharedMaterial 아님 — 패키지 공유 에셋 안 건드림
                if (mat.HasProperty("_PointSize")) mat.SetFloat("_PointSize", 0.008f);
                if (mat.HasProperty("_Tint")) mat.SetColor("_Tint", Color.white);
            }

            var meshFilter = cloud.GetComponentInChildren<MeshFilter>();
            Vector3 center = Map25DView.Offset;
            float radius = 3f;
            if (meshFilter != null && meshFilter.sharedMesh != null)
            {
                var mesh = meshFilter.mesh; // 인스턴스 복제 — 원본 임포트 에셋 안 건드림
                AlignVerticesToMapFrame(mesh);
                var b = mesh.bounds;
                center = Map25DView.Offset + b.center;
                radius = Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z)) * 0.8f;
                if (radius < 0.5f) radius = 3f;
            }

            var camGo = new GameObject("Map3DCloud_Cam");
            camGo.transform.SetParent(transform, false);
            cam = camGo.AddComponent<Camera>();
            cam.orthographic = false;
            cam.fieldOfView = 55f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.06f, 0.07f, 0.09f);
            cam.targetTexture = Texture;
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 50f;
            cam.cullingMask = 1 << CloudLayer; // 2.5D 벽/바닥/마커(같은 Offset 영역)가 안 섞이게 점군 레이어만

            // 점군은 실사 3D 재구성이라 어느 각도든(진짜 위/아래 포함) 자유롭게 볼 수 있어야 함 — 2.5D 스키매틱 클램프와 다름.
            orbit = new Map3DOrbitController(cam, center, radius, 225f, 40f,
                minPitch: -89f, maxPitch: 89f, minRadiusScale: 0.1f, maxRadiusScale: 6f);

            patrolMarkers = new Map25DPatrolMarkerLayer(transform, CloudLayer, cam);

            Debug.Log($"[Map3DPointCloudView] {resourcePath} 로드: center={center} radius={radius:F2}");
            SetActive(false);
            return true;
        }

        void OnDestroy() => patrolMarkers?.Dispose();

        // ply 원본 정점(x,y,z = RTAB-Map odom-frame, z=높이)을 arena_shared map-frame 미터 좌표로 변환.
        // mapX = cosθ*x - sinθ*y + tx, mapY = sinθ*x + cosθ*y + ty (평면 SE2), 높이(z)는 그대로 Unity Y로.
        // → Map25DView가 쓰는 Offset+(mapX,0,mapY) 규약과 동일해져서 우클릭 좌표가 2D/2.5D와 그대로 호환됨.
        static void AlignVerticesToMapFrame(Mesh mesh)
        {
            var verts = mesh.vertices;
            float cosT = Mathf.Cos(Theta), sinT = Mathf.Sin(Theta);
            for (int i = 0; i < verts.Length; i++)
            {
                var v = verts[i];
                float mapX = cosT * v.x - sinT * v.y + Tx;
                float mapY = sinT * v.x + cosT * v.y + Ty;
                verts[i] = new Vector3(mapX, v.z, mapY);
            }
            mesh.vertices = verts;
            mesh.RecalculateBounds();
        }

        static void SetLayerRecursively(GameObject go, int layer)
        {
            go.layer = layer;
            foreach (Transform child in go.transform) SetLayerRecursively(child.gameObject, layer);
        }

        public void AttachOrbitControl(VisualElement container) => orbit?.Attach(container);

        public void SetActive(bool on)
        {
            if (cam != null) cam.enabled = on;
        }
    }
}
