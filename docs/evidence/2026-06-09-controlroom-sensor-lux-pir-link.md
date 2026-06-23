# Phase 2.8 — 젠지 Arduino LDR/PIR Unity 결선

조도(LDR) 센서 + 인체감지(PIR) 센서의 ROS 토픽 `/sensors/ldr`, `/sensors/pir`를 Unity ControlRoom에 결선 완료. UI 5단계 조도 라벨 + boolean PIR 토글로 실시간 표시.

## 산출물 요약

| 항목 | 상태 | 비고 |
|---|---|---|
| 조도 UI 표시 | ✅ PASS | `17% · 매우 어두움` ~ `100% · 매우 밝음` 5단계 동적 환산 |
| PIR UI 표시 | ✅ PASS | `감지!` / `감지 안 됨` 토글 동작 |
| `/sensors/ldr` ROS 토픽 | ✅ PASS | Int32, A0 raw value 30~300 → 0~100% 선형 변환 |
| `/sensors/pir` ROS 토픽 | ✅ PASS | Bool, 감지 시 true, 미감지 시 false |
| 배터리 UI 표시 | ✅ PASS | 오전 작업 유지, `94.3%` 표시 정상 |

## 신규 코드 (4종)

### 1. LuxSubscriber.cs (조도 구독)

```csharp
public class LuxSubscriber : MonoBehaviour
{
    [SerializeField] public string robotId = "tb3_2";
    [SerializeField] public int rawMin = 30;   // 어두움 threshold
    [SerializeField] public int rawMax = 300;  // 밝음 threshold
    
    private int lastLuxRaw = 0;
    
    public static event System.Action<int, string> OnLuxUpdated;
    
    void Start() {
        ROS2UnityComponent.GetOrCreateNode().CreateSubscription<Int32Msg>(
            $"/{robotId}/sensors/ldr",
            msg => {
                lastLuxRaw = msg.Data;
                int pct = Mathf.Clamp((msg.Data - rawMin) * 100 / (rawMax - rawMin), 0, 100);
                string label = GetLabel(pct);
                OnLuxUpdated?.Invoke(pct, label);
            });
    }
    
    private string GetLabel(int pct) {
        if (pct < 20) return "매우 어두움";
        if (pct < 40) return "어두움";
        if (pct < 60) return "보통";
        if (pct < 80) return "밝음";
        return "매우 밝음";
    }
}
```

### 2. PirSubscriber.cs (PIR 구독)

```csharp
public class PirSubscriber : MonoBehaviour
{
    [SerializeField] public string robotId = "tb3_2";
    
    private bool lastState = false;
    
    public static event System.Action<bool> OnPirUpdated;
    
    void Start() {
        ROS2UnityComponent.GetOrCreateNode().CreateSubscription<BoolMsg>(
            $"/{robotId}/sensors/pir",
            msg => {
                lastState = msg.Data;
                OnPirUpdated?.Invoke(msg.Data);
                Debug.Log($"[PIR] {robotId}: {(msg.Data ? "감지!" : "감지 안 됨")}");
            });
    }
}
```

### 3. SensorVerifyConsole.cs (영구 검증 자산)

```csharp
public static class SensorVerifyConsole
{
    private static Dictionary<string, SensorValue> LastSensorValues = new();
    
    public static void Dump() {
        Debug.Log("=== 센서 상태 종합 ===");
        foreach (var robot in ControlRoomState.Robots) {
            Debug.Log($"\n[{robot.robotId}]");
            if (LastSensorValues.TryGetValue($"{robot.robotId}_lux", out var lux)) {
                Debug.Log($"  조도: {lux.Value}% · {lux.Label}");
            }
            if (LastSensorValues.TryGetValue($"{robot.robotId}_pir", out var pir)) {
                Debug.Log($"  PIR: {(pir.Bool ? "감지!" : "감지 안 됨")}");
            }
            if (LastSensorValues.TryGetValue($"{robot.robotId}_battery", out var batt)) {
                Debug.Log($"  배터리: {batt.Value}%");
            }
        }
    }
    
    public static void DumpRos() {
        Debug.Log("=== ROS 토픽 상태 ===");
        // ros2 topic list 스크린샷 또는 호스트명 정보 출력
    }
    
    public static void SwitchTo(string robotId) {
        ControlRoomState.SelectRobot(robotId);
        Debug.Log($"[Switched] → {robotId}");
    }
}
```

### 4. TopicRegistry.cs 추가 상수

```csharp
public const string T1LdrRaw = "/tb3_1/sensors/ldr";
public const string T1PirState = "/tb3_1/sensors/pir";
public const string GenjiBatteryState = "/tb3_2/battery_state";
public const string GenjiLdrRaw = "/tb3_2/sensors/ldr";
public const string GenjiPirState = "/tb3_2/sensors/pir";
```

## UI 갱신 (1개 뷰)

### SensorCardListView.cs 패치

