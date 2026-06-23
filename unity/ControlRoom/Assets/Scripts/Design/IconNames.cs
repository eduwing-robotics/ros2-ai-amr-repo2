// IconNames.cs — PNG 아이콘 자산 경로 상수.
// 실제 파일: Assets/Art/IconsPng/<Category>/<name>_<size>.png
// Resources.Load 가 아니라 USS background-image 또는 RawImage src로 사용.
namespace URHYNIX.ControlRoom.Design
{
    public static class IconNames
    {
        // Common
        public const string AlertFire    = "fire_alert";
        public const string TurtlebotBadge = "turtlebot_badge";
        public const string SensorBadge  = "sensor_badge";

        // Target
        public const string ProtectedFrame  = "protected_frame";
        public const string ProtectedArt    = "protected_art";
        public const string ProtectedObject = "protected_object";

        // Size variants
        public const string Size64  = "_64";
        public const string Size128 = "_128";
        public const string Size256 = "_256";
        public const string Size512 = "_512";

        // 기본 경로 prefix (USS background-image 용)
        public const string PathRoot = "Assets/Art/IconsPng/";
    }
}
