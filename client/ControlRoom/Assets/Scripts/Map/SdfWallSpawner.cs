// SdfWallSpawner.cs — Gazebo sdf의 정적 벽(box link)을 Unity Cube로 스폰. jaebo_v1.sdf 3D 뷰용.
// 입력 sdf의 각 <link name="wall_N">은 <pose>x y z r p yaw</pose> + <box><size>L W H</size>.
// map 프레임(REP103: x-forward, y-left, z-up, meters)을 천장뷰 Unity 좌표로 변환한다.
// straighten: 점유격자 추적의 계단식 벽을 직선 병합 + 스펙클 파편 제거 (표시 전용 — 로봇측 pgm 불변).
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public static class SdfWallSpawner
    {
        const float PerpTol = 0.06f; // 계단 오프셋 허용치 — 같은 직선으로 볼 수직거리
        const float GapTol = 0.12f;  // 이 이하 틈만 이어붙임(문/통로 0.3m+ 보존)
        const float MinLen = 0.12f;  // 병합 후 이보다 짧은 파편(스펙클)은 버림

        // <link name="wall_N"> 다음의 첫 <pose>...</pose> 와 첫 <box><size>...</size> 를 잡는다(collision=visual 동일).
        static readonly Regex LinkRe = new Regex(
            "<link\\s+name=\"(wall_\\d+)\">\\s*<pose>([^<]+)</pose>.*?<box><size>([^<]+)</size>",
            RegexOptions.Singleline);

        struct Wall { public string name; public float cx, cy, cz, lx, ly, h, yawDeg; }

        // sdf 텍스트 → parent 아래 Cube들. 반환: 스폰한 벽 개수. wallMat은 공유 머티리얼.
        // tilePerMeter: 벽마다 머티리얼 인스턴스 떠서 1타일/1m 타일링. heightOverride: >0이면 전 벽 높이 통일(접지 유지).
        // exclude: 스폰 제외할 링크 이름(차폐벽 일자 대체 등). straighten: 계단식 병합 on/off.
        public static int Spawn(string sdfText, Transform parent, Material wallMat,
            bool tilePerMeter = false, float heightOverride = 0f, bool straighten = false, string[] exclude = null)
        {
            var list = Parse(sdfText, exclude);
            if (straighten) list = Straighten(list);
            foreach (var w in list) SpawnCube(w, parent, wallMat, tilePerMeter, heightOverride);
            return list.Count;
        }

        static List<Wall> Parse(string sdfText, string[] exclude)
        {
            var list = new List<Wall>();
            foreach (Match m in LinkRe.Matches(sdfText))
            {
                if (exclude != null && System.Array.IndexOf(exclude, m.Groups[1].Value) >= 0) continue;
                var pose = ParseFloats(m.Groups[2].Value); // x y z r p yaw
                var size = ParseFloats(m.Groups[3].Value); // L(x) W(y) H(z)
                if (pose.Length < 6 || size.Length < 3) continue;
                list.Add(new Wall
                {
                    name = m.Groups[1].Value, cx = pose[0], cy = pose[1], cz = pose[2],
                    lx = size[0], ly = size[1], h = size[2], yawDeg = pose[5] * Mathf.Rad2Deg
                });
            }
            return list;
        }

        // 축정렬 벽을 방향별로 (수직거리 PerpTol 이내 클러스터 → 틈 GapTol 이내 구간 병합) 직선화.
        static List<Wall> Straighten(List<Wall> input)
        {
            var outp = new List<Wall>();
            var axisX = new List<Wall>();
            var axisY = new List<Wall>();
            foreach (var w in input)
            {
                bool axisAligned = Mathf.Abs(Mathf.DeltaAngle(w.yawDeg, 0f)) < 1f
                                || Mathf.Abs(Mathf.DeltaAngle(w.yawDeg, 180f)) < 1f;
                if (!axisAligned) { outp.Add(w); continue; } // 회전 벽은 그대로(점유격자 sdf엔 없음)
                if (w.lx >= w.ly) axisX.Add(w); else axisY.Add(w);
            }
            MergeAxis(axisX, true, outp);
            MergeAxis(axisY, false, outp);
            return outp;
        }

        static void MergeAxis(List<Wall> ws, bool alongX, List<Wall> outp)
        {
            ws.Sort((a, b) => Perp(a, alongX).CompareTo(Perp(b, alongX)));
            int i = 0;
            while (i < ws.Count)
            {
                int j = i + 1;
                while (j < ws.Count && Perp(ws[j], alongX) - Perp(ws[j - 1], alongX) <= PerpTol) j++;
                MergeCluster(ws.GetRange(i, j - i), alongX, outp);
                i = j;
            }
        }

        static float Perp(Wall w, bool alongX) => alongX ? w.cy : w.cx;
        static float Start(Wall w, bool alongX) => alongX ? w.cx - w.lx * 0.5f : w.cy - w.ly * 0.5f;
        static float End(Wall w, bool alongX) => alongX ? w.cx + w.lx * 0.5f : w.cy + w.ly * 0.5f;
        static float Len(Wall w, bool alongX) => alongX ? w.lx : w.ly;
        static float Thick(Wall w, bool alongX) => alongX ? w.ly : w.lx;

        static void MergeCluster(List<Wall> cluster, bool alongX, List<Wall> outp)
        {
            cluster.Sort((a, b) => Start(a, alongX).CompareTo(Start(b, alongX)));
            int i = 0;
            while (i < cluster.Count)
            {
                float end = End(cluster[i], alongX);
                int j = i + 1;
                while (j < cluster.Count && Start(cluster[j], alongX) - end <= GapTol)
                {
                    end = Mathf.Max(end, End(cluster[j], alongX));
                    j++;
                }
                var g = cluster.GetRange(i, j - i);
                float s = Start(g[0], alongX), len = end - s;
                if (len >= MinLen)
                {
                    float wsum = 0f, psum = 0f, thick = 0f, h = 0f;
                    foreach (var w in g)
                    {
                        wsum += Len(w, alongX);
                        psum += Perp(w, alongX) * Len(w, alongX);
                        thick = Mathf.Max(thick, Thick(w, alongX));
                        h = Mathf.Max(h, w.h);
                    }
                    float perp = psum / Mathf.Max(0.0001f, wsum), mid = (s + end) * 0.5f;
                    outp.Add(new Wall
                    {
                        name = $"wall_m{outp.Count}",
                        cx = alongX ? mid : perp, cy = alongX ? perp : mid, cz = h * 0.5f,
                        lx = alongX ? len : thick, ly = alongX ? thick : len, h = h, yawDeg = 0f
                    });
                }
                i = j;
            }
        }

        static void SpawnCube(Wall w, Transform parent, Material wallMat, bool tilePerMeter, float heightOverride)
        {
            var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
            cube.name = w.name;
            cube.transform.SetParent(parent, false);
            float h = heightOverride > 0f ? heightOverride : w.h;
            var pos = Convert(w.cx, w.cy, w.cz);
            if (heightOverride > 0f) pos.y = h * 0.5f; // sdf pose z=중심높이 전제 — 접지 유지
            cube.transform.localPosition = pos;
            // size: L(map x)→Unity X, H(map z=높이)→Unity Y, W(map y)→Unity Z.
            cube.transform.localScale = new Vector3(w.lx, h, w.ly);
            // yaw(map ccw about z) → Unity Y축 회전(천장뷰에서 화면 cw가 +라 부호 반전).
            cube.transform.localRotation = Quaternion.Euler(0f, -w.yawDeg, 0f);
            if (wallMat != null)
            {
                var rend = cube.GetComponent<Renderer>();
                if (tilePerMeter)
                {
                    var inst = new Material(wallMat) { name = "rt_wall" }; // rt_ = Map25DView 파괴 시 정리 대상
                    inst.mainTextureScale = new Vector2(Mathf.Max(w.lx, w.ly), h);
                    rend.sharedMaterial = inst;
                }
                else
                    rend.sharedMaterial = wallMat;
            }
            var col = cube.GetComponent<Collider>();
            if (col != null) Object.Destroy(col); // 표시 전용, 충돌 불필요
        }

        // map(x,y,z) → Unity(x=map x, y=map z 높이, z=map y). 천장뷰에서 위에서 보면 2D 점유격자와 같은 평면.
        public static Vector3 Convert(float mx, float my, float mz) => new Vector3(mx, mz, my);

        static float[] ParseFloats(string s)
        {
            var parts = s.Trim().Split(new[] { ' ', '\t', '\n', '\r' }, System.StringSplitOptions.RemoveEmptyEntries);
            var f = new float[parts.Length];
            for (int i = 0; i < parts.Length; i++)
                float.TryParse(parts[i], NumberStyles.Float, CultureInfo.InvariantCulture, out f[i]);
            return f;
        }
    }
}
