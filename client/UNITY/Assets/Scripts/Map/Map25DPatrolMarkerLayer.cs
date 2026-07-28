// Map25DPatrolMarkerLayer.cs — 2.5D/3D 공용 순회지점(웨이포인트) 마커+연결선+번호라벨. 2D PatrolMarkerLayer와 같은
// PatrolService.Points/OnPatrolChanged 구독, 3D 오브젝트(구+LineRenderer+TextMesh)로 표시. 없으면 우클릭
// "순회지점 추가"가 데이터는 쌓이는데(PatrolService) 화면엔 아무 것도 안 보이는 원인이 된다.
// layer/billboardCam을 주면 3D 점군 뷰처럼 별도 카메라·레이어에도 같은 클래스를 그대로 재사용 가능.
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map
{
    public class Map25DPatrolMarkerLayer
    {
        const float DotRadius = 0.08f, Y = 0.05f;
        static readonly Color DotColor = new Color(1f, 0.584f, 0f, 1f); // 토스 orange500 #FF9500

        readonly List<Transform> dotPool = new List<Transform>();
        readonly List<TextMesh> labelPool = new List<TextMesh>();
        readonly LineRenderer line;
        readonly Transform parent;
        readonly int layer;
        readonly Camera billboardCam;

        public Map25DPatrolMarkerLayer(Transform parent, int layer = 0, Camera billboardCam = null)
        {
            this.parent = parent;
            this.layer = layer;
            this.billboardCam = billboardCam;

            var lineGo = new GameObject("PatrolLines25D");
            lineGo.transform.SetParent(parent, false);
            lineGo.layer = layer;
            line = lineGo.AddComponent<LineRenderer>();
            line.material = MakeMat(DotColor);
            line.startColor = line.endColor = DotColor;
            line.startWidth = line.endWidth = 0.025f;
            line.positionCount = 0;
            line.useWorldSpace = false;

            ControlRoomEvents.OnPatrolChanged += Refresh;
            Refresh();
        }

        void Refresh()
        {
            var pts = PatrolService.Instance.Points;
            EnsureDots(pts.Count);

            line.positionCount = pts.Count;
            for (int i = 0; i < dotPool.Count; i++)
            {
                bool active = i < pts.Count;
                dotPool[i].gameObject.SetActive(active);
                if (!active) continue;
                Vector3 c = Map25DView.Offset + new Vector3(pts[i].x, Y, pts[i].y);
                dotPool[i].localPosition = c;
                line.SetPosition(i, c);
                labelPool[i].text = (i + 1).ToString();
                labelPool[i].transform.localPosition = c + Vector3.up * (DotRadius * 2.2f);
            }
        }

        void EnsureDots(int n)
        {
            while (dotPool.Count < n)
            {
                var go = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                go.name = "PatrolDot25D";
                go.transform.SetParent(parent, false);
                go.layer = layer;
                go.transform.localScale = Vector3.one * (DotRadius * 2f);
                go.GetComponent<Renderer>().sharedMaterial = MakeMat(DotColor);
                DestroyCollider(go);
                go.SetActive(false);
                dotPool.Add(go.transform);

                var labelGo = new GameObject("PatrolDotLabel25D");
                labelGo.transform.SetParent(parent, false);
                labelGo.layer = layer;
                labelGo.transform.localScale = Vector3.one * 0.15f;
                var tm = labelGo.AddComponent<TextMesh>();
                tm.fontSize = 48;
                tm.characterSize = 0.15f;
                tm.color = Color.white;
                tm.anchor = TextAnchor.LowerCenter;
                tm.alignment = TextAlignment.Center;
                var mr = labelGo.GetComponent<MeshRenderer>();
                if (mr != null) mr.sharedMaterial.renderQueue = 4000; // 항상 다른 지오메트리 위로
                if (billboardCam != null)
                {
                    var bb = labelGo.AddComponent<Billboard>();
                    bb.target = billboardCam;
                }
                labelPool.Add(tm);
            }
        }

        public void Dispose() => ControlRoomEvents.OnPatrolChanged -= Refresh;

        static void DestroyCollider(GameObject go)
        {
            var col = go.GetComponent<Collider>();
            if (col != null) Object.Destroy(col);
        }

        static Material MakeMat(Color c)
        {
            var sh = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
            return new Material(sh) { color = c, name = "rt_patrol" }; // rt_ = Map25DView 파괴 시 정리 대상
        }
    }
}
