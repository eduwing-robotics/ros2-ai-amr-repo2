// SituationInfo.cs — 좌표 기반 상황 SSOT(default_situations.json) 1:1 매핑(순수 POCO).
// 맵 우클릭 컨텍스트 메뉴의 "상황 출동" 액션을 SSOT가 주도하도록 한다.
using System;

namespace URHYNIX.ControlRoom.Data
{
    [Serializable]
    public class SituationInfo
    {
        public string situationId;   // "fire" / "intruder" ...
        public string displayName;   // "화재" / "침입"
        public string sensorTrigger; // 연관 센서 id (SensorInfo.sensorId), 옵션
        public int severity;         // 0~3 (경보 등급)
        public string icon;          // 메뉴 아이콘 텍스트/이모지, 옵션
    }

    [Serializable]
    public class SituationInfoList
    {
        public SituationInfo[] situations;
    }
}
