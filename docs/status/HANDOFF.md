<!-- opencode: 2026-07-01 - 2.5D 우클릭 메뉴 + 로봇 마커 추가, 합성이벤트 검증 PASS. -->
# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-07-09 (**🚇 티원 36cm 협소회랑 왕복순찰 완성 — 근본원인 5연타 해체 + 복귀주차·사전회전·JSONL 주행기록** — 어제 activate FAIL은 만충(12.48V)에서 8/8 OK로 **저전압 확정**. 협소통과 처방: inflation **0.15**(병목 실측 좌36/우44cm, 회랑 반폭 18cm보다 얇게)·PolygonStop **0.12**·Smac travel **1.0** + 젠지 `_robot_nav_up.sh`에 스톡 inflation 0.5→0.15 패치 신설(다음 기동 자동). 실주행에서 근본원인 5연타 순차 해체: ①Smac 10Hz 재플랜 Pi 포화→`expected_planner_frequency` 1.0 ②크롤이 진행률 10s 초과→20s ③theta=0 도착회전 벽옆 스톨→`yaw_goal_tolerance` 6.28 ④bt ack 20ms→200ms ⑤회항 166s=등지고 출발 셔플→bridge **레그별 사전회전**(166→5s, 증거: B-회랑 정136s vs 역29s). bridge: 왕복(1→6→역순→1)+**복귀주차**(goToPose+Spin 정렬, DOCK 상수)+레그별 goToPose+워치독 240s/레그+**JSONL `~/patrol_runs.jsonl`**(배포됨, 다음 부팅부터). 왕복 풀시퀀스 3판 연속 성공(최종 11/11+주차3s+정렬2s=454s). 물리 재배치 루프 `_dock_reseed.sh` 한 줄+스킬 트리거("충전소 물리 이동") 등록. 티원 셧다운. **다음 세션 첫 행동**: ①티원 bringup→`bash ~/_dock_reseed.sh`→`_restart_nav_ns.sh`+8노드 lifecycle→순찰→`~/patrol_runs.jsonl`로 레그 시간 자동 판정 ②크롤 복불복(같은 레그 6s↔130s, PolygonSlow ±0.18 경계) — `slowdown_ratio` 0.2→0.35 실험 ③젠지 프리셋 P2 실주행 ④백로그: 무한 순회(number_of_loops 예약), 유령 마커 차단, 발행자 per-robot 라우팅. 자세히: DECISION-LOG 2026-07-09 최상단). **이전(2026-07-08 밤)**: (**🤝 젠지 좌표주행 PASS(0.8m/4.1cm) + 맵-현실 정합 98.5% + 순찰 프리셋 5종/Unity 드롭다운** — 젠지(비-ns)를 `nav_up.sh`(arena_shared·현IP 갱신판)로 기동해 실주행 성공, bridge 존 토글·90s 타임아웃 첫 실전 검증, bridge `--nav-ns ''`로 양 로봇 겸용화. AMCL 함정 3종(반올림 쿼터니언 "malformed" 조용한 거부 — 수락 판정은 "Setting pose" 로그 / latched 옛값 / **옆에 주차된 로봇 블롭이 회전수렴 발산** → 위치 사용자확정+방향 물리정렬+타이트 시딩) 스킬화. 신규 `scripts/scan_vs_map_check.py`(--fit)로 **맵=현실 98.5% 입증**(장애물 2개 실존, costmap cost 100 인식, 우측 실물 ~8cm 삐짐만) — fit 보정값 재시딩 패턴 확립. 신규 `scripts/patrol_presets.py` → 클리어런스 0.25m 검증 프리셋 5종 + **MapPanelView 드롭다운**(적용/"내 경로 복원", 백업 arena_shared.user-backup.json) 컴파일 PASS. 유령 티원 마커 = MapMarkerLayer 전역 tf 폴백(리셋된 선택로봇에 얹힘) — 코드 차단 TODO. 신규 스킬 `urhynix-genji-nav2-drive`. 양 로봇 안전 셧다운(젠지 독 시딩 0.10,1.11,0.293 완료 상태). **다음 세션 첫 행동**: ①티원 완전충전 트랙(아래 저녁 캡슐 절차 그대로 — activate 재시도부터) ②젠지 트랙: 프리셋 드롭다운 육안 + P2(중앙 크로스) 실주행 완주 ③백로그: 유령 마커 폴백 차단, Unity 발행자 per-robot 라우팅, Unity 클릭 스냅. 자세히: DECISION-LOG 2026-07-08 최상단). **이전(2026-07-08 저녁)**: (**🧭 주행 개선 4종 처방 배포 — nav2 activate 검증만 배터리로 이월** — "회피 못하고 멈춤" 웹조사로 병인 특정: ①유령 장애물(`inf_is_valid: true`로 raytrace clearing 복구) ②NavFn→**Smac 2D** 교체 ③독 출발 = PolygonStop `enabled` 동적 토글(bridge에 이식, 0.3m 이동/30s 폴백 복원) ④bridge 레그당 90s 타임아웃+cancel. 미세조정: 속도 0.12·도착 tol 0.15. ⚠️지뢰 해체: patch 스크립트가 keepout 재주입하던 것 `--keepout` 게이트(기본 OFF), source_timeout 1.0 영속화 — **로봇 yaml 직접 수정은 재생성 때 증발, 수정은 반드시 patch 스크립트에**. params는 로봇 배포+재생성+grep 검증 완료했으나 **nav2 재기동 후 controller/planner activate FAIL — 배터리 불량과 겹쳐 원인 미확정(저전압 의심), 안전 셧다운**. bridge 신버전은 로컬만(py_compile OK, 미배포). **다음 세션 첫 행동**: 완전 충전 → bringup+AMCL 독 시딩(0.038,1.405,0.293) → `_restart_nav_ns.sh`+8노드 lifecycle → activate 재시도(성공=저전압 확정 / 실패=`/tmp/nav_tb3_1.log`의 Smac configure 에러 확인) → `scp patrol_waypoints_bridge.py t1:~/ && systemctl --user restart urhynix-bridge` → 수동 `ros2 param set .../PolygonStop.enabled false` 동적 지원 실측 → 검증 3종: C1 UI 4점 순찰 완주(벽스침 0·"경로 없음" 0) / C2 사람이 경로 5~10초 막았다 비킴→≤10s 자동 재개 / C3 완주 후 enabled=true 복원. 플랜: `~/.claude/plans/logical-crafting-pearl.md`, 자세히: DECISION-LOG 2026-07-08 최상단). **이전(2026-07-08 오후)**: (**🤖 티원 Unity좌표 주행 첫 성공(1.5m 실주행) — "안 움직임" 3중 결합 전부 규명, 배터리로 완주만 이월** — goal은 수락되는데 정지하는 증상의 원인이 ①keepout 마스크 서버 부재(costmap 미완성, "KeepoutFilter mask not received") ②collision_monitor scan source_timeout 0.2가 Pi 부하지연에 상시 걸림→1.0 ③독/구석 정차로 PolygonStop 상시 발동(출발 전 8방위 직접 cmd_vel 탈출로 해결)의 **겹침**이었음 — 층별 진단 트리를 신규 스킬 `urhynix-t1-drive-nomove-diag`로 박제. 튜닝 확정: inflation 0.20·PolygonStop 0.14·탈출각 60°(patch_nav_params_ns.py 반영). **로봇 상주 4서비스**(systemd user+linger): endpoint/scanfix/posepub/bridge — 재부팅 후 동반 프로세스 실종 클래스 종결, UI "순찰 시작"이 이제 저 없이 동작하는 구조. Unity 발행 유실 진범 = `ros_endpoint.json` endpointRobotId가 꺼진 젠지 → **tb3_1로 전환(Play 재시작해야 반영)**. **다음 세션 첫 행동**: 완전 충전 → 티원 전원 → bringup+AMCL 시딩([[urhynix-t1-amcl-saved-map]], 상주 서비스는 자동) → Unity Play 재시작 → 순찰 편집으로 좌표 → "순찰 시작" 완주 확인. 이후 백로그: 주행엔진 처방 6종+bridge P0 4종 이식(상세 설계 07-08 대화), Unity 발행자 per-robot 라우팅, 박물관 2.5D 육안 체크리스트(장식/데모 화재 버튼→셔터/시점 리셋/슬롯 전환). 자세히: DECISION-LOG 2026-07-08 최상단). **이전(2026-07-08 오전)**: 🏛️ 2.5D 박물관 디오라마 완성 + dogfood 감사 P1~7 수정 — 컴파일 PASS, 육안 검증만 남음 — Gallery Room 팩 마젠타는 URP 변환으로 해결(`GalleryRoomUrpUpgrade.cs` 재사용 가능), 장식은 전부 `StreamingAssets/Maps/arena_shared.decor.json` 데이터 주도: 검정 그리드 바닥·벽 직선화(표시 전용, 로봇 pgm 불변)·액자+벽당 트랙레일 조명·니케상/스핑크스(scale=실높이m)·충전독 연한 티원색 패치·**차폐벽(wall_13, 평소 열림→화재 출동 시 하강→10초 자동 개방)**·TB3 burger 실모델 마커. dogfood 감사(신규 스킬 `urhynix-dogfood-audit`)로 잡은 Blocker 2건 수정 완료: 데모 "화재" 버튼이 이제 모의 출동까지 발화(셔터+로봇 연쇄), 맵 슬롯 전환 시 2.5D 재빌드. +오프라인 출동 게이트, 시점 리셋 버튼+각도 영속, barrier 로그. **다음 Unity 세션 첫 행동**: Play → 2.5D 탭 → 육안 체크리스트(장식 전경/데모 화재 버튼→셔터 하강/시점 리셋/슬롯 전환/스케일은 decor.json 노브). ⚠️ unityctl 컴파일은 사용자 Play 중이면 stale — `play stop` 후 `exec 'UnityEditor.AssetDatabase.Refresh()'` 표준. 자세히: `docs/status/DECISION-LOG.md` 2026-07-08 최상단).---

