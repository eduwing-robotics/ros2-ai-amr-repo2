// TopicRegistry.cs — ROS2 토픽 이름 SSOT. 토픽 하드코딩 금지(Ros/CLAUDE.md 규칙).
// 카메라 토픽 정본: 젠지 /tb3_2/camera/image_raw/compressed (Pi Camera v2 IMX219, 30Hz)
//                  티원 /tb3_1/camera/color/image_raw/compressed (RealSense D435, 30Hz)
// 배터리 토픽 정본: turtlebot3_bringup robot.launch.py namespace:=tb3_* → /tb3_*/battery_state
// robotId 컨벤션: "tb3_1" 티원 / "tb3_2" 젠지 (default_robots.json과 1:1).
namespace URHYNIX.ControlRoom.Ros
{
    public static class TopicRegistry
    {
        public const string GenjiCameraCompressed = "/tb3_2/camera/image_raw/compressed";
        public const string T1CameraCompressed    = "/tb3_1/camera/color/image_raw/compressed";

        public const string T1BatteryState    = "/tb3_1/battery_state";
        public const string GenjiBatteryState = "/tb3_2/battery_state";

        // 2026-06-18 Phase B/C: arduino_bridge_quad.py가 root namespace `/sensors/*`로 4토픽 발행.
        // default_sensors.json도 `/sensors/*`로 정합. ROS_DOMAIN_ID=210. 현재 tb3_2(젠지)만 결선.
        // 4센서: PIR(Bool)·사운드(Int32 swing)·온도(Int32 raw)·레이저(Bool, 수신부 미결선→UI 비활성).
        // 구 LDR/ldr은 회로 폐기로 Phase C에서 제거됨.
        public const string GenjiPirState = "/sensors/pir";
        public const string GenjiSound    = "/sensors/sound";
        public const string GenjiTemp     = "/sensors/temp";
        public const string GenjiLaser    = "/sensors/laser";

        // SLAM 점유격자맵. cartographer가 글로벌 단일 /map으로 발행(네임스페이스 없음).
        // 2026-06-16 라이브 맵뷰(경로 B): OccupancyGrid → MapSubscriber → MapPanel Texture2D.
        public const string Map = "/map";

        // tf 트리. map→odom(cartographer) + odom→base_footprint(로봇). RobotPoseSubscriber가 합성.
        public const string Tf = "/tf";

        // Nav2 단일 목표 좌표(legacy). 새 경로는 robotId별 /<robotId>/goal_pose를 사용한다.
        public const string GoalPose = "/goal_pose";

        // 맵 우클릭 출동 목표(PoseStamped). per-robot 네임스페이스로 선택 로봇만 수신.
        public static string GetGoalPose(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/goal_pose";

        // 순찰 경로(PoseArray). FollowWaypointsPublisher가 발행 → 로봇측 patrol_waypoints_bridge.py가
        // Nav2 FollowWaypoints로 실행(ROS-TCP 액션 미지원 우회). per-robot 네임스페이스.
        public static string GetPatrolWaypoints(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/patrol_waypoints";

        // 주행준비 트리거(Bool). PrepareDrivePublisher가 true 발행 → 로봇측 readyd.py가
        // ~/t1_drive_ready.sh(bringup→AMCL→nav2 lifecycle→검증)를 1회 실행. per-robot 네임스페이스.
        public static string GetPrepareDrive(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/prepare_drive";

        // 주행준비 진행상황(String, 로봇측 latched). readyd.py가 6단계 각 줄을 발행 →
        // PrepareDrivePublisher가 구독해 관제 로그로 중계. 재시딩 진행도 이 토픽 공유. per-robot 네임스페이스.
        public static string GetDriveReadyStatus(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/drive_ready_status";

        // 재시딩 트리거(Bool). PrepareDrivePublisher가 true 발행 → 로봇측 readyd가 _dock_reseed.sh
        // (충전독 고정좌표로 AMCL 위치 재선언)를 1회 실행. 주행준비와 달리 bringup/nav2 미변경
        // (이미 기동된 상태 전제). per-robot 네임스페이스.
        public static string GetReseed(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/reseed";

        // 수동 조종 속도 명령(TwistStamped). TeleopCmdPublisher가 발행 → TurtleBot3 HW 직접 구동(Nav2 비경유).
        // ⚠ 메시지 타입은 TwistStamped(TurtleBot3 Jazzy 실기). CONTRACT.md의 Twist 표기는 드리프트.
        public static string GetCmdVel(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/cmd_vel";

        // 로봇별 위치(PoseStamped, map프레임). robot_pose_publisher.py가 tf→발행, pose_logger.py도 동일 구독.
        // 듀얼로봇 런타임에서 로봇별 마커를 구분 표시(전역 /tf는 단일로봇 맵제작용 fallback).
        public static string GetPose(string robotId)
            => string.IsNullOrEmpty(robotId) ? null : $"/{robotId}/pose";

        public static string GetCameraCompressed(string robotId)
        {
            switch (robotId)
            {
                case "tb3_1": return T1CameraCompressed;
                case "tb3_2": return GenjiCameraCompressed;
                default:      return null;
            }
        }

        public static string GetBatteryState(string robotId)
        {
            switch (robotId)
            {
                case "tb3_1": return T1BatteryState;
                case "tb3_2": return GenjiBatteryState;
                default:      return null;
            }
        }

        public static string GetPirState(string robotId)
        {
            switch (robotId)
            {
                case "tb3_2": return GenjiPirState;
                default:      return null;
            }
        }

        public static string GetSound(string robotId)
        {
            switch (robotId)
            {
                case "tb3_2": return GenjiSound;
                default:      return null;
            }
        }

        public static string GetTemp(string robotId)
        {
            switch (robotId)
            {
                case "tb3_2": return GenjiTemp;
                default:      return null;
            }
        }

        public static string GetLaser(string robotId)
        {
            switch (robotId)
            {
                case "tb3_2": return GenjiLaser;
                default:      return null;
            }
        }
    }
}
