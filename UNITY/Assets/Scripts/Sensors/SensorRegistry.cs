// SensorRegistry.cs — 센서 메타 등록소. default_sensors.json 1회 로드 → SensorInfo[] 보관.
// 외부에서 ID/로봇별 조회만 제공. 실 ROS 구독은 Phase 5 ISensorModule 구현체가 담당.
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Sensors
{
    public class SensorRegistry
    {
        const string ResourcePath = "SensorConfig/default_sensors";

        readonly List<SensorInfo> _sensors = new List<SensorInfo>();

        public IReadOnlyList<SensorInfo> All => _sensors;

        public void LoadFromResources()
        {
            _sensors.Clear();
            var ta = Resources.Load<TextAsset>(ResourcePath);
            if (ta == null)
            {
                Debug.LogWarning($"[SensorRegistry] '{ResourcePath}' 누락. 빈 컬렉션으로 부팅 계속.");
                return;
            }
            try
            {
                var list = JsonUtility.FromJson<SensorInfoList>(ta.text);
                if (list?.sensors != null) _sensors.AddRange(list.sensors);
                Debug.Log($"[SensorRegistry] {_sensors.Count}개 센서 로드.");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[SensorRegistry] 파싱 실패: {e.Message}");
            }
        }

        public SensorInfo GetById(string sensorId)
        {
            return _sensors.Find(s => s.sensorId == sensorId);
        }

        // robotId가 일치하는 센서만. POCO 규약상 robotId=""인 센서는 "전체 공통"으로 간주.
        public List<SensorInfo> GetSensorsForRobot(string robotId)
        {
            return _sensors.FindAll(s => s.robotId == robotId || string.IsNullOrEmpty(s.robotId));
        }
    }
}
