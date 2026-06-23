# Assets/UI/Parts/

> `ControlRoomMain.uxml`에 include되는 부분 UXML 조각들.

## 예정 파일

| 파일 | 영역 |
|---|---|
| `TopBar.uxml` | 상단바 (로봇 탭, 시간, 경보, 전원) |
| `LeftControlPanel.uxml` | 조작/순회/시나리오 버튼 |
| `MapPanel.uxml` | 2D/3D 맵 + 전환 버튼 |
| `CameraAndLogPanel.uxml` | 카메라 패널 + 이벤트 로그 |
| `RightStatusPanel.uxml` | 배터리, 센서, 기능 토글, 장치 정보 |

## 규칙

- 부분 UXML은 독립적으로 미리보기 가능해야 함 (Unity UI Builder로 단독 열어도 깨지면 안 됨).
- 외부 USS 참조는 `ControlRoomStyle.uss` 1개로 통일.
