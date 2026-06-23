// CameraStreamSetup.cs — ControlRoomMain.unity에 듀얼 CameraStreamSubscriber GameObject를 idempotent하게 추가.
// 모델 B (Phase 2.7-dual): 젠지 + 티원 두 Subscriber 항상 가동 → CameraPanelView가 활성 robotId만 표시.
// Scene이 이미 존재해야 함 (ControlRoomSceneSetup 선행). 재실행 안전.
// 메뉴: URHYNIX/Setup Camera Stream (Dual)
// CLI:
//   /Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app/Contents/MacOS/Unity \
//     -batchmode -quit -nographics \
//     -projectPath /Users/family/jason/URHYNIX/unity/ControlRoom \
//     -executeMethod URHYNIX.ControlRoom.Editor.CameraStreamSetup.Setup \
//     -logFile /tmp/unity-camera-stream-setup.log
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.Editor
{
    public static class CameraStreamSetup
    {
        const string ScenePath = "Assets/Scenes/ControlRoomMain.unity";

        struct SubSpec
        {
            public string goName;
            public string robotId;
            public string label;
            public string topic;
        }

        static readonly SubSpec[] Subs = new SubSpec[]
        {
            new SubSpec { goName = "CameraStreamSubscriber_Genji", robotId = "tb3_2", label = "젠지", topic = TopicRegistry.GenjiCameraCompressed },
            new SubSpec { goName = "CameraStreamSubscriber_T1",    robotId = "tb3_1", label = "티원", topic = TopicRegistry.T1CameraCompressed },
        };

        [MenuItem("URHYNIX/Setup Camera Stream (Dual)")]
        public static void Setup()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            if (!scene.IsValid())
            {
                Debug.LogError($"[CameraStreamSetup] Scene 열기 실패: {ScenePath} (ControlRoomSceneSetup 먼저 실행하세요)");
                return;
            }

            foreach (var s in Subs)
            {
                var existing = GameObject.Find(s.goName);
                GameObject go;
                if (existing != null)
                {
                    go = existing;
                    Debug.Log($"[CameraStreamSetup] GameObject 재사용: {s.goName}");
                }
                else
                {
                    go = new GameObject(s.goName);
                    Debug.Log($"[CameraStreamSetup] GameObject 신규 생성: {s.goName}");
                }

                var sub = go.GetComponent<CameraStreamSubscriber>();
                if (sub == null)
                {
                    sub = go.AddComponent<CameraStreamSubscriber>();
                    Debug.Log($"[CameraStreamSetup] CameraStreamSubscriber 컴포넌트 추가: {s.goName}");
                }

                sub.robotId      = s.robotId;
                sub.topicName    = s.topic;
                sub.displayLabel = s.label;
                EditorUtility.SetDirty(sub);

                Debug.Log($"[CameraStreamSetup] 설정 완료 → {s.goName} robotId={s.robotId} topic={s.topic} label={s.label}");
            }

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            AssetDatabase.SaveAssets();
            Debug.Log($"[CameraStreamSetup] Scene 저장 완료 — {Subs.Length}개 Subscriber 활성 (Dual)");
        }
    }
}
