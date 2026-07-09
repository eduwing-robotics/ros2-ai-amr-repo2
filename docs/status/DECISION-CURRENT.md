<!-- 2026-07-09 갱신: 07-09 1건 추가, 최고령 1건은 DECISION-LOG로만 -->
# Decision Current — 최신 결정 5건

> **진입용 최신 5건만 모음. 전체 역사는 DECISION-LOG.md 참조.**
> 
> 본 문서는 DECISION-LOG.md의 복사본으로 유지됨. 매 세션 종료 시 업데이트.

---

## 2026-07-09 — 🚇 티원 36cm 협소회랑 왕복순찰 완성 (근본원인 5연타 + 복귀주차·사전회전·JSONL)

- **저전압 확정**: 어제 activate FAIL이 만충(12.48V)에서 8/8 OK — 07-03부터의 배터리 가설 종결.
- **협소통과**: 병목 실측 좌36/우44cm → inflation **0.15**·PolygonStop **0.12**·Smac travel **1.0**. 젠지도 `_robot_nav_up.sh` 스톡 패치 신설(0.5→0.15).
- **근본원인 5연타**: ①Smac 10Hz 재플랜 Pi포화→`expected_planner_frequency` 1.0 ②크롤 진행률 10s 초과→20s ③theta=0 도착회전 벽옆 스톨→`yaw_goal_tolerance` 6.28 ④bt ack 20ms→200ms ⑤회항 166s 셔플→**레그별 사전회전**(166→5s, 증거: B-회랑 정136s vs 역29s).
- **bridge**: 왕복(1→6→역순→1)+**복귀주차**(goToPose+Spin 정렬)+레그별 goToPose+워치독 240s+**JSONL `~/patrol_runs.jsonl`**(다음 부팅부터). 풀시퀀스 3판 연속 성공(최종 11/11, 454s).
- **스킬화**: 물리 재배치 루프 — `_dock_reseed.sh` 한 줄 재시딩+수락판정, "충전소 물리 이동" 트리거.
- **다음 진입**: 순찰 후 JSONL 레그판정 → 크롤 복불복(`slowdown_ratio` 0.35 후보) → 젠지 프리셋 P2.

---

## 2026-07-08 (밤) — 🤝 젠지 좌표주행 PASS(4.1cm) + 맵-현실 정합 검증 도구 + 순찰 프리셋 5종/Unity 드롭다운

- **주행**: 젠지(비-ns 스택) `nav_up.sh`(arena_shared·현IP 갱신판) 기동 → 0.8m 실주행 13s, **오차 4.1cm PASS**. bridge 존 토글·90s 타임아웃 첫 실전 검증, `--nav-ns ''`로 티원/젠지 겸용화.
- **AMCL 함정 3종 스킬화**: 반올림 쿼터니언 "malformed. Rejecting" 조용한 거부(수락 판정="Setting pose" 로그), latched 옛값, 옆에 주차된 로봇 블롭이 회전수렴 발산(위치 사용자확정+방향 물리정렬+타이트 시딩으로 해결).
- **맵-현실 정합**: 신규 `scripts/scan_vs_map_check.py`(--fit) — baseline 45.6%→fit 98.7% = **맵(장애물 2개 포함)=현실**, 어긋남은 위치추정 잔차 → fit 보정값 재시딩(98.5% 재검증). 장애물은 라이다+로컬 costmap(cost 100) 2단 인식 확인. 우측 장애물 실물 ~8cm 삐짐만(무해).
- **순찰 프리셋**: 신규 `scripts/patrol_presets.py` — 클리어런스 ≥0.25m 검증 5종 → `arena_shared.presets.json` + MapPanelView **프리셋 드롭다운**(적용/"내 경로 복원") 컴파일 PASS. 클릭 실패 원인 = 25cm 회색지대(장애물A 남쪽 통로는 유효점 0).
- **유령 티원 마커**: MapMarkerLayer 전역 tf 폴백이 리셋된 선택로봇 마커에 얹힘 — 젠지 선택+Play 재시작으로 해소, 코드 차단 TODO.
- **종료**: 젠지 독 재시딩(0.10,1.11,0.293) 후 안전 셧다운. **다음 진입**: ①티원 충전→activate 재시도→Smac 검증 3종 ②젠지 프리셋 P2 실주행 ③유령 마커 차단·발행자 per-robot 라우팅.

---

## 2026-07-08 (저녁) — 🧭 주행 개선 4종 처방(웹조사) — Smac 2D·유령장애물·독 존 토글·bridge 강건화 배포 (활성화 검증은 배터리로 이월)

