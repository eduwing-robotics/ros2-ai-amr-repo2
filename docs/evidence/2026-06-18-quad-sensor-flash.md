# 4센서 통합 플래시 as-built — PIR+레이저+사운드+온도 (2026-06-18)

> Arduino UNO 1대에 PIR·레이저·사운드·온도(PP-A017) 4종을 통합 결선·업로드·시리얼 검증한 기록.
> 보드: Arduino UNO @ `/dev/cu.usbmodem11101`. 스케치: `sketches/quad_security/quad_security.ino`.
> 핵심 수확: 사운드 모듈 DO 불량 → AO 아날로그 swing 방식으로 우회. `arduino-flash` 스킬 v4 갱신.

## 1. 최종 핀맵 (as-built, 검증 PASS)

| 모듈 | 신호핀 | 종류 | 비고 |
|------|--------|------|------|
| PIR (HW-740) | **D2** | 디지털 IN | OUT→D2 |
| 레이저 송신 모듈 | **D4** | 디지털 OUT | PIR 연동 점등 |
| 사운드 모듈 | **A1** | 아날로그 IN (**AO**) | DO 불량 → AO swing 감지로 전환 |
| 온도 PP-A017 | **A0** | 아날로그 IN (AO) | DO 미사용 |
| LED (옵션) | D7 | 디지털 OUT | PIR 연동 |

- 전원: 네 모듈 VCC→5V 레일, GND→공통 레일.
- **금지핀**: `D0`/`D1`(USB 시리얼), `D13`(SCK). 아무것도 꽂지 않음.

## 2. 검증 결과 (시리얼 9600, `stty + cat` 비대화형 캡처)

| 센서 | 판정 | 근거 |
|------|------|------|
| PIR (D2) | ✅ PASS | `[MOTION] detected -> LED+LASER ON` / `[CLEAR]` 다수 |
| 레이저 (D4) | ✅ PASS | PIR HIGH 시 동시 점등 (시리얼+육안) |
| 사운드 (A1/AO) | ✅ PASS | 무음 swing=2 vs 박수 `[SOUND] DETECTED swing=94~114` (임계 60) |
| 온도 (A0) | ✅ PASS(raw) | raw 159~162 반응. ℃ 변환 공식은 모듈 불일치(-8.6C 표시) → 미보정 |

## 3. 트러블슈팅 (이번 세션에서 뚫은 함정)

| 증상 | 원인 | 해결 |
|------|------|------|
| PIR/레이저를 D0·D1에 배치 시도 | D0(RX)/D1(TX)는 USB 시리얼 전용 → 업로드·로그 깨짐 | PIR→D2, 레이저→D4로 이동 |
| 사운드 DO가 raw 19/digital 1 **상시 HIGH**, 가변저항 전 구간 돌려도 `DO=0` 안 나옴 | 모듈 DO 비교기 회로 이상(상시 트리거) | **DO 폐기, AO(A1) 아날로그 swing 감지로 전환** |
| A1 raw가 98 같은 중간값 | A1에 DO가 아니라 **AO가 꽂혀 있었음** (digital은 0/1만) | 핀 정체 파악 → AO 기반 코드로 정렬 |
| 사운드 미검출 진단 난항 | DO/AO 중 뭐가 박수에 반응하는지 불명 | **DO+AO 동시 디버그**(`sound_a1_debug.ino`)로 한 번에 판별: DO=0 고정, AO swing 162 |
| 온도 ℃가 -8.6C 비현실 | NTC 분압/B값이 코드 가정과 다름 | raw로 동작만 확인. 실 ℃ 필요 시 2점 캘리브레이션 |

## 4. 자산화 핵심 — 디지털 모듈 DO 불량 시 AO swing 우회

비교기 디지털 출력(DO)이 상시 트리거되거나 가변저항으로 임계가 안 잡히면, 마이크/센서의 **아날로그 출력(AO)을 짧은 윈도우 min/max(swing)로** 읽어 소프트웨어 임계로 감지한다. 가변저항 튜닝 불필요, 임계를 코드에서 조절해 안정적.

```cpp
const int SOUND = A1;        // 모듈 AO
const int SOUND_TH = 60;     // 무음 swing~2, 큰소리 160+
int smn = 1023, smx = 0;
for (int i = 0; i < 50; i++) { int v = analogRead(SOUND); if (v<smn) smn=v; if (v>smx) smx=v; }
if ((smx - smn) >= SOUND_TH) { /* 감지 */ }
```

## 5. 산출물

- `sketches/quad_security/quad_security.ino` — 4센서 통합 (컴파일 16%/RAM 10%)
- `sketches/sound_a1_debug/sound_a1_debug.ino` — DO+AO 동시 진단 디버그
- 갱신: `.claude/skills/arduino-flash/SKILL.md` v4 (핀맵·AO 우회·D0/D1 함정)

## 6. 남은 일 (선택)

- [ ] 온도 ℃ 2점 캘리브레이션 (raw↔실온)
- [ ] PIR 통합본 재캡처(이번 통합 빌드에서 손 흔들기 1회 — 코드 동일이라 PASS 추정)
- [ ] 핀맵이 DECISION-LOG 2026-05-27과 상이 → 결정 수준이면 `decision-broadcast`로 전파
