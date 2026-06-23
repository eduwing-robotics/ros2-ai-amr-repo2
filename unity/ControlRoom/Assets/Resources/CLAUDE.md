# Assets/Resources/

> `Resources.Load<T>(path)`로 런타임에 로드되는 자산.

## 예정 자산

| 파일 | 역할 |
|---|---|
| `SupabaseConfig.template.asset` | Supabase URL + anon key **빈 값** 템플릿 (커밋 OK) |
| `SupabaseConfig.local.asset` | 실제 anon key 박힘 — **`.gitignore` 차단** |
| `RobotConfig/default_robots.json` ✅ | 로봇 목록 (`tb3_1` 티원 / `tb3_2` 젠지, hostAddress + cameraTopic + poseTopic 포함) |
| `FeatureConfig/default_features.json` ✅ | 기능 목록 (`scan_360` / `boost` / `slam`, RobotFeatureInfo 1:1 매핑) |
| `SensorConfig/default_sensors.json` ✅ | 센서 5종 (`gas` / `noise` / `lux` / `pir` / `fire`, SensorInfo 1:1) |
| `MapConfig/office_base_map.json` ✅ | MapConfigData 1개 (MapMeta `museum_floor1` + waypoint 5개 + 보호대상 2개) |

## 폴더 구조 (Phase 3 결정)

```
Resources/
├── RobotConfig/   default_robots.json
├── FeatureConfig/ default_features.json
├── SensorConfig/  default_sensors.json
└── MapConfig/     office_base_map.json
```

각 카테고리별 폴더 분리. `Resources.Load<TextAsset>("RobotConfig/default_robots")` 패턴.

## 보안 규칙

- `SupabaseConfig.local.asset`은 `.gitignore`에 박혀 있음. 커밋 절대 금지.
- service_role 키 절대 박지 말 것. anon key만.
- 비밀 키 회전 시 `.local.asset`만 갱신, 템플릿은 빈 값 유지.

## 로드 패턴

```csharp
var cfg = Resources.Load<SupabaseConfig>("SupabaseConfig.local");
if (cfg == null) cfg = Resources.Load<SupabaseConfig>("SupabaseConfig.template");
```

## 주의

- `Resources/` 폴더의 자산은 빌드에 무조건 포함됨 (Tree shaking 불가). 큰 파일은 `Addressables` 또는 `StreamingAssets`로.