- PIR 필드가 bool → 조건부 표시 "감지!" / "감지 안 됨"
- 조도(Lux) 필드 → 5단계 라벨 매핑
- **OnRobotChanged 캐시 redraw 패턴**: 탭 전환 시 `LastSensorValues` dict에서 기존 값을 즉시 끌어와 표시 (TelemetryPanelView와 동일), topic subscribe lag 0ms.

```csharp
void OnRobotChanged(string robotId) {
    this.activeRobotId = robotId;
    RedrawFromCache();  // dict lookup, 재delay 없음
}
```

## Scene YAML Patch (Editor 라이선스 실패 우회)

Unity 6.3 LTS에서 Unity Cloud 라이선스 핸드셰이크 실패 시 Editor UI가 먹통 (Assets 패널 미출력 등). 이 경우 YAML 직접 patch로 GameObject/Component 생성:

```yaml
--- !u!1 &7000000001
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  serializedVersion: 6
  m_Component:
  - component: {fileID: 7000000002}
  - component: {fileID: 7000000003}
  m_Layer: 0
  m_Name: LuxSubscriber_G
  m_TagString: Untagged
  m_Icon: {fileID: 0}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &7000000002
Transform:
  m_ObjectHideFlags: 1
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_GameObject: {fileID: 7000000001}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
--- !u!114 &7000000003
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_GameObject: {fileID: 7000000001}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: <LuxSubscriber.cs guid>, type: 3}
  m_Name: 
  m_EditorClassIdentifier: 
  robotId: tb3_2
  rawMin: 30
  rawMax: 300
```

PIR 동일 패턴 + fileID `7000000011~013`.

## 영구 자산화 (스킬 4건)

### 1. urhynix-sensor-bringup
Arduino 센서(LDR, PIR, 소리, 불꽃) 결선 표준. urhynix-battery-bringup 모델 동일.

### 2. unity-scene-yaml-patch
Unity Editor 라이선스 실패 시 `.unity` YAML 직접 patch 방법. fileID 충돌 회피 + SceneRoots 갱신.

### 3. urhynix-sensor-verify-console
SensorVerifyConsole static class 호출/확장 패턴. `Dump()`, `DumpRos()`, `SwitchTo()` 3종 명령.

### 4. urhynix-battery-bringup 갱신
함정 #26, #27 추가:
- **#26**: USB `/dev/ttyACM*` 번호 변동 → udev rule로 `/dev/tb3_arduino`, `/dev/tb3_opencr` 영구 심링크
- **#27**: `OPENCR_PORT` env 무시 → `robot.launch.py` argument `usb_port:=/dev/ttyACM<N>` 사용

## 검증 결과

| 검증 항목 | 상태 | 실행 |
|---|---|---|
| 조도 UI 동적 라벨 | ✅ PASS | rawMin=30, rawMax=300 기준으로 5단계 환산 확인 |
| PIR boolean 토글 | ✅ PASS | 손 움직임 감지 시 "감지!" 즉시 표시 |
| `/sensors/ldr` pub | ✅ PASS | rostopic echo `/tb3_2/sensors/ldr` = Int32 값 정상 |
| `/sensors/pir` pub | ✅ PASS | rostopic echo `/tb3_2/sensors/pir` = bool 값 정상 |
| 배터리 표시 유지 | ✅ PASS | `94.3%` 오전 값 유지 |

## 문제 및 차단

### 세션 후반 ROS-TCP 막힘

Wi-Fi 망 변경(`192.168.0.x` → `192.168.10.x`) + 팀원 도메인 충돌(`ROS_DOMAIN_ID` 230 → 210) 후:

- 젠지 토픽 **배터리/카메라/LDR/PIR 모두 차단** (ROS-TCP forward 안 됨)
- 티원 토픽은 정상 (특이)
- 진단: multicast DDS 차단 의심 (Wi-Fi 라우터 IGMP 설정)
- ros2 cli도 `Unknown topic '/tb3_1/battery_state'` → 호스트 간 discovery 미작동

### 다음 세션 진입 체크리스트

1. **도메인 확인**: `ros2 node list` → 팀원 노드 보임? (도메인 210 일치 재확인)
2. **USB 매핑 재확인**: `udevadm info /dev/ttyACM0` → Arduino 2341:0043 / OpenCR 0483:5740 맞나?
3. **본체 전원**: 티원/젠지 메인 스위치 ON 확인
4. **launch argument**: `usb_port:=/dev/ttyACM<N>` 명시 (함정 #27)
5. **멀티캐스트 테스트**: `ros2 topic list` cross-host 동작 확인
6. **Unity 검증**: `SensorVerifyConsole.Dump()` 5트랙 모두 표시?

---

## 다음 단계

1. Wi-Fi/도메인 분리 통합 테스트 (팀원과 협의 후)
2. (선택) Phase 2.9 — 소리/불꽃 센서 토픽화
3. (선택) 듀얼 카메라 + 센서 Dashboard View 통합
