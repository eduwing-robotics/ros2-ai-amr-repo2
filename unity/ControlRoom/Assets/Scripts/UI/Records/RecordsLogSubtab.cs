// RecordsLogSubtab.cs — 기록 탭 > 로그 서브탭.
// category 칩 + level 칩으로 logs 테이블을 필터링해 카드 리스트로 렌더한다.
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UIElements;
using URHYNIX.ControlRoom.Data;
using URHYNIX.ControlRoom.Database;

namespace URHYNIX.ControlRoom.UI.Records
{
    public class RecordsLogSubtab : IRecordsSubtab
    {
        const int Limit = 50;

        readonly MonoBehaviour host;
        readonly LogRepository logRepo;
        readonly VisualElement chipRow;
        readonly VisualElement logsList;

        Button activeCategoryChip;
        Button activeLevelChip;
        string currentCategoryFilter;
        string currentLevelFilter;

        public RecordsLogSubtab(MonoBehaviour host, LogRepository logRepo,
                                VisualElement chipRow, VisualElement logsList)
        {
            this.host = host;
            this.logRepo = logRepo;
            this.chipRow = chipRow;
            this.logsList = logsList;
        }

        public void Build()
        {
            if (chipRow == null) return;
            chipRow.Clear();
            activeCategoryChip = null;
            activeLevelChip = null;
            currentCategoryFilter = null;
            currentLevelFilter = null;

            AddCategoryChip("전체", null, active: true);
            AddCategoryChip("시스템", "system");
            AddCategoryChip("센서", "sensor");
            AddCategoryChip("출동", "dispatch");
            AddCategoryChip("감사", "audit");

            var spacer = new VisualElement();
            spacer.style.width = 12;
            chipRow.Add(spacer);

            AddLevelChip("INFO", "INFO");
            AddLevelChip("WARN", "WARN");
            AddLevelChip("ERROR", "ERROR");
        }

        public void Load() => InternalLoad();
        public void Refresh() => InternalLoad();

        void InternalLoad()
        {
            if (host == null) return;
            host.StartCoroutine(logRepo.Query(Limit, (ok, rows) => RenderLogs(rows),
                category: currentCategoryFilter,
                level: currentLevelFilter));
        }

        void AddCategoryChip(string label, string value, bool active = false)
        {
            var btn = RecordsChipBar.MakeChip(label, active);
            btn.clicked += () =>
            {
                if (activeCategoryChip == btn)
                {
                    if (currentCategoryFilter != null)
                    {
                        RecordsChipBar.SetSingleChip(ref activeCategoryChip, btn, false);
                        currentCategoryFilter = null;
                        var all = chipRow.Query<Button>().ToList().FirstOrDefault(b => b.text == "전체");
                        if (all != null) RecordsChipBar.SetSingleChip(ref activeCategoryChip, all, true);
                        Refresh();
                    }
                    return;
                }
                RecordsChipBar.SetSingleChip(ref activeCategoryChip, btn, true);
                currentCategoryFilter = value;
                foreach (var other in chipRow.Query<Button>().ToList()
                    .Where(b => RecordsChipBar.IsCategoryLabel(b.text) && b != btn))
                    other.RemoveFromClassList("active");
                Refresh();
            };
            if (active)
            {
                activeCategoryChip = btn;
                currentCategoryFilter = value;
            }
            chipRow.Add(btn);
        }

        void AddLevelChip(string label, string value)
        {
            var btn = RecordsChipBar.MakeChip(label, false);
            btn.clicked += () =>
            {
                if (activeLevelChip == btn)
                {
                    RecordsChipBar.SetSingleChip(ref activeLevelChip, btn, false);
                    currentLevelFilter = null;
                }
                else
                {
                    RecordsChipBar.SetSingleChip(ref activeLevelChip, btn, true);
                    currentLevelFilter = value;
                }
                Refresh();
            };
            chipRow.Add(btn);
        }

        void RenderLogs(List<LogRow> rows)
        {
            if (logsList == null) return;
            logsList.Clear();
            if (rows == null || rows.Count == 0)
            {
                logsList.Add(RecordsRenderHelpers.MakeEmpty("조건에 맞는 로그가 없습니다."));
                return;
            }
            foreach (var r in rows)
                logsList.Add(RecordsRenderHelpers.MakeLogCard(r));
        }
    }
}
