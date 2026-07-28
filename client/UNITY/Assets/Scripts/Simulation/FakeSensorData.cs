// opencode: 2026-06-30 - ROS 연결 감지 시 fake off. 실제 연결된 로봇은 fake 값 발화 안 함.
// FakeSensorData.cs — 실기기 미연결 상태에서 쓰는 fake 센서값 generator.
// Perlin/Sin 기반(random walk 아님)이라 부드러운 변화. 1초당 1~2회 발화.
// as-built 4센서(2026-06-18): battery + sound(swing) + temp(raw). pir/laser는 전이형이라 fake 제외.
// 실제 ROS 연결되면 해당 로봇에는 fake 값을 발화하지 않는다.
using UnityEngine;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Simulation
{
    public class FakeSensorData : MonoBehaviour
    {
        [Header("Tick rate (Hz)")]
        public float tickHz = 1.5f;

        [Header("Debug: fake 발화 로깅")]
        public bool logTicks = false;

        float nextTick;
        float startTime;

        void OnEnable()
        {
            startTime = Time.time;
            nextTick = Time.time + 0.5f;
        }

        void Update()
        {
            if (Time.time < nextTick) return;
            nextTick = Time.time + (1f / Mathf.Max(0.1f, tickHz));

            float t = Time.time - startTime;
            var robots = ControlRoomState.Instance.Robots;
            if (robots == null) return;

            foreach (var robot in robots)
            {
                if (robot == null || string.IsNullOrEmpty(robot.robotId)) continue;
                string rid = robot.robotId;

                // 실제 ROS 연결 중이면 fake로 덮어쓰지 않는다.
                if (RobotConnectivityMonitor.IsOnline(rid))
                {
                    if (logTicks) Debug.Log($"[FakeSensorData] {rid} online — skip fake");
                    continue;
                }

                // Battery: 87% 근처에서 ±3% 천천히 변동 (Perlin)
                float battery = 87f + (Mathf.PerlinNoise(t * 0.05f, rid.GetHashCode() * 0.001f) - 0.5f) * 6f;
                ControlRoomEvents.RaiseBatteryChanged(rid, battery);
                ControlRoomState.Instance.SetSensorValue(rid, "battery", battery);

                // Sound: swing 0~120 (Perlin). 가끔 임계 60 넘겨 "소음 감지!" 색 토글 확인 가능.
                float sound = Mathf.PerlinNoise(t * 0.3f, 1f + rid.GetHashCode() * 0.001f) * 120f;
                ControlRoomState.Instance.SetSensorValue(rid, "sound", sound);

                // Temp: PP-A017 raw 150~260 (sin 파동, 보정 전 raw)
                float temp = 205f + Mathf.Sin(t * 0.15f + rid.GetHashCode() * 0.02f) * 55f;
                ControlRoomState.Instance.SetSensorValue(rid, "temp", temp);

                if (logTicks) Debug.Log($"[FakeSensorData] {rid} fake tick");
            }
        }

        void OnDisable()
        {
            // Domain Reload 안전: 다음 OnEnable에서 시작점 재계산.
            nextTick = 0;
        }
    }
}
