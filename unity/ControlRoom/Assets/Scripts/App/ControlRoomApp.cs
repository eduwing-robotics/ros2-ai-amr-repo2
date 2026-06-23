// ControlRoomApp.cs — 앱 부트스트랩. Scene 시작 시 1회 실행.
// 책임: default_robots.json 로드 → ControlRoomState 초기화 → Binder/Sim 깨우기.
// MonoBehaviour Awake에서 단방향 초기화. 직접 ROS/DB 호출 금지(Phase 5+).
using System;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Ros;
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

        void ConfigureRos()
        {
            string ip = FallbackRosIp;
            var robots = ControlRoomState.Instance.Robots;
            if (robots != null && robots.Count > 0)
            {
                var addr = robots[0].hostAddress ?? "";
                int at = addr.IndexOf('@');
                var host = at >= 0 ? addr.Substring(at + 1) : addr;
                if (!string.IsNullOrEmpty(host)) ip = host;
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
