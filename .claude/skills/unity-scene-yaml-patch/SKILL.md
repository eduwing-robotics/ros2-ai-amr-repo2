---
name: unity-scene-yaml-patch
description: Unity Editor 라이선스 핸드셰이크 실패 또는 unityctl IPC 잡힘 안 됨 상황에서 `.unity` YAML 파일을 직접 patch해서 GameObject + MonoBehaviour 컴포넌트를 박는 표준. 기존 GameObject 패턴 복제, fileID 충돌 회피, SceneRoots 갱신까지 자동. URHYNIX Phase 2.8에서 BatterySubscriber_G 패턴으로 LuxSubscriber_G/PirSubscriber_G 박는 데 성공한 자산.
---

# unity-scene-yaml-patch

> Unity Editor가 GUI로 뜨지 않거나(라이선스 핸드셰이크 실패) `unityctl`이 IPC를 못 잡을 때, `.unity` YAML 파일을 외부에서 직접 patch해서 Scene에 GameObject + Component를 박는 표준 흐름.

## 언제 트리거?

| 증상 | 우회 |
|---|---|
| `unityctl editor list --json` 모든 인스턴스 `isRunning=false` 보고 | 이 스킬로 외부 patch |
| Editor.log에 `[Licensing::Module] Error: Failed to handshake to channel` 반복 | 이 스킬로 외부 patch (라이선스 wait time 절약) |
| Unity Hub 없이 Scene 갱신 필요 | 이 스킬 |
| Scene .unity가 YAML 텍스트 → git diff 가능 (큰 변경은 commit 단위로 쪼개기 — `Assets/Scenes/CLAUDE.md` 규칙) | 이 스킬 |

⚠️ **선결 조건**: Unity Editor가 떠 있으면 외부 patch가 자동 저장으로 덮어쓰여질 위험. **반드시 Editor 종료 후 patch** (`ip-drift-resync` 함정 참고).

## 표준 흐름 (6단계)

### 1) Editor 종료 확인

```bash
pgrep -fl "Unity.app/Contents/MacOS/Unity" | head
# 있으면 kill <pid> 후 ps 비어있는지 확인
```

### 2) 기존 GameObject 패턴 분석

복제할 reference GameObject 위치 찾기:

```bash
grep -n "BatterySubscriber_G\|<reference name>" /path/to/Scene.unity | head
# → Line 344 (예) GameObject 정의 시작
```

해당 블록 20~30줄 Read해서 패턴 추출:
- `--- !u!1 &<fileID>` (GameObject)
- `--- !u!4 &<fileID>` (Transform)
- `--- !u!114 &<fileID>` (MonoBehaviour)
- `m_Script: {fileID: 11500000, guid: <SCRIPT_GUID>, type: 3}`

### 3) 새 Script의 GUID 확인

```bash
cat /path/to/Assets/Scripts/<X>/NewComponent.cs.meta | head -2
# fileFormatVersion: 2
# guid: <NEW_GUID>
```

### 4) fileID 충돌 회피

신규 fileID는 기존과 겹치지 않게 큰 양수 prefix 사용:

```bash
grep -c "7000000\|8888000\|9999000" /path/to/Scene.unity
# 0 matches → 7000000xxx 시리즈 안전
```

권장 prefix: **`7000000XXX`** (10자리, 기본 Unity가 안 박는 영역).

각 GameObject당 3개 fileID 필요 (GameObject + Transform + MonoBehaviour).
예: `7000000001` / `7000000002` / `7000000003` (Lux), `7000000011` / `7000000012` / `7000000013` (Pir)

### 5) Edit 도구로 SceneRoots 직전에 새 블록 삽입

```yaml
# SceneRoots 시작 라인 찾기 (보통 파일 끝 부근):
--- !u!1660057539 &9223372036854775807
SceneRoots:
```

이 라인 **직전**에 신규 GameObject 블록 추가. 동시에 `m_Roots:` 리스트 끝에 새 Transform fileID 추가.

### 6) Unity Editor 띄우고 자동 import 확인

```bash
open -a "/Applications/Unity/Hub/Editor/<VERSION>/Unity.app" --args -projectPath "/path/to/project"
# 부팅 후 unityctl로 Scene hierarchy 확인:
unityctl scene hierarchy --project ... --json | grep <new GameObject 이름>
```

## 블록 YAML 템플릿 (BatterySubscriber 패턴 1:1 복제)

