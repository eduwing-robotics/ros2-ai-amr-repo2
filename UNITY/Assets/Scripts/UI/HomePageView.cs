// opencode: 2026-06-29 - 홈 탭 대시보드 View. Coded with OpenCode; high-cost model review recommended.
// HomePageView.cs — 홈 탭 대시보드 데이터 렌더링.
// KPI 카운터(이벤트/경보/출동), 로봇 상태 카드(연결/역할/배터리/센서), 최근 활동 리스트를
// ControlRoomEvents/ControlRoomState로부터 갱신한다. 시뮬(FakeSensorData, DemoScenarioService)로
// 로봇 없이 즉시 검증 가능.
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.UI
{
    public class HomePageView
    {
        const int MaxActivityEntries = 50;
        const int SoundThreshold = 60;

        readonly Label dateLabel;
        readonly Label robotCountLabel;

        readonly Label kpiEvents;
        readonly Label kpiAlerts;
        readonly VisualElement kpiAlertsCard;
        readonly Label kpiDispatches;

        readonly VisualElement list;
        readonly ScrollView scroll;

        readonly Dictionary<string, HomeRobotRow> rows = new Dictionary<string, HomeRobotRow>();

        int eventCount;
        int alertCount;
        int dispatchCount;

        class HomeRobotRow
        {
            public Label Name;
            public Label Status;
            public Label Role;
            public Label BatteryPercent;
            public VisualElement BatteryFill;
            public Label Sensors;
        }

        public HomePageView(VisualElement root)
        {
            var page = root.Q<VisualElement>("home-page");
            if (page == null)
            {
                Debug.LogWarning("[HomePageView] home-page element not found — HomePage.uxml Instance 확인");
                return;
            }

            dateLabel = page.Q<Label>("home-date");
            robotCountLabel = page.Q<Label>("home-robot-count");

            kpiEvents = page.Q<Label>("kpi-events-value");
            kpiAlerts = page.Q<Label>("kpi-alerts-value");
            kpiAlertsCard = page.Q<VisualElement>("kpi-alerts");
            kpiDispatches = page.Q<Label>("kpi-dispatches-value");

            list = page.Q<VisualElement>("home-activity-list");
            scroll = page.Q<ScrollView>("home-activity-scroll");

            BindRobotRow(page, "tb3_1");
            BindRobotRow(page, "tb3_2");

            ControlRoomEvents.OnBatteryChanged += OnBatteryChanged;
            ControlRoomEvents.OnRobotConnectivity += OnRobotConnectivity;
            ControlRoomEvents.OnSensorChanged += OnSensorChanged;
            ControlRoomEvents.OnLogAdded += OnLogAdded;
            ControlRoomEvents.OnAlert += OnAlert;
            ControlRoomEvents.OnScenarioTriggered += OnScenarioTriggered;
            ControlRoomEvents.OnDispatchRequested += OnDispatchRequested;

            RefreshStatic();
            RestoreFromState();
            ShowEmptyIfNeeded();
        }

        void ShowEmptyIfNeeded()
        {
            if (list == null || list.childCount > 0) return;
            var empty = new Label("아직 활동이 없습니다") { name = "activity-empty" };
            empty.AddToClassList("home-activity-empty");
            list.Add(empty);
        }

        void BindRobotRow(VisualElement page, string robotId)
        {
            rows[robotId] = new HomeRobotRow
            {
                Name = page.Q<Label>($"robot-name-{robotId}"),
                Status = page.Q<Label>($"robot-status-{robotId}"),
                Role = page.Q<Label>($"robot-role-{robotId}"),
                BatteryPercent = page.Q<Label>($"robot-battery-{robotId}"),
                BatteryFill = page.Q<VisualElement>($"robot-battery-fill-{robotId}"),
                Sensors = page.Q<Label>($"robot-sensors-{robotId}")
            };
            // 배터리 데이터 오기 전에는 게이지를 비운다(USS 기본 폭이 "-- %"와 모순되지 않게).
            if (rows[robotId].BatteryFill != null)
                rows[robotId].BatteryFill.style.width = Length.Percent(0);
        }

        void RefreshStatic()
        {
            if (dateLabel != null) dateLabel.text = DateTime.Now.ToString("yyyy-MM-dd dddd", new System.Globalization.CultureInfo("ko-KR"));

            var robots = ControlRoomState.Instance.Robots;
            int total = robots?.Count ?? 0;
            int online = 0;
            if (robots != null)
            {
                foreach (var r in robots)
                    if (RobotConnectivityMonitor.IsOnline(r.robotId)) online++;
            }
            if (robotCountLabel != null) robotCountLabel.text = $"활성 로봇 {online}/{total}";

            if (robots != null)
            {
                foreach (var r in robots)
                {
                    if (rows.TryGetValue(r.robotId, out var row))
                    {
                        if (row.Name != null) row.Name.text = r.displayName;
                        if (row.Role != null)
                        {
                            row.Role.text = r.role;
                            row.Role.RemoveFromClassList("vision");
                            row.Role.RemoveFromClassList("sensor");
                            row.Role.RemoveFromClassList("unknown");
                            row.Role.AddToClassList(r.role == "sensor" ? "sensor" : r.role == "vision" ? "vision" : "unknown");
                        }
                    }
                }
            }
        }

        void RestoreFromState()
        {
            var s = ControlRoomState.Instance;
            foreach (var rid in rows.Keys)
            {
                bool online = RobotConnectivityMonitor.IsOnline(rid);
                ApplyConnectivity(rid, online);

                if (s.LastSensorValues.TryGetValue(rid, out var dict))
                {
                    if (dict.TryGetValue("battery", out var batt)) ApplyBattery(rid, batt);
                    UpdateSensorSummary(rid, dict);
                }
            }
        }

        void OnBatteryChanged(string robotId, float percent)
        {
            ApplyBattery(robotId, percent);
        }

        void ApplyBattery(string robotId, float percent)
        {
            if (!rows.TryGetValue(robotId, out var row)) return;
            if (row.BatteryPercent != null) row.BatteryPercent.text = $"{percent:F1} %";
            if (row.BatteryFill != null)
                row.BatteryFill.style.width = Length.Percent(Mathf.Clamp(percent, 0f, 100f));
        }

        void OnRobotConnectivity(string robotId, bool online)
        {
            ApplyConnectivity(robotId, online);
            RefreshStatic(); // 활성 로봇 수 갱신
        }

        void ApplyConnectivity(string robotId, bool online)
        {
            if (!rows.TryGetValue(robotId, out var row)) return;
            if (row.Status == null) return;

            row.Status.text = online ? "온라인" : "오프라인";
            row.Status.RemoveFromClassList("home-status-online");
            row.Status.RemoveFromClassList("home-status-offline");
            row.Status.AddToClassList(online ? "home-status-online" : "home-status-offline");
        }

        void OnSensorChanged(string robotId, string sensorId, float value)
        {
            var s = ControlRoomState.Instance;
            if (s.LastSensorValues.TryGetValue(robotId, out var dict))
                UpdateSensorSummary(robotId, dict);
        }

        void UpdateSensorSummary(string robotId, Dictionary<string, float> dict)
        {
            if (!rows.TryGetValue(robotId, out var row) || row.Sensors == null) return;

            var parts = new List<string>();
            if (dict.TryGetValue("pir", out var pir))
                parts.Add(pir >= 0.5f ? "PIR 감지" : "PIR 정상");
            if (dict.TryGetValue("sound", out var sound))
                parts.Add(sound >= SoundThreshold ? $"소음 {sound:F0}" : "소음 양호");
            if (dict.TryGetValue("temp", out var temp))
                parts.Add($"온도 {temp:F0}");

            row.Sensors.text = parts.Count > 0 ? string.Join(" · ", parts) : "센서 대기 중";
        }

        void OnLogAdded(string category, string level, string message)
        {
            if (level == "WARN" || level == "ERROR")
                eventCount++;
            AddActivity($"[{level}] {message}", LevelToClass(level));
            ApplyKpi();
        }

        void OnAlert(int severity, string message)
        {
            alertCount++;
            AddActivity($"[경보{severity}] {message}", "alert");
            ApplyKpi();
        }

        void OnScenarioTriggered(string scenarioId)
        {
            eventCount++;
            AddActivity($"[시나리오] {scenarioId}", "info");
            ApplyKpi();
        }

        void OnDispatchRequested(string robotId, float x, float y, string reason, bool simulated)
        {
            dispatchCount++;
            var tag = simulated ? "[출동-모의]" : "[출동]";
            AddActivity($"{tag} {robotId} → {reason}", "info");
            ApplyKpi();
        }

        void AddActivity(string text, string styleClass)
        {
            if (list == null) return;
            list.Q<Label>("activity-empty")?.RemoveFromHierarchy();
            var entry = new Label($"{DateTime.Now:HH:mm}  {text}");
            entry.AddToClassList("home-activity-entry");
            if (!string.IsNullOrEmpty(styleClass)) entry.AddToClassList(styleClass);
            list.Add(entry);
            while (list.childCount > MaxActivityEntries) list.RemoveAt(0);

            if (scroll != null)
                scroll.schedule.Execute(() => scroll.scrollOffset = new Vector2(0, float.MaxValue));
        }

        void ApplyKpi()
        {
            if (kpiEvents != null) kpiEvents.text = eventCount.ToString();
            if (kpiAlerts != null) kpiAlerts.text = alertCount.ToString();
            if (kpiDispatches != null) kpiDispatches.text = dispatchCount.ToString();
        }

        static string LevelToClass(string level)
        {
            switch (level)
            {
                case "WARN": return "warn";
                case "ERROR": return "error";
                default: return "info";
            }
        }
    }
}
