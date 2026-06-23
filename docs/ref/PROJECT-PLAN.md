# Project Plan

> 디지털트윈경비로봇 — 7주 / 스크럼 1~7 관리자 에픽 + 기존 실행 카드
> 스크럼 에픽은 관리자 타임라인/보드/캘린더용이고, 기존 SCRUM-8~25 카드는 실행 상세용이다. 담당자는 공동(최대 3명)까지 허용한다.
> Jira 카드 제목과 설명은 2026-06-02 밤 기준 `스크럼 1`~`스크럼 7`의 쉬운 한글 표현으로 정리했다. 실제 Jira Sprint 객체 이름은 Backlog 화면에서 직접 수정한다.

## Intake Verdict

- verdict: `doc-sync`
- chosen skill: `task-intake-router`
- next skill: `doc-sync`, `evidence-review`
- tech ref: `docs/ref/tech/OPS-HARNESS.md`
- sub-agent needed: no
- reasoning: Claude/Codex 스킬 하네스와 ref 로딩 흐름을 기술별로 분리해 Unity/ROS2/Arduino/DB/카메라/운영 작업마다 필요한 최소 ref만 빠르게 읽게 하는 문서 구조 개선 요청이다.

### Tech Ref Routing Update (2026-06-02)

- 변경 목적: `docs/ref` 전체를 매번 읽는 비용을 줄이고, 요청 기술별 첫 문서가 명확해지게 한다.
- 새 인덱스: `docs/ref/TECH-INDEX.md`
- 새 기술 ref: `docs/ref/tech/UNITY.md`, `docs/ref/tech/ROS2-ROBOT.md`, `docs/ref/tech/ARDUINO-SENSORS.md`, `docs/ref/tech/DATABASE-SUPABASE.md`, `docs/ref/tech/VISION-CAMERA.md`, `docs/ref/tech/OPS-HARNESS.md`
- Unity 작업 기본 진입: `docs/ref/tech/UNITY.md` -> `unity/ControlRoom/README.md` -> `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md`
- 하네스 연결: `AGENTS.md`, `AGENT.md`, `CLAUDE.md`, `ai-context/START-HERE.md`, `.claude/skills/README.md`, `task-intake-router`

## 병렬 작업 원칙

> **한 모듈 안에서는 순차, 모듈 간에는 병렬.** 직렬 대기 시간을 최소화하기 위해 각자의 모듈은 인터페이스(`CONTRACT.md`)만 합의된 상태에서 동시에 진행한다.

### 직렬 병목 (먼저 끝내야 다음이 가능)

- **SCRUM-8 합의 (1일)** → 모든 작업의 전제 조건
- **SCRUM-16 트랙 환경** → SCRUM-10 SLAM/Nav2
- **SCRUM-13 센서+이벤트 발행** → SCRUM-12 출동 / SCRUM-21 AI 분류
- **SCRUM-14 DB 스키마** → SCRUM-23 저장 확장(좌표 로그·미디어·보호 대상) / SCRUM-15 KPI 쿼리
- **SCRUM-19 카메라 스트림** → SCRUM-25 라이브 / SCRUM-23 이미지 저장
- **SCRUM-16 박물관/미술관 waypoint** → SCRUM-21 액자형 중요물품 인식 / SCRUM-24 발표 컷

### 주차 × 모듈 병렬 매트릭스 (7주)