## ⚡ Top 1 Action (가장 최신)

**티원 기동(bringup→`_dock_reseed.sh`→8노드 lifecycle) → 순찰 → `~/patrol_runs.jsonl` 레그 판정 → 크롤 복불복 실험(slowdown_ratio 0.35)**

- **배경**: 07-03부터 이어진 저전압 가설은 07-09 만충 activate 8/8로 **확정 종결**. 왕복+복귀주차+방향정렬 풀시퀀스는 3판 연속 성공 — 남은 건 속도 품질(같은 레그가 판마다 6s↔130s인 크롤 복불복)과 이번에 배포한 JSONL 주행기록의 첫 데이터 수집·자동 판정.
- **할 일(순서대로)**:
  1. **완전 충전 후 시작** — 저전압 상태에서의 재시도는 진단에 노이즈만 더함(우선순위 최상단).
  2. bringup 후 `/tb3_1/odom` 발행자 수 확인 + `/tmp/nsbu_tb3_1.log`에서 `stack smashing`/`no status packet` **재발 여부 확인** — 완전충전 후에도 재발하면 그때 비로소 OpenCR 물리연결(케이블/보드) 점검으로 넘어갈 것(저전압 가설이 틀렸다는 뜻이므로).
  3. AMCL 재시딩(`x=0.038,y=1.405,yaw=0.293` — arena_shared 기준) → `/tb3_1/amcl_pose` sane 확인.
  4. nav2 8노드 재기동 + `ros2 param get /tb3_1/collision_monitor PolygonStop.radius`로 **0.18m** 로드 확인(0.30 아님), `polygons`에 `PolygonLimit` 포함 확인.
  5. 4점 순찰 재트리거 → 이번엔 **#3~#4까지 완주** 확인(1~2는 이미 클린 통과 확인됨).
  6. 완주 PASS면 **일부러 장애물(사람/젠지)을 경로에 놓고** 재주행 — 안전마진이 실제 장애물에도 통하는지 의도적 테스트(아직 미검증).
  7. 그 다음 7웨이포인트 전체 재계산(`patrol_multi_waypoint.py`) → 완주 검증 → ssot-trio-update.
