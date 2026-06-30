# RTAB-Map 멀티세션 3D 맵 계획 (텔레옵 + 들기)

작성: 2026-06-25 · 갱신: 2026-06-26(핵심 2포인트 조사검증) · 상태: **계획 — 코드/로봇 미검증, 절차 조사검증**

티원 D435로 **가림 없는 완전한 3D 디지털트윈 맵**을 만든다. 어제(6-25) odom 누적 점군(`rot360_odom.ply`, 1200만점)은 한 위치 회전이라 가림이 많았다. 이를 RTAB-Map 멀티세션으로 보강한다.

> 전제: 3D 점군은 **발표·관제 시각화용**. 로봇 주행은 LDS-03 2D 맵(arena_v4)이 정본 — 3D가 흔들려도 주행엔 영향 없음. (`REALSENSE-D435-3D-MAPPING-RESEARCH.md` 2D Correction Policy)

> ★ 선결정(2026-06-26): **액자(중요전시품)는 빼고 정적 환경만 스캔.** 액자는 "움직임 감지 대상(시나리오 ②)"이라 맵에 구우면 옛위치 vs 실제가 충돌하고, RTAB loop closure는 정적 특징으로 봉합하므로 가동물체는 정합을 깬다. 빈 거치대/걸이만 둔다.

## 조사로 메운 2포인트 (2026-06-26 웹검증)

1. **멀티세션 append 방법** — `Mem/IncrementalMemory=true` + **`--delete_db_on_start` 제거** → 기존 DB 이어쓰기. 최신 RTAB는 파라미터를 DB에 저장(별도 ini 불필요). S2 시작 시 **localization 모드로 기존 맵 재정합**(loop closure inliers >100 = 좋은 anchor) 후 매핑 재개 → 아래 "S1에서 본 곳 먼저 비추기"와 정확히 일치.
2. **오프라인 reprocess** — `use_sim_time:=true` + rosbag `--clock` 재생 + rtabmap `offline:=true`. rosbag엔 `/tf`,`/tf_static`,aligned depth/color + camera_info 필수(기존 `d435_record_smoke.sh`가 이미 다 녹화).
3. **⚠️ 트레이드오프** — 오프라인 reprocess는 **추적 실패 시 자동 relocate(복구)가 없다**(라이브만 복구). → **S1(휠odom 안정)=오프라인 OK / S2(visual odom·들기=끊기기 쉬움)=라이브 권장.**

> ⚠️ 선행 스크립트 실재 확인: 스킬이 참조하는 `_t1_bringup_only.sh`·`_t1_rs_pointcloud.sh`가 repo `scripts/`에 **없음**(6-25 `/tmp`에만 생성 추정). 실행 전 티원 `/tmp`/repo 확인, 없으면 스킬 절차로 재생성.
> 실행 런북(Phase별 명령 상세): `~/.claude/plans/partitioned-wiggling-aurora.md`(2026-06-26 승인).

## 핵심 전략 — 세션 2개로 분리

| 세션 | 시점 | 위치추정 | 담당 |
|---|---|---|---|
| **S1 텔레옵 주행** | 로봇 눈높이(낮음) | **휠 odom + visual** → 안정 | 바닥·벽 뼈대 |
| **S2 들어서 부감** | 위→아래(높음) | **visual odom 단독**(바퀴 무시) | 책상 위·높은 곳·천장 |
| **병합** | — | RTAB loop closure | S1+S2 같은 좌표로 |

**왜 분리?** 터틀봇을 들면 바퀴가 안 굴러 휠 odom이 "안 움직였다"고 거짓 보고 → 연속 세션이면 추적이 깨진다. 세션을 끊고 S2는 visual odom으로 전환하면 회피된다.

## 선행 조건 (6-25 검증됨, 재사용)
- 도메인 `ROS_DOMAIN_ID=210`, 티원 `t1@192.168.10.250`(IP drift 주의).
- D435 토픽: `/tb3_1/camera/{color/image_raw, aligned_depth_to_color/image_raw, aligned_depth_to_color/camera_info}`. RGB-D 14~15Hz, USB3.
- bringup(odom) + static tf(`tb3_1/base_link→camera_link`) 절차는 스킬 [[urhynix-d435-3d-pointcloud-capture]].
- cmd_vel = TwistStamped(`drive_rotate.py`). 텔레옵은 `teleop_twist_keyboard` 또는 키보드 노드.

## Phase R0 — RTAB-Map 설치 (미검증)
- 티원: `echo 123 | sudo -S apt install ros-jazzy-rtabmap-ros` (인터넷 필요). RAM 3.6GB라 부하 주의.
- 대안: Mac에 RTAB-Map(docker/소스). 6-17 메모리 "Mac 오프로드" 방향.
- **결정 포인트(2026-06-26 정정)**: 티원 단독 라이브 vs Mac 오프라인 replay는 **세션별로 갈린다**. S1(휠odom 안정)은 rosbag→Mac replay 안전. **S2(들기·visual odom)는 오프라인이면 추적 끊겨도 복구 불가** → 라이브 권장. 현장 `free -h`로 티원 RAM 보고 결정(640x480x15면 라이브 견딜만, 폭주 시 폴백).

## Phase R1 — S1 텔레옵 주행 맵 (휠 odom)
1. bringup + D435 RGB-D + static tf 가동(스킬 절차).
2. RTAB-Map `rgbd` 모드, odom 소스 = 휠 odom(`/tb3_1/odom`) + RGB-D.
3. 텔레옵으로 맵 **구석구석 천천히** 한 바퀴. 같은 곳 거치며 loop closure 유도.
4. RTAB DB 저장(`~/.ros/rtabmap.db` 또는 지정).

## Phase R2 — S2 들기 부감 맵 (visual odom)
1. **새 세션**으로 시작(S1 DB는 보존, multi-session append).
2. odom 소스 = **visual odom**(RGB-D odometry, 휠 무시).
3. 터틀봇(또는 D435만 분리)을 **천천히** 들어올림. 들 때 **S1에서 본 곳을 먼저 비춰** 위치 재획득(loop closure 다리).
4. 위에서 아래로 책상 위·높은 곳·천장 보완 스캔.

## Phase R3 — 병합 + export
- RTAB loop closure로 S1+S2 자동 정렬.
- export: `.ply`/`.pcd`(점군) 또는 `.obj`(메시) → `docs/evidence/3d_maps/2026-06-26-rtab/`.
- A/B 비교: 6-25 odom 누적(`rot360_odom.ply`) vs RTAB 멀티세션 — 밀도/가림/드리프트/벽 정합.

## 들기 실전 팁
1. **천천히** 들어올림(확 들면 visual odom 추적 실패).
2. **S1에서 본 장면을 거쳐** 올림(loop closure 재정렬 = 두 세션 봉합).
3. 카메라가 터틀봇에 수평 고정 → 아래 보려면 기울임. **D435만 분리**하면 가볍고 각도 자유(USB 연장 필요).
4. 특징 없는 흰 벽 정면은 피함(visual odom이 길 잃음).

## 함정 (예상)
- 들 때 휠 odom 거짓 → S2는 반드시 visual odom.
- RAM 3.6GB → RTAB 라이브가 무거우면 rosbag replay 오프라인.
- D435 0.3~3m → 높이서 멀면 바닥 디테일 손실(너무 높이 들지 말 것).
- RTAB visual odom은 텍스처 필요 → 조명·무늬 부족하면 실패.

## 산출 기대
- 바닥(텔레옵) + 높이(들기)가 합쳐진 **가림 적은 완전 3D 맵**.
- 이후 Unity ControlRoom `map-3d-container`에 로드(Phase 3).
