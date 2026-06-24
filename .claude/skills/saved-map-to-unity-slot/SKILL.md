---
name: saved-map-to-unity-slot
description: SLAM이 저장한 점유격자맵(.pgm/.yaml)을 품질 검증한 뒤 Unity ControlRoom 맵 슬롯(StreamingAssets/Maps/<id>.png+.json)으로 등록하는 엔드투엔드 표준. "맵 유니티에 넣어줘", "슬롯에 등록", "새 맵 등록", "arena_v3 유니티에" 같은 요청에 발동. 픽셀통계+ASCII+PNG 시각검증 → scp로 evidence 복사 → pgm_to_map_slot.py 변환 → MapCatalog 자동인식 확인까지 한 호흡. map-quality-eval(평가만)과 pgm_to_map_slot.py(변환만) 사이의 빈 구멍을 메운다. 2026-06-24 arena_v3 도출.
---

# Saved Map → Unity Slot

## 목적

map_saver가 만든 `.pgm/.yaml`을 (1) 깨지지 않았는지 정량 검증하고 (2) Unity ControlRoom이 런타임에 읽는 슬롯으로 등록한다. 맵을 새로 뜰 때마다(arena, genji_arena, arena_v3…) 반복되는 흐름.

## 발동 트리거

"맵 유니티에 넣어줘", "슬롯에 등록", "새 SLAM 맵 등록", "<id> 유니티에" 등.

## 입력

- 소스 `.pgm` + `.yaml` 위치. 로봇에 있으면 먼저 `scp`로 Mac `docs/evidence/maps/<id>/`로 가져온다(로봇 IP는 `default_robots.json`/메모리 `project_robot_ip_dynamic`).
- 슬롯 id(예: `arena_v3`), 표시 이름(예: "티원 아레나 v3").

## 절차

### Step 1 — 맵 확보 + 품질 검증 (검증은 성역 — 생략 금지)

pgm 픽셀 통계로 깨짐을 판정한다(P5 binary PGM 가정):

```python
f=open(PGM,'rb'); assert f.readline().strip()==b'P5'
l=f.readline()
while l.startswith(b'#'): l=f.readline()
w,h=map(int,l.split()); f.readline(); d=f.read()
occ=sum(1 for b in d if b<50); free=sum(1 for b in d if b>200); unk=w*h-occ-free
# 점유(벽)·자유(주행가능)·미지 비율 출력. free>50 & occ>20 이면 맵 형성 OK
```

추가로 **ASCII 오버레이**(`#`=벽 `.`=자유 ` `=미지)와 **12배 확대 PNG**(표준 zlib만, PIL 불요)로 육안 확인. 판정 기준:
- 외곽선이 닫혔는가(루프 클로저), 벽 겹침/휨(드리프트) 없는가
- 자유공간이 비어있지 않은가
- ⚠️ 실제 크기(= w·h × resolution)가 의도한 공간과 맞는가 — 너무 작으면 부분맵일 수 있으니 주인님께 알린다(자동 통과 금지).

### Step 2 — evidence 복사

```bash
mkdir -p docs/evidence/maps/<id>
scp -o ConnectTimeout=6 <host>:/path/<id>.pgm docs/evidence/maps/<id>/   # 한 파일씩(quote로 2개 묶으면 실패)
scp -o ConnectTimeout=6 <host>:/path/<id>.yaml docs/evidence/maps/<id>/
```

### Step 3 — Unity 슬롯 변환 (기존 스크립트 재사용)

```bash
python3 scripts/pgm_to_map_slot.py docs/evidence/maps/<id>/<id>.pgm docs/evidence/maps/<id>/<id>.yaml <id> "<표시이름>"
# → unity/ControlRoom/Assets/StreamingAssets/Maps/<id>.png + <id>.json 생성
```

`pgm_to_map_slot.py`는 PIL(Pillow) 필요. 없으면 `python3 -m pip install Pillow`.

### Step 4 — 슬롯 인식 확인

- `MapCatalog.cs`는 `Directory.GetFiles(MapsDir,"*.json")` **디렉토리 스캔** → 새 슬롯 자동 인식. 코드 등록 불필요.
- 시작 기본맵은 `StaticMapLoader.cs`의 `defaultSlotId`(기본 "arena"). 새 맵을 기본으로 하려면 이 한 줄만 교체(주인님 승인 후). 아니면 ControlRoom에서 1회 선택 시 PlayerPrefs가 기억.
- `.meta`는 Unity 에디터를 다음에 열 때 자동 생성 → git 커밋 전 에디터 1회 오픈.

## 함정

- **`ls` 출력이 비어 보임(rtk 프록시 표시 버그)**: `stat -f "%N %z" <file>`로 실제 존재 확인.
- **scp 두 파일 한 줄 quote(`'~/a ~/b'`)는 `No such file`**: 파일당 1회 호출.
- **품질검증 자동 PASS 금지**: 크기가 작거나 미지 0%처럼 특이하면 육안 확인 후 주인님 판단을 받는다.

## Verify

- `StreamingAssets/Maps/<id>.png` + `<id>.json` 존재(stat 확인), json의 origin/resolution/widthPx/heightPx가 yaml과 일치.
- 품질 매트릭스(벽/자유/미지 %) + 시각(ASCII 또는 PNG) 1건.

## Outputs

- evidence 맵 3종(pgm/yaml/png) + Unity 슬롯 2종(png/json) + 품질 판정 1표.

## 관련

- `map-quality-eval`(정량 평가 단독), `live-map-pull-from-domain`(라이브 /map 떠오기), `unity-live-map-twin`(슬롯을 맵뷰에 렌더 + /tf 마커 + goal_pose).
- 변환 스크립트: `scripts/pgm_to_map_slot.py`.