- **결정**: "장애물 회피 못하고 멈춤" 웹조사(하이쿠+직접검색)로 병인 특정 → 4종 처방 확정: ①obstacle layer `inf_is_valid: true`(무반사 inf 광선이 버려져 raytrace clearing 불가 → **유령 장애물**이 영구 정지 유발) ②플래너 NavFn→**Smac 2D**(협소공간 경로질·속도 2~3배, 플러그인 설치 확인) ③독/구석 출발 = PolygonStop **`enabled` 동적 토글**(nav2 공식 도킹 패턴 — 8방위 cmd_vel 탈출 대체) ④bridge `wait_result` 타임아웃(90s/레그)+cancel. 컨트롤러는 DWB 유지(RPP는 회피 불가라 기각), MPPI/TEB 제외.
- **미세 조정(주인님 확정)**: max_vel_x/max_speed_xy 0.08→**0.12**, xy_goal_tolerance 0.25→**0.15**. controller_frequency는 스톡이 이미 10이라 무변경.
- **지뢰 2개 해체**: `patch_nav_params_ns.py`가 ①keepout filter를 여전히 주입(재생성 시 "마스크 미수신" 정지 부활) → `--keepout` 플래그 게이트(기본 OFF) ②source_timeout 1.0 미영속(로봇 yaml 직접 수정분) → 스크립트에 박음. **"로봇 yaml 직접 수정은 재생성 때 증발한다" — 수정은 반드시 patch 스크립트에.**
- **진행 상태**: Phase A(params) 로봇 배포+재생성+키 검증(grep 5종 전부 OK) 완료. 그러나 nav2 재기동 후 **controller/planner activate FAIL — 같은 시점 배터리 상태불량(47.8%에서 급락 추정)이라 원인 미확정(저전압 의심)**, 진단 없이 안전 셧다운. bridge 패치(존 토글+타임아웃)는 로컬 완료·py_compile OK, **로봇 미배포**.
- **다음 진입(순서)**: 완전 충전 → bringup+AMCL 독 시딩 → `bash ~/_restart_nav_ns.sh`+8노드 lifecycle → activate 재시도(성공하면 저전압 원인 확정, 실패하면 `/tmp/nav_tb3_1.log`에서 Smac configure 에러 확인) → `scp patrol_waypoints_bridge.py t1:~/ && systemctl --user restart urhynix-bridge` → 수동 `ros2 param set /tb3_1/collision_monitor PolygonStop.enabled false` 동적 토글 실측 → Phase C 검증 3종(C1 UI 4점 순찰 완주+벽스침 0, C2 사람 5~10초 막았다 비키기→≤10s 자동재개, C3 완주 후 enabled=true 복원). 맵의 고정 장애물 2개 근처 통과 경로로 pinch point 확인.
- **부수 산출물**: `scripts/patch_nav_params_ns.py`(keepout 게이트·inf_is_valid·Smac·0.12·tol 0.15·source_timeout), `scripts/patrol_waypoints_bridge.py`(존 토글·타임아웃), 플랜 `~/.claude/plans/logical-crafting-pearl.md`

---

## 2026-07-08 (오후) — 🤖 티원 첫 좌표주행 세션 — "안 움직임" 3중 결합 규명 + 1.5m 실주행 PASS + 상주 서비스 표준화 (배터리로 완주 이월)

