// MapPanelView.cs — 중앙 맵 패널의 툴바/토글 담당. 2D 콘텐츠는 Map/MapView 서브시스템에 위임.
// 2026-06-16: 직접 텍스처 렌더를 걷어내고 MapView(Viewport/Image/Hud/[Phase2]Marker/[Phase3]Interaction)로 분리.
// 2.5D는 Map25DView(sdf 벽+궤도 카메라)에 위임. 3D는 RTAB-Map 점군 예정 안내만(placeholder). 이 파일은 토글만 유지(비대화 방지).
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Map;
using URHYNIX.ControlRoom.Services;

namespace URHYNIX.ControlRoom.UI
{
    public class MapPanelView
    {
        readonly Button btn2D;
        readonly Button btn25D;
        readonly Button btn3D;
        readonly VisualElement container2D;
        readonly VisualElement container25D;
        readonly VisualElement container3D;
        readonly MapView mapView;   // 2D 맵 서브시스템 — 2.5D가 ContextMenu/Actions를 이걸로 공유
        Label angleLabel;           // 회전 각도 표시
        Map25DView map25D;          // 2.5D sdf 궤도뷰 (첫 진입 시 lazy 생성)
        Map3DPointCloudView map3D;  // 3D RTAB-Map 점군 궤도뷰 (첫 진입 시 lazy 생성)

        public MapPanelView(VisualElement root)
        {
            btn2D        = root.Q<Button>("btn-map-2d");
            btn25D       = root.Q<Button>("btn-map-25d");
            btn3D        = root.Q<Button>("btn-map-3d");
            container2D  = root.Q<VisualElement>("map-2d-container");
            container25D = root.Q<VisualElement>("map-25d-container");
            container3D  = root.Q<VisualElement>("map-3d-container");

            if (btn2D != null) btn2D.clicked += () => SetMode("2d");
            if (btn25D != null) btn25D.clicked += () => SetMode("25d");
            if (btn3D != null) btn3D.clicked += () => SetMode("3d");

            if (container2D != null) mapView = new MapView(container2D, root);

            SetupSlotDropdown(root);
            SetupPatrolControls(root);

            // 맵 회전 컨트롤 (SLAM 원점↔실제 경기장 정렬 보정). 맵+마커 함께 회전.
            var btnCcw = root.Q<Button>("btn-map-rot-ccw");
            var btnCw  = root.Q<Button>("btn-map-rot-cw");
            angleLabel = root.Q<Label>("map-rot-angle");
            if (angleLabel != null) angleLabel.style.minWidth = 34;
            if (mapView != null)
            {
                if (btnCcw != null) btnCcw.clicked += () => RotateMap(-5f);
                if (btnCw  != null) btnCw.clicked  += () => RotateMap(5f);
                if (angleLabel != null) angleLabel.text = $"{mapView.Viewport.RotationDeg:0}°"; // 시작 시 디폴트 반영
            }

            ControlRoomEvents.OnMapViewModeChanged += SyncUI;
            SyncUI(ControlRoomState.Instance.MapViewMode);
        }

        // 맵 슬롯 드롭다운: 저장맵 슬롯 + 라이브(SLAM)를 나열, 선택 시 슬롯 전환 이벤트 발화.
        void SetupSlotDropdown(VisualElement root)
        {
            var dd = root.Q<DropdownField>("map-slot-dropdown");
            if (dd == null) return;

            var choices = new List<string>();
            foreach (var id in MapCatalog.SlotIds()) choices.Add(id);
            choices.Add(MapCatalog.LiveLabel);   // 라이브(SLAM)
            dd.choices = choices;

            // 초기값: 마지막 선택 슬롯(없으면 첫 슬롯, 그것도 없으면 라이브).
            string active = PlayerPrefs.GetString(StaticMapLoader.ActiveSlotPrefKey, "");
            string initial = (active == MapCatalog.LiveSlotId) ? MapCatalog.LiveLabel
                           : (choices.Contains(active) ? active : choices[0]);
            dd.SetValueWithoutNotify(initial);

            dd.RegisterValueChangedCallback(evt =>
            {
                string slot = (evt.newValue == MapCatalog.LiveLabel) ? MapCatalog.LiveSlotId : evt.newValue;
                ControlRoomEvents.RaiseMapSlotSelected(slot);
                ControlRoomEvents.RaiseLogAdded("map", "INFO", $"맵 슬롯 전환: {evt.newValue}");
            });
        }

