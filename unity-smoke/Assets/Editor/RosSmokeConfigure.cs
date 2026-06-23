using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

[InitializeOnLoad]
public static class RosSmokeConfigure
{
    const string ScenePath = "Assets/Scenes/SampleScene.unity";
    const string AutoPlayKey = "URHYNIX.RosSmoke.AutoPlayed";

    static RosSmokeConfigure()
    {
        EditorApplication.delayCall += () =>
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || Application.isPlaying) return;
            if (SessionState.GetBool(AutoPlayKey, false)) return;
            SessionState.SetBool(AutoPlayKey, true);
            try { Configure(); EditorApplication.EnterPlaymode(); }
            catch (System.Exception e) { Debug.LogWarning($"[RosSmoke] auto-play skipped: {e.Message}"); }
        };
    }

    [MenuItem("URHYNIX/Configure RosSmoke Scene")]
    public static void Configure()
    {
        var scene = EditorSceneManager.OpenScene(ScenePath);
        var existing = Object.FindFirstObjectByType<RosSmokeDashboard>();
        if (existing == null)
        {
            var go = new GameObject("RosSmokeDashboard");
            go.AddComponent<RosSmokeDashboard>();
        }
        EditorSceneManager.SaveScene(scene);
        Debug.Log("[RosSmoke] Scene configured.");
    }

    [MenuItem("URHYNIX/Play RosSmoke")]
    public static void Play()
    {
        Configure();
        EditorApplication.EnterPlaymode();
    }
}
