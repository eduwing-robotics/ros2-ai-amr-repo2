// UiTokens.cs — UI 디자인 토큰 C# 상수. USS `ControlRoomTokens.uss`와 1:1.
// 박물관 고품격 밝은 슬레이트 톤. 색은 hex string + Color 둘 다 노출.
// USS 변수 추가/수정 시 본 파일도 같이 갱신 (수동 SSOT).
using UnityEngine;

namespace URHYNIX.ControlRoom.Design
{
    public static class UiTokens
    {
        // Background / Surface / Border
        public const string ColorBgPrimaryHex   = "#f1f5f9"; // 화면 배경 (slate-100)
        public const string ColorSurfaceHex     = "#ffffff"; // 카드/패널
        public const string ColorBorderHex      = "#e2e8f0"; // 테두리 (slate-200)

        // Text
        public const string ColorTextPrimaryHex   = "#1e293b"; // 본문 (slate-800)
        public const string ColorTextSecondaryHex = "#64748b"; // 라벨 (slate-500)

        // Accent + Status
        public const string ColorAccentHex   = "#2563eb"; // 활성/링크 (blue-600)
        public const string ColorStatusOkHex = "#10b981"; // 안전/OK (emerald-500)
        public const string ColorStatusWarnHex = "#f59e0b"; // 경고 (amber-500)
        public const string ColorStatusDangerHex = "#dc2626"; // 위험 (rose-600)
        public const string ColorStatusInfoHex = "#06b6d4"; // 정보 (cyan-500)

        // Spacing (px)
        public const int SpaceXs = 4;
        public const int SpaceSm = 8;
        public const int SpaceMd = 12;
        public const int SpaceLg = 16;
        public const int SpaceXl = 24;

        // Sizes (px)
        public const int TopBarHeight = 48;
        public const int LeftPanelWidth = 230;
        public const int RightPanelWidth = 240;
        public const int CameraLogRowHeight = 180;

        public static Color FromHex(string hex)
        {
            ColorUtility.TryParseHtmlString(hex, out var c);
            return c;
        }
    }
}
