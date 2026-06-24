# Skills Index

이 디렉토리는 새 프로젝트에 이식 가능한 범용 실행형 스킬 세트다.

## Start Here

1. 현재 작업의 성격을 먼저 분류한다.
2. 아래 표에서 가장 가까운 스킬 1~2개를 고른다.
3. 기술이 명확하면 `docs/ref/TECH-INDEX.md`에서 기술 ref 1개를 고른다.
4. 스킬을 읽고 실제 파일/명령/산출물에 맞게 적용한다.
5. 긴 스킬은 `references/`가 있으면 본문 다음에 필요한 참고만 읽는다.

## Technology Ref Routing

| Work type | Fast ref | Typical skills |
|---|---|---|
| Unity ControlRoom / UI / ROS-TCP panel | `docs/ref/tech/UNITY.md` | `unity-camera-panel`, `unity-live-map-twin`, `unity-unityctl-ops`, `doc-sync`, `evidence-review` |
| ROS2 / TurtleBot / SLAM / Nav2 | `docs/ref/tech/ROS2-ROBOT.md` | `slam-nav2-arena-survey`, `map-quality-eval`, `ip-drift-resync`, `urhynix-fullstack-bringup` |
| Arduino / PIR / LDR / sensor serial | `docs/ref/tech/ARDUINO-SENSORS.md` | `arduino-flash`, `api-contract-guard`, `doc-sync` |
| Supabase / schema / DB writer | `docs/ref/tech/DATABASE-SUPABASE.md` | `api-contract-guard`, `doc-sync`, `evidence-review` |
| Pi Camera / RealSense / compressed image / YOLO | `docs/ref/tech/VISION-CAMERA.md` | `robot-camera-bringup`, `unity-camera-panel` |
| T1 RealSense 맞춤 YOLO 캡처/라벨/학습 | `docs/evidence/2026-06-10-mac-yolo-realsense-live.md` | `urhynix-yolo-capture-train`, `robot-camera-stream-diag` |
| Claude/Codex skill harness / intake / evidence | `docs/ref/tech/OPS-HARNESS.md` | `task-intake-router`, `doc-sync`, `evidence-review` |

## Core Skills

| Skill | Use When | Output |
|---|---|---|
| `doc-framework` | 프로젝트에 문서 체계를 심거나 정리할 때 | SSOT 구조, 문서 계층, change class 규칙 |
| `doc-sync` | 코드 변경 후 어떤 문서를 같이 고쳐야 할지 헷갈릴 때 | 문서 누락 판정, companion check |
| `doc-health-audit` | "문서 건강성 체크" — 진입 문서 인덱싱성/토큰부담/폴더 정리 상태를 진단하고 선택적 편집까지 닫을 때 | 3기준 등급표 + 🔴🟡🟢 + 소넷 편집(HANDOFF 캡슐화·DECISION 분리·archive) + 검증 |
| `project-bootstrap` | 새 프로젝트 시작 시 | 최소 골격, 초기 문서, 첫 검증 |
| `session-retro` | 세션 종료 시 | 성공/실패 패턴 기록, 승격 후보 |
| `big-task` | 작업 규모가 크고 단계를 쪼개야 할 때 | 단계 계획, 검증 루프, 문서 동기화 |

## Design / Planning Skills

| Skill | Use When | Output |
|---|---|---|
| `project-planning` | 새 프로젝트나 큰 기능 착수 전에 실행 계약형 계획을 잠글 때 | file map, skill routing, phase contract, verify/doc-sync/exit criteria |
| `task-intake-router` | 새 요청을 먼저 분류해야 할 때 | intake verdict, chosen skill, next skill, sub-agent 여부 |
| `profile-recommendation` | stack이 모호해서 starter profile 추천이 필요할 때 | recommended profile, confidence, alternative |
| `design-to-code` | 화면 설계나 리디자인 시작 시 | 화면 목록, route map, design decisions |
| `socratic-review` | 큰 설계 전 검증이 필요할 때 | 질문 기반 설계 리뷰, decision log |

## Safety / Verification Skills

