# Stack Profiles

새 프로젝트는 아래 starter profile 중 가장 가까운 것을 골라 `PROJECT-PLAN.md`, `ARCHITECTURE.md`, `PROJECT-STATUS.md`, 필요 시 `PRD.md`를 채운다.

## Next.js + FastAPI + Supabase

- Use when:
  - 웹 UI, Python 백엔드, auth/database 속도가 동시에 필요할 때
- Suggested boundaries:
  - `apps/web`
  - `backend/app`
  - `src/shared`
- Naming contract starters:
  - route: `GET /api/v1/records`
  - table/schema: `health_records`
  - env: `NEXT_PUBLIC_SUPABASE_URL`
  - env: `SUPABASE_SERVICE_ROLE_KEY`
- Suggested skills:
  - `project-planning`
  - `socratic-review`
  - `big-task`
  - `api-contract-guard`
  - `doc-sync`
- Suggested verify:
  - `bash scripts/check-project.sh`
  - `pnpm typecheck`
  - `pnpm build`
  - `pytest`
- Suggested file map starters:
  - `candidate:apps/web/app/dashboard/page.tsx`
  - `candidate:backend/app/api/records.py`
  - `docs/ref/PRD.md`
  - `docs/status/PROJECT-STATUS.md`
- Suggested architecture notes:
  - `apps/web`는 route, page, UI surface를 담당한다
  - `backend/app`은 API contract와 workflow orchestration을 담당한다
  - `src/shared`는 공용 types와 helper를 담당한다
  - external systems는 auth, database, storage를 명시한다
- Suggested next actions:
  - `ARCHITECTURE.md`에 web/api/shared boundary를 적는다
  - `PROJECT-PLAN.md`에 first route와 first API 후보를 적는다
  - `PROJECT-STATUS.md`에 `pnpm typecheck`, `pnpm build`, `pytest`를 추가한다

## Next.js + Supabase

- Use when:
  - 빠른 MVP
  - BaaS 중심
  - 별도 백엔드가 아직 불필요할 때
- Suggested boundaries:
  - `apps/web`
  - `src/features`
- Naming contract starters:
  - route: `app/dashboard/page.tsx`
  - table/schema: `user_profiles`
  - env: `NEXT_PUBLIC_SUPABASE_URL`
  - env: `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Suggested skills:
  - `project-planning`
  - `design-to-code`
  - `api-contract-guard`
  - `doc-sync`
- Suggested verify:
  - `bash scripts/check-project.sh`
  - `pnpm typecheck`
  - `pnpm build`
- Suggested file map starters:
  - `candidate:apps/web/app/dashboard/page.tsx`
  - `candidate:src/features/onboarding/index.ts`
  - `docs/ref/PRD.md`
  - `docs/status/PROJECT-STATUS.md`
- Suggested architecture notes:
  - `apps/web`는 app route와 page surface를 담당한다
  - `src/features`는 feature module 경계다
  - external systems는 auth, database, storage를 명시한다
  - 별도 backend를 쓰지 않으면 그 사실을 boundaries에 적는다
- Suggested next actions:
  - `PROJECT-PLAN.md`에 route starter와 feature boundary를 적는다
  - `ARCHITECTURE.md`에 backend 미사용 여부를 적는다
  - `PROJECT-STATUS.md`에 `pnpm typecheck`, `pnpm build`를 추가한다

## Python API + Worker

- Use when:
  - ingestion
  - automation
  - batch
  - workflow 중심 프로젝트일 때
- Suggested boundaries:
  - `src/`
  - `backend/`
  - `workers/`
- Naming contract starters:
  - route: `POST /internal/jobs/sync`
  - table/schema: `job_runs`
  - env: `SERVICE_BASE_URL`
  - env: `QUEUE_NAME`
- Suggested skills:
  - `project-planning`
  - `big-task`
  - `migration-manifest`
  - `doc-sync`
- Suggested verify:
  - `bash scripts/check-project.sh`
  - `ruff check .`
  - `pytest`
- Suggested file map starters:
  - `candidate:backend/app/api/jobs.py`
  - `candidate:workers/sync_runner.py`
  - `docs/ref/PRD.md`
  - `docs/status/PROJECT-STATUS.md`
- Suggested architecture notes:
  - `backend/`는 API surface와 admin/internal contract를 담당한다
  - `workers/`는 long-running workflow와 batch boundary를 담당한다
  - `src/`는 shared domain과 helper를 담당한다
  - external systems는 queue, db, upstream API를 명시한다
- Suggested next actions:
  - `PROJECT-PLAN.md`에 first worker와 API path를 적는다
  - `ARCHITECTURE.md`에 queue/db/upstream boundary를 적는다
  - `PROJECT-STATUS.md`에 `ruff check .`, `pytest`를 추가한다

## Unity / Robot / C#

- Use when:
  - runtime state
  - scene/prefab
  - 하드웨어/IPC 계약이 중요한 프로젝트일 때
- Suggested boundaries:
  - `Assets/Scripts`
  - `Assets/Scenes`
  - `docs/status`
- Naming contract starters:
  - route: `robot.control.movej`
  - table/schema: `latest_state_snapshot`
  - env: `ROBOT_ENDPOINT`
  - env: `UNITY_ENV`
- Suggested skills:
  - `project-planning`
  - `socratic-review`
  - `big-task`
  - `doc-sync`
- Suggested verify:
  - `bash scripts/check-project.sh`
  - `play mode smoke`
  - `ipc preflight`
  - `readback verification`
- Suggested file map starters:
  - `candidate:Assets/Scripts/Runtime/RobotControl.cs`
  - `candidate:Assets/Scenes/Main.unity`
  - `docs/ref/PRD.md`
  - `docs/status/PROJECT-STATUS.md`
- Suggested architecture notes:
  - runtime truth source를 먼저 명시한다
  - scene, prefab, runtime controller 경계를 분리한다
  - external systems는 robot, ipc, calibration config를 명시한다
- Suggested next actions:
  - `PROJECT-PLAN.md`에 first runtime component와 event 이름을 적는다
  - `ARCHITECTURE.md`에 truth source와 scene/runtime boundary를 적는다
  - `PROJECT-STATUS.md`에 play mode/ipc/readback 검증을 추가한다

## URHYNIX — 디지털트윈경비로봇 (확정)

> 위 starter profile 중 `Unity / Robot / C#`을 베이스로 하되, 본 프로젝트의 실제 스택을 잠근다.
> 2026-05-27 디지털트윈경비로봇으로 전환되면서 확정.