- **결정/증상**: Unity 우클릭 좌표로 티원 주행 시도 — goal 수락·피드백 정상인데 물리 정지. 규명 결과 **단일 원인이 아니라 3중 결합**: ①keepout 마스크 서버 부재(재부팅 소실) → costmap 미완성 ②collision_monitor scan `source_timeout 0.2` < Pi 부하지연 0.21~0.36s → 상시 정지 ③독/구석 정차 → PolygonStop 상시 발동. 하나 풀 때마다 다음 층 노출 — 층별 이분탐색으로 해결 후 **1.5m 실주행 확인**.
- **추가 발견(상류)**: Unity 순찰/출동 발행이 로봇에 안 간 진범 = `ros_endpoint.json`의 `endpointRobotId: tb3_2`(꺼진 젠지) — 발행자는 공유 기본 연결만 씀(구독은 per-robot이라 마커는 뜸). **tb3_1로 전환**(Play 재시작 필요). 근본 수정(발행자 per-robot 라우팅)은 TODO.
- **튜닝 확정**: inflation 0.35→**0.20**(통로 폐색 해소), PolygonStop 0.18→**0.14**, Slow/Limit 0.18/0.16, source_timeout **1.0**, 탈출각 30→**60°** — `patch_nav_params_ns.py` 반영.
- **인프라 표준화**: 로봇 상주 4서비스(systemd user+linger, 재부팅 생존) — endpoint/scanfix/posepub/**bridge**(UI 순찰 수신). 원본 `scripts/robot_services/`. "재부팅 후 동반 프로세스 실종" 클래스 종결.
- **부수 산출물**: `scripts/nav2_goal_t1.py`(표준 주행 — 외부 nav2_goal_v3 이식+티원 3대 즉사 수정), 신규 스킬 `urhynix-t1-drive-nomove-diag`(계층 진단 트리), patrol-drive 스킬 함정#13~19, ip-drift-resync 함정 추가, `tb3.sh` CIDR 10→20.
- **다음 진입**: 충전 후 ①Play 재시작(endpointRobotId=tb3_1 반영) ②UI "순찰 시작" → bridge 수신·완주 확인 ③주행엔진 처방 6종(출발 전 자기점검/직접탈출 폴백/ETA0 조기진단/조기 스턱/입력단 클리어런스/회전 진전) + bridge P0 4종(타임아웃/선점/안전이식/상태방송) 이식 — 상세 설계는 이 날짜 대화 로그.

---

## 2026-07-08 (오전) — 🏛️ 2.5D 박물관 장식 시스템 구축 + dogfood 감사 → P1~7 수정 PASS (컴파일 검증, 육안 대기)

- **결정/증상**: Gallery Room 팩(302MB) 임포트 → 전부 마젠타. 원인 = **URP 17 ↔ 팩 Built-in Standard 셰이더 미스매치** → 에디터 `StandardUpgrader` 스크립트로 16/16 변환(재사용: `Assets/Editor/GalleryRoomUrpUpgrade.cs`, SpeedTree는 GUID 스왑).
- **장식 시스템(전부 데이터 주도)**: `StreamingAssets/Maps/<slot>.decor.json` + `MuseumDecorSpawner` — 검정 그리드 바닥, 갤러리 벽 스킨, 벽 직선화 병합(34→10, 표시 전용·로봇 pgm 불변), 액자+벽당 트랙레일 조명+스팟, 충전독 연한 로봇색 패치, 차폐벽(wall_13 자리, 평소 열림→화재 출동 시 하강→10초 자동 개방, `FireShutter`), 니케상/스핑크스(사용자 STL→Blender 데시메이트→1m 정규화 OBJ, `scale`=실높이m), 로봇 마커 = ROBOTIS 공식 TB3 burger 실모델.
- **dogfood 감사**(ChatterBox 스킬 이식 실행): 정찰 1 + 페르소나 워커 4(Opus) + 메인 검증 → 시연 Blocker(데모 화재 버튼 미결선)·운영 Blocker(2.5D 슬롯 stale) 확정, 워커의 "ROS 콜백 백그라운드 스레드 P0"는 `ROSConnection.Update()` 메인스레드 디스패치로 **반증**.
- **P1~7 수정(phase-loop, 자기리뷰 메인 직접)**: ①데모 화재 버튼→모의 출동 발화(SSOT `demoDispatch/demoX/demoY`) ②셔터 개폐 barrier 로그 ③오프라인 로봇 출동 게이트(수동 숨김·상황 출동은 경고 유지) ④2.5D 시점 리셋 버튼+yaw/pitch 영속 ⑤URP per-object 라이트 4→8 ⑥슬롯 전환 시 2.5D 재빌드+`rt_` 규약 리소스 정리(잔존 UI 콜백은 cam null 가드) ⑦위생(에디터 전용 로그 등). 컴파일 PASS(DLL mtime > 마지막 소스 편집으로 stale 배제).
- **핵심 학습 3건**: ⑴ unityctl stale check — 사용자가 Play 중이면 재컴파일 안 됨, `exec 'UnityEditor.AssetDatabase.Refresh()'`가 키스트로크보다 확정적 ⑵ 오프셋 씬(반사프로브 無)에서 고metallic 재질은 검게 렌더 — 저metallic 사용 ⑶ 맵 지형지물 특정은 기하 추론 금지, `[MapClick]` 우클릭 로그+확인질문 필수(차폐벽 2회 오특정).
- **부수 산출물**: `.claude/skills/urhynix-dogfood-audit/SKILL.md`(신규), `Assets/Resources/MuseumDecor/`(OBJ 3종+Wall.mat+prefab 4), `arena_shared.decor.json`, 메모리 2건(unity-urp-material-upgrade, feedback-map-feature-identify-confirm).
- **다음 진입**: 로봇 트랙 Top 액션(완전 충전 후 4점 순찰 #3~#4 완주)은 그대로 유지. Unity 트랙은 Play → 2.5D 육안 체크리스트: 장식 전경 / 데모 "화재" 버튼 → 셔터 하강·10초 개방 / 시점 리셋 버튼 / 슬롯 전환 반영 / 액자·조각상 스케일(decor.json 노브 조정).

---