| Skill | Use When | Output |
|---|---|---|
| `api-contract-guard` | 외부 API/스키마/모델명을 코드에 박으려 할 때 | 런타임 확인, 중앙화, 검증 기록 |
| `change-impact-map` | route/schema/env/worker/UI 변경 영향 범위를 먼저 그려야 할 때 | impact map, companion docs, verify matrix |
| `evidence-review` | 완료 선언 전에 근거를 점검할 때 | executed verify, changed docs, release verdict |
| `stack-drift-guard` | 현재 프로젝트가 원래 stack profile에서 벗어났는지 볼 때 | drift verdict, re-profile recommendation |
| `migration-manifest` | 마이그레이션/대규모 리팩터링 시 | parity ID, wave plan, progress tracking |
| `parallel-qa` | E2E 회귀를 빨리 넓게 돌리고 싶을 때 | grouped QA scenarios, pass/fail report |
| `code-review-graph-ops` | docs-heavy / cross-cutting repo에서 영향 범위를 좁혀야 할 때 | graph-first impact analysis |
| `ssot-trio-update` | 작업 1건 PASS/FAIL 직후 `docs/status/` 3종(DECISION-LOG + PROJECT-STATUS + HANDOFF)을 1회 갱신할 때. HTML/Jira 손 안 댐. | DECISION-LOG 최상단 entry + PROJECT-STATUS Last updated + HANDOFF 캡슐 chain |
| `ssot-board-sync` | SSOT(docs/ref/*, docs/status/*) 변경을 dev-plan HTML 7페이지 + 단일 번들에 동기화할 때 | 매핑 표 기반 양쪽 갱신 + 번들 재빌드 + 검증 grep |
| `decision-broadcast` | 한 건의 결정을 DECISION-LOG → SSOT → HTML → Jira → Slack 5채널에 한 번에 동기화할 때 | 5채널 매핑 + Slack 템플릿 + Jira 갱신 절차 (ssot-board-sync 위임) |

## Agent Orchestration Skills

| Skill | Use When | Output |
|---|---|---|
| `session-handoff` | 세션 종료 또는 pause 직전 | next entrypoint, blocker, first verify |
| `failure-mode-playbooks` | 공통 실패 모드에서 안전한 복구 흐름이 필요할 때 | recovery steps, docs to update, verify to re-run |

## Embedded / Hardware Skills

| Skill | Use When | Output |
|---|---|---|
| `arduino-flash` | Arduino 스케치를 GUI IDE 없이 컴파일·업로드·시리얼 검증까지 한 번에 돌릴 때 (URHYNIX 센서 4종 반복 플래시) | 표준 핀 매핑, one-liner 명령, 비대화형 시리얼 캡처 우회 |
| `slam-nav2-arena-survey` | TurtleBot3 + LDS-03으로 새 경기장/실내 공간에 처음 진입해 SLAM 매핑 + Nav2 베이스라인 + Unity 임포트 한 흐름이 필요할 때 | 6 Phase (연결→매핑→저장→평가→Unity→Nav2), Robot/Mac/Ubuntu 결정 트리, ROS 모드 통일 표, 트러블슈팅 매트릭스, 좌표축 변환 표 (2026-05-29 책상 매핑 통과 검증) |
| `map-quality-eval` | `tb3-slam-save → tb3-fetch-map` 직후 매핑 quality를 정량 평가하고 다음 액션(재매핑/Nav2 진입)을 정해야 할 때 | 픽셀 통계(occupied/free/unknown), use case go/no-go, 표준 `eval.md` 자동 생성 + 백업 (2026-05-29 arena_v1 dry-run 검증) |
| `ip-drift-resync` | DHCP로 robot IP가 변경됐고 Unity Scene/Script/known_hosts를 일괄 동기화해야 할 때 (매 세션 첫 5분) | Unity Editor 종료 → sed patch → known_hosts purge 자동화. Unity 자동 save back 함정 회피 (2026-05-29 발견) |
| `robot-camera-bringup` | 매 세션 첫 5분 — 두 로봇 카메라 트랙(camera_ros Pi Camera + realsense2_camera D435 + ros_tcp_endpoint)을 한 번에 살릴 때 | LD_LIBRARY_PATH 우회 + ssh ControlMaster=no + nohup/disown + 토픽 hz 30Hz 검증 한 줄. 함정 8건 매트릭스 (ABI 충돌/sudo stdin/연결 끊김/launch 파일 이름 등). 2026-06-02 젠지 30.095Hz 검증 통과 |
| `unity-camera-panel` | Unity 관제 UI에 ROS2 카메라 라이브 RGB 패널을 코드 손 안 대고 추가할 때. 새 카메라 추가 시 AddCameraPanel 한 줄로 확장 | `CameraStreamPanel.cs` 컴포넌트(topic Inspector 입력) + `CameraPanelSetup.cs` Editor script(batch mode) + Unity batch CLI 한 줄. 함정 7건 매트릭스. 2026-06-02 GenjiCameraPanel + T1CameraPanel 자동 추가 통과 |
| `unity-ui-interaction-audit` | UI Toolkit View 레이어 완료 후 UI Contract Lock 잠그기 전 모든 버튼/토글의 핸들러+이벤트+구독자+시각 피드백 정합성 검증 | Phase A Opus 정적 매트릭스 (25개 요소, 결함 6분류) + Phase B unityctl 동적 한계 5종 우회 표. 함정 7건 (script validate 가짜 PASS / exec 사용자 어셈블리 unreachable / Button.clicked event invoke 불가 등). 2026-06-04 URHYNIX Phase 2.5 검증 통과 |
| `unity-live-map-twin` | ControlRoom 맵뷰에 라이브 SLAM `/map`을 카메라 없이 그리거나, /tf 로봇 마커·우클릭 SSOT 출동·맵 회전 보정을 추가할 때 | map-frame 비율맞춤(여백 제거) + 좌표 SSOT(`MapCoordinateSystem`) + /tf 합성 마커 + 우클릭 컨텍스트 메뉴(`IMapAction`+SSOT) + `/goal_pose` 발행 + 회전 영속(PlayerPrefs+json). 컴포넌트화 Map/ 레이어. 2026-06-16 젠지 검증(회전 85° CW) |
| `unity-unityctl-ops` | unityctl로 코드 수정 검증/Play 할 때, check가 stale하거나 IPC "not ready"/스크린샷 검정/에디터 교착일 때 | 안전 절차(play stop→refresh→isCompiling 폴링→check) + 함정표(Play 중 재컴파일 차단, --json 우회, UI Toolkit 스크린샷 검정, 로봇-오프 ROS 스팸 교착). 2026-06-16 반복 학습 |
| `urhynix-fullstack-bringup` | 디지털트윈 dry-run — 배터리·카메라·맵·LDR·PIR 5트랙을 한 로봇에 동시에 띄워 Unity에 다 표시할 때, 또는 "개별은 되는데 다 같이" 안 될 때 | SLAM 공존 위한 non-namespaced bringup + 배터리 relay 결정, USB 2개(Arduino 2341/OpenCR 0483) usb_port·심링크, 기동 5단계, SensorVerifyConsole 검증, 함정표(usb스왑·edge-trigger·libcamera LD·ros_tcp크래시·wifi churn). 2026-06-16 젠지 5트랙 PASS |
| `urhynix-yolo-capture-train` | T1 RealSense 브라우저 UI로 맞춤 물체를 Space 촬영, ROI 연사, 마스크 bbox 보정, YOLO 학습, best.pt 탐지 검증, hard-negative 오탐 배경 정제까지 이어갈 때 | 8090 preview polling, datasets/runs 위치, ROI crop→mask→bbox→YOLO txt, rembg/SAM/GrabCut/fallback 규칙, 검수 삭제, `N 오탐 배경 저장`, 학습 후 live detect 검증 |

## Selection Rule Of Thumb

- "무슨 문서를 고쳐야 하지?" -> `doc-sync`
- "문서 건강성 체크해줘 / 진입 문서 너무 큰 것 같다 / docs 정리됐나?" -> `doc-health-audit`
- "새 프로젝트 골격부터" -> `project-bootstrap`
- "프로젝트 계획부터 촘촘히" -> `project-planning`
- "이 요청부터 먼저 분류해야 한다" -> `task-intake-router`
- "이 변경이 어디까지 번지지?" -> `change-impact-map`
- "현재 stack이 애매하다" -> `profile-recommendation`
- "이 설계 맞나?" -> `socratic-review`
- "작업이 너무 크다" -> `big-task`
- "화면부터 그려야 한다" -> `design-to-code`
- "외부 계약값을 문자열로 박을 것 같다" -> `api-contract-guard`
- "완료라고 말해도 되나?" -> `evidence-review`
- "프로젝트가 stack에서 벗어나는 것 같다" -> `stack-drift-guard`
- "세션을 넘겨야 한다" -> `session-handoff`
- "계속 꼬이는 실패 패턴을 복구해야 한다" -> `failure-mode-playbooks`
- "검증을 한 번에 넓게 돌리고 싶다" -> `parallel-qa`
- "Arduino에 스케치 굽고 시리얼 확인해야 한다" -> `arduino-flash`
- "새 경기장에서 SLAM 맵 산출 + Unity 임포트 + Nav2 베이스라인" -> `slam-nav2-arena-survey`
- "작업 끝났으니 SSOT 3종에 박고 마무리" -> `ssot-trio-update`
- "Unity 작업에 필요한 ref만 빨리 보고 싶다" -> `docs/ref/tech/UNITY.md`
- "UI 버튼/토글 다 잘 위치하고 클릭에 반응하나 검증" -> `unity-ui-interaction-audit`
- "라이브 SLAM 맵을 Unity 맵뷰에 띄우고 로봇 마커/우클릭 출동/회전 보정" -> `unity-live-map-twin`
- "배터리·카메라·맵·센서 5트랙을 한 로봇에 동시에 띄워 Unity에 다 표시" -> `urhynix-fullstack-bringup`
- "unityctl로 코드 검증하는데 컴파일이 stale/스크린샷 검정/에디터 묶임" -> `unity-unityctl-ops`
- "다른 PC가 라이다/Nav2 돌리는 중인데 위치값만 방해 없이 읽고 싶다" -> `ros2-noninvasive-pose-tap`
- "텔레옵으로 로봇 세워가며 실측 순찰 웨이포인트를 만들고 싶다" -> `urhynix-teleop-waypoint-capture`
- "저장맵에서 안전 순찰 좌표를 자동으로 뽑고 싶다" -> `map-pgm-waypoint-autogen`
- "DB 살았나/연결됐나 5초에 확인하고 싶다" -> `supabase-db-health-ping`
- "팀원 파일 없이 운영 중 도메인에서 현재 맵을 직접 떠오고 싶다" -> `live-map-pull-from-domain`

## Writing Rules

- 새 스킬은 `docs/ops/skill-authoring.md`를 따른다.
- `SKILL.md`가 길어지면 `references/`로 분리한다.
- 여러 스킬을 항상 같이 로드하는 구조는 피한다.