- Use when:
  - URHYNIX 프로젝트 작업 (디지털트윈경비로봇)
- Boundaries (실제):
  - `ros2_ws/src/urhynix_*` (ROS2 패키지)
  - `unity-src/Assets/Scripts` (Unity 클라이언트)
  - `arduino/` (MCU 펌웨어 + 시리얼 브릿지, TurtleBot 연결 방식은 S1에서 확정)
  - `db/migrations` (Supabase/Postgres SQL)
  - `docs/ref` + `docs/status` (SSOT)
- Naming contract (실제):
  - topic ns: `/tb3_1/*`, `/tb3_2/*`, `/security/event`, `/security/dispatch`, `/security/camera_confirm`
  - table: current `events`, `dispatches`, `camera_captures`, `session_meta`; planned `pose_logs`, `media_artifacts`, `protected_assets`
  - env: `ROS_DOMAIN_ID`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `TB3_MODEL`
- Skills (이 프로젝트에서 자주 쓰는):
  - `project-planning`
  - `socratic-review`
  - `change-impact-map`
  - `doc-sync`
  - `api-contract-guard`
- Verify:
  - `bash scripts/check-project.sh`
  - `colcon build --symlink-install --packages-select urhynix_msgs urhynix_bringup` (ROS2 워크스페이스 빌드 시)
  - **RPi 4 메모리 제약**: `--parallel-workers 1 --executor sequential` 강제 (병렬 빌드는 4GB RAM + SD swap thrash로 SSH 응답 멈춤). 시간: 8 패키지 6-10분. `nohup ... &; disown`으로 SSH 끊겨도 빌드 살아남음. (2026-05-29 검증)
  - **`~/turtlebot3_ws/build` 절대 삭제 금지** — install/setup.bash hook이 build 일부 파일 참조. 디스크 정리 시 build/ 보호. (2026-05-29 학습)
  - Unity Play Mode smoke (듀얼 로봇 pose 갱신 + 이벤트 마커 확인)
  - `python3 -c "import html.parser as h; h.HTMLParser().feed(open('docs/dev-plan.html').read())"`
- File map starters:
  - `candidate:ros2_ws/src/urhynix_bringup/launch/multi_tb3.launch.py`
  - `candidate:ros2_ws/src/urhynix_sensor_bridge/urhynix_sensor_bridge/bridge.py`
  - `candidate:unity-src/Assets/Scripts/Network/PoseSubscriber.cs`
  - `candidate:unity-src/Assets/Scripts/UI/Events/EventMarker.cs`
  - `candidate:arduino/mcu_tb3_1/mcu_tb3_1.ino`
  - `docs/ref/PRD.md`
  - `docs/status/PROJECT-STATUS.md`
- Architecture notes:
  - 진실값은 ROS2 (tb3_1/tb3_2 Nav2). Unity는 시각화·관제.
  - 모든 이벤트 메시지는 `robot_id` 포함.
  - 박물관/미술관 액자형 중요물품은 SCRUM-23에서 `protected_assets` + camera/AI label로 관리 예정.
  - 사진/영상/사운드는 Storage에 저장하고 DB에는 `media_artifacts.storage_path`만 두는 확장안으로 둔다.
  - 화재 이벤트는 모의 입력. 실제 불꽃 테스트 금지.
- Next actions:
  - `JIRA-MAP.md` 매핑 따라 SCRUM-8~25 일괄 갱신
  - `docs/dev-plan.html` 발행 후 팀 공유
  - Sprint 1 킥오프
