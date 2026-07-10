// ControlRoomCaptureMenu.cs — Editor 메뉴로 ControlRoom Play 화면을 PNG로 저장.
// unityctl screenshot이 UI Toolkit을 검정으로 캡처하는 함정 우회 —
// UIPanel의 root VisualElement에서 IPanelVisualElement를 직렬화하지 않고
// EditorWindow의 'GameView' 국소 캡처(UnityExpanse용) 대신 Editor 스크립트로
// ScreenCapture.CaptureScreenshot을 Play 중인 GameView에서 직접 호출.
// opencode: 2026-06-28 - UI Toolkit unityctl 검정 우회 Editor script.
// Coded with OpenCode; high-cost model review recommended.
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.Editor
{
    public static class ControlRoomCaptureMenu
    {
        const string MENU = "URHYNIX/ControlRoom Capture/";

        // ControlRoom Play 화면 전체를 1920x1080 png로 저장
        [MenuItem(MENU + "1. 전체 화면 (1920x1080)")]
        public static void CaptureFull()
        {
            EnsurePlaying();
            string path = GetOutputPath("ui_live_full");
            ScreenCapture.CaptureScreenshot(path, 1);
            AssetDatabase.Refresh();
            Debug.Log($"[Capture] 전체 → {path} (1~2초 후 파일 완성)");
            EditorUtility.DisplayDialog("캡처 완료", $"전체 화면 저장됨:\n{path}\n\n파일은 1~2초 뒤 디스크에 나타납니다.", "OK");
        }

        // 고해상도 4K
        [MenuItem(MENU + "2. 전체 화면 4K (3840x2160)")]
        public static void CaptureFull4K()
        {
            EnsurePlaying();
            string path = GetOutputPath("ui_live_4k");
            ScreenCapture.CaptureScreenshot(path, 2);
            AssetDatabase.Refresh();
            Debug.Log($"[Capture] 4K → {path}");
            EditorUtility.DisplayDialog("캡처 완료", $"4K 전체 화면 저장됨:\n{path}", "OK");
        }

        // 3.Overlay UI 포함 — GameView 윈도우를 직접. UI Toolkit이 카메라에 안 잡히는
        //   함정 때문에 더 안정적인 'EditorWindow' 경로 사용.
        [MenuItem(MENU + "3. GameView 창 캡처 (UI Toolkit 포함)")]
        public static void CaptureWindow()
        {
            EnsurePlaying();
            // GameView 창 찾아서 텍스처로 캡처
            var gameView = GetGameViewWindow();
            if (gameView == null)
            {
                EditorUtility.DisplayDialog("GameView 없음", "GameView 창을 찾을 수 없습니다.\nUnity Window > Analysis > Game 탭을 활성화하세요.", "OK");
                return;
            }
            string path = GetOutputPath("ui_live_window");
            gameView.ShowNotification(new GUIContent("캡처 중..."), 0.2);
            EditorApplication.delayCall += () => CaptureWindowInternal(gameView, path);
        }

        // 4.컨트롤룸 패널 요소별 저장 (좌/중앙/우/하단 탭 별 4장 자동 생성)
        [MenuItem(MENU + "4. UI 패널 Crop 4장 자동 (좌·중앙·우·하단)")]
        public static void CapturePanels()
        {
            EnsurePlaying();
            string baseDir = GetBaseDir();
            EnsureDir(baseDir);

            ScreenCapture.CaptureScreenshot($"{baseDir}/ui_live_full.png", 2);
            Debug.Log("[Capture](ui_live_full) 전체 화면 4K — 로드 후 crop");
            AssetDatabase.Refresh();
            EditorUtility.DisplayDialog("캡처 시작",
              $"1) 1~2초 후 {baseDir}/ui_live_full.png 완성됨.\n" +
              "2) 그 다음 '5. 최신 화면 UI 패널 Crop 실행' 메뉴로 4분할 crop.\n\n" +
              $"대상 폴더: {baseDir}", "OK");
        }

        [MenuItem(MENU + "5. 최신 화면 UI 패널 Crop 실행 (1장 → 4장 분할 )")]
        public static void CropPanels()
        {
            string baseDir = GetBaseDir();
            string fullPng = $"{baseDir}/ui_live_full.png";
            if (!System.IO.File.Exists(fullPng))
            {
                EditorUtility.DisplayDialog("원본 없음",
                  $"먼저 '4. UI 패널 Crop 4장 자동'을 실행해 캡처해두세요.\n\n찾는 파일: {fullPng}", "OK");
                return;
            }
            // Texture2D로 읽어 4등분 crop 저장
            var bytes = System.IO.File.ReadAllBytes(fullPng);
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!tex.LoadImage(bytes))
            {
                EditorUtility.DisplayDialog("로드 실패", $"PNG 로드 실패: {fullPng}", "OK");
                return;
            }
            int w = tex.width, h = tex.height;
            // 4영역: 좌패널(0~40%)·중앙맵(40~75%)·우패널(75~100%)·하단(60~100% y) — 위에서부터 y=0 (Unity Texture2D)
            SaveCrop(tex, 0,             0,            Mathf.RoundToInt(w * 0.40f), h,                    $"{baseDir}/panel_left.png");
            SaveCrop(tex, Mathf.RoundToInt(w * 0.40f), Mathf.RoundToInt(h * 0.40f), Mathf.RoundToInt(w * 0.60f), Mathf.RoundToInt(h * 0.60f), $"{baseDir}/panel_center.png");
            SaveCrop(tex, Mathf.RoundToInt(w * 0.75f), 0,            Mathf.RoundToInt(w * 0.25f), h,                     $"{baseDir}/panel_right.png");
            SaveCrop(tex, 0,             Mathf.RoundToInt(h * 0.85f), w, Mathf.RoundToInt(h * 0.15f), $"{baseDir}/panel_bottom.png");

            AssetDatabase.Refresh();
            EditorUtility.DisplayDialog("Crop 완료",
              $"4장 저장 완료:\n" +
              $"- {baseDir}/panel_left.png\n" +
              $"- {baseDir}/panel_center.png\n" +
              $"- {baseDir}/panel_right.png\n" +
              $"- {baseDir}/panel_bottom.png",
              "OK");
            Debug.Log("[Capture] panel_left/center/right/bottom.png 완성");
        }

        // ── helpers ─────────────────────────────

        static void EnsurePlaying()
        {
            if (!EditorApplication.isPlaying)
            {
                EditorApplication.EnterPlaymode();
                System.Threading.Thread.Sleep(800); // Play 안정화 대기
            }
        }

        static string GetBaseDir()
        {
            // docs/presentation/weekly_ppt/assets/img/ 로드 직행 — 과 활 활/비/  4   과  은사 logout
            var repoRoot = System.IO.Directory.GetParent(Application.dataPath).Parent.FullName;
            return $"{repoRoot}/docs/presentation/weekly_ppt/assets/img";
        }

        static void EnsureDir(string path)
        {
            if (!System.IO.Directory.Exists(path))
                System.IO.Directory.CreateDirectory(path);
        }

        static string GetOutputPath(string fileBase)
        {
            string dir = GetBaseDir();
            EnsureDir(dir);
            return $"{dir}/{fileBase}.png";
        }

        static EditorWindow GetGameViewWindow()
        {
            var windows = UnityEngine.Resources.FindObjectsOfTypeAll<EditorWindow>();
            foreach (var w in windows)
            {
                if (w.GetType().Name == "GameView") return w;
            }
            return null;
        }

        static void CaptureWindowInternal(EditorWindow gameView, string path)
        {
            // GameView의 root VisualElement 트리 렌더 — UI Toolkit 포함
            var root = gameView.rootVisualElement;
            //root.MarkDirtyRepaint(); // UI Toolkit 요소 강제 갱신
            // 1프레임 대기 후 EditorApplication.update에서 캡처
            EditorApplication.CallbackFunction capture = null;
            capture = () =>
            {
                try
                {
                    ScreenCapture.CaptureScreenshot(path, 1);
                    AssetDatabase.Refresh();
                    Debug.Log($"[Capture] window 저장 {path}");
                    EditorUtility.DisplayDialog("GameView 캡처 완료", $"ScreenCapture 경로:\n{path}\n\n1~2초 후 파일 디스크에 나타남.", "OK");
                }
                finally
                {
                    EditorApplication.update -= capture;
                }
            };
            EditorApplication.update += capture;
        }

        static void SaveCrop(Texture2D src, int x, int y, int w, int h, string path)
        {
            // Texture2D.LoadImage 후 y축은 위가 0.
            // Unity Texture2D.GetPixels는 왼쪽 아래 원점 → 위쪽 y는 (texH - y - h)로 변환
            int srcH = src.height;
            int colorY = srcH - y - h;
            if (colorY < 0) colorY = 0;
            if (x < 0) x = 0;
            if (x + w > src.width) w = src.width - x;
            if (y + h > srcH) h = srcH - y;
            Color[] px = src.GetPixels(x, colorY, w, h);
            var crop = new Texture2D(w, h, TextureFormat.RGBA32, false);
            crop.SetPixels(px);
            crop.Apply();
            System.IO.File.WriteAllBytes(path, crop.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(crop);
        }

        // 메뉴 활성화 조건: ControlRoom 씬이 열려 있을 때만
        [MenuItem(MENU + "1. 전체 화면 (1920x1080)", true)]
        [MenuItem(MENU + "2. 전체 화면 4K (3840x2160)", true)]
        [MenuItem(MENU + "3. GameView 창 캡처 (UI Toolkit 포함)", true)]
        [MenuItem(MENU + "4. UI 패널 Crop 4장 자동 (좌·중앙·우·하단)", true)]
        [MenuItem(MENU + "5. 최신 화면 UI 패널 Crop 실행 (1장 → 4장 분할 )", true)]
        public static bool ValidateMenu()
        {
            return UnityEditor.SceneManagement.EditorSceneManager.GetActiveScene().name == "ControlRoomMain"
                || EditorApplication.isPlaying;
        }
    }
}