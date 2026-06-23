---
name: map-quality-eval
description: SLAM이 산출한 점유 격자맵(pgm+yaml)을 픽셀 통계로 정량 평가하고 Nav2/발표 시연/디지털 트윈 use case별 go/no-go를 판정해 evidence eval.md까지 자동 생성한다. URHYNIX 경기장 매핑 회귀 평가 표준.
user_invocable: true
tags: [slam, mapping, evidence, automation, urhynix-m5]
trigger: "매핑(tb3-slam-save + tb3-fetch-map) 직후 결과 quality를 정량 평가하고 다음 액션(재매핑/Nav2 진입)을 정해야 할 때"
version: 1
---

# Map Quality Eval

`tb3-slam-save → tb3-fetch-map → tb3-map-to-unity`까지 끝낸 직후 호출.
**픽셀 통계 + use case go/no-go + eval.md 자동 생성**을 한 줄로 끝낸다.

URHYNIX의 2026-05-29 경기장 1차 매핑(`arena_v1`)에서 발견한 패턴:
"unknown 0% + occupied 매우 적음" = 회전만 매핑의 한계 sign. 이 진단을 표준화.

## Use When

- 매 매핑(`arena_vN`) 직후 정량 평가가 필요할 때
- 발표 시연용 vs Nav2 베이스라인용 use case별 적합도를 판정할 때
- 재매핑 vs 다음 단계 진입 결정이 필요할 때
- evidence `eval.md`를 일관된 형식으로 자동 생성하고 싶을 때
- 매핑 회귀 검증 (helper 갱신·DDS 모드 변경 후) 시 baseline 비교가 필요할 때

## Inputs

- `<map_name>`: 평가 대상 맵 이름 (예: `arena_v2`)
- 전제: `docs/evidence/maps/<map_name>/<map_name>.png` + `.yaml` 존재
  (`tb3-fetch-map`이 자동 생성)

## Outputs

1. **콘솔 통계 (요약)** — 픽셀 비율 + use case verdict + 다음 액션 추천
2. **`docs/evidence/maps/<map_name>/eval.md`** — 표준 형식으로 자동 갱신
   (기존 파일 있으면 덮어쓰기 전 확인 prompt)

## One-Liner

```bash
python3 .claude/skills/map-quality-eval/eval.py <map_name>
```

또는 helper alias (`scripts/aliases.sh`에 등록 후):
```bash
map-eval <map_name>
```

## 픽셀 통계 의미

```
PGM trinary mode (map_io 기본):
  값 < 128 (검정)   → Occupied   ← 가벽/장애물
  값 > 200 (흰색)   → Free       ← LiDAR가 통과한 자유공간
  128~200 (회색)    → Unknown    ← 미관측 영역
```

| 비율 패턴 | 해석 | 액션 |
|---|---|---|
| occupied ≥ 5% + unknown ≥ 10% | 건강한 매핑 | ✅ 다음 단계 진입 |
| occupied < 3% + unknown 0% | **회전만 매핑의 한계** (가벽이 LiDAR 반경 일부 외) | ⚠️ 하이브리드 재매핑 권장 |
| occupied ≥ 5% + unknown 0% | 회전+이동 OK, 외곽 다 닿음 | ✅ 발표용 적합 |
| occupied < 1% | LiDAR 거의 빈 공간 보고 있음 | 🟥 매핑 자체 실패 |

## Visual Verdict 체크리스트 (PNG 시각 확인 보조)

- [ ] 외곽이 둥글게 끊김 = LDS-03 3.5m 반경 한계 노출 → 이동 매핑 필요
- [ ] 가벽 연결선이 끊겨있음 = 일부 가벽이 LiDAR 밖 → stop 추가
- [ ] 중앙 구조물 형태 깨끗 = 좋음
- [ ] 가벽 두께가 일정 = 좋음 (휘었으면 회전 속도 과다)
- [ ] 격자 무늬가 사선/회전 = 드리프트, 루프 클로저 실패

## Use Case Go/No-Go

| Use case | 통과 기준 |
|---|---|
| 데이터 저장 검증 | 파일 3곳 존재 (robot, local evidence, Unity Assets) |
| W2 SCRUM-10 Nav2 베이스라인 | occupied ≥ 3% AND 가벽 연결성 확인 |
| 발표 시연 (S1) | occupied ≥ 5% AND 외곽 끊김 없음 |
| Unity 디지털 트윈 텍스처 | PNG 정상 + yaml resolution/origin 유효 |

## eval.md 자동 생성 형식

`arena_v1/eval.md` (2026-05-29 작성)와 동일 형식:
- Date / SLAM T0 / Operator / Robot
- Environment (Site, Approach, Teleop pattern, LDS range)
- Map Output 표 (크기, resolution, origin, Unity scale)
- Pixel Statistics 표
- Visual Verdict
- Use Case Assessment 표
- Recommendation
- Reproduction Commands
- Related (이전 maps 링크)

## 트러블슈팅

| 증상 | 원인 | 해법 |
|---|---|---|
| `FileNotFoundError: <name>.png` | `tb3-fetch-map` 미실행 또는 PIL 변환 실패 | `tb3-fetch-map <name>` 재실행 후 png 생성 확인 |
| occupied 0% | map_io trinary threshold 너무 낮음 | yaml의 `occupied_thresh` 0.65 확인, cartographer 재시작 후 재매핑 |
| unknown 100% | cartographer가 scan 못 받음 | bringup `/scan` hz 재확인 (`tb3-up` 재시작) |
| eval.md 덮어쓰기 망설임 | 기존 evidence 보존 필요 | rename: `eval.md → eval_v1.md`, 새로 생성 |

## Chain With

- 직전: `tb3-slam-save <name>` → `tb3-fetch-map <name>` → `tb3-map-to-unity <name>`
- 결과 활용: `decision-broadcast` (재매핑 결정 시), `session-handoff` (Top 1 갱신)
- 비교: `slam-nav2-arena-survey` (전체 매핑 사이클의 한 단계)

## 산출 evidence 표준 위치

- `docs/evidence/maps/<name>/<name>.{pgm,yaml,png}` (3 파일)
- `docs/evidence/maps/<name>/eval.md` (이 스킬이 생성)
- `unity-smoke/Assets/Maps/<name>.{png,yaml}` (`tb3-map-to-unity` 산출)

## 한줄정리

매핑 끝나면 한 줄로 픽셀 통계 + use case verdict + eval.md 생성. unknown 0% + occupied 매우 적음 = 회전만의 한계 sign이라 자동으로 하이브리드 재매핑 권장.
