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
            frame.RegisterCallback<PointerUpEvent>(OnUp);
            frame.RegisterCallback<WheelEvent>(OnWheel);
        }

        // 휠 줌(커서 기준) + 중간버튼 드래그 팬 상태.
        bool panning;
        Vector2 lastPanPointer;
        float panAccum;

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

        // 포인터 패널좌표 → frame-local px. WorldToLocal은 Frame의 rotate(displayRotationDeg)까지
        // 역변환하므로 마커 배치(style.left/top, 회전된 Frame의 자식)와 같은 공간이 된다.
        // (e.localPosition은 rotate 변환을 반영 안 해 맵 회전 시 클릭이 어긋남 — 2026-06-25 수정.)
        Vector2 FrameLocal(IPointerEvent e) => viewport.Frame.WorldToLocal((Vector2)e.position);

        // 휠 = 커서 기준 줌인/아웃. delta.y<0(휠 업)=확대.
        void OnWheel(WheelEvent e)
        {
            if (!viewport.HasMap) return;
            float factor = e.delta.y < 0f ? 1.15f : 1f / 1.15f;
            viewport.SetZoom(viewport.Zoom * factor, viewport.Frame.WorldToLocal((Vector2)e.mousePosition));
            e.StopPropagation();
        }

        void OnUp(PointerUpEvent e)
        {
            if (!panning || e.button != 2) return;
            panning = false;
            viewport.Frame.ReleasePointer(e.pointerId);
            if (panAccum < 3f) viewport.ResetView();   // 거의 안 움직인 중간버튼 클릭 = 뷰 리셋
            e.StopPropagation();
        }

        void OnMove(PointerMoveEvent e)
        {
            if (panning)
            {
                Vector2 p = e.position;
                Vector2 d = p - lastPanPointer;
                lastPanPointer = p;
                panAccum += d.magnitude;
                viewport.Pan(d.x, d.y);
                return;
            }
            if (ToWorld(FrameLocal(e), out float wx, out float wy))
                hud.SetCoordinate(wx, wy);
        }

        void OnDown(PointerDownEvent e)
        {
            if (e.button == 2)   // 중간버튼 = 팬 시작
            {
                panning = true; panAccum = 0f;
                lastPanPointer = e.position;
                viewport.Frame.CapturePointer(e.pointerId);
                e.StopPropagation();
                return;
            }

            // 순찰 편집 모드: 좌클릭=지점 추가, 우클릭=마지막 제거 (레퍼런스 UX).
            if (ControlRoomState.Instance.PatrolEditMode && (e.button == 0 || e.button == 1))
            {
                if (!ToWorld(FrameLocal(e), out float ewx, out float ewy)) return;
                if (e.button == 0) PatrolService.Instance.Add(ewx, ewy);
                else PatrolService.Instance.RemoveLast();
                menu.Close();
                e.StopPropagation();
                return;
            }

            if (e.button == 0) { menu.Close(); return; }   // 좌클릭 → 닫기
            if (e.button != 1) return;                       // 우클릭만 메뉴
            if (!ToWorld(FrameLocal(e), out float wx, out float wy)) return;

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