| 주차 | M1 백엔드/AI | M2 아두이노 메인 | M3 Unity | M4 센서 | M5 터틀봇 | 공통 |
|---|---|---|---|---|---|---|
| **W1** | SCRUM-14 스키마 초안 | 키트 점검·핀 배선 도면 | SCRUM-9 UI 초안 | 회로 도면 작성 | — | SCRUM-8 합의(1일), SCRUM-16 트랙 |
| **W2** | (SCRUM-14 계속) + `protected_assets` 예정 스키마 초안 | 적층 부품 발주 (스페이서·모듈) | (SCRUM-9 계속) | 센서 도착·동작 확인 | SCRUM-10 tb3_1 SLAM | 박물관/미술관 waypoint 초안 |
| **W3** | pose log 설계 | SCRUM-13 브릿지 노드 | SCRUM-11 pose+마커 | SCRUM-13 회로/펌웨어 | SCRUM-20 timestamp sync | 액자형 사진 타깃 설치 |
| **W4** | media path 정책 | (SCRUM-13 계속) | SCRUM-22 야간모드 UI + LiDAR 강화 표시 | (SCRUM-13 계속) | SCRUM-19 Pi Camera | 보호 대상 카메라 확인 |
| **W5** | SCRUM-23 저장 확장(좌표·사진·영상·사운드) | — | SCRUM-25 라이브 스트림 | SCRUM-17 추가 센서 | SCRUM-12 tb3_2 출동 | — |
| **W6** | SCRUM-21 AI 분류 + 액자 인식 라벨 | — | (SCRUM-25 계속) | (SCRUM-17 계속) | (SCRUM-12 계속) | — |
| **W7** | SCRUM-15 지표 시연 | — | SCRUM-24 발표 영상 | — | — | SCRUM-18 시연 환경 |

### Jira 관리자 보기 (2026-06-02 밤 가독성 정리 반영)

| 주차 | Jira Epic | 기간 | 담당 | 상태 | 관리자 화면에서 보는 의미 |
|---|---|---|---|---|---|
| 스크럼 1 | SCRUM-39 | 2026-05-26 ~ 2026-06-01 | 김주영 | 완료 | 팀명, 사용자 요구사항, 프로젝트 주제 선정 완료 |
| 스크럼 2 | SCRUM-40 | 2026-06-02 ~ 2026-06-08 | 김선일 | 완료 | 기능 요구사항, Unity 화면 초안, 비전 자료조사 완료 |
| 스크럼 3 | SCRUM-41 | 2026-06-09 ~ 2026-06-15 | 임현찬 | 해야 할 일 | 로봇 주행과 센서 연결 |
| 스크럼 4 | SCRUM-42 | 2026-06-16 ~ 2026-06-22 | 김선일 | 해야 할 일 | Unity 관리자 화면 만들기 |
| 스크럼 5 | SCRUM-43 | 2026-06-23 ~ 2026-06-29 | 김주영 | 해야 할 일 | 데이터 저장과 출동 흐름 연결 |
| 스크럼 6 | SCRUM-44 | 2026-06-30 ~ 2026-07-06 | 김주영 | 해야 할 일 | AI 비전 테스트와 통합 리허설 |
| 스크럼 7 | SCRUM-45 | 2026-07-07 ~ 2026-07-13 | 박태진 | 해야 할 일 | 최종 발표 준비 |

스크럼 1/2 완료 산출물은 하위 카드로도 분리했다. 기존 완료 기록은 스크럼 1: SCRUM-46 팀명 정하기, SCRUM-47 사용자 요구사항 정리하기, SCRUM-48 프로젝트 주제 정하기. 스크럼 2: SCRUM-49 기능 요구사항 정리하기, SCRUM-50 Unity 화면 초안 만들기, SCRUM-51 비전 자료 조사하기.

사용자가 Jira 화면에서 직접 만든 실제 Sprint 1/2에는 Backlog에서 새 카드 `SCRUM-67`~`SCRUM-72`를 드래그해 넣는다. 이 6개 카드는 일부러 `해야 할 일` 상태로 두었다. 스프린트에 들어간 뒤 완료 컬럼으로 옮기면 된다.

관리자가 쉽게 보려면 Jira에서 필터 `project = SCRUM AND summary ~ "스크럼" ORDER BY duedate ASC`를 저장하고, 보드는 Epic 기준, 타임라인은 Epic+Due date 기준, 캘린더는 Due date 기준으로 표시한다. Sprint 1/2 수동 이동용 카드는 `key in (SCRUM-67, SCRUM-68, SCRUM-69, SCRUM-70, SCRUM-71, SCRUM-72)`로 바로 찾는다.

### S1 W1 Day-1 (2026-05-27 확정) — 즉시 시작 3팀

