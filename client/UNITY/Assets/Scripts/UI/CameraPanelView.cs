// CameraPanelView.cs — 카메라 패널 View. 활성 robotId(상단 탭 선택)의 frame만 ui:Image에 표시.
// 모델 B (동시 구독 + display 토글): 두 Subscriber가 항상 frame을 쏘고, View가 robotId로 필터링.
// 전환 지연 0~33ms (다음 frame 즉시). 로딩 스피너 불필요.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Ros;

namespace URHYNIX.ControlRoom.UI
{
    public class CameraPanelView
    {
        readonly Image cameraImage;
        readonly Label hzLabel;
        readonly Label placeholderText;
        string activeRobotId;

        public CameraPanelView(VisualElement root)
        {
            cameraImage     = root.Q<Image>("camera-image");
            hzLabel         = root.Q<Label>("camera-hz");
            placeholderText = root.Q<Label>("camera-placeholder-text");

            if (hzLabel != null) hzLabel.text = "-- Hz";

            activeRobotId = ControlRoomState.Instance.SelectedRobotId;

            CameraStreamSubscriber.OnFrameUpdated += OnFrameUpdated;
            ControlRoomEvents.OnRobotChanged      += OnRobotChanged;
        }

        void OnFrameUpdated(string robotId, Texture2D tex, float hz)
        {
            if (robotId != activeRobotId) return;
            if (cameraImage != null && tex != null)
            {
                cameraImage.image = tex;
                if (placeholderText != null && placeholderText.style.display != DisplayStyle.None)
                    placeholderText.style.display = DisplayStyle.None;
            }
            if (hzLabel != null) hzLabel.text = $"{hz:F1} Hz";
        }

        void OnRobotChanged(string robotId)
        {
            activeRobotId = robotId;
            if (hzLabel != null) hzLabel.text = "-- Hz";
            ControlRoomEvents.RaiseLogAdded("camera", "INFO", $"카메라 전환 → {robotId}");
        }
    }
}
