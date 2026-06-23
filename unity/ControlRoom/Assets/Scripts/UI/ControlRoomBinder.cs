// ControlRoomBinder.cs — UIDocument rootVisualElement와 모든 View를 결선.
// Awake에서 View 인스턴스 생성, 각 View가 자기 element 잡아 핸들러 박음.
// View 추가/삭제 시 본 파일만 갱신. 시계는 본 컴포넌트 Update에서 1초마다 갱신.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    [RequireComponent(typeof(UIDocument))]
    public class ControlRoomBinder : MonoBehaviour
    {
        UIDocument uiDoc;
        VisualElement root;

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
        TelemetryPanelView telemetry;
        SensorCardListView sensors;
        HardwarePanelView hardware;
        ProtectedTargetView protectedTargets;
        AlertPopupView alertPopup;

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

            topBar         = new TopBarView(root);
            robotTabs      = new RobotTabView(root);
            powerBtn       = new PowerButtonView(root);
            scenario       = new ScenarioPanelView(root);
            move           = new MovePanelView(root);
            mode           = new ModePanelView(root);
            featureToggles = new FeatureToggleListView(root);
            waypoints      = new WaypointListView(root);
            map            = new MapPanelView(root);
            cameraView     = new CameraPanelView(root);
            log            = new LogPanelView(root);
            telemetry      = new TelemetryPanelView(root);
            sensors          = new SensorCardListView(root);
            hardware         = new HardwarePanelView(root);
            protectedTargets = new ProtectedTargetView(root);
            alertPopup       = new AlertPopupView(root);

            ControlRoomEvents.RaiseLogAdded("system", "INFO", "Binder 초기화 완료 — 16 View 활성");
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
    }
}
