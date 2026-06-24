// ControlRoomApp.cs — 앱 부트스트랩. Scene 시작 시 1회 실행.
// 책임: default_robots.json 로드 → ControlRoomState 초기화 → Binder/Sim 깨우기.
// MonoBehaviour Awake에서 단방향 초기화. 직접 ROS/DB 호출 금지(Phase 5+).
using System;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Ros;
using URHYNIX.ControlRoom.Map;
using URHYNIX.ControlRoom.Persistence;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.App
{
    public class ControlRoomApp : MonoBehaviour
    {
        const string RobotsJsonResourcePath = "RobotConfig/default_robots";
        const string FallbackRosIp = "192.168.0.250";   // mDNS 미작동 시 fallback. SSOT는 default_robots.json[0].hostAddress.
        const int DefaultRosPort = 10000;

        void Awake()
        {
            LoadRobots();
            ConfigureRos();
            CreateRosSubscribers();
            CreateDbService();   // 이벤트 → Supabase 라이터(DB 비활성이어도 안전)
            ControlRoomEvents.RaiseLogAdded("system", "INFO", "ControlRoom 부팅 완료.");
            ControlRoomEvents.RaiseLogAdded("gemma", "INFO", "⚪ Gemma 4 12B 대기 중");
        }

        // Supabase DB 라이터를 코드로 부착(씬 YAML 비의존). 설정 없으면 내부에서 비활성.
        void CreateDbService()
        {
            if (FindObjectOfType<SupabaseDbService>() == null)
            {
                var go = new GameObject("SupabaseDbService");
                go.transform.SetParent(transform, false);
                go.AddComponent<SupabaseDbService>();
            }
        }

        [Serializable] class RosEndpointConfig { public string endpointIp; }

        void ConfigureRos()
        {
            string ip = "";
            // 1순위: RosConfig/ros_endpoint.json (ros_tcp_endpoint가 뜬 PC IP, 보통 Nav2 PC). shell 편집 가능.
            var rosTa = Resources.Load<TextAsset>("RosConfig/ros_endpoint");
            if (rosTa != null)
            {
                var cfg = JsonUtility.FromJson<RosEndpointConfig>(rosTa.text);
                if (cfg != null && !string.IsNullOrEmpty(cfg.endpointIp)) ip = cfg.endpointIp;
            }
            // 2순위: 선택된 로봇 hostAddress → 3순위: fallback.
            if (string.IsNullOrEmpty(ip))
            {
                ip = FallbackRosIp;
                var robots = ControlRoomState.Instance.Robots;
                var src = ControlRoomState.Instance.GetSelectedRobot()
                          ?? (robots != null && robots.Count > 0 ? robots[0] : null);
                if (src != null)
                {
                    var addr = src.hostAddress ?? "";
                    int at = addr.IndexOf('@');
                    var host = at >= 0 ? addr.Substring(at + 1) : addr;
                    if (!string.IsNullOrEmpty(host)) ip = host;
                }
            }
            var ros = ROSConnection.GetOrCreateInstance();
            ros.RosIPAddress = ip;
            ros.RosPort = DefaultRosPort;
            Debug.Log($"[ControlRoomApp] ROS IP set: {ip}:{DefaultRosPort}");
        }

        // 코드로 부착하는 글로벌 구독자(씬 YAML 비의존). 현재: SLAM /map 라이브 맵뷰(경로 B).
        // 카메라/배터리/센서는 씬 GameObject MonoBehaviour로 결선되어 있어 여기서 다루지 않음.
        void CreateRosSubscribers()
        {
            if (FindObjectOfType<MapSubscriber>() == null)
            {
                var go = new GameObject("MapSubscriber");
                go.transform.SetParent(transform, false);
                go.AddComponent<MapSubscriber>();
            }
            if (FindObjectOfType<RobotPoseSubscriber>() == null)
            {
                var go = new GameObject("RobotPoseSubscriber");
                go.transform.SetParent(transform, false);
                go.AddComponent<RobotPoseSubscriber>();
            }
            if (FindObjectOfType<DispatchPublisher>() == null)
            {
                var go = new GameObject("DispatchPublisher");
                go.transform.SetParent(transform, false);
                go.AddComponent<DispatchPublisher>();
            }
            // 저장맵 슬롯 로더(ROS 비의존, 오프라인 표시). 라이브 /map이 오면 MapImageLayer가 우선.
            if (FindObjectOfType<StaticMapLoader>() == null)
            {
                var go = new GameObject("StaticMapLoader");
                go.transform.SetParent(transform, false);
                go.AddComponent<StaticMapLoader>();
            }
            // 순찰 경로 PoseArray 발행기(로봇측 브리지가 FollowWaypoints로 실행).
            if (FindObjectOfType<FollowWaypointsPublisher>() == null)
            {
                var go = new GameObject("FollowWaypointsPublisher");
                go.transform.SetParent(transform, false);
                go.AddComponent<FollowWaypointsPublisher>();
            }
            // 순찰 경로 로컬 영속(맵별 자동 저장/복원, Wi-Fi 무관).
            if (FindObjectOfType<PatrolRepository>() == null)
            {
                var go = new GameObject("PatrolRepository");
                go.transform.SetParent(transform, false);
                go.AddComponent<PatrolRepository>();
            }
        }

        void LoadRobots()
        {
            var ta = Resources.Load<TextAsset>(RobotsJsonResourcePath);
            if (ta == null)
            {
                Debug.LogWarning($"[ControlRoomApp] {RobotsJsonResourcePath}.json 누락 — 빈 로봇 목록으로 시작");
                return;
            }
            try
            {
                var list = JsonUtility.FromJson<RobotInfoList>(ta.text);
                if (list?.robots != null)
                {
                    ControlRoomState.Instance.Robots.Clear();
                    ControlRoomState.Instance.Robots.AddRange(list.robots);
                    Debug.Log($"[ControlRoomApp] 로봇 {list.robots.Length}대 로드");
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[ControlRoomApp] default_robots.json 파싱 실패: {e.Message}");
            }
        }
    }
}
