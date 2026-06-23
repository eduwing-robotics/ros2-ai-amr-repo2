// CameraPanelSetup.cs — URHYNIX 박물관 시연 카메라 라이브 패널 자동 추가
//
// 사용:
//   Unity Editor 메뉴: URHYNIX → Setup Camera Panels
//   또는 CLI batch mode:
//     /Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app/Contents/MacOS/Unity \
//       -batchmode -quit \
//       -projectPath /Users/family/jason/URHYNIX/unity-smoke \
//       -executeMethod CameraPanelSetup.Setup \
//       -logFile /tmp/unity_camera_setup.log
//
// 동작:
//   1. SampleScene.unity 열기
//   2. Canvas (Screen Space Overlay) 찾거나 생성
//   3. GenjiCameraPanel — RawImage + CameraStreamPanel(topic=/tb3_2/.../compressed, label=젠지)
//   4. T1CameraPanel — RawImage + CameraStreamPanel(topic=/tb3_1/.../compressed, label=티원)
//   5. Scene 저장
//
// 확장성: 새 카메라 추가하려면 Setup() 안의 AddCameraPanel 호출 한 줄만 더 박으면 됨.
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

public static class CameraPanelSetup
{
    const string ScenePath = "Assets/Scenes/SampleScene.unity";

    [MenuItem("URHYNIX/Setup Camera Panels")]
    public static void Setup()
    {
        var scene = EditorSceneManager.OpenScene(ScenePath);

        // 1) Canvas 찾거나 생성 (Screen Space Overlay)
        var canvas = Object.FindFirstObjectByType<Canvas>();
        if (canvas == null)
        {
            var canvasGo = new GameObject("CameraPanelCanvas");
            canvas = canvasGo.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 100;
            canvasGo.AddComponent<CanvasScaler>();
            canvasGo.AddComponent<GraphicRaycaster>();
            Debug.Log("[CameraPanelSetup] Canvas created");
        }
        else
        {
            Debug.Log($"[CameraPanelSetup] Reusing existing Canvas: {canvas.name}");
        }

        // 2) EventSystem 필요 시 (Canvas 동작 위함)
        if (Object.FindFirstObjectByType<UnityEngine.EventSystems.EventSystem>() == null)
        {
            var es = new GameObject("EventSystem");
            es.AddComponent<UnityEngine.EventSystems.EventSystem>();
            es.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();
        }

        // 3) 카메라 패널 2종 추가 (회의록 5111810 역할 분담 반영)
        // 젠지 (tb3_2) — Pi Camera v2 IMX219
        AddCameraPanel(
            canvas: canvas,
            name: "GenjiCameraPanel",
            topic: "/tb3_2/camera/image_raw/compressed",
            label: "젠지 (Pi Camera)",
            anchorMin: new Vector2(1, 1),
            anchorMax: new Vector2(1, 1),
            pivot: new Vector2(1, 1),
            anchoredPos: new Vector2(-20, -20),
            size: new Vector2(320, 240)
        );

        // 티원 (tb3_1) — RealSense D435
        AddCameraPanel(
            canvas: canvas,
            name: "T1CameraPanel",
            topic: "/tb3_1/camera/color/image_raw/compressed",
            label: "티원 (D435)",
            anchorMin: new Vector2(1, 1),
            anchorMax: new Vector2(1, 1),
            pivot: new Vector2(1, 1),
            anchoredPos: new Vector2(-20, -280),
            size: new Vector2(320, 240)
        );

        // 4) Scene 저장
        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        Debug.Log($"[CameraPanelSetup] Done. Scene saved: {ScenePath}");
    }

    static void AddCameraPanel(
        Canvas canvas,
        string name,
        string topic,
        string label,
        Vector2 anchorMin,
        Vector2 anchorMax,
        Vector2 pivot,
        Vector2 anchoredPos,
        Vector2 size)
    {
        // 이미 있으면 갱신만
        var existing = GameObject.Find(name);
        GameObject panelGo;
        if (existing != null)
        {
            panelGo = existing;
            Debug.Log($"[CameraPanelSetup] Updating existing: {name}");
        }
        else
        {
            // RectTransform을 default Transform 대신 가지고 시작 (UI GameObject 표준 패턴)
            panelGo = new GameObject(name, typeof(RectTransform));
            panelGo.transform.SetParent(canvas.transform, false);
        }

        // RectTransform (UI GameObject는 이미 가지고 있음)
        var rt = panelGo.GetComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = pivot;
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = size;

        // RawImage
        var raw = panelGo.GetComponent<RawImage>() ?? panelGo.AddComponent<RawImage>();
        raw.color = Color.white;

        // CameraStreamPanel
        var panel = panelGo.GetComponent<CameraStreamPanel>() ?? panelGo.AddComponent<CameraStreamPanel>();
        panel.topicName = topic;
        panel.displayLabel = label;
        panel.targetImage = raw;

        // 라벨 Text (자식 GameObject로 추가 — 옵션)
        var labelGo = GameObject.Find($"{name}/Label");
        if (labelGo == null)
        {
            labelGo = new GameObject("Label", typeof(RectTransform));
            labelGo.transform.SetParent(panelGo.transform, false);
            var labelRt = labelGo.GetComponent<RectTransform>();
            labelRt.anchorMin = new Vector2(0, 1);
            labelRt.anchorMax = new Vector2(1, 1);
            labelRt.pivot = new Vector2(0.5f, 1);
            labelRt.anchoredPosition = Vector2.zero;
            labelRt.sizeDelta = new Vector2(0, 24);

            var text = labelGo.AddComponent<Text>();
            text.text = label;
            text.alignment = TextAnchor.MiddleCenter;
            text.color = Color.white;
            text.fontSize = 16;
            text.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            // background-friendly outline
            var outline = labelGo.AddComponent<Outline>();
            outline.effectColor = Color.black;
            outline.effectDistance = new Vector2(1, -1);

            panel.labelText = text;
        }
        else
        {
            var text = labelGo.GetComponent<Text>();
            if (text != null) panel.labelText = text;
        }

        Debug.Log($"[CameraPanelSetup] {name} → topic={topic} label={label}");
    }
}
