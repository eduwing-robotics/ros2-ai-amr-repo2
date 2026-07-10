# scripts/v2 — 주행 코드 v2 (작업용)

`scripts/v1/`(동결본)과 동일한 코드로 시작한 작업 버전. 여기서 개선/재작성한다.

## nav2_goal 계열 (Nav2 기반 grid 목표 주행)

버전이 올라갈수록 기능이 누적된다. `nav2_goal.py` → `_v3` → `_v4`.

### `nav2_goal.py` — 베이스라인
- grid(0~200) 목표 → `BasicNavigator.goToPose`
- 피드백 루프 실사용: 남은거리 / ETA / 경과 / 복구횟수 로깅
- **다중 웨이포인트 + `--loop`**, 도착방향 정책(다음점/왔던곳/루프)
- Nav2 활성화 무한대기하되 60초마다 로그, 안전 종료 + 중단 시 goal 취소

### `nav2_goal_v3.py` — 견고성/UX 추가 (좌표계는 하드코딩)
`nav2_goal.py` + 아래:
- **스턱 감지** — 무진전(남은거리 STUCK_TIME 동안 안 줄음) + 복구 누적 임계
- **번갈이 탈출 기동** — 스턱 시 `backup→spin(±ESCAPE_ANGLE)→driveOnHeading`, 막히면 반대쪽으로 번갈아(오→왼→오→왼), 소진 시 스킵
- 취소 후 완료 대기(`cancel_and_wait`, getResult 레이스 방지)
- 퇴화 bearing 가드(두 점 근접 시 현재 heading 유지)
- **localize 가드** — `map→base_footprint` TF 없으면 주행 중단
- **argparse** — `--loop --laps --timeout --stuck-time --max-escape --escape-angle --escape-back --escape-fwd` (튜닝값 실행 시 조절), `--help`
- 좌표계: `MAP_ORIGIN_X/Y`, `MAP_SIZE`, `GRID_MAX` **코드 하드코딩**

### `nav2_goal_v4.py` — 좌표계를 맵 파일에서 로드
`nav2_goal_v3.py` + 아래:
- **`--map <map.yaml>`** — `load_map_frame()`이 origin/resolution/이미지 픽셀크기를 읽어 좌표계 설정 (하드코딩 제거, 맵 바뀌어도 코드 수정 0). PGM/PNG 픽셀 리더 내장
- **`check_map_match()`** — Nav2 `/map`(latched) 메타데이터와 `--map` 파일 비교, 불일치 시 경고
- `MAP_SIZE_X/Y`로 비정사각 맵 대응 (`--map` 미지정 시 기본값 폴백)

## 기타 스크립트

- `goto_axis.py` — 축 정렬 주행(X정렬→X직진→Y정렬→Y직진). 직진 중 heading **deadband 8° / gate 20°** (무보정 구간으로 꿈틀거림 억제). **Nav2 미사용 = 장애물 회피 없음**
- `rotate_to_goal.py` — 목표 정면 제자리 회전 (v1과 동일)
- `pose_logger_grid.py` — `/amcl_pose` → grid 좌표 캡처 (v1과 동일)

## 남은 개선 후보

- goto_axis: 순차 축이동 cross-axis 드리프트 → 도착 후 X,Y 재확인 **수렴 루프** (deadband 넓혀 정확도 손해 본 것 되잡기)
- nav2_goal: 목표가 벽/맵밖인지 **도달가능 사전확인**(헛도는 탈출/스킵 방지), 탈출 방향 **costmap 반영**(트인 쪽 먼저), map origin **θ(회전)** 반영
- 실기 검증: 탈출 기동(`backup/spin/driveOnHeading` 인자·±30°/20cm), 좌표계 정확도 — 봇 + Nav2 띄운 뒤

v1 동결본: `scripts/v1/` · 검증 기록: `/home/kimsunil/waypoint/주행기록_2026-06-25.txt`
