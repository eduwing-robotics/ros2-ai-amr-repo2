// opencode: 2026-06-30 - SituationConfig SSOT 기반 동적 처리 + demoMode 분기 추가.
// DemoScenarioService.cs — HTML의 화재/침입/소리/도난 데모 시나리오 트리거.
// ScenarioPanelView가 본 서비스의 Trigger(scenarioId) 호출 → 로그+경보 발화.
// demoMode=true 일 때만 인공 로그/경보를 발화. 실제 운영 모드(demoMode=false)에서는
// 시나리오 버튼이 비활성화되며, 실제 이벤트는 ROS 보안 이벤트 subscriber가 처리(Phase 4).
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Simulation
{
    public class DemoScenarioService : MonoBehaviour
    {
        public static DemoScenarioService Instance { get; private set; }

        [Header("Demo mode")]
        [Tooltip("true면 시나리오 버튼이 모의 로그/경보를 발화. false면 비활성화.")]
        public bool demoMode = true;

        const string SituationConfigPath = "SituationConfig/default_situations";
        readonly Dictionary<string, SituationInfo> situations = new Dictionary<string, SituationInfo>();

        void Awake()
        {
            if (Instance != null) { Destroy(gameObject); return; }
            Instance = this;

            LoadSituations();
            ControlRoomEvents.OnScenarioTriggered += HandleScenarioTriggered;
        }

        void OnDestroy()
        {
            if (Instance == this) Instance = null;
            ControlRoomEvents.OnScenarioTriggered -= HandleScenarioTriggered;
        }

        void LoadSituations()
        {
            var ta = Resources.Load<TextAsset>(SituationConfigPath);
            if (ta == null)
            {
                Debug.LogWarning($"[DemoScenarioService] {SituationConfigPath}.json 없음 — 하드코딩 fallback");
                return;
            }
            var list = JsonUtility.FromJson<SituationInfoList>(ta.text);
            if (list?.situations == null) return;
            foreach (var s in list.situations)
                if (s != null && !string.IsNullOrEmpty(s.situationId))
                    situations[s.situationId] = s;
        }

        void HandleScenarioTriggered(string scenarioId)
        {
            if (!demoMode)
            {
                Debug.Log($"[DemoScenarioService] {scenarioId} 무시 — demoMode=false");
                return;
            }

            if (!situations.TryGetValue(scenarioId, out var s))
            {
                ControlRoomEvents.RaiseLogAdded("scenario", "ERROR", $"미정의 시나리오: {scenarioId}");
                return;
            }

            ControlRoomEvents.RaiseLogAdded("scenario", "WARN", $"{s.displayName} 시나리오 발화 ({s.sensorTrigger}) 모의");
            ControlRoomEvents.RaiseAlert(s.severity, $"{s.displayName} 감지 — {s.sensorTrigger}");

            // SSOT의 demoDispatch=true면 모의 출동까지 발화 — 차폐벽(FireShutter) 등 출동 구독자가 데모 버튼으로도 반응.
            if (s.demoDispatch)
            {
                string robotId = ControlRoomState.Instance?.SelectedRobotId;
                ControlRoomEvents.RaiseLogAdded("dispatch", "WARN",
                    $"{s.displayName} 모의 출동: {robotId} → ({s.demoX:0.00}, {s.demoY:0.00})");
                ControlRoomEvents.RaiseDispatchRequested(robotId, s.demoX, s.demoY, s.situationId, simulated: true);
            }
        }
    }
}