| 팀 | 인원 | 작업 | 관련 SCRUM | 오늘 끝 산출물 |
|---|---|---|---|---|
| **Pi+DB팀** | 김주영, 임현찬 | Pi Camera 스트림 확인 + DB 연결 테스트 (Supabase 또는 로컬 PG) | SCRUM-19, SCRUM-14 | `/tb3_1/camera/image_raw` 토픽 확인 영상 + `events` sample insert |
| **PIR+DB팀** | 박태진 | Arduino + PIR 센서값 → 시리얼 → DB insert까지 한 줄 통과 | SCRUM-13, SCRUM-14 | Arduino `.ino` + DB insert 로그 |
| **Unity 문서팀** | 김선일 | Unity 관제 UI 기능 정의 문서 (UI 명세) | SCRUM-9, SCRUM-22 | UI 기능 명세 1장 (운영 대시보드 / 이벤트 패널 / 카메라 패널 / 모드 토글) |

**Day-1 통합 검증 라인**: 박태진의 Arduino+PIR이 발행한 이벤트가 김주영·임현찬의 DB `events` 테이블에 한 줄 저장되면 Day-1 PASS.

### Unity 관제 UI v1 요구사항 (2026-06-01 회의록 기반, 정의/계획)

- 변경 목적: 2026-06-01 SCRUM 회의록(Confluence page `5111810`)의 UI 기능 정의를 로컬 SSOT에 반영한다.
- 상호작용/좌표:
  - 맵 우클릭: 좌표 생성/삭제, 맵 좌클릭: 화면 좌/우 스크롤.
  - 좌표 선택 시 속성 변경: 충전 위치/특정 좌표/이름 지정.
  - 좌표 설정 후 이동 경로·방향 편집, 순회 번호를 UI에 표시.
  - 모달에서 드래그앤드랍으로 순회 순서 조정.
- 차단 지역: 자유 변형 가능한 영역 스케치.
- 모드:
  - 수동 = teleop.
  - 자동 = 순회 시작(“하시겠습니까?” 확인 팝업).
  - 스캔 = 좌표마다 360° 1회전.
  - 가속(주행) = 속도 프리셋.
- 토글/표시:
  - 카메라 ON/OFF.
  - 로봇 상태: 배터리 + PIR·온도·소리·레이저 센서 [정본 v18]
  - 위험 상태 알람 팝업.
  - “화재 이미지 매칭 UI”는 제거하고 “온도 센서 상태” 우선 추가 [정본 v18: 조도→온도]

### 2대 로봇 역할 분리 (2026-06-01 회의록 기반, 계획/진행 중)

- 변경 목적: 2대 실기 운용 시 모듈 병렬을 막는 역할 충돌을 줄이기 위해, 로봇별 탑재를 고정한다.
- `tb3_1`(로봇 1, 별명 **티원**): 비전 중심 (RealSense `D435`). 호스트 `t1@192.168.0.250` (hostname `rb`).
- `tb3_2`(로봇 2, 별명 **젠지**): 센서/확인 중심 (Arduino 센서 4종 스택 + Pi Camera(IMX219)). 호스트 `urhynix-robot` (kim@192.168.0.82).
- 2026-06-02 14:30 회의 기준 `ROS_DOMAIN_ID=230`으로 통일하기로 했으나, 2026-06-15 210으로 수정 통일(팀 공유 도메인, cross-discovery PASS).
- Unity에서 두 로봇 카메라 화면 동시 송출은 검증 완료로 취급한다. 근거: Confluence `2026.06.02`, `image-20260602-031954.png`, `docs/evidence/2026-06-02-camera-ros2-topic-unity-batch-setup.md`.

### AI 객체 분류 스파이크 (2026-06-02 회의 기준)

- 변경 목적: 로봇 카메라 영상에서 빠르게 객체 분류가 되는지 확인한다.
- 학습 도구: Google Teachable Machine.
- 모델 형식: TensorFlow/Keras.
- 1차 학습 클래스: 빈공간, 박스, 마우스(검정/흰색), 손.
- 적용 Jira: `SCRUM-44`(스크럼 6 에픽), `SCRUM-61`(AI 비전 인식 기준), `SCRUM-62`(전체 리허설).
- 주의: 이 스파이크는 Keras 추론 경로 검증용이다. 5/29 기준 발표용 YOLO/OpenCV 큰 범위 클래스(로봇/사람/중요품/불)는 유지한다.

