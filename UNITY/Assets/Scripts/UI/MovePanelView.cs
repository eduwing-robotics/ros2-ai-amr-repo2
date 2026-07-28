// MovePanelView.cs — 좌측 패널의 순회/조작 카드. 순회 시작/정지 버튼.
// 클릭 → ControlRoomEvents.RaiseLogAdded로 로그 push. Phase 5에서 RobotCommandService로 swap.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class MovePanelView
    {
        readonly Button startBtn;
        readonly Button stopBtn;
        bool patrolling;

        public MovePanelView(VisualElement root)
        {
            startBtn = root.Q<Button>("btn-patrol-start");
            stopBtn  = root.Q<Button>("btn-patrol-stop");

            if (startBtn != null) startBtn.clicked += OnStart;
            if (stopBtn  != null) stopBtn.clicked  += OnStop;

            UpdateActiveStyle();
        }

        void OnStart()
        {
            if (patrolling) return;
            patrolling = true;
            UpdateActiveStyle();
            ControlRoomEvents.RaiseLogAdded("patrol", "INFO", "순회 시작 요청");
        }

        void OnStop()
        {
            if (!patrolling) return;
            patrolling = false;
            UpdateActiveStyle();
            ControlRoomEvents.RaiseLogAdded("patrol", "INFO", "순회 정지 요청");
        }

        void UpdateActiveStyle()
        {
            if (startBtn != null)
            {
                if (patrolling) startBtn.AddToClassList("active");
                else startBtn.RemoveFromClassList("active");
            }
            if (stopBtn != null)
            {
                if (!patrolling) stopBtn.AddToClassList("active");
                else stopBtn.RemoveFromClassList("active");
            }
        }
    }
}
