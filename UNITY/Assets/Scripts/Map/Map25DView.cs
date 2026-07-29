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
        const string YawPrefKey = "urhynix.map25d.yaw", PitchPrefKey = "urhynix.map25d.pitch";

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

            // 박물관 스킨: 벽=갤러리 Wall.mat(Resources, 없으면 플랫컬러 폴백), 바닥=검정 그리드 통일,
            // 장식(액자/조각상/차폐벽/충전독)은 <slotId>.decor.json 있을 때만.
            var decorCfg = MuseumDecorSpawner.Load(slotId);
            var museumWall = Resources.Load<Material>("MuseumDecor/Wall");
            var wallMat = museumWall != null ? museumWall : MakeMat(new Color(0.10f, 0.10f, 0.12f));

            // 벽 (sdf)
            var walls = new GameObject("Map25D_Walls").transform;
            walls.SetParent(transform, false);
            walls.localPosition = Offset;
            string sdf = Path.Combine(Application.streamingAssetsPath, "Maps", slotId + ".sdf");
            int n = File.Exists(sdf)
                ? SdfWallSpawner.Spawn(File.ReadAllText(sdf), walls, wallMat,
                    tilePerMeter: museumWall != null, heightOverride: decorCfg?.wallHeight ?? 0f,
                    straighten: decorCfg?.straightenWalls ?? false, exclude: decorCfg?.hideWalls)
                : 0;

            // 바닥 — 전 슬롯 공통 검정 그리드
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Map25D_Floor";
            floor.transform.SetParent(transform, false);
            floor.transform.localPosition = center;
            floor.transform.localScale = new Vector3(wm / 10f, 1f, hm / 10f); // Plane 기본 10m
            float cell = decorCfg != null && decorCfg.floorGridMeters > 0f ? decorCfg.floorGridMeters : 0.25f;
            floor.GetComponent<Renderer>().sharedMaterial = MuseumDecorSpawner.MakeGridFloorMat(wm, hm, cell);
            DestroyCollider(floor);

            // Lit 콘텐츠(갤러리 벽/소품/은색 차폐벽)용 광원 — 이 씬은 원래 Unlit 전용이라 조명이 없음.
            var sun = new GameObject("Map25D_Sun").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.transform.SetParent(transform, false);
            sun.transform.rotation = Quaternion.Euler(55f, 210f, 0f);
            sun.intensity = 1.1f;

            MuseumDecorSpawner.Apply(decorCfg, transform, walls);

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
            // 시점 영속: 저장각 있으면 복원(기본각은 ResetCamera 목적지로 보존), 드래그/줌 종료마다 저장.
            if (PlayerPrefs.HasKey(YawPrefKey))
                orbit.SetView(PlayerPrefs.GetFloat(YawPrefKey, StartYaw), PlayerPrefs.GetFloat(PitchPrefKey, StartPitch));
            orbit.OnViewChanged = () =>
            {
                PlayerPrefs.SetFloat(YawPrefKey, orbit.Yaw);
                PlayerPrefs.SetFloat(PitchPrefKey, orbit.Pitch);
                PlayerPrefs.Save();
            };

            Debug.Log($"[Map25DView] {slotId} 빌드: 벽 {n}개, 맵 {wm:F1}×{hm:F1}m");
            robotMarkers = new Map25DRobotMarkerLayer(transform, cam);
            patrolMarkers = new Map25DPatrolMarkerLayer(transform, billboardCam: cam);
            SetActive(false);
            return true;
        }

        void OnDestroy()
        {
            robotMarkers?.Dispose();
            patrolMarkers?.Dispose();
            CleanupRuntimeAssets();
            if (cam != null) cam.targetTexture = null;
            if (Texture != null)
            {
                Texture.Release();
                Destroy(Texture);
            }
        }

        // 슬롯 재빌드로 파괴될 때 "rt_" 이름 규약의 런타임 생성 머티리얼/텍스처만 정리.
        // Resources 공유 에셋(갤러리 Wall.mat 등)은 이름이 달라 건드리지 않는다.
        void CleanupRuntimeAssets()
        {
            var seen = new System.Collections.Generic.HashSet<Material>();
            foreach (var r in GetComponentsInChildren<Renderer>(true))
            {
                var m = r.sharedMaterial;
                if (m == null || !m.name.StartsWith("rt_") || !seen.Add(m)) continue;
                if (m.mainTexture != null && m.mainTexture.name.StartsWith("rt_")) Destroy(m.mainTexture);
                Destroy(m);
            }
        }

        // container에 드래그 입력을 붙인다. MapPanelView.EnsureMap25D()에서 1회만 호출.
        public void AttachOrbitControl(VisualElement container) => orbit?.Attach(container);

        // 기본각(225/50)으로 복귀 + 저장각 폐기 — 시연 중 실수 드래그 복구.
        public void ResetCamera()
        {
            PlayerPrefs.DeleteKey(YawPrefKey);
            PlayerPrefs.DeleteKey(PitchPrefKey);
            orbit?.ResetView();
        }

        // 카메라만 토글 — 비활성 시 RT 렌더 정지(매 프레임 비용 0).
        public void SetActive(bool on)
        {
            if (cam != null) cam.enabled = on;
        }

        // Unlit — 조명/노출 설정에 안 흔들리는 평면 색상(스키마틱 맵뷰라 사실적 셰이딩 불필요, 흰색 뜸 방지).
        static Material MakeMat(Color c)
        {
            var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            var m = new Material(sh) { color = c, name = "rt_flat" }; // rt_ = 파괴 시 정리 대상
            return m;
        }

        static void DestroyCollider(GameObject go)
        {
            var col = go.GetComponent<Collider>();
            if (col != null) Destroy(col);
        }
    }
}
