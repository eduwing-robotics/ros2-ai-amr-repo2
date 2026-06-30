// SdfWallSpawner.cs — Gazebo sdf의 정적 벽(box link)을 Unity Cube로 스폰. jaebo_v1.sdf 3D 뷰용.
// 입력 sdf의 각 <link name="wall_N">은 <pose>x y z r p yaw</pose> + <box><size>L W H</size>.
// map 프레임(REP103: x-forward, y-left, z-up, meters)을 천장뷰 Unity 좌표로 변환한다.
// ponytail: 좌표 매핑(아래 Convert)은 천장뷰 정합 1차안 — 2D 슬롯과 윤곽 비교 후 축·부호만 조정.
using System.Globalization;
using System.Text.RegularExpressions;
using UnityEngine;

namespace URHYNIX.ControlRoom.Map
{
    public static class SdfWallSpawner
    {
        // <link name="wall_N"> 다음의 첫 <pose>...</pose> 와 첫 <box><size>...</size> 를 잡는다(collision=visual 동일).
        static readonly Regex LinkRe = new Regex(
            "<link\\s+name=\"(wall_\\d+)\">\\s*<pose>([^<]+)</pose>.*?<box><size>([^<]+)</size>",
            RegexOptions.Singleline);

        // sdf 텍스트 → parent 아래 Cube들. 반환: 스폰한 벽 개수. wallMat은 공유 머티리얼.
        public static int Spawn(string sdfText, Transform parent, Material wallMat)
        {
            int n = 0;
            foreach (Match m in LinkRe.Matches(sdfText))
            {
                var pose = ParseFloats(m.Groups[2].Value); // x y z r p yaw
                var size = ParseFloats(m.Groups[3].Value); // L(x) W(y) H(z)
                if (pose.Length < 6 || size.Length < 3) continue;

                var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                cube.name = m.Groups[1].Value;
                cube.transform.SetParent(parent, false);
                cube.transform.localPosition = Convert(pose[0], pose[1], pose[2]);
                // size: L(map x)→Unity X, H(map z=높이)→Unity Y, W(map y)→Unity Z.
                cube.transform.localScale = new Vector3(size[0], size[2], size[1]);
                // yaw(map ccw about z) → Unity Y축 회전(천장뷰에서 화면 cw가 +라 부호 반전).
                cube.transform.localRotation = Quaternion.Euler(0f, -pose[5] * Mathf.Rad2Deg, 0f);
                if (wallMat != null) cube.GetComponent<Renderer>().sharedMaterial = wallMat;
                var col = cube.GetComponent<Collider>();
                if (col != null) Object.Destroy(col); // 표시 전용, 충돌 불필요
                n++;
            }
            return n;
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
