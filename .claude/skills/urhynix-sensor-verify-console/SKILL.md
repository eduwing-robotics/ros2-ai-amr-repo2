---
name: urhynix-sensor-verify-console
description: URHYNIX Unity ControlRoom 5트랙(배터리·카메라·LDR·PIR·시나리오) 종합 검증 콘솔 패턴 — Runtime static helper(`SensorVerifyConsole.cs`) + unityctl exec 호출. SensorRegistry/Robots 동적 순회로 새 센서 추가 시 dict 1줄로 자동 포함. State 캐시 + UI 라벨 동시 dump. 매 세션 시연 직전 표준 검증.
---

# urhynix-sensor-verify-console

> URHYNIX Unity ControlRoom의 **모든 트랙(배터리·카메라·LDR·PIR·…)이 ROS → State → UI까지 흐르는지** 한 번의 `unityctl exec` 호출로 종합 검증하는 영구 자산.

## 자산 위치

`unity/ControlRoom/Assets/Scripts/App/SensorVerifyConsole.cs` — Runtime static class (Editor 폴더 X — Play 모드 AppDomain에서 호출 가능해야 함).

## 호출 패턴

```bash
# 1) 종합 dump (State 캐시 + UI 라벨 + USS 클래스)
unityctl exec --project /path/to/project --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()' --json

# 2) 탭 강제 전환 (검증 전 필수)
unityctl exec --project ... --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.SwitchTo("tb3_2")' --json

# 3) TopicRegistry SSOT 매핑 확인
unityctl exec --project ... --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.DumpRos()' --json
```

## 출력 예시

```
selected=tb3_2
robots=2
  [state tb3_1 티원]  battery=27.6
  [state tb3_2 젠지]  battery=94.3 light=17.0 pir=1.0
--- UI labels (현재 탭 기준) ---
  battery  → battery-percent-label  = '94.3 %'         [...battery-percent]
  gas      → sensor-gas-value       = '--'             [...sensor-value]
  noise    → sensor-sound-value     = '--'             [...sensor-value]
  sound    → sensor-sound-value     = '--'             [...sensor-value]
  lux      → sensor-light-value     = '17% · 매우 어두움' [...sensor-value]
  light    → sensor-light-value     = '17% · 매우 어두움' [...sensor-value]
  pir      → sensor-pir-value       = '감지!'          [...sensor-danger]
  fire     → sensor-fire-value      = '정상'           [...sensor-ok]
```

## 코드 골격

```csharp
namespace URHYNIX.ControlRoom.App
{
    public static class SensorVerifyConsole
    {
        // sensorId → UXML 라벨 ID 매핑 (Phase 2 alias 우회).
        // 새 센서 추가 시 1줄만 추가. Phase 3에서 convention `sensor-{id}-value`로 통일하면 dict 제거 가능.
        static readonly Dictionary<string, string> SensorIdToLabelId = new()
        {
            { "battery", "battery-percent-label" },
            { "gas",     "sensor-gas-value" },
            { "noise",   "sensor-sound-value" },
            { "sound",   "sensor-sound-value" },  // 코드 alias
            { "lux",     "sensor-light-value" },
            { "light",   "sensor-light-value" },  // 코드 alias
            { "pir",     "sensor-pir-value" },
            { "fire",    "sensor-fire-value" },
        };

        public static string SwitchTo(string robotId) { ... }
        public static string Dump() { ... ControlRoomState.Robots/LastSensorValues 동적 순회 ... }
        public static string DumpRos() { ... TopicRegistry.Get*() 모두 ... }
    }
}
```

## 확장 패턴 (새 센서 추가)

| 단계 | 변경 |
|---|---|
| 1 | `default_sensors.json`에 센서 ID 추가 (예: `gas`) |
| 2 | `TopicRegistry.cs`에 토픽 상수 + lookup 추가 (`GetGas`) |
| 3 | `Assets/Scripts/Ros/GasSubscriber.cs` 신규 (1:1 복제) |
| 4 | `SensorCardListView.cs` switch에 `case "gas":` 분기 |
| 5 | `SensorVerifyConsole.SensorIdToLabelId`에 `{ "gas", "sensor-gas-value" }` 추가 (사실 이미 있음) |
| 6 | `DumpRos`에 `gas = TopicRegistry.GetGas(rid)` 1줄 추가 |

→ 검증 콘솔은 자동으로 새 센서 포함.

