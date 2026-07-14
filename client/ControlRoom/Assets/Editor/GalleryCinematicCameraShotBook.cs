// GalleryCinematicCameraShotBook.cs — 사용자가 잡은 영상 카메라 구도를 앵커로 저장·복원한다.
// GalleryCinematic 씬만 편집하며 Timeline, ROS, Nav2, TurtleBot 배치에는 관여하지 않는다.
using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace URHYNIX.ControlRoom.Editor
{
    public sealed class GalleryCinematicCameraShotBook : EditorWindow
    {
        const string ScenePath = "Assets/Scenes/GalleryCinematic.unity";
        const string CameraName = "GalleryCinematicCamera";
        const string RootName = "CinematicCameraShotBook";
        const string FirstShotName = "SHOT_01_Exterior_Wide";
        const string SecondShotName = "SHOT_02_Entrance_Approach";

        string newShotName = "SHOT_02_Entrance_Approach";

        [MenuItem("URHYNIX/Cinematic Camera Shot Book")]
        public static void OpenWindow()
        {
            GetWindow<GalleryCinematicCameraShotBook>("Cinematic Shot Book");
        }

        [MenuItem("URHYNIX/Capture Current Camera as SHOT 01 Exterior Wide")]
        public static void CaptureFirstShot()
        {
            Capture(FirstShotName, true);
        }

        [MenuItem("URHYNIX/Capture Current Camera as SHOT 02 Entrance Approach")]
        public static void CaptureSecondShot()
        {
            Capture(SecondShotName, true);
        }

        [MenuItem("URHYNIX/Restore SHOT 01 Exterior Wide")]
        public static void RestoreFirstShot()
        {
            Apply(FirstShotName);
        }

        [MenuItem("URHYNIX/Audit Cinematic Camera Shot Book")]
        public static void Audit()
        {
            Scene scene = OpenCinematicScene();
            Camera camera = FindCinematicCamera(scene);
            Transform root = FindRoot(scene);
            Transform firstShot = root == null ? null : root.Find(FirstShotName);
            Camera lens = firstShot == null ? null : firstShot.GetComponent<Camera>();

            if (camera == null || root == null || firstShot == null || lens == null || lens.enabled)
                throw new InvalidOperationException("[CinematicShotBook] main camera or SHOT_01 anchor is incomplete");

            Debug.Log($"[CinematicShotBook] AUDIT PASS shots={root.childCount} first={FirstShotName} fov={lens.fieldOfView:F1} videoOnly=true");
        }

        void OnGUI()
        {
            EditorGUILayout.LabelField("Cinematic Camera Shot Book", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "1. 씬 뷰에서 구도를 잡고 GalleryCinematicCamera를 Align With View 합니다.\n" +
                "2. 샷 이름을 적고 Capture 합니다.\n" +
                "3. 이후 메인 카메라를 움직여도 Apply로 이 구도에 정확히 돌아옵니다.",
                MessageType.Info);

            newShotName = EditorGUILayout.TextField("New shot name", newShotName);
            using (new EditorGUI.DisabledScope(string.IsNullOrWhiteSpace(newShotName)))
            {
                if (GUILayout.Button("Capture Current Gallery Camera"))
                    Capture(newShotName, false);
            }

            EditorGUILayout.Space(8);
            EditorGUILayout.LabelField("Saved shots", EditorStyles.boldLabel);
            Scene scene = SceneManager.GetSceneByPath(ScenePath);
            Transform root = scene.IsValid() && scene.isLoaded ? FindRoot(scene) : null;
            if (root == null)
            {
                EditorGUILayout.LabelField("No saved camera shots yet.", EditorStyles.miniLabel);
                return;
            }

            foreach (Transform shot in root)
            {
                Camera lens = shot.GetComponent<Camera>();
                string lensText = lens == null ? "lens missing" : $"FOV {lens.fieldOfView:F1}";
                EditorGUILayout.BeginHorizontal();
                EditorGUILayout.LabelField(shot.name, GUILayout.Width(240));
                EditorGUILayout.LabelField(lensText, EditorStyles.miniLabel, GUILayout.Width(70));
                if (GUILayout.Button("Apply", GUILayout.Width(60))) Apply(shot.name);
                if (GUILayout.Button("Select", GUILayout.Width(60))) Selection.activeGameObject = shot.gameObject;
                EditorGUILayout.EndHorizontal();
            }
        }

        static void Capture(string requestedName, bool replaceWithoutPrompt)
        {
            string shotName = SanitizeName(requestedName);
            if (string.IsNullOrWhiteSpace(shotName))
                throw new InvalidOperationException("[CinematicShotBook] a shot name is required");

            Scene scene = OpenCinematicScene();
            Camera source = FindCinematicCamera(scene);
            if (source == null) throw new InvalidOperationException("[CinematicShotBook] GalleryCinematicCamera missing");

            Transform root = FindOrCreateRoot(scene);
            Transform shot = root.Find(shotName);
            if (shot != null && !replaceWithoutPrompt && !EditorUtility.DisplayDialog(
                    "Replace camera shot?", $"'{shotName}' already exists. Replace it with the current camera?", "Replace", "Cancel"))
                return;
            if (shot == null)
            {
                shot = new GameObject(shotName).transform;
                shot.SetParent(root, false);
            }

            Undo.RecordObject(shot, "Capture cinematic camera shot");
            shot.SetPositionAndRotation(source.transform.position, source.transform.rotation);
            Camera lens = shot.GetComponent<Camera>();
            if (lens == null) lens = Undo.AddComponent<Camera>(shot.gameObject);
            Undo.RecordObject(lens, "Capture cinematic camera lens");
            CopyLens(source, lens);
            lens.enabled = false;

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Selection.activeGameObject = shot.gameObject;
            Debug.Log($"[CinematicShotBook] captured {shotName} from {CameraName}; fov={lens.fieldOfView:F1}");
        }

        static void Apply(string requestedName)
        {
            string shotName = SanitizeName(requestedName);
            Scene scene = OpenCinematicScene();
            Camera destination = FindCinematicCamera(scene);
            Transform shot = FindRoot(scene)?.Find(shotName);
            Camera lens = shot == null ? null : shot.GetComponent<Camera>();
            if (destination == null || shot == null || lens == null)
                throw new InvalidOperationException($"[CinematicShotBook] saved shot '{shotName}' is missing or incomplete");

            Undo.RecordObject(destination.transform, "Restore cinematic camera shot");
            Undo.RecordObject(destination, "Restore cinematic camera lens");
            destination.transform.SetPositionAndRotation(shot.position, shot.rotation);
            CopyLens(lens, destination);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            Selection.activeGameObject = destination.gameObject;
            Debug.Log($"[CinematicShotBook] restored {shotName} to {CameraName}; fov={destination.fieldOfView:F1}");
        }

        static void CopyLens(Camera source, Camera destination)
        {
            destination.orthographic = source.orthographic;
            destination.fieldOfView = source.fieldOfView;
            destination.orthographicSize = source.orthographicSize;
            destination.nearClipPlane = source.nearClipPlane;
            destination.farClipPlane = source.farClipPlane;
            destination.usePhysicalProperties = source.usePhysicalProperties;
            destination.focalLength = source.focalLength;
            destination.sensorSize = source.sensorSize;
            destination.lensShift = source.lensShift;
        }

        static Scene OpenCinematicScene()
        {
            Scene scene = SceneManager.GetSceneByPath(ScenePath);
            return scene.IsValid() && scene.isLoaded ? scene : EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        }

        static Transform FindOrCreateRoot(Scene scene)
        {
            Transform root = FindRoot(scene);
            if (root != null) return root;
            return new GameObject(RootName).transform;
        }

        static Transform FindRoot(Scene scene)
        {
            foreach (GameObject root in scene.GetRootGameObjects())
                if (root.name == RootName) return root.transform;
            return null;
        }

        static Camera FindCinematicCamera(Scene scene)
        {
            foreach (GameObject root in scene.GetRootGameObjects())
                foreach (Camera candidate in root.GetComponentsInChildren<Camera>(true))
                    if (candidate.name == CameraName) return candidate;
            return null;
        }

        static string SanitizeName(string value) => value == null ? string.Empty : value.Trim().Replace('/', '_');
    }
}
