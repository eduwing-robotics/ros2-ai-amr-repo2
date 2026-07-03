# scripts/v1 — 주행 코드 v1 (동결)

2026-06-25 실기 검증된 grid 좌표 주행 스크립트 스냅샷. **수정 금지(동결).**
이후 개선은 `scripts/v2/`에서 진행한다.

- `nav2_goal.py` — grid 목표 → Nav2 goToPose (planner/costmap)
- `goto_axis.py` — 축 정렬 주행(X직진→Y회전→Y직진), 회전±2°/위치 7cm 오차범위
- `rotate_to_goal.py` — 목표 정면으로 제자리 회전
- `pose_logger_grid.py` — /amcl_pose → grid 좌표 캡처

검증 기록: `/home/kimsunil/waypoint/주행기록_2026-06-25.txt`
