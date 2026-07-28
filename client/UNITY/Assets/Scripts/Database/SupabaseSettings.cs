// SupabaseSettings.cs — Resources/SupabaseConfig/supabase.json 로드 컨테이너.
// anon(publishable) 키 전용. service_role 절대 미반입. 파일은 .gitignore 차단.
// 없으면 enabled=false로 graceful degrade (DB 없이도 앱 동작).
using UnityEngine;

namespace URHYNIX.ControlRoom.Database
{
    [System.Serializable]
    public class SupabaseSettings
    {
        public string url;
        public string anonKey;
        public string defaultRobotId = "tb3_2";
        public string fallbackSessionId = "00000000-0000-0000-0000-000000000001";
        public string scenario = "mixed";
        public float poseWriteHz = 2.0f;
        public float poseMinMoveMeters = 0.05f;
        public bool enabled = true;

        const string ResourcePath = "SupabaseConfig/supabase";

        // Resources에서 1회 로드. 파일 없거나 키 비면 null 반환(호출부가 비활성 처리).
        public static SupabaseSettings Load()
        {
            var ta = Resources.Load<TextAsset>(ResourcePath);
            if (ta == null)
            {
                Debug.LogWarning($"[SupabaseSettings] {ResourcePath}.json 없음 — DB 비활성. " +
                                 "supabase.example.json 복사해 supabase.json 생성 필요.");
                return null;
            }
            try
            {
                var s = JsonUtility.FromJson<SupabaseSettings>(ta.text);
                if (s == null || string.IsNullOrEmpty(s.url) || string.IsNullOrEmpty(s.anonKey))
                {
                    Debug.LogWarning("[SupabaseSettings] url/anonKey 비어있음 — DB 비활성.");
                    return null;
                }
                if (s.anonKey.StartsWith("sb_secret") || s.anonKey.Contains("service_role"))
                {
                    Debug.LogError("[SupabaseSettings] service_role 키 감지 — 보안 위반. DB 비활성.");
                    return null;
                }
                return s;
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[SupabaseSettings] 파싱 실패: {e.Message}");
                return null;
            }
        }
    }
}
