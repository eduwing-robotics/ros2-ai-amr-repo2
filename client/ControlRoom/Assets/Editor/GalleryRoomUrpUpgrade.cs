// GalleryRoomUrpUpgrade.cs — Gallery Room 팩의 Built-in Standard .mat들을 URP Lit으로 일괄 변환.
// 원인: 프로젝트 URP 17 ↔ 팩 Built-in Standard 셰이더 미스매치 → 마젠타 폴백 렌더.
// URP 공식 StandardUpgrader가 _MainTex→_BaseMap 리매핑 + _Mode→_Surface(투명) + 키워드까지 처리.
// 실행: 메뉴 URHYNIX/Upgrade Gallery Room Materials to URP 또는
//       unityctl exec --code 'URHYNIX.ControlRoom.Editor.GalleryRoomUrpUpgrade.Run()'
using UnityEditor;
using UnityEditor.Rendering;
using UnityEditor.Rendering.Universal;
using UnityEngine;

namespace URHYNIX.ControlRoom.Editor
{
    public static class GalleryRoomUrpUpgrade
    {
        const string TargetFolder = "Assets/Gallery Room";

        [MenuItem("URHYNIX/Upgrade Gallery Room Materials to URP")]
        public static void Run()
        {
            var guids = AssetDatabase.FindAssets("t:Material", new[] { TargetFolder });
            int converted = 0, skipped = 0;
            foreach (var guid in guids)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null || mat.shader == null || !mat.shader.name.StartsWith("Standard"))
                {
                    skipped++;
                    Debug.Log($"[GalleryRoomUrpUpgrade] skip {path} (shader={mat?.shader?.name})");
                    continue;
                }
                new StandardUpgrader(mat.shader.name).Upgrade(mat, MaterialUpgrader.UpgradeFlags.None);
                converted++;
                Debug.Log($"[GalleryRoomUrpUpgrade] {path} → {mat.shader.name}");
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"[GalleryRoomUrpUpgrade] done: converted={converted} skipped={skipped} total={guids.Length}");
        }

        // 차폐벽 가시성 진단: 은색(metallic .9) vs 저metallic vs 기본회색 큐브를 런타임과 같은 광원으로 렌더.
        public static void RenderShutterTest(string outPng)
        {
            var lightGo = new GameObject("tmp_sh_light");
            var li = lightGo.AddComponent<Light>();
            li.type = LightType.Directional;
            li.transform.rotation = Quaternion.Euler(55f, 210f, 0f);
            li.intensity = 1.1f;
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var mats = new Material[3];
            mats[0] = new Material(lit); // 현행 은색
            mats[0].SetColor("_BaseColor", new Color(0.78f, 0.79f, 0.82f));
            mats[0].SetFloat("_Metallic", 0.9f); mats[0].SetFloat("_Smoothness", 0.7f);
            mats[1] = new Material(lit); // 저metallic 은색 후보
            mats[1].SetColor("_BaseColor", new Color(0.80f, 0.81f, 0.85f));
            mats[1].SetFloat("_Metallic", 0.35f); mats[1].SetFloat("_Smoothness", 0.5f);
            mats[2] = new Material(lit); // 기준 회색(조각상과 동일 조건)
            var cubes = new GameObject[3];
            for (int i = 0; i < 3; i++)
            {
                cubes[i] = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cubes[i].transform.position = new Vector3(6000f + i * 1.3f, 0.16f, 6000f);
                cubes[i].transform.localScale = new Vector3(0.92f, 0.32f, 0.05f);
                cubes[i].GetComponent<Renderer>().sharedMaterial = mats[i];
            }
            var camGo = new GameObject("tmp_sh_cam");
            var cam = camGo.AddComponent<Camera>();
            var rt = new RenderTexture(768, 256, 16);
            cam.targetTexture = rt;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.125f, 0.149f, 0.196f); // Map25D 배경과 동일
            cam.transform.position = new Vector3(6001.3f, 1.2f, 5998.2f);
            cam.transform.LookAt(new Vector3(6001.3f, 0.16f, 6000f));
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(768, 256, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, 768, 256), 0, 0);
            tex.Apply();
            System.IO.File.WriteAllBytes(outPng, tex.EncodeToPNG());
            RenderTexture.active = null;
            foreach (var c in cubes) Object.DestroyImmediate(c);
            Object.DestroyImmediate(camGo); Object.DestroyImmediate(lightGo);
            Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
            Debug.Log($"[ShutterTest] saved {outPng} (좌: 현행 metallic0.9 / 중: metallic0.35 / 우: 기본회색)");
        }

        // 조각상 방향 판정용: 두 statue OBJ를 4방향(+X,+Z,-X,-Z 시점)에서 렌더한 몽타주 PNG 저장.
        public static void RenderStatueViews(string outPng)
        {
            string[] paths = { "Assets/Resources/MuseumDecor/WingedVictory.obj", "Assets/Resources/MuseumDecor/Sphinx.obj" };
            const int T = 256;
            var big = new Texture2D(T * 4, T * 2, TextureFormat.RGB24, false);
            var rt = new RenderTexture(T, T, 16);
            var camGo = new GameObject("tmp_statue_cam");
            var cam = camGo.AddComponent<Camera>();
            cam.targetTexture = rt;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.2f, 0.2f, 0.25f);
            var lightGo = new GameObject("tmp_statue_light");
            var li = lightGo.AddComponent<Light>();
            li.type = LightType.Directional;
            li.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
            li.intensity = 1.2f;
            Vector3[] dirs = { Vector3.right, Vector3.forward, Vector3.left, Vector3.back };
            for (int r = 0; r < paths.Length; r++)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(paths[r]);
                var inst = Object.Instantiate(prefab, new Vector3(5000f, 0f, 5000f), Quaternion.identity);
                var rends = inst.GetComponentsInChildren<Renderer>();
                var b = rends[0].bounds;
                foreach (var rr in rends) b.Encapsulate(rr.bounds);
                for (int c = 0; c < 4; c++)
                {
                    cam.transform.position = b.center + dirs[c] * (b.size.magnitude * 1.4f) + Vector3.up * (b.size.y * 0.25f);
                    cam.transform.LookAt(b.center);
                    cam.Render();
                    RenderTexture.active = rt;
                    var tex = new Texture2D(T, T, TextureFormat.RGB24, false);
                    tex.ReadPixels(new Rect(0, 0, T, T), 0, 0);
                    tex.Apply();
                    big.SetPixels(c * T, (1 - r) * T, T, T, tex.GetPixels());
                    Object.DestroyImmediate(tex);
                }
                Object.DestroyImmediate(inst);
            }
            RenderTexture.active = null;
            big.Apply();
            System.IO.File.WriteAllBytes(outPng, big.EncodeToPNG());
            Object.DestroyImmediate(camGo);
            Object.DestroyImmediate(lightGo);
            Object.DestroyImmediate(rt);
            Object.DestroyImmediate(big);
            Debug.Log($"[StatueViews] saved {outPng} (rows: top=WingedVictory bottom=Sphinx; cols: cam from +X,+Z,-X,-Z)");
        }

        // 프리팹 렌더러 합산 bounds/피벗 확인용 (MuseumDecor 배치 계수 산출) — unityctl exec로 호출.
        public static void LogPrefabBounds(string assetPath)
        {
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (go == null) { Debug.LogWarning($"[Bounds] 없음: {assetPath}"); return; }
            var rends = go.GetComponentsInChildren<Renderer>();
            if (rends.Length == 0) { Debug.LogWarning($"[Bounds] 렌더러 없음: {assetPath}"); return; }
            var b = rends[0].bounds;
            foreach (var r in rends) b.Encapsulate(r.bounds);
            Debug.Log($"[Bounds] {assetPath}: center={b.center:F3} size={b.size:F3} min={b.min:F3} max={b.max:F3} rootScale={go.transform.localScale:F2}");
        }
    }
}
