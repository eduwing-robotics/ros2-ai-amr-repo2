// ControlRoomSceneSetup.cs — ControlRoomMain.unity Scene을 batch 또는 메뉴로 자동 생성.
// PanelSettings 생성 → UIDocument GO + Binder → EventSystem → AppRoot/Simulation 3개 GO → Scene 저장.
// 재실행 시 기존 Scene 덮어씀.
//
// CLI 실행:
//   /Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app/Contents/MacOS/Unity \
//     -batchmode -quit -nographics \
//     -projectPath /Users/family/jason/URHYNIX/unity/ControlRoom \
//     -executeMethod URHYNIX.ControlRoom.Editor.ControlRoomSceneSetup.Setup \
//     -logFile /tmp/unity-controlroom-scene.log
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Simulation;
using URHYNIX.ControlRoom.UI;

namespace URHYNIX.ControlRoom.Editor
{
    public static class ControlRoomSceneSetup
    {
        const string ScenePath = "Assets/Scenes/ControlRoomMain.unity";
        const string UxmlPath = "Assets/UI/ControlRoomMain.uxml";
        const string PanelSettingsPath = "Assets/UI/ControlRoomPanelSettings.asset";

        [MenuItem("URHYNIX/Setup ControlRoom Scene")]
        public static void Setup()
        {
            var panel = LoadOrCreatePanelSettings();
            var uxml = AssetDatabase.LoadAssetAtPath<VisualTreeAsset>(UxmlPath);
            if (uxml == null)
            {
                Debug.LogError($"[ControlRoomSceneSetup] UXML 누락: {UxmlPath}");
                return;
            }

            // DefaultGameObjects → MainCamera + Directional Light 자동 포함 (Game View 렌더용)
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

            // 1) UIDocument GameObject + Binder (같은 GO, RequireComponent)
            // SerializedObject로 박는 이유: doc.panelSettings = panel; setter가 Unity 6.3에서
            // 직렬화 안 되는 케이스 발견 (Scene 저장 시 m_PanelSettings: fileID 0). 백킹 필드 직접 set.
            var uiGO = new GameObject("UIDocument");
            var doc = uiGO.AddComponent<UIDocument>();
            var serDoc = new SerializedObject(doc);
            serDoc.FindProperty("sourceAsset").objectReferenceValue = uxml;
            serDoc.FindProperty("m_PanelSettings").objectReferenceValue = panel;
            serDoc.ApplyModifiedPropertiesWithoutUndo();
            uiGO.AddComponent<ControlRoomBinder>();

            // 2) EventSystem + InputSystemUIInputModule (필수 — InputModule 빠지면 UI Toolkit 클릭 0 반응).
            // 2026-06-04 발견: 주석에 "자동 추가" 가정했으나 실제로는 수동 명시 필요. Phase 2.5 Scene이 이 버그로 0 반응.
            new GameObject("EventSystem",
                typeof(UnityEngine.EventSystems.EventSystem),
                typeof(UnityEngine.InputSystem.UI.InputSystemUIInputModule));

            // 3) App root
            var appGO = new GameObject("ControlRoomAppRoot");
            appGO.AddComponent<ControlRoomApp>();

            // 4) Simulation
            var simGO = new GameObject("Simulation");
            simGO.AddComponent<FakeSensorData>();
            simGO.AddComponent<DemoScenarioService>();

            // 5) ROS Bridge placeholder
            new GameObject("ROSBridge_Placeholder");

            // Scene 저장
            System.IO.Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Debug.Log($"[ControlRoomSceneSetup] Scene 저장: {ScenePath}");
        }

        static PanelSettings LoadOrCreatePanelSettings()
        {
            var existing = AssetDatabase.LoadAssetAtPath<PanelSettings>(PanelSettingsPath);
            if (existing != null) return existing;

            var panel = ScriptableObject.CreateInstance<PanelSettings>();
            panel.scaleMode = PanelScaleMode.ScaleWithScreenSize;
            panel.referenceResolution = new Vector2Int(1920, 1080);
            panel.match = 0.5f;
            AssetDatabase.CreateAsset(panel, PanelSettingsPath);
            AssetDatabase.SaveAssets();
            Debug.Log($"[ControlRoomSceneSetup] PanelSettings 생성: {PanelSettingsPath}");
            return panel;
        }
    }
}
