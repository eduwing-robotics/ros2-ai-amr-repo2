// MuseumDecorSpawner.cs — StreamingAssets/Maps/<slot>.decor.json으로 2.5D 맵을 박물관 장식.
// 검정 그리드 바닥 생성, 계단식 벽 숨김+일자 은색 차폐벽(FireShutter) 대체, 충전독 흰 패치,
// 긴 벽면에 Canvas 액자 자동 배치(+위에 LightStand), Statue/Stand는 지정 좌표 스폰.
// 프리팹/머티리얼은 Resources/MuseumDecor/(Gallery Room 복사본). json 없으면 장식 생략(그리드 바닥은 Map25DView가 항상 적용).
using System;
using System.IO;
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public static class MuseumDecorSpawner
    {
        [Serializable] public class Config
        {
            public float wallHeight;      // 0 = sdf 원본 높이 유지
            public float floorGridMeters; // 0 = 기본 0.25
            public bool straightenWalls;  // 계단식 벽 직선 병합(SdfWallSpawner, 표시 전용)
            public string[] hideWalls;    // 스폰 제외할 원본 벽(차폐벽 일자 대체용) — Spawn의 exclude로 전달
            public Shutter shutter;
            public Dock dock;
            public CanvasCfg canvas;
            public Prop[] props;
        }
        [Serializable] public class Shutter { public float x, y, len, thick, height, yaw, autoOpenSeconds; }
        [Serializable] public class Dock { public float x, y, r; public string robotId; public string colorHex; }
        [Serializable] public class CanvasCfg
        {
            public float minWallLen, everyMeters, y, scale, lightScale;
            public bool light;                 // 벽 상단 일렬 그림조명(액자당 1개)
            public float lightY;               // 조명 높이(0=벽높이 0.3 가정)
            public float lightPitchDeg;        // 그림 향해 내리쬐는 각(0=40)
            public float spotIntensity;        // 실제 SpotLight 세기(0=끄기)
        }
        [Serializable] public class Prop { public string prefab; public float x, y, yaw, scale; }

        public static Config Load(string slotId)
        {
            string p = Path.Combine(Application.streamingAssetsPath, "Maps", slotId + ".decor.json");
            if (!File.Exists(p)) return null;
            try { return JsonUtility.FromJson<Config>(File.ReadAllText(p)); }
            catch (Exception e) { Debug.LogWarning($"[MuseumDecor] {p} 파싱 실패: {e.Message}"); return null; }
        }

        // 검정 계열 그리드 바닥(Unlit — 조명·노출에 안 흔들림). cellMeters당 1칸.
        public static Material MakeGridFloorMat(float wm, float hm, float cellMeters)
        {
            const int T = 64;
            var tex = new Texture2D(T, T, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Repeat, name = "rt_grid_tex" };
            var bg = new Color(0.055f, 0.06f, 0.07f);
            var line = new Color(0.16f, 0.18f, 0.22f);
            var px = new Color[T * T];
            for (int yy = 0; yy < T; yy++)
                for (int xx = 0; xx < T; xx++)
                    px[yy * T + xx] = (xx < 2 || yy < 2) ? line : bg;
            tex.SetPixels(px);
            tex.Apply();
            var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Texture");
            var m = new Material(sh) { mainTexture = tex, name = "rt_grid" }; // rt_ = Map25DView 파괴 시 정리 대상
            m.mainTextureScale = new Vector2(wm / cellMeters, hm / cellMeters);
            return m;
        }

        // walls: SdfWallSpawner 큐브들의 부모(local=Offset, 자식 좌표=map frame).
        public static void Apply(Config cfg, Transform root, Transform walls)
        {
            if (cfg == null) return;
            var decor = new GameObject("Map25D_Decor").transform;
            decor.SetParent(root, false);
            decor.localPosition = walls.localPosition;

            // hideWalls는 SdfWallSpawner.Spawn(exclude)에서 이미 스폰 제외됨 — 여기선 소비 안 함.
            if (cfg.shutter != null && cfg.shutter.len > 0f) SpawnShutter(cfg.shutter, decor);
            if (cfg.dock != null && cfg.dock.r > 0f) SpawnDock(cfg.dock, decor);
            if (cfg.canvas != null && cfg.canvas.scale > 0f) SpawnCanvases(cfg.canvas, walls, decor);
            if (cfg.props != null)
                foreach (var p in cfg.props) SpawnProp(p, decor);

            StripColliders(decor.gameObject); // 표시 전용 — 우클릭 ground raycast 방해 금지
            Debug.Log($"[MuseumDecor] 장식 {decor.childCount}개 스폰 — shutter={cfg.shutter != null && cfg.shutter.len > 0f} " +
                      $"dock={cfg.dock != null && cfg.dock.r > 0f} canvas={cfg.canvas != null && cfg.canvas.scale > 0f} props={cfg.props?.Length ?? 0}");
        }

        // 차폐벽: 헤더박스+가이드레일 상시 표시, 패널은 평소 말려 올라가 있다가 화재 출동 시 하강(FireShutter).
        // metallic은 낮게 — 2.5D 오프셋 씬엔 반사프로브가 없어 고metallic이 검게 떠서 안 보였던 근본원인 대응.
        static void SpawnShutter(Shutter s, Transform decor)
        {
            float h = s.height > 0f ? s.height : 0.3f;
            float thick = s.thick > 0f ? s.thick : 0.04f;
            var group = new GameObject("FireShutter");
            group.transform.SetParent(decor, false);
            group.transform.localPosition = new Vector3(s.x, 0f, s.y);
            group.transform.localRotation = Quaternion.Euler(0f, -s.yaw, 0f);

            var body = MakeLitMat(new Color(0.82f, 0.84f, 0.88f), 0.35f, 0.5f);
            var frame = MakeLitMat(new Color(0.55f, 0.57f, 0.62f), 0.35f, 0.45f);

            var header = GameObject.CreatePrimitive(PrimitiveType.Cube);
            header.name = "Header";
            header.transform.SetParent(group.transform, false);
            header.transform.localPosition = new Vector3(0f, h + 0.03f, 0f);
            header.transform.localScale = new Vector3(s.len + 0.08f, 0.06f, thick + 0.04f);
            header.GetComponent<Renderer>().sharedMaterial = frame;

            for (int i = -1; i <= 1; i += 2)
            {
                var rail = GameObject.CreatePrimitive(PrimitiveType.Cube);
                rail.name = "Rail";
                rail.transform.SetParent(group.transform, false);
                rail.transform.localPosition = new Vector3(i * (s.len * 0.5f + 0.025f), h * 0.5f, 0f);
                rail.transform.localScale = new Vector3(0.04f, h, thick + 0.02f);
                rail.GetComponent<Renderer>().sharedMaterial = frame;
            }

            var panel = GameObject.CreatePrimitive(PrimitiveType.Cube);
            panel.name = "Panel";
            panel.transform.SetParent(group.transform, false);
            panel.transform.localScale = new Vector3(s.len, h, thick);
            panel.GetComponent<Renderer>().sharedMaterial = body;

            var fs = group.AddComponent<FireShutter>();
            if (s.autoOpenSeconds > 0f) fs.autoOpenSeconds = s.autoOpenSeconds;
            fs.Configure(panel.transform, h);
        }

        static Material MakeLitMat(Color c, float metallic, float smooth)
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = "rt_lit" };
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Metallic", metallic);
            m.SetFloat("_Smoothness", smooth);
            return m;
        }

        // 충전소: 바닥 패치. 색 = colorHex > robotId의 markerColor > 흰색, 연한 톤으로 밝힘.
        static void SpawnDock(Dock d, Transform decor)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad);
            q.name = "DockPatch";
            q.transform.SetParent(decor, false);
            q.transform.localPosition = new Vector3(d.x, 0.006f, d.y);
            q.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            q.transform.localScale = new Vector3(d.r * 2f, d.r * 2f, 1f);
            var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            q.GetComponent<Renderer>().sharedMaterial = new Material(sh) { color = ResolveDockColor(d), name = "rt_dock" };
        }

        static Color ResolveDockColor(Dock d)
        {
            Color c = Color.white;
            if (!string.IsNullOrEmpty(d.colorHex) && ColorUtility.TryParseHtmlString(d.colorHex, out var pc))
                c = pc;
            else if (!string.IsNullOrEmpty(d.robotId))
            {
                var robots = App.ControlRoomState.Instance?.Robots;
                if (robots != null)
                    foreach (var r in robots)
                        if (r != null && r.robotId == d.robotId
                            && ColorUtility.TryParseHtmlString(r.markerColor, out var rc))
                        { c = rc; break; }
            }
            return Color.Lerp(c, Color.white, 0.55f); // 연한 톤
        }

        // 축정렬 긴 벽의 맵중심 쪽 면에 Canvas를 등간격 배치, 각 액자 위에 LightStand.
        static void SpawnCanvases(CanvasCfg c, Transform walls, Transform decor)
        {
            var prefab = Resources.Load<GameObject>("MuseumDecor/Canvas");
            var lightPrefab = c.light ? Resources.Load<GameObject>("MuseumDecor/LightStand") : null;
            if (prefab == null) { Debug.LogWarning("[MuseumDecor] Canvas prefab 없음"); return; }
            // 액자가 안쪽 면을 보도록 벽 무게중심을 "맵 중심" 근사로 사용.
            Vector3 centerLocal = Vector3.zero;
            int active = 0;
            for (int i = 0; i < walls.childCount; i++)
                if (walls.GetChild(i).gameObject.activeSelf) { centerLocal += walls.GetChild(i).localPosition; active++; }
            if (active > 0) centerLocal /= active;

            for (int i = 0; i < walls.childCount; i++)
            {
                var w = walls.GetChild(i);
                if (!w.gameObject.activeSelf || !w.name.StartsWith("wall_")) continue;
                float yawAbs = Mathf.Abs(Mathf.DeltaAngle(0f, w.localEulerAngles.y));
                if (yawAbs > 1f && Mathf.Abs(yawAbs - 180f) > 1f) continue; // ponytail: 축정렬 벽만(점유격자 벽 전제)
                var sc = w.localScale;
                bool alongX = sc.x >= sc.z;
                float len = alongX ? sc.x : sc.z, thick = alongX ? sc.z : sc.x;
                if (len < c.minWallLen) continue;
                Vector3 axis = alongX ? Vector3.right : Vector3.forward;
                Vector3 nrm = alongX ? Vector3.forward : Vector3.right;
                float side = Mathf.Sign(Vector3.Dot(centerLocal - w.localPosition, nrm));
                if (side == 0f) side = 1f;
                Vector3 outDir = nrm * side;
                float wallH = sc.y;

                // 벽당 레일 1개: LightStand 원작 패턴 = 수평 트랙레일(로컬 Z가 긴축, 실측 7.943m, 램프가 아래로).
                // 벽 상단에 벽과 평행하게 가로로 붙이고, 램프들이 아래 액자를 향해 매달린다.
                float railY = 0f, railScale = 0f;
                if (lightPrefab != null)
                {
                    const float RailNativeLen = 7.943f, RailNativeTop = 0.071f;
                    railScale = (len * 0.9f / RailNativeLen) * (c.lightScale > 0f ? c.lightScale : 1f);
                    railY = c.lightY > 0f ? c.lightY : wallH - RailNativeTop * railScale; // 레일 상단 ≈ 벽 상단
                    var lg = UnityEngine.Object.Instantiate(lightPrefab, decor, false);
                    lg.transform.localPosition = new Vector3(w.localPosition.x, railY, w.localPosition.z)
                                                 + outDir * (thick * 0.5f + 0.1f * railScale + 0.005f);
                    lg.transform.localRotation = Quaternion.LookRotation(axis, Vector3.up); // 레일 긴축(Z)을 벽 방향으로
                    lg.transform.localScale = Vector3.one * railScale;
                }

                int count = Mathf.Max(1, Mathf.FloorToInt(len / Mathf.Max(0.2f, c.everyMeters)));
                for (int k = 0; k < count; k++)
                {
                    float t = (k + 1f) / (count + 1f) - 0.5f;
                    Vector3 pos = w.localPosition + axis * (t * len) + outDir * (thick * 0.5f + 0.005f);
                    pos.y = c.y;
                    var go = UnityEngine.Object.Instantiate(prefab, decor, false);
                    go.transform.localPosition = pos;
                    go.transform.localRotation = Quaternion.LookRotation(outDir, Vector3.up); // ponytail: prefab forward=그림면 가정, 육안 후 조정
                    go.transform.localScale = Vector3.one * c.scale;
                    if (c.spotIntensity > 0f)
                    {
                        // 액자당 스팟 1개: 레일 높이에서 그림을 향해 내리쬠.
                        float pitch = c.lightPitchDeg > 0f ? c.lightPitchDeg : 70f;
                        var sp = new GameObject("PicLight").AddComponent<Light>();
                        sp.type = LightType.Spot;
                        sp.transform.SetParent(decor, false);
                        sp.transform.localPosition = new Vector3(pos.x, railY > 0f ? railY : wallH, pos.z) + outDir * 0.05f;
                        sp.transform.localRotation = Quaternion.Euler(pitch, Mathf.Atan2(-outDir.x, -outDir.z) * Mathf.Rad2Deg, 0f);
                        sp.range = 0.8f;
                        sp.spotAngle = 60f;
                        sp.intensity = c.spotIntensity;
                        sp.color = new Color(1f, 0.95f, 0.85f);
                    }
                }
            }
        }

        static void SpawnProp(Prop p, Transform decor)
        {
            if (string.IsNullOrEmpty(p.prefab)) return;
            var prefab = Resources.Load<GameObject>("MuseumDecor/" + p.prefab);
            if (prefab == null) { Debug.LogWarning($"[MuseumDecor] prefab 없음: {p.prefab}"); return; }
            var go = UnityEngine.Object.Instantiate(prefab, decor, false);
            go.transform.localPosition = new Vector3(p.x, 0f, p.y);
            go.transform.localRotation = Quaternion.Euler(0f, -p.yaw, 0f);
            go.transform.localScale = Vector3.one * (p.scale > 0f ? p.scale : 1f);
            SnapToFloor(go, decor);
        }

        // 팩 프리팹들은 피벗이 바닥이 아님(Statue는 바닥 위 1.34m, Stand는 꼭대기) — 렌더러 바운드로 접지.
        static void SnapToFloor(GameObject go, Transform decor)
        {
            var rends = go.GetComponentsInChildren<Renderer>();
            if (rends.Length == 0) return;
            var b = rends[0].bounds;
            foreach (var r in rends) b.Encapsulate(r.bounds);
            go.transform.position += Vector3.up * (decor.position.y - b.min.y);
        }

        static void StripColliders(GameObject rootGo)
        {
            foreach (var col in rootGo.GetComponentsInChildren<Collider>(true))
                UnityEngine.Object.Destroy(col);
        }

        // 에디터 ground-check용: json 파싱/프리팹 로드만 검증(씬 미변경). unityctl exec로 호출.
        public static void DebugLoad(string slotId)
        {
            var c = Load(slotId);
            Debug.Log(c == null
                ? $"[MuseumDecor] {slotId}: decor.json 없음/파싱실패"
                : $"[MuseumDecor] {slotId}: hide={c.hideWalls?.Length ?? 0} shutter={c.shutter != null && c.shutter.len > 0f} dock={c.dock != null && c.dock.r > 0f} canvas={c.canvas != null && c.canvas.scale > 0f} props={c.props?.Length ?? 0} straighten={c.straightenWalls} pfCanvas={Resources.Load<GameObject>("MuseumDecor/Canvas") != null} pfLightStand={Resources.Load<GameObject>("MuseumDecor/LightStand") != null} pfStatue={Resources.Load<GameObject>("MuseumDecor/Statue") != null} pfStand={Resources.Load<GameObject>("MuseumDecor/Stand") != null} pfTb3={Resources.Load<GameObject>("MuseumDecor/tb3_burger") != null}");
        }
    }
}
