// opencode: 2026-06-29 - 하단 네비 4탭 pageTabs 추가 및 SetPage 연결. Coded with OpenCode; high-cost model review recommended.
// ControlRoomBinder.cs — UIDocument rootVisualElement와 모든 View를 결선.
// Awake에서 View 인스턴스 생성, 각 View가 자기 element 잡아 핸들러 박음.
// View 추가/삭제 시 본 파일만 갱신. 시계는 본 컴포넌트 Update에서 1초마다 갱신.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.UI.Records;

namespace URHYNIX.ControlRoom.UI
{
    [RequireComponent(typeof(UIDocument))]
    public class ControlRoomBinder : MonoBehaviour
    {
        UIDocument uiDoc;
        VisualElement root;

        PanelTabView leftTabs;
        PanelTabView rightTabs;
        PanelTabView bottomTabs;
        PanelTabView pageTabs;
        TopBarView topBar;
        RobotTabView robotTabs;
        PowerButtonView powerBtn;
        ScenarioPanelView scenario;
        MovePanelView move;
        ModePanelView mode;
        FeatureToggleListView featureToggles;
        WaypointListView waypoints;
        MapPanelView map;
        CameraPanelView cameraView;
        LogPanelView log;
        HomePageView homePage;
        ResponsePageView responsePage;
        RecordsPageView recordsPage;
        TelemetryPanelView telemetry;
        SensorCardListView sensors;
        HardwarePanelView hardware;
        FeatureInventoryView featureInventory;
        ProtectedTargetView protectedTargets;
        AlertPopupView alertPopup;
        RobotRoleCardView roleCard;
        QuickActionView quickActions;
        TeleopPadView teleopPad;

        float clockTick;

        void Awake()
        {
            uiDoc = GetComponent<UIDocument>();

            // PanelSettings 누락 fallback — Unity 6.3 SceneSetup 직렬화 버그 우회용.
            if (uiDoc.panelSettings == null)
            {
#if UNITY_EDITOR
                uiDoc.panelSettings = UnityEditor.AssetDatabase.LoadAssetAtPath<PanelSettings>(
                    "Assets/UI/ControlRoomPanelSettings.asset");
#endif
                if (uiDoc.panelSettings == null)
                    Debug.LogError("[ControlRoomBinder] PanelSettings null — Assets/UI/ControlRoomPanelSettings.asset 확인");
            }

            root = uiDoc.rootVisualElement;
            if (root == null)
            {
                Debug.LogError("[ControlRoomBinder] rootVisualElement null — UIDocument source asset 확인");
                return;
            }
            NormalizeTemplateLayout();

            leftTabs = new PanelTabView(root,
                new[] { "left-tab-ops", "left-tab-scenario", "left-tab-patrol" },
                new[] { "left-panel-ops", "left-panel-scenario", "left-panel-patrol" });
            rightTabs = new PanelTabView(root,
                new[] { "right-tab-status", "right-tab-sensors", "right-tab-inventory", "right-tab-targets" },
                new[] { "right-panel-status", "right-panel-sensors", "right-panel-inventory", "right-panel-targets" });
            bottomTabs = new PanelTabView(root,
                new[] { "bottom-tab-camera", "bottom-tab-log" },
                new[] { "bottom-panel-camera", "bottom-panel-log" });
            pageTabs = new PanelTabView(root,
                new[] { "btn-page-operations", "btn-page-home", "btn-page-response", "btn-page-records" },
                new[] { "page-operations", "page-home", "page-response", "page-records" },
                activeIndex: 0,
                onSelected: idx => ControlRoomState.Instance?.SetPage(PageIndexToName(idx)));

            topBar           = new TopBarView(root);
            robotTabs        = new RobotTabView(root);
            powerBtn         = new PowerButtonView(root);
            scenario         = new ScenarioPanelView(root);
            move             = new MovePanelView(root);
            mode             = new ModePanelView(root);
            featureToggles   = new FeatureToggleListView(root);
            waypoints        = new WaypointListView(root);
            map              = new MapPanelView(root);
            cameraView       = new CameraPanelView(root);
            log              = new LogPanelView(root);
            homePage         = new HomePageView(root);
            responsePage     = new ResponsePageView(this, root);
            recordsPage      = new RecordsPageView(this, root);
            telemetry        = new TelemetryPanelView(root);
            sensors          = new SensorCardListView(root);
            hardware         = new HardwarePanelView(root);
            featureInventory = new FeatureInventoryView(root);
            protectedTargets = new ProtectedTargetView(root);
            alertPopup       = new AlertPopupView(root);
            roleCard         = new RobotRoleCardView(root);
            quickActions     = new QuickActionView(root);
            teleopPad        = new TeleopPadView(root);

            ControlRoomEvents.RaiseLogAdded("system", "INFO", "Binder 초기화 완료 — 25 View 활성");
        }

        void NormalizeTemplateLayout()
        {
            Fill(root.Q<VisualElement>("center-map-slot"));
            Fill(root.Q<VisualElement>("center-bottom-slot"));
            Fill(root.Q<VisualElement>("map-panel"));
            Fill(root.Q<VisualElement>("map-2d-container"));
            Fill(root.Q<VisualElement>("camera-log-row"));
            Fill(root.Q<VisualElement>("bottom-panel-camera"));
            Fill(root.Q<VisualElement>("camera-panel"));
            Fill(root.Q<VisualElement>("camera-image"));

            foreach (var template in root.Query<TemplateContainer>().ToList())
            {
                template.style.minWidth = 0;
                template.style.flexDirection = FlexDirection.Column;

                foreach (var child in template.Children())
                {
                    if (child.name == "map-panel" || child.name == "camera-log-row")
                        Fill(template);
                    break;
                }
            }
        }

        static void Fill(VisualElement element)
        {
            if (element == null) return;
            element.style.flexGrow = 1;
            element.style.flexShrink = 1;
            element.style.flexBasis = 0;
            element.style.minHeight = 0;
            element.style.height = Length.Percent(100);
        }

        void Update()
        {
            // 시계 1초마다 갱신
            clockTick += Time.deltaTime;
            if (clockTick >= 1f)
            {
                clockTick = 0f;
                topBar?.UpdateClock(System.DateTime.Now.ToString("HH:mm:ss"));
            }
        }

        static string PageIndexToName(int idx)
        {
            switch (idx)
            {
                case 0: return "operations";
                case 1: return "home";
                case 2: return "response";
                case 3: return "records";
                default: return "operations";
            }
        }
    }
}
