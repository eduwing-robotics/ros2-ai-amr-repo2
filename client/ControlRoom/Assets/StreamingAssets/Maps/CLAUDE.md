# StreamingAssets/Maps/

> 맵 슬롯 저장소. 저장맵을 `<slotId>.png`(점유격자 이미지) + `<slotId>.json`(MapConfigData 메타) 쌍으로 둔다.
> 런타임에 드롭다운으로 언제든 슬롯 전환(StaticMapLoader). 라이브 `/map`이 오면 우선되지만, 슬롯을 직접 고르면 그 맵이 핀 고정된다.

## 슬롯 추가/교체 (맵 언제든 바꾸기)

```bash
python3 scripts/pgm_to_map_slot.py <src.pgm> <src.yaml> <slotId> "표시이름"
```

- ROS `map_saver` 산출(.pgm+.yaml)을 그대로 슬롯으로 변환한다.
- 새 `<slotId>` 쌍을 넣으면 MapCatalog가 자동 인식 → 드롭다운에 등장.
- StreamingAssets는 런타임 경로 로드라 텍스처 임포터 불필요(빌드 후 교체 가능).

## 규칙

- `.json`의 originX/originY/resolution/widthPx/heightPx는 그 맵 .yaml/.pgm과 일치해야 좌표가 맞는다.
- 슬롯 id는 소문자+언더스코어 권장 (예: `arena`, `genji_arena`).
