# Instructor Report Deck

10분 컨펌용 발표 HTML. 더블클릭으로 바로 열림.

## 파일

| 경로 | 용도 |
|---|---|
| `index.html` | 단일 발표 덱 (7슬라이드, ~40KB) |
| `assets/turtlebot3.b64.js` | 터틀봇3 GLB base64 임베드 (2.2MB) |
| `assets/turtlebot3_burger.glb` | 원본 GLB (1.6MB, ROBOTIS 공식 STL → Blender 변환) |
| `SCRIPT.md` | 슬라이드별 발표 대본 + 예상 질문 |

## 발표 키 단축키

| 키 | 동작 |
|---|---|
| `←` `→` | 슬라이드 이동 |
| `1` ~ `7` | 슬라이드 점프 |
| `F` | 전체화면 토글 |
| `ESC` | 목차 오버레이 |
| `Home` / `End` | 처음 / 마지막 슬라이드 |

## 슬라이드 구성 (10분 = 슬라이드당 평균 85초)

| # | 시간 | 제목 | 핵심 |
|---|---|---|---|
| 1 | 0:00 ~ 0:50 | URHYNIX · 인트로 | 팀명 + 부팅 로그 + 팀원 4명 |
| 2 | 0:50 ~ 2:00 | 미션 한 그림 | 감지 → 출동 → 기록 |
| 3 | 2:00 ~ 3:30 | 시나리오 4종 | 야간 · 침입 · 소음 · 화재 |
| 4 | 3:30 ~ 5:30 | 하드웨어 3D | 터틀봇3 실제 모델 + 핫스팟 4개 |
| 5 | 5:30 ~ 7:00 | 시스템 구조 | M1~M5 + 데이터 흐름 |
| 6 | 7:00 ~ 8:30 | 현재 진행 | 터틀봇·시각화·유니티 통신 ✅ |
| 7 | 8:30 ~ 10:00 | 다음 단계 | 4단계 마일스톤 + 한줄정리 |

## 색 토큰 (보라 0, 청량 우선)

- bg: `#0A1726` deep navy
- cyan: `#5BD0E8` (메인 강조)
- sky: `#7CC4F2` (보조)
- mint: `#62E3A3` (완료/정상)
- ice: `#C8EEF8` (텍스트 하이라이트)
- warn: `#F5C26B` (대기/주의)

## 3D 모델 출처

ROBOTIS 공식 `turtlebot3` 리포지토리의 STL 4종을 Blender 5.1 CLI 헤드리스로 단일 GLB로 합쳤어요.

- `bases/burger_base.stl` — 본체
- `wheels/left_tire.stl`, `right_tire.stl` — 바퀴
- `sensors/lds.stl` — 라이다 (cyan 머티리얼 적용)

변환 스크립트: `/tmp/tb3_src/convert.py` (재현 시 동일 위치에 메시 다운로드 후 `blender --background --python convert.py`)

## 인터넷 연결 필요 여부

- **Three.js + 폰트는 CDN 로딩** → 발표장에서 인터넷이 안정적이지 않으면 미리 한 번 열어 캐시해두기 권장
- GLB 로드 실패 시 자동으로 cyan 원기둥 fallback (검은 화면은 안 나옴)
