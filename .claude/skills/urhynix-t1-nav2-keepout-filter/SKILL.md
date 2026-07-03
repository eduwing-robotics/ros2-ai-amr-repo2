---
name: urhynix-t1-nav2-keepout-filter
description: 티원(tb3_1) nav2 costmap에 원형 진입금지구역(Keepout Zone)을 얹어서 보호대상 주변으로 로봇이 못 가게 하는 절차. "보호대상 근처 못 가게", "진입금지 구역 설정", "keepout zone", "특정 좌표 회피"에 발동. 벽/맵 이미지 기준 원형 마스크(pgm+yaml) 생성 → nav2 Costmap Filter(KeepoutFilter) 플러그인 배선 → 마스크 map_server + costmap_filter_info_server 수동 lifecycle 기동까지 검증된 순서. (2026-07-01 로그로 local/global costmap 양쪽 필터 수신 확인 PASS, AMCL 무관 반증됨)
tags: [ros2, nav2, costmap, keepout, turtlebot3, urhynix]
version: 1
---

# URHYNIX 티원 Keepout Zone (nav2 Costmap Filter)

`urhynix-t1-nav2-patrol-drive`로 nav2가 이미 떠 있는 티원에, 보호대상 좌표 주변 원형 반경을 **하드 회피구역**으로 등록한다. 플래너가 애초에 그 안으로 경로를 안 잡는다(global+local costmap 둘 다 적용 시).

## Use When

- "보호대상 근처는 못 가게", "이 좌표 반경 진입금지" 요청
- 맵에 표시된 protected target(액자/작품 등) 주변에 순찰 로봇이 접근하지 못하게 해야 할 때

## 방식 선택 기준

- **Keepout Filter(본 스킬)**: 여러 개/반경 조정/온오프가 필요하면 이 방식. SSOT 맵(`arena_shared.pgm`)은 안 건드림.
- **맵에 직접 벽으로 굽기(대안, 더 가벼움)**: 딱 한 번뿐이고 반경/온오프 조정 불필요하면 `scripts/pgm_to_sdf_walls.py` 패턴처럼 맵 자체에 박아버리는 게 더 빠름 — 단 "보호대상"이라는 의미가 사라지고(그냥 고정 벽) 나중에 바꾸려면 맵을 재생성해야 함.

## 절차 (검증된 순서)

1. **마스크 생성**(로컬, 로봇 아님) — 보호대상 좌표(x,y)+반경(m) 지정:
   ```bash
   python3 scripts/make_keepout_mask.py \
     docs/evidence/maps/arena_shared/arena_shared.pgm docs/evidence/maps/arena_shared/arena_shared.yaml \
     /tmp/keepout_mask.pgm /tmp/keepout_mask.yaml <cx> <cy> <radius_m>
   ```
   반지름 기준: 로봇 반경(버거 ~0.105m) + 여유 0.3m 이상 → **최소 0.4~0.5m** 추천. 보호대상이 크면 바운딩박스+0.3m 버퍼로 계산.
2. **params 패치**(재생성 시 자동 포함) — `scripts/patch_nav_params_ns.py`에 이미 `filters:[keepout_filter]` + `keepout_filter:` 블록이 박혀있음(global_costmap/local_costmap 양쪽). 로봇에서 `python3 patch_nav_params_ns.py` 재실행하면 `/home/t1/nav2_tb3_1_params.yaml`에 자동 반영.
   - **끄고 싶으면**: 생성된 yaml에서 두 costmap의 `filters`/`keepout_filter` 키를 제거(python yaml 로드→pop→저장)하고 nav2 재기동.
3. **마스크 파일 배포** — `scp keepout_mask.pgm keepout_mask.yaml t1@<ip>:/home/t1/maps/arena_shared/`
4. **마스크 서버 기동** — `scripts/_keepout_filter_up.sh`(map_server 패턴 재사용, 수동 lifecycle):
   ```bash
   bash /home/t1/_keepout_filter_up.sh tb3_1 /home/t1/maps/arena_shared/keepout_mask.yaml 2
   ```
   내부적으로 `tb3_1_keepout_mask_server`(/tb3_1/keepout_mask 발행) + `tb3_1_costmap_filter_info_server`(/tb3_1/costmap_filter_info 발행) 기동 후 configure→activate.
5. **nav2 스택 재기동 필수** — costmap `filters` 파라미터는 노드 기동 시점에만 읽히므로, params.yaml을 고친 뒤(또는 처음 켤 때) nav2 8노드를 반드시 kill+relaunch 해야 반영됨(`urhynix-t1-nav2-patrol-drive` 절차 3~4 재실행).
6. **연결 확인** — `nav_tb3_1.log`에서 아래 라인이 local_costmap(controller_server)과 global_costmap(planner_server) **양쪽 다** 나와야 진짜 적용된 것:
   ```
   Using costmap filter "keepout_filter"
   KeepoutFilter: Received filter info from ... topic.
   KeepoutFilter: Received filter mask from ... topic.
   ```

## 함정표

| # | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | params.yaml에 필터 설정을 넣고 nav2를 재기동 안 하면 아무 효과 없음 | costmap `filters` 리스트는 노드 **기동 시점**에만 읽음, 런타임 추가 불가 | 필터 켜고/끄고 나면 반드시 nav2 8노드 kill+relaunch |
| 2 | `pkill -f '[m]ap_server'`로 nav2 재부팅 정리할 때 keepout mask_server까지 같이 죽음 | 마스크 서버도 내부적으로 같은 `nav2_map_server::map_server` 바이너리를 씀 — 패턴이 `map_server`를 포함하는 모든 프로세스에 매칭됨 | nav2 재기동 후 `pgrep -fa keepout`으로 죽었는지 확인하고, 죽었으면 `_keepout_filter_up.sh` 재실행 |
| 3 | AMCL이 멈추거나 nav2 goal이 타임아웃될 때 keepout filter를 의심하기 쉬움 | 실제로는 무관할 수 있음 — 2026-07-01 세션에서 필터를 완전히 제거하고도 동일 증상이 재현돼 **반증됨**(진짜 원인은 [[urhynix-t1-nav2-patrol-drive]] 함정#8, `/dev/shm` 시스템 정체) | 증상이 keepout 추가 "직후"였다고 바로 원인으로 단정하지 말고, 필터 없는 상태로 같은 시나리오 재현 테스트부터(원인 격리) |

## 재사용 스크립트

- `scripts/make_keepout_mask.py` — 맵 pgm/yaml과 같은 해상도/원점으로 원형 keepout 마스크(pgm+yaml) 생성
- `scripts/_keepout_filter_up.sh` — 마스크 map_server + costmap_filter_info_server 수동 기동+lifecycle
- `scripts/patch_nav_params_ns.py` — costmap filters 블록이 이미 patch됨(2026-07-01부터)

## 검증 (2026-07-01)

보호대상 좌표(1.14,-0.97) 반경 0.5m 마스크 생성(시각 확인: 벽 안쪽 정확한 위치) → params 패치+배포 → nav2 재기동 → 로그로 local+global costmap 양쪽 `KeepoutFilter: Received filter info/mask` 확인 PASS. 이후 AMCL 멈춤 증상과 무관함을 필터 제거 재현 테스트로 반증.

## 관련

[[urhynix-t1-nav2-patrol-drive]](nav2 스택 선행 조건 + AMCL 멈춤 함정#8 진범) · [[urhynix-t1-amcl-saved-map]](AMCL/맵 기반)