```yaml
--- !u!1 &7000000001
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  serializedVersion: 6
  m_Component:
  - component: {fileID: 7000000002}  # Transform
  - component: {fileID: 7000000003}  # MonoBehaviour
  m_Layer: 0
  m_Name: <NEW_GAMEOBJECT_NAME>
  m_TagString: Untagged
  m_Icon: {fileID: 0}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: 1
--- !u!4 &7000000002
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_GameObject: {fileID: 7000000001}
  serializedVersion: 2
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
  m_ConstrainProportionsScale: 0
  m_Children: []
  m_Father: {fileID: 0}      # 0 = Scene 루트
  m_LocalEulerAnglesHint: {x: 0, y: 0, z: 0}
--- !u!114 &7000000003
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {fileID: 0}
  m_PrefabInstance: {fileID: 0}
  m_PrefabAsset: {fileID: 0}
  m_GameObject: {fileID: 7000000001}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: <SCRIPT_GUID_FROM_META>, type: 3}
  m_Name:
  m_EditorClassIdentifier: Assembly-CSharp::<FULL.NAMESPACE.ClassName>
  # Inspector serialized fields:
  field1: value1
  field2: "유니코드 한글 OK"
```

## SceneRoots 갱신

```yaml
--- !u!1660057539 &9223372036854775807
SceneRoots:
  m_ObjectHideFlags: 0
  m_Roots:
  - {fileID: <기존1>}
  - {fileID: <기존N>}
  - {fileID: 7000000002}   # 신규 GameObject Transform fileID 추가
  - {fileID: 7000000012}   # 추가 GameObject 있으면 더
```

## Edit 도구 사용 패턴

`Edit` 도구로 두 위치 갱신:

1. **`--- !u!1660057539 &9223372036854775807`** 라인을 찾아 그 앞에 신규 블록 삽입
2. **`m_Roots:`** 리스트 마지막에 신규 Transform fileID 추가

Read + Edit 으로 정확한 indent 보존.

## 함정표

| # | 함정 | 우회 |
|---|---|---|
| 1 | Unity Editor가 떠 있는 상태에서 외부 patch → 자동 저장으로 덮어쓰임 | 반드시 `kill <PID>` 후 patch (ip-drift-resync와 동일 함정) |
| 2 | fileID 충돌 — 기본 Unity는 ~1.x10^9 영역 사용 | `7000000XXX` 등 큰 양수 prefix 사용. grep -c로 사전 확인. |
| 3 | `m_EditorClassIdentifier` 누락 → Unity가 컴포넌트 인식 못 함 | 정확한 `Assembly-CSharp::<FULL.NAMESPACE.ClassName>` 박기. 기존 Component에서 복사. |
| 4 | YAML indent 오류 (Tab vs Space) — Unity yaml은 2-space indent | Read 결과 그대로 copy. 절대 Tab 박지 말 것. |
| 5 | `m_Father: {fileID: 0}` 가 루트 의미. 부모 계층 박으려면 부모 Transform fileID. | 루트 박는 게 가장 단순 (대부분 시연 컴포넌트). |
| 6 | SceneRoots m_Roots에 추가 안 함 → Hierarchy 보이지 않음 (단 컴포넌트는 작동) | 반드시 SceneRoots 갱신. |
| 7 | 한글 displayLabel 직접 박아도 OK — Unity가 UTF-8 처리. `"\uXXXX"` escape도 가능 | 가독성 위해 한글 직접 박기 권장. |
| 8 | Script `.meta` 파일이 없으면 GUID 모름 — 새 .cs 파일은 Unity import 후 .meta 생성됨 | Unity Editor 한 번 띄워서 .meta 생성 후 patch. 또는 `cat <file>.cs.meta`로 GUID 확인. |

## 검증

```bash
# 1) YAML 문법 OK인지 (정상 import되는지)
python3 -c "import yaml; yaml.safe_load_all(open('<Scene.unity>'))" 2>&1 | tail

# 2) Editor 띄우고 컴파일/import 에러 없는지
open -a Unity.app --args -projectPath ...
until unityctl status --project ... --json 2>/dev/null | grep -q '"isCompiling": false'; do sleep 2; done
unityctl console get-count --project ... --json
# 기대: errors=0

# 3) Hierarchy 확인
unityctl scene hierarchy --project ... --json | grep <NewGameObject>

# 4) Inspector 필드 확인 (Play 모드)
unityctl exec --project ... --code '<Component>.<staticVerify>()'
```

## URHYNIX 사례 (2026-06-09)

- **Trigger**: Unity 라이선스 핸드셰이크 실패 (`[Licensing::Module] Error`) → Editor GUI 부팅 못 함 + unityctl `isRunning=false`
- **작업**: `LuxSubscriber_G` + `PirSubscriber_G` 2개 GameObject 직접 박음
- **참고 패턴**: `BatterySubscriber_G` (Line 344)
- **사용 fileID**: 7000000001~003 (Lux), 7000000011~013 (Pir)
- **결과**: 다음 Editor 띄울 때 자동 import 성공, Subscribe → 메시지 수신 PASS

## 관련 자산

- 자매 스킬 — `ip-drift-resync` (Editor 종료 후 외부 patch 패턴 공유)
- 자매 스킬 — `urhynix-sensor-bringup` (이 스킬로 Scene 박는 컴포넌트)
- 자매 스킬 — `urhynix-battery-bringup` (기존 BatterySubscriber_G 패턴 source)
- 자매 스킬 — `unity-ui-interaction-audit` (Scene patch 후 검증 단계 공유)
