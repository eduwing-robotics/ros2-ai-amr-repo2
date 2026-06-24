// MapPanelView.cs — 중앙 맵 패널의 툴바/토글 담당. 2D 콘텐츠는 Map/MapView 서브시스템에 위임.
// 2026-06-16: 직접 텍스처 렌더를 걷어내고 MapView(Viewport/Image/Hud/[Phase2]Marker/[Phase3]Interaction)로 분리.
// 3D는 Phase 6 안내. 책임분리로 이 파일은 토글만 유지(비대화 방지).
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
        readonly Button btn3D;
        readonly VisualElement container2D;
        readonly VisualElement container3D;
        readonly MapView mapView;   // 2D 맵 서브시스템
        Label angleLabel;           // 회전 각도 표시

        public MapPanelView(VisualElement root)
        {
            btn2D       = root.Q<Button>("btn-map-2d");
            btn3D       = root.Q<Button>("btn-map-3d");
            container2D = root.Q<VisualElement>("map-2d-container");
            container3D = root.Q<VisualElement>("map-3d-container");

            if (btn2D != null) btn2D.clicked += () => SetMode("2d");
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
            ControlRoomEvents.RaiseLogAdded("map", "INFO",
                mode == "3d"
                    ? "3D 맵 — Phase 6에서 URDF Importer로 채워질 예정"
                    : "2D 맵 모드");
        }

        void SyncUI(string mode)
        {
            bool is3D = mode == "3d";
            btn2D?.EnableInClassList("active", !is3D);
            btn3D?.EnableInClassList("active",  is3D);
            container2D?.EnableInClassList("hidden",  is3D);
            container3D?.EnableInClassList("hidden", !is3D);
        }
    }
}
