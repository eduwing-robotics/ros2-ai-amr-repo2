---
name: urhynix-teleop-waypoint-capture
description: 텔레옵으로 로봇을 실제 지점에 세워가며 map 프레임 실측 pose를 on-demand로 캡처해 Nav2 FollowWaypoints용 순찰 웨이포인트 YAML을 만드는 표준. 위치/방향 2단계 캡처·재설정/덮어쓰기·직진 자동·START 복귀각·최종 조립+ASCII 검증. 맵 계산 대신 지상검증(ground-truth) 좌표가 필요할 때. URHYNIX 티원/젠지. 2026-06-23 티원 9점(START+WP8) 검증.
user_invocable: true
tags: [ros2, nav2, waypoint, teleop, urhynix, scrum-10]
version: 1
---

# URHYNIX Teleop Waypoint Capture

로봇을 텔레옵으로 실제 순찰 지점에 세우고, 그때의 **실측 pose**를 on-demand로 캡처해 순찰 웨이포인트를 만든다. 맵에서 계산한 좌표보다 정확한 ground-truth 방식. (SCRUM-10 다중 waypoint 갭 충족.)

## Use When

- 시연용 순찰 경로를 실제 주행으로 확정할 때
- 자동 생성([[map-pgm-waypoint-autogen]])이 장애물 근처라 못 믿을 때
- 팀원이 다른 PC에서 라이다/Nav2를 돌리는 중에도 방해 없이 좌표만 따야 할 때

## 읽기 엔진

좌표 캡처는 [[ros2-noninvasive-pose-tap]] 원리로 동작한다(subscriber=무해). `scripts/wp_capture.sh`가 매 호출마다 `map→base_footprint`를 1회 읽어 YAML에 append.

## 캡처 도구

```bash
bash scripts/wp_capture.sh <label>     # 예: START / WP1 / WP1_head
# 출력: /Users/family/Downloads/wp_captures.yaml 에 1행 추가 + 화면에 x/y/yaw
# 환경변수: T1_HOST(기본 t1@192.168.10.250), WP_OUT(기본 위 경로)
```

## 프로토콜 (위치/방향 2단계)

| 단계 | 팀원 | 운영자 명령 | 캡처 |
|---|---|---|---|
| START | 시작점 정지 | `wp_capture.sh START` | 시작 위치+초기방향 |
| WPn 위치 | WPn 정지 → "도착" | `wp_capture.sh WPn` | 정지 지점 위치 |
| WPn 방향 | 다음 WP 바라보게 회전 | `wp_capture.sh WPn_head` | 회전 후 방향 |
| 반복 | 다음 WP로 | … | … |

- **2단계 근거:** 제자리 회전은 위치를 거의 안 바꾸므로 회전 후 1회만 떠도 되지만, 정지 저장(위치 확정)+회전 저장(방향 확정)으로 나누면 회전 중 미세 전진까지 잡는다.
- **직진 구간:** 방향 캡처 생략 가능 → 조립 시 도착 방향(WPn 자체 yaw) 사용.
- **복귀각:** 마지막 WP에서 START를 겨눈 방향을 `WPn_head_start`로 캡처(루프 닫기).

## 재설정 / 덮어쓰기

- **전체 초기화:** `rm -f /Users/family/Downloads/wp_captures.yaml` 후 START부터.
- **특정 라벨 덮어쓰기:** 해당 `- name: <label>` 블록 삭제 후 재캡처.

```bash
python3 - "WP4_head" /Users/family/Downloads/wp_captures.yaml <<'PY'
import sys,re
lbl,p=sys.argv[1],sys.argv[2]; t=open(p).read()
t=re.sub(r"  - name: "+re.escape(lbl)+r"\n(?:    .*\n|      .*\n)*","",t)
open(p,"w").write(t)
PY
bash scripts/wp_capture.sh WP4_head
```

## 최종 조립

`assemble_waypoints.py`가 캡처본을 읽어 **위치(WPn) + 방향(WPn_head, 없으면 도착 yaw)** 을 합쳐 정렬된 `waypoints_<robot>_final.yaml`을 만든다.

```bash
python3 .claude/skills/urhynix-teleop-waypoint-capture/assemble_waypoints.py \
  /Users/family/Downloads/wp_captures.yaml /Users/family/Downloads/waypoints_tb3_1_final.yaml
```

산출은 사진과 동일한 `frame_id: map` + `position` + `orientation`(쿼터니언) PoseStamped 리스트.

## 검증

- 조립 후 ASCII 오버레이로 9점이 자유공간 안인지 눈으로 확인(맵 PGM 위에 S/1~8 찍기 — [[map-pgm-waypoint-autogen]] 오버레이 코드 재사용).
- 각 yaw가 다음 점을 향하는지(진행 방향과 일치) 확인.

## ⚠️ 프레임 안정성 (팀원 전달 시 필수)

좌표는 **캡처 당시 맵 프레임 기준**이다. 팀원은 **같은 저장맵 + AMCL**로 구동해야 맞는다. Cartographer로 새로 매핑하면 origin이 달라져 좌표가 어긋난다([[live-map-pull-from-domain]] 프레임 판정 참조).

관련: [[ros2-noninvasive-pose-tap]] · [[map-pgm-waypoint-autogen]] · [[live-map-pull-from-domain]] · [[slam-nav2-arena-survey]]
