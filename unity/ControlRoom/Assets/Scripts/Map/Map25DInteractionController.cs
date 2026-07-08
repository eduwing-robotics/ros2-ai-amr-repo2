// Map25DInteractionController.cs — 2.5D 우클릭 → 카메라 레이캐스트(y=0 평면) → map-frame 좌표 변환 → 2D와 같은 컨텍스트 메뉴/액션 재사용.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Map.Actions;

namespace URHYNIX.ControlRoom.Map
{
    public class Map25DInteractionController
    {
        readonly Camera cam;
        readonly VisualElement container;
        readonly MapContextMenuView menu;
        readonly MapActionRegistry registry;
        static readonly Plane GroundPlane = new Plane(Vector3.up, Vector3.zero);

        public Map25DInteractionController(VisualElement container, Camera cam,
            MapContextMenuView menu, MapActionRegistry registry)
        {
            this.container = container; this.cam = cam; this.menu = menu; this.registry = registry;
            container.RegisterCallback<PointerDownEvent>(OnDown);
        }

        // 컨테이너 로컬 픽셀 → 정규화 viewport(0~1, y-up) → 카메라 레이 → y=0 바닥평면 교차 → map-frame world(m).
        // hit에서 Map25DView.Offset을 빼면 Map25DView.Build()가 벽/바닥을 배치할 때 쓴 것과 같은 원점이라 2D의 worldX/worldY와 동일해진다.
        bool ToWorld(Vector2 screenPos, out float wx, out float wy)
        {
            wx = wy = 0f;
            float w = container.resolvedStyle.width, h = container.resolvedStyle.height;
            if (w <= 0f || h <= 0f || cam == null) return false;
            Vector2 local = container.WorldToLocal(screenPos);
            float u = local.x / w;
            float v = 1f - local.y / h;   // UI Toolkit y-down → viewport y-up
            Ray ray = cam.ViewportPointToRay(new Vector3(u, v, 0f));
            if (!GroundPlane.Raycast(ray, out float enter) || enter < 0f) return false;
            Vector3 hit = ray.GetPoint(enter);
            wx = hit.x - Map25DView.Offset.x;
            wy = hit.z - Map25DView.Offset.z;
            return true;
        }

        void OnDown(PointerDownEvent e)
        {
            if (e.button == 0) { menu.Close(); return; }   // 좌클릭 → 닫기 (2D와 동일 UX)
            if (e.button != 1) return;                       // 우클릭만 메뉴
            if (!ToWorld(e.position, out float wx, out float wy)) return;
#if UNITY_EDITOR
            Debug.Log($"[MapClick] map=({wx:F3},{wy:F3})"); // decor.json 좌표 교정용 — 에디터 전용(빌드 로그 오염 방지)
#endif

            var ctx = new MapClickContext
            {
                worldX = wx, worldY = wy,
                screenX = e.position.x, screenY = e.position.y,
                selectedRobotId = ControlRoomState.Instance.SelectedRobotId
            };
            menu.Open(ctx, registry.GetActions(ctx));
            e.StopPropagation();
        }
    }
}
