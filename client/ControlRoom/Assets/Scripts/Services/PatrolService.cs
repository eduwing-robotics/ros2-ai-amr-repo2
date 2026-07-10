// PatrolService.cs — 순찰 웨이포인트 목록 SSOT(싱글톤). 추가/마지막제거/전체삭제 + 자동 재번호.
// 변경 시 ControlRoomEvents.OnPatrolChanged 발화 → 마커레이어/리스트뷰가 갱신. ROS/UI 비의존.
using System.Collections.Generic;
using URHYNIX.ControlRoom.App;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Services
{
    public class PatrolService
    {
        public static PatrolService Instance { get; } = new PatrolService();
        private PatrolService() { }

        readonly List<PatrolPoint> points = new List<PatrolPoint>();
        public IReadOnlyList<PatrolPoint> Points => points;
        public int Count => points.Count;

        public void Add(float x, float y, float theta = 0f)
        {
            points.Add(new PatrolPoint { x = x, y = y, theta = theta });
            Renumber();
            ControlRoomEvents.RaisePatrolChanged();
        }

        public void RemoveLast()
        {
            if (points.Count == 0) return;
            points.RemoveAt(points.Count - 1);
            Renumber();
            ControlRoomEvents.RaisePatrolChanged();
        }

        public void Clear()
        {
            if (points.Count == 0) return;
            points.Clear();
            ControlRoomEvents.RaisePatrolChanged();
        }

        // 외부(리포지토리)에서 통째로 교체할 때.
        public void Replace(IEnumerable<PatrolPoint> newPoints)
        {
            points.Clear();
            if (newPoints != null) points.AddRange(newPoints);
            Renumber();
            ControlRoomEvents.RaisePatrolChanged();
        }

        void Renumber()
        {
            for (int i = 0; i < points.Count; i++) points[i].seq = i + 1;
        }
    }
}
