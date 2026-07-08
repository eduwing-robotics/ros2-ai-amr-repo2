// FireShutter.cs — 차폐벽: 평소 열림(패널이 헤더박스 안으로 말려 올라감), 화재 출동 시 하강 닫힘.
// ControlRoomEvents.OnDispatchRequested(reason=="fire") 구독 → 닫힘 → autoOpenSeconds 후 자동 오픈.
// 지오메트리(헤더/레일/패널)는 MuseumDecorSpawner.SpawnShutter가 만들고 Configure()로 결선.
using System.Collections;
using UnityEngine;
using URHYNIX.ControlRoom.App;

namespace URHYNIX.ControlRoom.Map
{
    public class FireShutter : MonoBehaviour
    {
        public float slideSeconds = 1.2f;
        public float autoOpenSeconds = 10f;
        const float RolledHeight = 0.015f; // 열림 시 헤더 밑에 살짝 보이는 패널 두께

        Transform panel;
        float fullHeight, topY;
        Coroutine run;

        public void Configure(Transform panelTf, float height)
        {
            panel = panelTf;
            fullHeight = height;
            topY = height; // 패널 상단 고정선(헤더박스 하단) — 여기 매달려 아래로 자람
            SetPanelHeight(RolledHeight); // 평소 열림
        }

        void OnEnable() => ControlRoomEvents.OnDispatchRequested += OnDispatch;
        void OnDisable() => ControlRoomEvents.OnDispatchRequested -= OnDispatch;

        void OnDispatch(string robotId, float x, float y, string reason, bool simulated)
        {
            if (reason == "fire") TriggerClose();
        }

        // 데모/수동 트리거용 공개 API — 화재 출동 이벤트와 동일 동작.
        public void TriggerClose()
        {
            if (panel == null) return;
            if (run != null) StopCoroutine(run);
            run = StartCoroutine(CloseThenAutoOpen());
        }

        IEnumerator CloseThenAutoOpen()
        {
            ControlRoomEvents.RaiseLogAdded("barrier", "WARN", "차폐벽 하강 시작 — 화재 출동");
            yield return Slide(fullHeight);
            ControlRoomEvents.RaiseLogAdded("barrier", "WARN", $"차폐벽 닫힘 — {autoOpenSeconds:0}초 후 자동 개방");
            yield return new WaitForSeconds(autoOpenSeconds);
            yield return Slide(RolledHeight);
            ControlRoomEvents.RaiseLogAdded("barrier", "INFO", "차폐벽 개방 — 상황 해제");
            run = null;
        }

        IEnumerator Slide(float targetH)
        {
            float from = panel.localScale.y, t = 0f;
            while (t < 1f)
            {
                t += Time.deltaTime / Mathf.Max(0.05f, slideSeconds);
                SetPanelHeight(Mathf.Lerp(from, targetH, Mathf.SmoothStep(0f, 1f, t)));
                yield return null;
            }
        }

        // 상단 고정 롤업: 높이 h로 스케일하고 중심을 topY-h/2에 둬 위쪽 모서리를 고정.
        void SetPanelHeight(float h)
        {
            var sc = panel.localScale;
            sc.y = h;
            panel.localScale = sc;
            var p = panel.localPosition;
            p.y = topY - h * 0.5f;
            panel.localPosition = p;
        }
    }
}
