// RosConnectionManager.cs — robotId별 ROSConnection(멀티 endpoint) 관리.
// 왜: 로봇간 Wi-Fi AP isolation으로 cross-host DDS(UDP)가 막히면 "한 로봇 endpoint로 양쪽 중계"가
//   불가능하다(2026-06-29 측정: 로봇끼리 ping/UDP 차단, Mac↔각로봇 TCP는 OK). Unity는 각 로봇의
//   ros_tcp_endpoint(TCP 10000)에 개별 연결할 수 있으므로, robotId별 전용 ROSConnection을 만들어
//   각 로봇(.84/.250)에 직접 붙는다. ROSConnection은 RosIPAddress/Subscribe가 인스턴스 멤버라
//   인스턴스 다중화가 가능(_instance static만 편의 싱글톤).
using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.App
{
    public class RosConnectionManager : MonoBehaviour
    {
        const int Port = 10000;
        static RosConnectionManager _inst;
        readonly Dictionary<string, ROSConnection> _byRobot = new Dictionary<string, ROSConnection>();

        public static RosConnectionManager GetOrCreate()
        {
            if (_inst == null)
            {
                var go = new GameObject("RosConnectionManager");
                _inst = go.AddComponent<RosConnectionManager>();
            }
            return _inst;
        }

        // hostAddress("user@ip" 또는 "ip")에서 IP만 추출.
        public static string ExtractIp(string hostAddress)
        {
            if (string.IsNullOrEmpty(hostAddress)) return "";
            int at = hostAddress.IndexOf('@');
            return at >= 0 ? hostAddress.Substring(at + 1) : hostAddress;
        }

        // robotId 전용 ROSConnection 반환. shared(싱글톤)와 IP가 같으면 재사용(중복 연결 방지),
        // 다르면 새 GameObject에 ROSConnection을 붙여 해당 로봇 IP로 직접 연결한다.
        public ROSConnection GetForRobot(RobotInfo robot, ROSConnection shared)
        {
            if (robot == null || string.IsNullOrEmpty(robot.robotId)) return shared;
            if (_byRobot.TryGetValue(robot.robotId, out var existing)) return existing;

            string ip = ExtractIp(robot.hostAddress);
            if (string.IsNullOrEmpty(ip)) { _byRobot[robot.robotId] = shared; return shared; }

            if (shared != null && shared.RosIPAddress == ip)
            {
                _byRobot[robot.robotId] = shared;
                return shared;
            }

            var go = new GameObject($"ROSConnection_{robot.robotId}");
            go.transform.SetParent(transform, false);
            var conn = go.AddComponent<ROSConnection>();
            conn.RosIPAddress = ip;
            conn.RosPort = Port;
            conn.ConnectOnStart = true;
            _byRobot[robot.robotId] = conn;
            Debug.Log($"[RosConnectionManager] {robot.robotId} → 전용 endpoint {ip}:{Port}");
            return conn;
        }
    }
}
