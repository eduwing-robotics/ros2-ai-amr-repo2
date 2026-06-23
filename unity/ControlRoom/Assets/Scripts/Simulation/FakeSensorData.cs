// FakeSensorData.cs — 실기기 미연결 상태에서 쓰는 fake 센서값 generator.
// Perlin/Sin 기반(random walk 아님)이라 부드러운 변화. 1초당 1~2회 발화.
// as-built 4센서(2026-06-18): battery + sound(swing) + temp(raw). pir/laser는 전이형이라 fake 제외.
// 실제 ROS 연결되면 본 컴포넌트는 비활성(enabled=false).
using UnityEngine;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Simulation
{
    public class FakeSensorData : MonoBehaviour
    {
        [Header("Tick rate (Hz)")]
        public float tickHz = 1.5f;

        [Header("Robot IDs to fake")]
        // tb3_2(젠지)는 실 ROS(arduino_bridge_quad → pir/sound/temp/laser + battery_state) 결선됨 → fake 제외.
        // tb3_1(티원)은 아직 센서 미준비 → fake 유지.
        public string[] robotIds = { "tb3_1" };

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
            foreach (var rid in robotIds)
            {
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
            }
        }

        void OnDisable()
        {
            // Domain Reload 안전: 다음 OnEnable에서 시작점 재계산.
            nextTick = 0;
        }
    }
}
