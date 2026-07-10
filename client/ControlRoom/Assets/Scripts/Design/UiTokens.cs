// opencode: 2026-06-29 - ControlRoomTokens.uss와 1:1 토스 TDS 토큰 SSOT. Coded with OpenCode; high-cost model review recommended.
// UiTokens.cs — ControlRoomTokens.uss와 1:1로 매핑하는 C# 디자인 토큰 SSOT.
// UI Toolkit USS 변수와 C# 코드가 같은 값을 참조하도록 유지한다.
// 토스 TDS 이식(2026-06-29).
namespace URHYNIX.ControlRoom.Design
{
    public static class UiTokens
    {
        // Surface
        public const string ColorBgPrimary = "#F2F4F6";
        public const string ColorSurface = "#ffffff";
        public const string ColorSurfaceOverlay = "rgba(255, 255, 255, 0.9)";
        public const string ColorBorder = "#E5E8EB";

        // Text
        public const string ColorTextPrimary = "#202632";
        public const string ColorTextSecondary = "#8B95A1";
        public const string ColorTextMuted = "#B0B8C1";
        public const string ColorTextInverse = "#ffffff";

        // Accent / Status
        public const string ColorAccent = "#4E8AFF";
        public const string ColorStatusOk = "#00C471";
        public const string ColorStatusWarn = "#FF9500";
        public const string ColorStatusDanger = "#FF4B4B";
        public const string ColorStatusInfo = "#6EAAFF";

        // Domain surfaces
        public const string ColorCameraBg = "#202632";
        public const string ColorCameraPlaceholder = "#4E5968";
        public const string ColorCameraCrosshair = "rgba(139, 149, 161, 0.3)";
        public const string ColorMapPlaceholder = "#D1D6DB";
        public const string ColorMap3dBg = "#4E5968";
        public const string ColorMapLabelBg = "rgba(255, 255, 255, 0.85)";
        public const string ColorMap3dLabel = "rgba(255, 255, 255, 0.85)";

        // Role badges
        public const string ColorRoleVisionFg = "#4E8AFF";
        public const string ColorRoleVisionBg = "rgba(78, 138, 255, 0.12)";
        public const string ColorRoleVisionIconBg = "rgba(78, 138, 255, 0.2)";
        public const string ColorRoleSensorFg = "#00C471";
        public const string ColorRoleSensorBg = "rgba(0, 196, 113, 0.12)";
        public const string ColorRoleSensorIconBg = "rgba(0, 196, 113, 0.2)";

        // Border
        public const int BorderWidth = 1;

        // Spacing
        public const int SpaceXxs = 2;
        public const int SpaceXs = 4;
        public const int SpaceSm = 8;
        public const int SpaceMd = 12;
        public const int SpaceLg = 16;
        public const int SpaceXl = 24;

        // Font sizes
        public const int FontSizeXs = 10;
        public const int FontSizeSm = 11;
        public const int FontSizeMd = 12;
        public const int FontSizeLg = 14;
        public const int FontSizeXl = 22;

        // Layout
        public const int PanelWidth = 236;
        public const int BottomPanelHeight = 260;
        public const int TopbarHeight = 48;
        public const int BottomNavbarHeight = 64;

        // Icon / Marker sizes
        public const int IconDotSm = 8;
        public const int IconDotMd = 16;
        public const int IconWaypoint = 24;
        public const int IconRobot = 28;

        // Radius
        public const int RadiusSm = 8;
        public const int RadiusMd = 12;
        public const int RadiusWaypoint = 12;
        public const int RadiusProtected = 2;
        public const int RadiusRobot = 14;
        public const int RadiusFull = 999;
    }
}
