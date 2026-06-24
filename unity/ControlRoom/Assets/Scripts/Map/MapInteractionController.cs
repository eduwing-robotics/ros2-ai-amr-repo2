// MapInteractionController.cs — map-frame 포인터 입력. hover→HUD 좌표, 우클릭→world 좌표+컨텍스트 메뉴.
// 좌표 변환은 MapCoordinateSystem 1곳에 위임. 액션 목록은 MapActionRegistry가 제공.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Map.Actions;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.Map
{
    public class MapInteractionController
    {
        readonly MapViewport viewport;
        readonly MapHudLayer hud;
        readonly MapContextMenuView menu;
        readonly MapActionRegistry registry;

        public MapInteractionController(MapViewport viewport, MapHudLayer hud,
            MapContextMenuView menu, MapActionRegistry registry)
        {
            this.viewport = viewport;
            this.hud = hud;
            this.menu = menu;
            this.registry = registry;

            var frame = viewport.Frame;
            frame.RegisterCallback<PointerMoveEvent>(OnMove);
            frame.RegisterCallback<PointerLeaveEvent>(_ => hud.ClearCoordinate());
            frame.RegisterCallback<PointerDownEvent>(OnDown);
        }

        bool ToWorld(Vector2 framePx, out float wx, out float wy)
        {
            wx = wy = 0f;
            if (!viewport.HasMap) return false;
            float fw = viewport.FrameWidth, fh = viewport.FrameHeight;
            if (fw <= 0f || fh <= 0f) return false;
            var w = MapCoordinateSystem.FramePxToWorld(framePx,
                viewport.OriginX, viewport.OriginY, viewport.MapW, viewport.MapH, fw, fh);
            wx = w.x; wy = w.y;
            return true;
        }

        void OnMove(PointerMoveEvent e)
        {
            if (ToWorld((Vector2)e.localPosition, out float wx, out float wy))
                hud.SetCoordinate(wx, wy);
        }

        void OnDown(PointerDownEvent e)
        {
            // 순찰 편집 모드: 좌클릭=지점 추가, 우클릭=마지막 제거 (레퍼런스 UX).
            if (ControlRoomState.Instance.PatrolEditMode && (e.button == 0 || e.button == 1))
            {
                if (!ToWorld((Vector2)e.localPosition, out float ewx, out float ewy)) return;
                if (e.button == 0) PatrolService.Instance.Add(ewx, ewy);
                else PatrolService.Instance.RemoveLast();
                menu.Close();
                e.StopPropagation();
                return;
            }

            if (e.button == 0) { menu.Close(); return; }   // 좌클릭 → 닫기
            if (e.button != 1) return;                       // 우클릭만 메뉴
            if (!ToWorld((Vector2)e.localPosition, out float wx, out float wy)) return;

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