### T1 맞춤 YOLO 학습실 + 오탐 정제 루프 (2026-06-10 적용)

- 변경 목적: 박물관/미술관 중요 물품을 로컬에서 빠르게 촬영, 라벨링, 학습, 탐지, 정제까지 반복한다.
- 앱: `scripts/yolo_training/custom_yolo_studio.py`
- 주소: `http://127.0.0.1:8766/`
- 데이터셋: `datasets/custom_object`
- 학습 결과: `runs/custom_object/**/weights/best.pt`
- 기본 흐름:
  1. `best.pt 불러오기` 또는 Space/ROI 연사로 데이터 수집.
  2. ROI 자동연사는 SAM2/rembg/GrabCut으로 bbox를 좁히고, 매핑 실패 컷은 저장하지 않는다.
  3. `검수 시작`에서 `←/→`로 넘기며 잘못 잡힌 컷은 `D 삭제` 또는 Delete/Backspace로 제거한다.
  4. 배경이 물건으로 감지되면 `N 오탐 배경 저장`으로 빈 라벨 hard-negative 샘플을 저장한다.
  5. positive 샘플과 hard-negative 샘플을 함께 재학습한다.
- 운영 원칙:
  - `.pt` 파일은 직접 정제하지 않는다. 데이터셋을 정제하고 재학습한다.
  - 반복된 동일 bbox가 많으면 모델이 물건보다 위치/배경을 배운다.
  - 검증셋에는 물건 있는 사진뿐 아니라 배경-only negative 샘플도 포함한다.
  - 학습 직후 mAP만 보지 말고 실제 배경 오탐 테스트를 통과해야 한다.

### S1 W1 잔여 (Day-2 이후)

| 모듈 | 작업 | 담당 |
|---|---|---|
| SCRUM-8 합의 마무리 | 5 모듈 매트릭스 + Day-1 결과 공유 | 김주영 |
| SCRUM-16 실내 트랙 | 야간 광량 환경 + waypoint 측정 | 박태진·임현찬 |
| 부품 발주 | 소리·온도·레이저 센서 + 릴레이·워터펌프 [정본 v18] | 박태진 |
| OpenCR 5V 패드 도면 | 점퍼 배선 위치 실측 후 회로도 | 임현찬·김주영 |

## Sprint 1 — 단일 로봇 베이스라인 (2주)

목표: tb3_1 한 대로 순찰 주행과 Unity pose 표시까지 라인을 통하게 만든다. 모든 후속 작업의 토대.

| 작업 | Jira | 담당 | 모듈 |
|---|---|---|---|
| MVP 범위·역할 매트릭스·SSOT 합의 | SCRUM-8 | 김주영 · 김선일 | 공통 |
| Unity 박물관/미술관 모델 + 듀얼 로봇 표시 가능한 관제 UI 초안 | SCRUM-9 | 김선일 · 박태진 | M3 |
| tb3_1 SLAM/Nav2 기본 순찰 주행 | SCRUM-10 | 임현찬 · 김선일 | M5 |
| 실내 트랙·박물관/미술관 경비 구역·야간 모드 환경 세팅 | SCRUM-16 | 박태진 · 임현찬 | 공통 |
| DB 스키마 초안 (`events`, `dispatches`, `camera_captures`, `session_meta`) | SCRUM-14 | 김주영 · 김선일 | M1 |

## Sprint 2 — 센서 + 이벤트 1종 (2주)

목표: 아두이노 센서 1종으로 이벤트를 발행해 Unity 마커까지 띄운다. "감지→표시" 한 줄을 통과.

| 작업 | Jira | 담당 | 모듈 |
|---|---|---|---|
| 아두이노 센서 노드 1종(PIR 또는 조도) 연동 + `/security/event` 발행 | SCRUM-13 | 김주영 · 임현찬 · 박태진 | M4 |
| Pi Camera 설치·스트림 토픽 발행 | SCRUM-19 | 박태진 · 임현찬 | M3 / M5 |
| tb3_1 pose ↔ 센서 이벤트 timestamp 동기화 | SCRUM-20 | 임현찬 · 김선일 | M5 |
| Unity 로봇 위치/경로/이벤트 마커 표시 | SCRUM-11 | 김선일 · 박태진 | M3 |
| 야간 모드 / 이벤트 패널 / 운영 대시보드 UI | SCRUM-22 | 김선일 · 박태진 | M3 |

