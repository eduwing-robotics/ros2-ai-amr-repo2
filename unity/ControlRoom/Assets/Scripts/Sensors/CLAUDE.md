# Assets/Scripts/Sensors/

> 센서 카드 인터페이스 + Registry (배터리/가스/소리/조도/PIR/화재).

## 예정 파일

| 파일 | 역할 |
|---|---|
| `ISensorModule.cs` | 센서 추가용 공통 인터페이스 |
| `SensorRegistry.cs` ✅ | 센서 등록소 (`SensorConfig/default_sensors.json` 로드 + ID/로봇별 조회) |
| `BatterySensor.cs` | 배터리 (`/battery_state`) |
| `GasSensor.cs` | 가스 |
| `SoundSensor.cs` | 소리 |
| `LightSensor.cs` | 조도 (LDR) |
| `PirSensor.cs` | 인체 감지 |
| `FireSensor.cs` | 화재/불꽃 |

## 새 센서 추가 절차

1. `Resources/default_sensors.json`에 센서 ID/표시 이름/단위/토픽/경고 임계값/아이콘 추가.
2. 단순 수치 센서는 generic renderer로 처리.
3. 특수 로직 있으면 `ISensorModule` 구현체 만들기.
4. `SensorRegistry`에 등록.
5. UI 카드는 `Scripts/UI/SensorCardListView`가 자동 생성.
6. 위험 이벤트 승격 조건은 `Ros/SecurityEventSubscriber` 또는 sensor module에 둠.

## 아두이노 연결

`tb3_2`(젠지) 측 Arduino 4종(PIR/LDR/소리/불꽃) → `/dev/tb3_arduino` serial → ROS2 publisher → Unity subscribe.
스킬: `arduino-flash`.