        // 순찰 편집 토글 + 전체삭제 버튼. 토글 ON이면 맵 좌클릭=추가, 우클릭=마지막제거.
        void SetupPatrolControls(VisualElement root)
        {
            var btnEdit = root.Q<Button>("btn-patrol-edit");
            var btnClear = root.Q<Button>("btn-patrol-clear");
            if (btnEdit != null)
                btnEdit.clicked += () =>
                {
                    bool on = !ControlRoomState.Instance.PatrolEditMode;
                    ControlRoomState.Instance.SetPatrolEditMode(on);
                    btnEdit.EnableInClassList("active", on);
                    ControlRoomEvents.RaiseLogAdded("map", "INFO",
                        on ? "순찰 편집 ON — 좌클릭=지점추가, 우클릭=마지막제거" : "순찰 편집 OFF");
                };
            if (btnClear != null)
                btnClear.clicked += () => PatrolService.Instance.Clear();

            var btnRun = root.Q<Button>("btn-patrol-run");
            if (btnRun != null)
                btnRun.clicked += () =>
                {
                    if (!ActiveRobotService.Has(ActiveRobotService.CapPatrol))
                    {
                        ControlRoomEvents.RaiseLogAdded("patrol", "WARN",
                            $"{ActiveRobotService.CurrentId}는 순찰 미지원(capabilities)");
                        return;
                    }
                    ControlRoomEvents.RaisePatrolRunRequested(ControlRoomState.Instance.SelectedRobotId);
                };
        }

        void RotateMap(float delta)
        {
            mapView.Viewport.AddRotation(delta);
            float deg = mapView.Viewport.RotationDeg;
            PlayerPrefs.SetFloat(MapView.RotationPrefKey, deg);  // 현재값을 디폴트로 영속
            PlayerPrefs.Save();
            if (angleLabel != null) angleLabel.text = $"{deg:0}°";
            Debug.Log($"[MapView] rotation = {deg:0}° (saved as default)");
        }

        void SetMode(string mode)
        {
            ControlRoomState.Instance.SetMapViewMode(mode);
            if (mode == "25d") EnsureMap25D();
            if (mode == "3d") EnsureMap3D();
            map25D?.SetActive(mode == "25d");
            map3D?.SetActive(mode == "3d");
            ControlRoomEvents.RaiseLogAdded("map", "INFO", ModeLabel(mode));
        }

        static string ModeLabel(string mode) => mode switch
        {
            "25d" => "2.5D 맵 모드 (드래그로 회전)",
            "3d"  => "3D 맵 — RTAB-Map 점군 (드래그로 회전)",
            _     => "2D 맵 모드",
        };

        // 첫 2.5D 진입 시 Map25DView를 만들고 RenderTexture를 container25D 배경으로 건다 + 드래그 궤도 회전 연결.
        // 현재 로드된 슬롯(StaticMapLoader)의 .sdf로 벽을 세운다 — jaebo_v1이면 89벽, sdf 없는 슬롯이면 바닥만.
        void EnsureMap25D()
        {
            if (map25D != null || container25D == null) return;
            var go = new GameObject("Map25DView");
            map25D = go.AddComponent<Map25DView>();
            string slot = string.IsNullOrEmpty(StaticMapLoader.LatestSlotId) ? "jaebo_v1" : StaticMapLoader.LatestSlotId;
            map25D.Build(slot, StaticMapLoader.LatestOriginX, StaticMapLoader.LatestOriginY,
                         StaticMapLoader.LatestWidth, StaticMapLoader.LatestHeight,
                         StaticMapLoader.LatestResolution > 0f ? StaticMapLoader.LatestResolution : 0.05f);
            if (map25D.Texture != null)
            {
                container25D.style.backgroundImage = Background.FromRenderTexture(map25D.Texture);
                var overlay = container25D.Q<Label>("map-25d-overlay");
                if (overlay != null) overlay.style.display = DisplayStyle.None;
                map25D.AttachOrbitControl(container25D);
                if (mapView != null)
                    new Map25DInteractionController(container25D, map25D.Cam, mapView.ContextMenu, mapView.Actions);
            }
        }

        // 첫 3D 진입 시 Map3DPointCloudView를 만들고 RenderTexture를 container3D 배경으로 건다 + 드래그 궤도 회전 연결.
        void EnsureMap3D()
        {
            if (map3D != null || container3D == null) return;
            var go = new GameObject("Map3DPointCloudView");
            map3D = go.AddComponent<Map3DPointCloudView>();
            bool ok = map3D.Build("PointClouds/arena_shared_room");
            if (ok && map3D.Texture != null)
            {
                container3D.style.backgroundImage = Background.FromRenderTexture(map3D.Texture);
                var overlay = container3D.Q<Label>("map-3d-overlay");
                if (overlay != null) overlay.style.display = DisplayStyle.None;
                map3D.AttachOrbitControl(container3D);
                // 2026-07-03: 3D는 보기 전용으로 스코프 축소 — 점군이 성겨서 클릭 좌표 판정이 불안정했음.
                // 좌표 입력은 2D/2.5D에서. 우클릭은 별도 리스너가 없어 자연스럽게 무반응.
            }
        }

        void SyncUI(string mode)
        {
            btn2D?.EnableInClassList("active", mode == "2d");
            btn25D?.EnableInClassList("active", mode == "25d");
            btn3D?.EnableInClassList("active", mode == "3d");
            container2D?.EnableInClassList("hidden", mode != "2d");
            container25D?.EnableInClassList("hidden", mode != "25d");
            container3D?.EnableInClassList("hidden", mode != "3d");
        }
    }
}
