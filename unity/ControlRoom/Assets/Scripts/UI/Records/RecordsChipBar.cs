// RecordsChipBar.cs — 기록 탭 칩 필터 UI 공통 헬퍼.
// MakeChip/SetSingleChip/IsCategoryLabel은 로그/타임라인/KPI 서브탭에서 재사용.
using UnityEngine.UIElements;

namespace URHYNIX.ControlRoom.UI.Records
{
    public static class RecordsChipBar
    {
        public static Button MakeChip(string label, bool active)
        {
            var btn = new Button { text = label };
            btn.AddToClassList("records-chip");
            if (active) btn.AddToClassList("active");
            return btn;
        }

        public static void SetSingleChip(ref Button current, Button next, bool active)
        {
            if (active)
            {
                current?.RemoveFromClassList("active");
                current = next;
                current.AddToClassList("active");
            }
            else
            {
                next.RemoveFromClassList("active");
                if (current == next) current = null;
            }
        }

        public static bool IsCategoryLabel(string text)
        {
            return text == "전체" || text == "시스템" || text == "센서" || text == "출동" || text == "감사";
        }
    }
}
