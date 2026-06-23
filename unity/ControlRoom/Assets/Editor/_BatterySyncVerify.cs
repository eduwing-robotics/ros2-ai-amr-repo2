// _BatterySyncVerify.cs — 일회성 검증 Editor 스크립트. 검증 후 즉시 삭제.
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.EditorTools
{
    public static class _BatterySyncVerify
    {
        public static void Run()
        {
            var s = ControlRoomState.Instance;
            UIDocument uiDoc = null;
            var all = Object.FindObjectsByType<UIDocument>(FindObjectsSortMode.None);
            foreach (var d in all)
            {
                var rv = d != null ? d.rootVisualElement : null;
                if (rv != null && rv.Q<Label>("battery-percent-label") != null) { uiDoc = d; break; }
            }
            if (uiDoc == null) { Debug.LogError("[VERIFY] UIDocument(battery-percent-label) 미발견"); return; }

            var root  = uiDoc.rootVisualElement;
            var label = root.Q<Label>("battery-percent-label");
            var fill  = root.Q<VisualElement>("battery-bar-fill");

            float v1 = float.NaN, v2 = float.NaN;
            if (s.LastSensorValues.TryGetValue("tb3_1", out var d1) && d1.TryGetValue("battery", out var x)) v1 = x;
            if (s.LastSensorValues.TryGetValue("tb3_2", out var d2) && d2.TryGetValue("battery", out var y)) v2 = y;

            string current = s.SelectedRobotId;
            string other   = current == "tb3_1" ? "tb3_2" : "tb3_1";

            Debug.Log($"[VERIFY] BEFORE selected={current} label='{label.text}' fillW={fill.style.width.value.value:F1}% tb3_1={v1:F2} tb3_2={v2:F2}");

            s.SelectRobot(other);
            Debug.Log($"[VERIFY] AFTER  selected={s.SelectedRobotId} label='{label.text}' fillW={fill.style.width.value.value:F1}%");

            s.SelectRobot(current);
            Debug.Log($"[VERIFY] RESTORE selected={s.SelectedRobotId} label='{label.text}' fillW={fill.style.width.value.value:F1}%");
        }
    }
}
