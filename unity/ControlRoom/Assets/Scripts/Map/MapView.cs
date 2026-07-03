// opencode: 2026-06-29 - 맵 캔버스 배경색 토스 grey900으로 변환. Coded with OpenCode; high-cost model review recommended.
// MapView.cs — 맵 2D 서브시스템 오케스트레이터(thin). 레이어 스택을 조립·연결만 한다.
// 책임 분리: Viewport(프레임 비율맞춤) / ImageLayer(텍스처) / HudLayer(스케일·좌표) / [Phase2] Marker / [Phase3] Interaction.
// MapPanelView가 2D 컨테이너를 넘겨 생성. 무거운 로직은 각 레이어가 보유(파일 비대화 방지).
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Map.Actions;

namespace URHYNIX.ControlRoom.Map
{
    public class MapView
    {
        // 회전 보정각 영속 키 — 마지막 회전값이 다음 실행의 디폴트가 됨.
        public const string RotationPrefKey = "urhynix.map.displayRotationDeg";

        public MapViewport Viewport { get; }
        public MapHudLayer Hud { get; }

        readonly MapImageLayer imageLayer;
        readonly MapMarkerLayer markerLayer;
        readonly PatrolMarkerLayer patrolLayer;
        readonly MapContextMenuView contextMenu;
        readonly MapInteractionController interaction;
        readonly Label emptyHint;

        // 2.5D(Map25DInteractionController)가 같은 메뉴/액션 레지스트리를 재사용 — 2D/2.5D는 동시 표시 안 되므로 공유해도 안전.
        public MapContextMenuView ContextMenu => contextMenu;
        public MapActionRegistry Actions { get; }

        // root: 컨텍스트 메뉴가 패널 위에 뜨도록 최상위 VisualElement.
        public MapView(VisualElement container2D, VisualElement root)
        {
            // 컨테이너 크기 확보 — 목업 제거 때 .map-placeholder(flex-grow/min-height)가 빠져 찌그러지던 것 보정.
            container2D.style.flexGrow = 1;
            container2D.style.minHeight = 320;
            // 테마 캔버스 — 비율맞춤 후 남는 여백이 이 색으로 채워져 "의도된 배경"이 됨.
            container2D.style.backgroundColor = new Color(0.125f, 0.149f, 0.196f, 1f); // 토스 grey900 #202632

            Viewport = new MapViewport(container2D);
            imageLayer = new MapImageLayer(Viewport);
            markerLayer = new MapMarkerLayer(Viewport);
            patrolLayer = new PatrolMarkerLayer(Viewport);   // 순찰 웨이포인트 번호+연결선
            Hud = new MapHudLayer(container2D, Viewport);

            contextMenu = new MapContextMenuView(root);
            Actions = new MapActionRegistry();
            interaction = new MapInteractionController(Viewport, Hud, contextMenu, Actions);

            // 회전 보정각 적용: PlayerPrefs(마지막 값) → 없으면 0(회전 없음).
            // 예전엔 office_base_map.json(레거시, 맵 슬롯 시스템과 무관)의 displayRotationDeg를 읽었으나,
            // 실제 활성 슬롯(arena_shared 등)과 연결되지 않는 값이라 드리프트였다 — 안전한 항등 기본값 0으로 교체.
            Viewport.SetRotation(PlayerPrefs.GetFloat(RotationPrefKey, 0f));

            // "수신 대기" 힌트(UXML) — 첫 맵으로 frame이 생기면 숨김.
            emptyHint = container2D.Q<Label>("map-empty-hint");
            if (emptyHint != null) emptyHint.BringToFront();
            Viewport.OnFrameChanged += HideHintOnce;
        }

        void HideHintOnce()
        {
            if (emptyHint == null) return;
            emptyHint.style.display = DisplayStyle.None;
            Viewport.OnFrameChanged -= HideHintOnce;
        }

        public void Dispose()
        {
            imageLayer?.Dispose();
            markerLayer?.Dispose();
            patrolLayer?.Dispose();
        }
    }
}