## 호출 환경 함정

| # | 함정 | 우회 |
|---|---|---|
| 1 | `unityctl exec` parser는 **`Type.Method(arg)` 또는 `Type.Member`만 지원**. `.Instance.Method()` 체인 불가. | helper static method 추가 (예: `SwitchTo("tb3_2")`로 Instance 호출 래핑) |
| 2 | float literal 전달 어려움 (`1.0f` 직접 안 됨) | `int` 인자로 받는 helper 또는 `f` 없이 시도 |
| 3 | Play 모드에서 새 코드 컴파일 후 **AppDomain reload 안 됨** → 새 메서드 보이지 않음 | Play stop → start 사이클 필요. 또는 `unityctl status` 확인 후 Play 재시작. |
| 4 | `unityctl exec` 출력에 Spectre.Console Markup 에러(Busy 버그) | `--json` 옵션 우회 |
| 5 | UI Toolkit `Q<Label>(id)`가 null 반환 — UXML 라벨 ID 변경됐거나 PanelSettings dispose | UXML grep으로 라벨 ID 재확인. `SensorVerifyConsole.Dump` 출력에 `(no label)` 표시. |
| 6 | `selected` 가 호출 직전과 다름 — SwitchTo 후 즉시 Dump해도 ControlRoomApp/RobotTabView가 reset 시도 가능 | SwitchTo + Dump를 같은 exec 호출 안에 또는 짧은 chain으로 |

## 검증 시나리오 표준

### 매 세션 시연 직전 5분 점검

```bash
# 1) Play 모드 진입 확인
unityctl status --project ... --json | grep -E "(isPlaying|ipcPipePresent)"
# 기대: isPlaying=true, ipcPipePresent=true

# 2) 종합 dump (탭=tb3_1 기본)
unityctl exec --project ... --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()' --json | head -10
# 검증:
# - robots=2 (default_robots.json 로드 OK)
# - state[tb3_1] battery=N (티원 트랙 OK)
# - state[tb3_2] battery=N light=N (젠지 트랙 OK)
# - UI battery 라벨 '94.3 %' 형태

# 3) 탭 전환 → 즉각 표시 확인
unityctl exec --project ... --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.SwitchTo("tb3_2")' --json
unityctl exec --project ... --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.Dump()' --json | head -10
# 검증: light/pir 라벨이 tb3_2 값으로 즉시 표시 (캐시 redraw 패턴)

# 4) TopicRegistry SSOT 확인
unityctl exec --project ... --code 'URHYNIX.ControlRoom.App.SensorVerifyConsole.DumpRos()' --json
# 검증: 모든 토픽이 null 아님
```

### PASS 기준

| 항목 | 기대 |
|---|---|
| `robots` | 2 (default_robots.json 로드 OK) |
| `state[tb3_1].battery` | 0 < N < 100 (티원 BatterySubscriber 살아있음) |
| `state[tb3_2].battery` | 0 < N < 100 (젠지) |
| `state[tb3_2].light` | 0~100 (LDR Subscriber 살아있음) |
| `state[tb3_2].pir` | 0 또는 1 (PIR Subscriber, latching X라 NaN 가능 — 손 흔들기 후 확인) |
| UI `battery-percent-label` | `"{N} %"` (탭 일치 시) |
| UI `sensor-light-value` | `"{N}% · 매우 어두움/어두움/보통/밝음/매우 밝음"` |
| UI `sensor-pir-value` | `"감지!"` 또는 `"감지 안 됨"` + USS sensor-danger/sensor-ok |

## 관련 자산

- 코드 — `unity/ControlRoom/Assets/Scripts/App/SensorVerifyConsole.cs`
- 의존 — `unity/ControlRoom/Assets/Scripts/App/{ControlRoomState,ControlRoomEvents}.cs`
- 의존 — `unity/ControlRoom/Assets/Scripts/Sensors/SensorRegistry.cs` (Phase 3 동적 순회 진입 시)
- 자매 스킬 — `urhynix-battery-bringup` (배터리 트랙)
- 자매 스킬 — `urhynix-sensor-bringup` (LDR/PIR/가스/화재 트랙)
- 자매 스킬 — `unity-ui-interaction-audit` (UI Contract Lock 직전 정적/동적 감사)
- 자매 스킬 — `evidence-review` (시연 PASS/FAIL 평가)
