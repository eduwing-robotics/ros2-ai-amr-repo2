# Design Decisions — URHYNIX ControlRoom

> URHYNIX Unity ControlRoom UI/UX 디자인 방향과 채택/기록 보관.
> 본 문서는 디자인 토큰, 레퍼런스, 향후 UI 개선 우선순위를 담는다.

## 디자인 방향

- **컨셉**: 박물관/미술관 고품격 밝은 슬레이트 톤의 산업용 관제실(Control Room).
- **목표**: 맵 중심 레이아웃을 유지하면서 좌/우 사이드바의 정보 밀도를 높인다.
- **기준**: Foxglove Studio의 로봇 데이터 밀도 + Grafana/SCADA의 카드/뱃지/위젯 밀도를 참고한다.

## 채택한 결정

| 결정 | 이유 |
|---|---|
| 밝은 슬레이트 톤 유지 | 프로젝트 초기 컨셉과 일치, 야간/어두운 전시 환경에서도 가독성 우수 |
| 사이드바 폭 236px 고정 | 맵이 항상 주인공이 되도록 하고, 태블릿/노트북에서 예측 가능한 레이아웃 유지 |
| 디자인 토큰 SSOT (`ControlRoomTokens.uss` + `UiTokens.cs`) | USS와 C# 코드 간 색상/간격/폰트/크기 동기화, 하드코딩 제거 |
| PNG 아이콘/레퍼런스만 사용 | SVG는 Unity UI Toolkit에서 추가 처리 필요, PNG가 표준 |
| Left 사이드바에 역할카드 + 퀙액션 + Teleop D-pad | 제어 중심 기능을 한 눈에 모아 정보 밀도 향상 |

## 기각한 대안

| 대안 | 기각 이유 |
|---|---|
| 다크 모드 | 프로젝트 컨셉과 맞지 않고, 데모 시 밝은 환경에서 더 잘 보이는 밝은 톤 유지 |
| 사이드바 가변 폭 | UI Toolkit의 `@media` 제한으로 인해 복잡도 증가, 236px 고정이 안정적 |
| SVG 아이콘 | Unity import 설정 복잡, PNG 세트로 통일 |
| 3D URDF 먼저 도입 | Phase 6 예정, 현재는 2D 맵과 UI 밀도가 우선 |

## 디자인 토큰 요약

전체 토큰은 `unity/ControlRoom/Assets/UI/ControlRoomTokens.uss`와
`unity/ControlRoom/Assets/Scripts/Design/UiTokens.cs`를 참조.

| 카테고리 | 핵심 토큰 예시 |
|---|---|
| 색상 | `--color-bg-primary`, `--color-surface`, `--color-accent`, `--color-status-danger` |
| 도메인 색상 | `--color-camera-bg`, `--color-map-placeholder`, `--color-map-3d-bg` |
| 역할 뱃지 색상 | `--color-role-vision-fg/bg/icon-bg`, `--color-role-sensor-fg/bg/icon-bg` |
| 폰트 | `--font-size-xs:10px` ~ `--font-size-xl:22px` |
| 레이아웃 | `--panel-width:236px`, `--bottom-panel-height:260px`, `--topbar-height:48px` |
| 아이콘/마커 | `--icon-dot-sm:8px`, `--icon-waypoint:24px`, `--icon-robot:28px` |
| 간격 | `--space-xxs:2px` ~ `--space-xl:24px` |
| Radius | `--radius-sm:4px`, `--radius-md:8px`, `--radius-full:999px` |

## 레퍼런스 이미지

| 파일 | 출처 | 용도 |
|---|---|---|
| `unity/ControlRoom/Assets/Art/References/foxglove-reference.png` | Foxglove 공식 홈페이지 | 로봇 데이터 밀도, 패널 분할, 토픽 시각화 참고 |
| `unity/ControlRoom/Assets/Art/References/grafana-reference.png` | Grafana Labs 공식 홈페이지 | 모니터링 위젯, KPI 카드, 알람 뱃지 스타일 참고 |

> ⚠️ 위 이미지는 외부 사이트의 공개 프로모션 자료이며, 상업적 재배포 조건을 확인 후 사용해야 한다.
> 본 프로젝트에서는 내참고 용도로만 보관한다.

## 와이어프레임 텍스트 스케치

### 최종 목표 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  URHYNIX 관제실   [티원] [젠지]          14:32:00  경보 0  전원  │
├──────────┬──────────────────────────────────────┬───────────┤
│ 운영/상황 │                                      │  상태/센서  │
│ [역할카드]│           2D/3D 맵                   │  배터리     │
│ [퀙액션] │                                      │  토픽 Hz   │
│ [Teleop] │                                      │  보호대상   │
│ [특수모드]│                                      │           │
├──────────┴──────────────────────────────────────┴───────────┤
│  칩허라 / 로그                                              │
└─────────────────────────────────────────────────────────────┘
```

### Left 사이드바 세부

- **운영 탭**
  - 모드: 자동 / 수동
  - 순회: 시작 / 정지
  - 역할 카드: 로봇 아이콘 + 이름 + 연결 상태 + 역할 뱃지
  - 퀙액션: 즉시정지 / 충전소복귀 / ArUco주차 / 주행잠금
  - Teleop D-pad: ▲ ▼ ◀ ▶ + 정지 (수동 모드 시 활성)
  - 특수 모드: 360° / 가속 / SLAM

## 다음 UI 개선 우선순위

1. Right 사이드바 밀도 업: 토픽 Hz 모니터 + 센서 스파크라인 + 최근 이벤트 피드
2. 출동(Dispatch) 상태 패널: `/security/dispatch` → UI 카드
3. 차단 구역 스케치: 맵 위에서 자유 영역 그리기
4. 3D URDF 맵: Phase 6 예정
5. 보호대상/미디어/순찰경로 DB 연동
