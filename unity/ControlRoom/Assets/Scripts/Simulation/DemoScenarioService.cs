// DemoScenarioService.cs — HTML의 화재/침입/소리/도난 데모 시나리오 트리거.
// ScenarioPanelView가 본 서비스의 Trigger(scenarioId) 호출 → 로그+경보 발화.
// 실제 ROS 이벤트 연결되면 본 서비스는 데모 모드 진입(수동) 시에만 활성.
using UnityEngine;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Simulation
{
    public class DemoScenarioService : MonoBehaviour
    {
        void Awake()
        {
            ControlRoomEvents.OnScenarioTriggered += HandleScenarioTriggered;
        }

        void OnDestroy()
        {
            ControlRoomEvents.OnScenarioTriggered -= HandleScenarioTriggered;
        }

        void HandleScenarioTriggered(string scenarioId)
        {
            switch (scenarioId)
            {
                case "fire":
                    ControlRoomEvents.RaiseLogAdded("scenario", "WARN", "화재 의심 시나리오 발화 (모의)");
                    ControlRoomEvents.RaiseAlert(3, "화재 감지 — 액자 주변 카메라 확인 필요");
                    break;
                case "intruder":
                    ControlRoomEvents.RaiseLogAdded("scenario", "WARN", "침입 시나리오 발화 (PIR+LiDAR 모의)");
                    ControlRoomEvents.RaiseAlert(2, "외부자 감지 — 출동 권장");
                    break;
                case "noise":
                    ControlRoomEvents.RaiseLogAdded("scenario", "INFO", "이상 소음 시나리오 발화 (모의)");
                    ControlRoomEvents.RaiseAlert(1, "이상 소음 감지");
                    break;
                case "theft":
                    ControlRoomEvents.RaiseLogAdded("scenario", "WARN", "도난 시나리오 발화 (보호 대상 미확인)");
                    ControlRoomEvents.RaiseAlert(3, "보호 대상 누락 의심");
                    break;
                default:
                    ControlRoomEvents.RaiseLogAdded("scenario", "ERROR", $"미정의 시나리오: {scenarioId}");
                    break;
            }
        }
    }
}
