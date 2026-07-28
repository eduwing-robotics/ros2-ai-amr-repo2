// FeatureInventoryView.cs — 현재 로봇 기준 기능/센서/예정 항목을 한눈에 보여주는 상태 인벤토리.
// Registry JSON을 읽어 "준비됨/부분/대기/예정" 뱃지로만 표시한다. 명령 실행은 다른 View 책임.
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Features;
using URHYNIX.ControlRoom.Sensors;

namespace URHYNIX.ControlRoom.UI
{
    public class FeatureInventoryView
    {
        readonly VisualElement list;
        readonly FeatureRegistry features = new FeatureRegistry();
        readonly SensorRegistry sensors = new SensorRegistry();

        public FeatureInventoryView(VisualElement root)
        {
            list = root.Q<VisualElement>("feature-inventory-list");
            features.LoadFromResources();
            sensors.LoadFromResources();

            ControlRoomEvents.OnRobotChanged += _ => Rebuild();
            Rebuild();
        }

        void Rebuild()
        {
            if (list == null) return;
            list.Clear();

            var robot = ControlRoomState.Instance.GetSelectedRobot();
            if (robot == null)
            {
                AddRow("로봇 메타", "대기", "inventory-status-planned");
                return;
            }

            AddRow($"{robot.displayName} 카메라", string.IsNullOrEmpty(robot.cameraTopic) ? "예정" : "준비됨",
                string.IsNullOrEmpty(robot.cameraTopic) ? "inventory-status-planned" : "inventory-status-ready");
            AddRow($"{robot.displayName} 위치", string.IsNullOrEmpty(robot.poseTopic) ? "예정" : "준비됨",
                string.IsNullOrEmpty(robot.poseTopic) ? "inventory-status-planned" : "inventory-status-ready");
            AddRow("좌표 출동", HasCapability(robot, "patrol") ? "준비됨" : "미지원",
                HasCapability(robot, "patrol") ? "inventory-status-ready" : "inventory-status-planned");
            AddRow("3D URDF 맵", "예정", "inventory-status-planned");

            foreach (var feature in features.GetFeaturesForRobot(robot.robotId))
            {
                string status = feature.isActive ? "켜짐" : "대기";
                AddRow(feature.displayName, status, feature.isActive ? "inventory-status-ready" : "inventory-status-off");
            }

            var robotSensors = sensors.GetSensorsForRobot(robot.robotId);
            if (robotSensors.Count == 0)
            {
                AddRow("센서 카드", "미지원", "inventory-status-planned");
            }
            foreach (var sensor in robotSensors)
            {
                string status = "준비됨";
                string statusClass = "inventory-status-ready";
                if (sensor.sensorId == "temp")
                {
                    status = "raw";
                    statusClass = "inventory-status-partial";
                }
                else if (sensor.sensorId == "laser")
                {
                    status = "미결선";
                    statusClass = "inventory-status-partial";
                }
                AddRow(sensor.displayName, status, statusClass);
            }

            AddRow("보호대상 저장", "예정", "inventory-status-planned");
        }

        static bool HasCapability(RobotInfo robot, string capability)
        {
            if (robot?.capabilities == null) return false;
            foreach (var cap in robot.capabilities)
                if (cap == capability) return true;
            return false;
        }

        void AddRow(string name, string status, string statusClass)
        {
            var row = new VisualElement();
            row.AddToClassList("inventory-row");

            var nameLabel = new Label(name);
            nameLabel.AddToClassList("inventory-name");
            row.Add(nameLabel);

            var statusLabel = new Label(status);
            statusLabel.AddToClassList("inventory-status");
            statusLabel.AddToClassList(statusClass);
            row.Add(statusLabel);

            list.Add(row);
        }
    }
}