- **관련 파일**: `scripts/{patch_nav_params_ns.py,patrol_waypoints_bridge.py,patrol_multi_waypoint.py,patrol_safe_clearance.py}`, `.claude/skills/urhynix-t1-nav2-patrol-drive/SKILL.md`(함정#12).
- **병행 이월(여전히 유효)**: 2.5D 우클릭/로봇마커 육안 확인. 젠지 pose 마커 표시(subscribe-only 가능 확인했으나 AMCL 초기포즈 미시딩이라 아직 `/tb3_2/pose` 없음).

---

## 🔍 고비용 모델 리뷰 체크리스트

### 1. 아키텍처/계약 검토
| # | 항목 | 파일 | 질문 |
|---|---|---|---|
| 1.1 | `FakeSensorData` 자동 on/off | `Simulation/FakeSensorData.cs` | `RobotConnectivityMonitor.IsOnline()`을 `Update()`에서 폴링하는 방식이 실제 연결/끊김에 충분히 빠른가? timeout 3초 이내에 fake가 덮어쓰지 않는가? |
| 1.2 | `DemoScenarioService` 모드 분리 | `Simulation/DemoScenarioService.cs` | `demoMode=false`일 때 버튼 비활성화만으로 실제 운영 시 오동작을 막을 수 있는가? 실제 ROS 보안 이벤트 subscriber와 중복 발화 우려는 없는가? |
| 1.3 | `RaiseDispatchRequested` 시그니처 변경 | `App/ControlRoomEvents.cs` | `simulated` bool을 5번째 인자로 추가한 설계가 향후 실제 출동/모의 출동을 명확히 구분하는가? 호출자 6곳이 모두 올바르게 갱신됐는가? |
| 1.4 | `SupabaseDbService` pose robot_id | `Database/SupabaseDbService.cs` | `RobotPoseFeed.OnRobotPose` per-robot 이벤트를 소비해 `pose_logs.robot_id`를 동적으로 쓰는 흐름이 멀티로봇 시나리오에서 정확한가? `RobotPoseSubscriber`(`/tf`)와 중복 쓰기 가능성은 없는가? |
| 1.5 | Simulation 서비스 생명주기 | `App/ControlRoomApp.cs` | `CreateSimulationServices()`에서 `FindObjectOfType` 후 중복 생성 방지. 씬에 이미 `FakeSensorData`/`DemoScenarioService`가 있는 경우와 충돌하지 않는가? |

### 2. 코드 품질/안전성 검토
| # | 항목 | 파일 | 질문 |
|---|---|---|---|
| 2.1 | null/empty 방어 | `Simulation/DemoScenarioService.cs`, `UI/ScenarioPanelView.cs` | `SituationConfig` 로드 실패 시 동작이 graceful한가? |
| 2.2 | 딕셔너리 누수 | `Database/SupabaseDbService.cs` | `poseStates` 딕셔너리가 로봇 추가/제거 시 계속 커지지 않는가? 현재 로봇 2대라 문제 없지만, 장기 운영 시 클리어 지점이 필요한가? |
| 2.3 | 이벤트 누수 | `Database/SupabaseDbService.cs` | `RobotPoseFeed.OnRobotPose` 구독/해제가 `OnDestroy`에서 정확히 처리됐는가? |
| 2.4 | UI Toolkit 동적 생성 | `UI/ScenarioPanelView.cs` | `Button` 인스턴스의 `clicked` 이벤트에 람다가 캡처한 `s.situationId`가 의도한 값을 갖는가? 동일한 JSON 항목에 대한 클로저 문제는 없는가? |
| 2.5 | JSON 직렬화 | `Resources/SituationConfig/default_situations.json` | `noise` 항목의 `sensorTrigger="sound"`가 실제 센서 ID(`SensorInfo.sensorId`)와 일치하는가? 대소문자/오타 확인 필요. |

### 3. 실제 로봇 연동 준비도 검토 (고비용 모델이 채울 부분)
| # | 항목 | 현재 상태 | 필요한 결정/작업 |
|---|---|---|---|
| 3.1 | FakeSensorData 완전 제거 | ROS 연결 시 skip | 실제 시연 시 `FakeSensorData` 컴포넌트를 아예 비활성화할 것인가, 아니면 미연결 fallback으로 유지할 것인가? |
| 3.2 | DemoScenarioService 실제 모드 | `demoMode=false`일 때 버튼 비활성화 | 실제 보안 이벤트(화재/침입/소음/도난)가 ROS topic으로 들어오면 어떤 subscriber가 `ControlRoomEvents.RaiseScenarioTriggered` 또는 `RaiseAlert`를 발화할 것인가? |
| 3.3 | 출동 명령 실제 발행 | `DispatchPublisher`가 `/goal_pose` 발행 중 | `simulated=false` 출동에 대해 Nav2 `goToPose`가 실제로 실행되는지, `patrol_waypoints_bridge.py`와의 계약이 맞는지 확인 필요. |
| 3.4 | DB 실제 쓰기 검증 | `SupabaseDbService` 큐잉 구현됨 | 실제 Supabase 설정 하에서 `dispatches`/`pose_logs`/`logs` insert가 정상 동작하는지, RLS 정책이 anon key에 맞춰져 있는지 확인 필요. |
| 3.5 | Sensor topic 교차검증 | `default_sensors.json` topic `/sensors/*` | 실제 `arduino_bridge_quad`의 발행 토픽명과 일치하는지, `pir`/`sound`/`temp`/`laser` 네이밍이 맞는지 확인 필요. |

### 4. 문서/SSOT 동기화 검토
| # | 항목 | 파일 | 질문 |
|---|---|---|---|
| 4.1 | ROADMAP 상태 | `docs/ref/UNITY-MOCK-TO-REAL-ROADMAP.md` | A1/A2/A7/A9가 ✅로 표시됐는가? Phase 3/4 체크리스트가 현재 상태와 일치하는가? |
| 4.2 | Evidence Status | `docs/status/PROJECT-STATUS.md` | bridge 에러와 본 `Assets/Scripts` 컴파일 상태가 분리되어 기록됐는가? |
| 4.3 | HANDOFF | `docs/status/HANDOFF.md` | 다음 세션 진입점과 고비용 모델 리뷰 항목이 명확한가? |

---

## 📋 First 5 Min Checklist

```bash
# 1. Unity 컴파일 확인 (에디터 이미 떠있으면 생략)
unityctl script get-errors --project /Users/family/jason/URHYNIX/unity/ControlRoom --json
# → 0 error(s) 확인

# 2. arena_shared 2.5D 탭 회귀 확인(육안, 성역) — 벽 27개(외곽+칸막이+돌출) 정상 렌더되는지
# Unity Play → 맵패널 2.5D 탭 → 드래그 회전 + 휠 줌 동작 확인

# 3. 우클릭 설계 착수 전 기존 2D 패턴 읽기
#    unity/ControlRoom/Assets/Scripts/Map/MapContextMenuView.cs
#    unity/ControlRoom/Assets/Scripts/Map/MapInteractionController.cs
#    unity/ControlRoom/Assets/Scripts/Map/Actions/ (DispatchHereAction.cs 등)

# 4. (선택) 어제 bag→rtabmap PLY 스레드 살아있는지 확인 — 별개 작업, 필요시만
ssh rtabmap@orb "echo OK && ls -la ~/bags/mapping_20260630_1658/ 2>&1"
```

---

## 🔧 If Stuck (빠른 복구)

| 증상 | 명령 |
|------|------|
| `unityctl exec` project lock | Unity Editor 완전 종료 후 재시작, 또는 `unityctl session clean` 후 재시도 |
| bridge 로드 안 됨 | `unityctl init --project /Users/family/jason/URHYNIX/unity/ControlRoom` 후 Editor 재기동 |
| `SensorVerifyConsole.Dump()` 라벨 4개 안 보임 | `tb3_2` 선택 후 센서 탭 활성화 확인; `default_sensors.json`에 `robotId: tb3_2` 센서 4개 있는지 확인 |
| 동적 UI 미생성 | `RightStatusPanel.uxml`, `LeftControlPanel.uxml`에서 고정 행/버튼 제거 여부 확인 |
| bridge compile error 6건 | `Packages/com.unityctl.bridge/Editor/Commands/DescribeTypeHandler.cs` 확인. 본 작업과 무관하면 패키지 다운그레이드 또는 고비용 모델 판단 |
| `unityctl check`/`get-errors`가 옛 결과 그대로(stale) | 백그라운드 컴파일은 신뢰 불가 | `EditorUtility.RequestScriptReload()`로 강제 리로드 → `transport: batch`로 잠깐 폴백됐다 `ipc`로 돌아올 때까지 대기(수십초, 짧은 간격 재시도 금지 — project lock 악화) |
| 3D 오브젝트가 핑크로 렌더 | URP RenderPipelineAsset이 ProjectSettings에서 끊어진 참조일 수 있음(`grep customRenderPipeline ProjectSettings/QualitySettings.asset`으로 GUID가 실제 asset과 매칭되는지 확인) | `Assets/Settings/ControlRoom_URP.asset`(2026-07-01 생성)로 이미 수정됨 — 재발 시 같은 GUID로 재확인 |
| Unity kill -TERM 반복 후 씬이 이상함 | 강제종료 반복 시 auto-recovery가 stale 백업을 잘못 복원할 수 있음(2026-07-01 실제 발생, `ControlRoomMain.unity` 컴포넌트 소실) | `git status`로 씬 diff 확인 → 있으면 `git checkout -- <scene>` + `unityctl scene open --project <P> --path <scene> --force`로 디스크에서 재로드 |

---

## 📚 More Info (상세 내용)

| 문서 | 용도 |
|------|------|
| **`docs/ref/UNITY-MOCK-TO-REAL-ROADMAP.md`** | Phase 2/3 완료 항목 + Phase 4 체크리스트 |
| **`docs/status/PROJECT-STATUS.md`** | Evidence Status + Handoff Capsule |
| **`docs/status/DECISION-LOG.md`** | 외부 도구 판정 + 목업 교체 결정 이력 |
| **`docs/status/HANDOFF-FULL.md`** | 이전 모든 세션 기록 |
| **`../ref/TECH-INDEX.md`** | 작업별 빠른 문서 라우팅 |

---

## ✅ 한줄정리

**2026-06-30: Unity ControlRoom Phase 3 준비 완료(FakeSensorData ROS 연결 감지 off, DemoScenarioService SSOT 정합, SupabaseDbService simulated/robot_id 동적화). 실제 로봇/ROS 연동은 고비용 모델 리뷰 후 진행. `Assets/Scripts`는 컴파일 OK, `unityctl bridge` 패키지에서 6 compile error 발생 중. 다음 세션: 고비용 모델 리뷰 → Editor 재기동 → SensorVerifyConsole 런타임 검증.**