## Sprint 3 — DB + 2호기 출동 시뮬 (2주)

목표: 모든 이벤트가 DB에 저장되고, tb3_2가 (시뮬레이션 또는 실기) 출동해 카메라로 확인하는 흐름을 완성.

| 작업 | Jira | 담당 | 모듈 |
|---|---|---|---|
| tb3_2 출동 로직 (이벤트 수신 → Nav2 goal 발행) | SCRUM-12 | 임현찬 · 김선일 | M5 |
| 추가 센서(소리/불꽃) 회로 + 모의 입력 인터페이스 | SCRUM-17 | 김주영 · 임현찬 · 박태진 | M4 |
| 라벨링 + AI 오탐/실탐 분류 보조 모델 + 액자형 중요물품 인식 | SCRUM-21 | 김주영 · 김선일 | M1 |
| 이벤트·이미지·대응 시간·이동좌표·영상·사운드 저장 구조 확장 | SCRUM-23 | 김선일 · 김주영 | M1 |
| Pi Camera 라이브 스트리밍 → Unity 패널 | SCRUM-25 | 김선일 · 박태진 | M3 |

## Sprint 4 — 2대 실기 확장 + 발표 데모 (1주)

목표: 시나리오 4종을 시연하고 발표 지표 표를 만든다. 가능하면 2대 실기 동시 주행.

| 작업 | Jira | 담당 | 모듈 |
|---|---|---|---|
| 시나리오 4종(야간/PIR/소리/화재 모의) + 박물관/미술관 액자 보호 통합 시연 + 지표 표 | SCRUM-15 | 김주영 · 김선일 | M1 |
| 최종 시연 환경(2대 동시 구동, 백업 부품, 광량) 준비 | SCRUM-18 | 박태진 · 임현찬 | 공통 |
| 발표용 화면/영상/시나리오 컷 캡처 | SCRUM-24 | 박태진 · 김선일 | M3 |

## 추천 진행 순서

1. SSOT 합의 + Jira 재라벨링 (S1 시작 전 1~2일)
2. 박물관/미술관 실내 트랙·액자형 보호 대상 waypoint 고정
3. tb3_1 SLAM/Nav2 순찰 베이스라인
4. Unity pose + 듀얼 로봇 표시 준비
5. 센서 연결 방식 스파이크 (Arduino 보드→Raspberry Pi USB serial / OpenCR GPIO·ADC / Raspberry Pi GPIO·I2C·UART 비교)
6. 아두이노 센서 1종 + `/security/event` 발행
7. Unity 이벤트 마커 + 카메라 패널
8. DB 저장 (현재: events → dispatches → camera_captures, SCRUM-23 예정: pose_logs/media_artifacts/protected_assets)
9. tb3_2 출동 시뮬
10. 추가 센서 + AI 분류 + 액자형 중요물품 인식
11. 2대 실기 확장 + 시나리오 4종 시연 + 발표 지표

## Open Questions

- (모두 해결됨) 아두이노 센서 연결 방식은 2026-05-27 결정으로 **Arduino Uno R3 + 미니 브레드보드 → Raspberry Pi USB serial**로 확정. OpenCR GPIO/ADC 및 RPi GPIO 직접 연결 후보는 폐기. 상세는 `docs/status/DECISION-LOG.md` "센서 연결·적층 구조 확정" 항목 참조.

## 축소안 (일정 지연 시)

- S3 종료 시점에 v4 어렵다고 판단되면 **2대 실기 → 1대 실기 + 1대 Unity 시뮬레이션**으로 축소.
- 시나리오 4종 중 안정성 낮은 화재/소리 항목은 모의 입력만 시연, 발표에서 명시.
- 라벨링/AI 분류(SCRUM-21)는 발표 직전 1일에 단순 임계값 비교로 대체 가능.
