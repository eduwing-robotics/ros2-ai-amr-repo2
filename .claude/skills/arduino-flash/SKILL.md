---
name: arduino-flash
description: Arduino 스케치를 GUI IDE 없이 arduino-cli로 컴파일·업로드·시리얼 검증까지 한 번에 돌리는 자동화 스킬. URHYNIX 센서/액추에이터 결선 플래시 파이프라인. v4에서 4센서 통합(PIR+레이저+사운드+온도) 핀맵 + 사운드 DO 불량 시 AO 아날로그 swing 우회 + D0/D1 금지핀 함정 추가.
user_invocable: true
tags: [arduino, embedded, sensor, automation, urhynix-m2-m4]
trigger: "Arduino UNO에 스케치를 빠르게 굽고 시리얼로 동작 확인해야 할 때"
version: 4
---

# Arduino Flash

GUI 아두이노 IDE를 거치지 않고 터미널 한 줄로 **스케치 작성 → 컴파일 → 업로드 → 시리얼 검증**까지 끝내는 표준 파이프라인.

URHYNIX의 Day-1 (PIR) 작업에서 검증된 흐름이며, 남은 센서 3종(조도/소리/불꽃)에도 동일 패턴으로 재사용한다.

## Use When

- Arduino 스케치를 짠 뒤 IDE 켜기 귀찮을 때
- 동일 스케치를 여러 번 수정·재업로드 반복할 때
- AI 에이전트(나)에게 컴파일·업로드를 위임하고 싶을 때
- 센서 변경/핀 변경 후 회귀 검증이 필요할 때
- CI나 스크립트에서 펌웨어를 자동 굽고 싶을 때

## URHYNIX 핀 매핑 (DECISION-LOG 2026-05-27 확정, SSOT)

| 핀 | 용도 | 신호 |
|---|---|---|
| D2 | LED (PIR 연동) | 디지털 |
| D3 | 소리 (KY-038 D-out) | 디지털 |
| D4 | 불꽃 D-out | 디지털 |
| D5 | 모의 입력 버튼 (화재) | 디지털 |
| D8 | 레이저 송신 모듈 (PIR 연동) | 디지털 |
| ~~A0~~ | ~~조도 (LDR + 10kΩ 분압)~~ | 제거됨 (정본 v18, 2026-06-16) |

> ⚠️ LED·부저 등 액추에이터는 위 핀을 피해서 배치한다. (예: D6, D8, D11)
> 시리얼 포맷: `EVT,<type>,<severity>,<unix_ts>\n` (예: `EVT,pir,3,1716800000\n`)
> 디버그/검증 로그 포맷(라즈베리파이 인서트 전 단계):
> - PIR: `[MOTION] detected -> LED ON` / `[CLEAR ] no motion -> LED OFF`
> - LDR: `[LDR] A0=<0-1023>  (dark|dim|bright|very bright)` — 2초 주기
> - 소리/불꽃: `[SOUND] D3=<H|L>` / `[FLAME] D4=<H|L>` (검증용, 본 운영은 `EVT,...`로 전환)

### 4센서 통합 as-built (2026-06-18, `sketches/quad_security`) — PASS

| 모듈 | 핀 | 신호 | 비고 |
|---|---|---|---|
| PIR | **D2** | 디지털 IN | OUT→D2 |
| 레이저 송신 | **D4** | 디지털 OUT | PIR 연동 점등 |
| 사운드 | **A1** | 아날로그 IN(**AO**) | DO 불량 → AO swing 감지로 전환 (아래 Fallback) |
| 온도 PP-A017 | **A0** | 아날로그 IN(AO) | DO 미사용 |
| LED(옵션) | D7 | 디지털 OUT | PIR 연동 |

> ⛔ **금지핀**: `D0`(RX)/`D1`(TX)는 USB 시리얼 전용 → 센서 꽂으면 업로드·로그 깨짐. `D13`(SCK)는 부트로더 동기화 방해. 셋 다 비워둔다.
> 사운드 검증 로그(AO 방식): `[SOUND] DETECTED (swing=<n>)` / `[SOUND] quiet (swing=<n>)` — 무음 swing~2, 큰소리 60+ 임계.
> 근거: `docs/evidence/2026-06-18-quad-sensor-flash.md`.

## LDR 분압회로 배선 (과거 참조용 — ⚠️ 정본 v18에서 조도 제거)

```
+5V 레일 ──┬── PIR.VCC
           └── LDR 한쪽 다리
                      │
                      ├──→ Arduino A0
                      │
                  10kΩ
                      │
GND 레일 ──┬── 10kΩ 반대쪽
           └── PIR.GND
```

- LDR과 10kΩ은 무극성. 반대로 꽂아도 동작 (다만 값이 반전되므로 `dark/bright` 라벨 임계값을 뒤집어야 함).
- 정상 범위 (실내 기준): 어둠 30 이하, 보통 실내 150~250, 밝은 형광등 500~700, 손전등 직사 900+.
- 코드 패턴:
  ```cpp
  const int LDR = A0;
  const unsigned long LDR_INTERVAL = 2000;
  unsigned long lastLdrMs = 0;
  void loop() {
    if (millis() - lastLdrMs >= LDR_INTERVAL) {
      int lux = analogRead(LDR);
      Serial.print(F("[LDR] A0=")); Serial.print(lux);
      if (lux < 200)      Serial.println(F("  (dark)"));
      else if (lux < 600) Serial.println(F("  (dim)"));
      else if (lux < 900) Serial.println(F("  (bright)"));
      else                Serial.println(F("  (very bright)"));
      lastLdrMs = millis();
    }
  }
  ```

## Prerequisites (1회만)

```bash
# 1. arduino-cli 설치
brew install arduino-cli

# 2. 설정 초기화 + 인덱스 업데이트
arduino-cli config init
arduino-cli core update-index

# 3. UNO/Nano 등 AVR 코어 설치
arduino-cli core install arduino:avr
```

## Steps (반복 사용)

### Step 1: 스케치 폴더 준비

```
sketches/
  └─ <sensor_name>/
      └─ <sensor_name>.ino   ← 폴더와 파일명이 같아야 함
```

URHYNIX 기준 경로: `/Users/family/jason/URHYNIX/sketches/<sensor_name>/`

### Step 2: 보드/포트 자동 탐지

```bash
arduino-cli board list
```

`Board Name`이 `Arduino UNO`로 잡힌 행의 `포트` 컬럼을 사용한다.
macOS 기준 일반적으로 `/dev/cu.usbmodemNNNN` 형태.

### Step 3: 컴파일

```bash
arduino-cli compile --fqbn arduino:avr:uno <sketch_dir>
```

성공 시 사용 메모리 사용량 줄이 나온다. RAM이 80% 넘으면 `F("...")` 매크로로 문자열을 플래시로 이동.

### Step 4: 업로드

```bash
arduino-cli upload -p <port> --fqbn arduino:avr:uno <sketch_dir>
```

업로드 중에는 시리얼 모니터를 닫아둔다. (포트 점유 충돌 방지)

### Step 5: 시리얼 검증 (AI 비대화형)

`arduino-cli monitor`는 TTY가 없으면 즉시 종료된다. AI/스크립트에서는 raw `cat` 우회로 읽는다:

```bash
stty -f <port> 9600 cs8 -cstopb -parenb -echo raw
(cat <port> & CAT_PID=$!; sleep 30; kill $CAT_PID 2>/dev/null) | head -60
```

사람이 직접 볼 때는 그냥:

```bash
arduino-cli monitor -p <port> -c baudrate=9600
```

### Step 6: 표준 검증 출력 확인

워밍업 후 다음 패턴이 보이면 PASS:

```
=== PIR + LASER Test ===
Warming up sensor.....................
Ready. ...
[MOTION] detected -> LED+LASER ON   ← 또는 EVT,<type>,...
[CLEAR ] no motion -> LED+LASER OFF
```

## One-Liner (수정 → 재업로드)

```bash
SKETCH=~/jason/URHYNIX/sketches/pir_laser
PORT=/dev/cu.usbmodem11101
arduino-cli compile --fqbn arduino:avr:uno $SKETCH \
  && arduino-cli upload -p $PORT --fqbn arduino:avr:uno $SKETCH
```

## Outputs

- 컴파일된 `.hex` (보드에 흐름)
- 시리얼 검증 로그 (최소 30초 캡처)
- (선택) `docs/evidence/YYYY-MM-DD-<sensor>-flash.md` 증거 기록

## Verify

- [ ] `arduino-cli board list`에서 보드가 `Arduino UNO`로 인식되는가
- [ ] 컴파일 사용량이 프로그램 80% / RAM 80% 이하인가
- [ ] 업로드 후 `Verifying ... done` 또는 무에러 종료
- [ ] 시리얼 30초 캡처에 표준 검증 출력이 1회 이상 보이는가
- [ ] 핀 매핑이 URHYNIX SSOT(DECISION-LOG)와 일치하는가
- [ ] (레이저 사용 시) 시리얼 로그에 `LED+LASER ON/OFF` 동시 표시가 보이는가

## Failure / Fallback

| 증상 | 원인 | 우회 |
|---|---|---|
| 포트 비어있음 (`/dev/cu.*` 0건) | USB 케이블 불량(충전전용) 또는 보드 미연결 | 데이터 케이블 교체, 다른 USB 포트 |
| `avrdude: stk500_recv()` | 포트 충돌 / 보드 다른 종류 | 시리얼 모니터 종료, FQBN 재확인 |
| `arduino-cli monitor` 즉시 종료 | 비-TTY 환경 | `stty + cat` 우회 사용 |
| 컴파일은 되는데 동작 X | 핀 매핑 어긋남 / LED 역방향 | URHYNIX SSOT 핀 매핑 표 재확인 |
| RAM 90% 이상 | 문자열이 SRAM 차지 | `Serial.println(F("..."))` 매크로 적용 |
| 워밍업 중 LED 멋대로 깜빡 | PIR 정상 행동 (20~60초) | `WARMUP_MS` 상수 충분히 (≥20000) |
| LDR 값이 0 또는 1023 고정 | 10kΩ 누락 / 한 다리 떠 있음 | 분압회로 점검: `5V — LDR — A0 노드 — 10kΩ — GND` |
| LDR 값이 어두울 때 더 큼 (반전) | LDR과 10kΩ 위치 바뀜 | 회로 위·아래 스왑 또는 코드 라벨 임계값 반전 |
| 업로드 `not in sync: resp=0x00` / `programmer not responding` | 액추에이터(레이저 등)를 D13(SCK)에 연결 → 부트로더 동기화 방해 | 데이터핀 D13→D8 이동(또는 업로드 중 분리), 자동리셋 안 되면 USB 재꽂기/RESET 버튼 |
| 업로드/시리얼 둘 다 깨짐, 센서가 D0/D1에 연결됨 | D0(RX)/D1(TX)는 USB 시리얼 전용 핀 | 센서를 D2~D12 중 빈 핀으로 이동 (D13도 회피) |
| 디지털 센서 DO가 상시 HIGH, 가변저항 전 구간 돌려도 변화 없음 | 모듈 DO 비교기 회로 이상(상시 트리거) | **DO 폐기 → AO(아날로그) swing 감지로 우회** (아래) |
| DO/AO 중 뭐가 박수/소리에 반응하는지 불명 | 핀 정체 불확실 | **DO+AO 동시 디버그** 스케치로 한 번에 판별 (`sketches/sound_a1_debug` 패턴) |
| 아날로그 센서 raw는 변하는데 ℃ 등 환산값이 비현실적 | 분압저항·B값이 코드 가정과 불일치 | raw로 동작만 확인, 실값은 알려진 2점 캘리브레이션 |

### 디지털 모듈 DO 불량 시 AO swing 우회 (2026-06-18 검증)

비교기 DO가 상시 트리거되거나 가변저항으로 임계가 안 잡히면, 아날로그 출력(AO)을 짧은 윈도우 min/max(swing)로 읽어 **소프트웨어 임계**로 감지한다. 가변저항 튜닝 불필요.

```cpp
const int SOUND = A1;        // 모듈 AO
const int SOUND_TH = 60;     // 무음 swing~2, 큰소리 160+
int mn = 1023, mx = 0;
for (int i = 0; i < 50; i++) { int v = analogRead(SOUND); if (v<mn) mn=v; if (v>mx) mx=v; }
if ((mx - mn) >= SOUND_TH) { /* [SOUND] DETECTED */ }
```

## Promotion Path

- 이 스킬은 URHYNIX의 센서/액추에이터 스택 변경에 따라 갱신된다.
- 진척 (2026-06-18 기준):
  - ✅ PIR (HW-740): 디지털 엣지 트리거, MOTION/CLEAR 로그
  - ~~❌ LDR (조도): A0 + 10kΩ 분압~~ → 제거됨 (정본 v18, 2026-06-16)
  - ✅ 레이저 송신 모듈 (PIR 연동 점등): 2026-06-16 PASS. 4센서 통합본은 D4 배치(2026-06-18)
  - ✅ 소리: **AO swing 방식(A1)** 으로 PASS (2026-06-18). DO 불량 우회 — 위 Fallback 참조
  - ✅ 온도 (PP-A017): AO→A0 raw 반응 PASS (2026-06-18). ℃ 환산 캘리브레이션은 잔여
  - ⏳ 불꽃 (적외선): KY-026 또는 등가 — 정본 v18에서 레이저로 대체 검토
  - 📍 4센서 통합 as-built(PIR D2·레이저 D4·사운드 A1·온도 A0): `docs/evidence/2026-06-18-quad-sensor-flash.md`
- 다음 스택(온도/워터펌프 등)이 추가되면 → `docs/evidence/`에 한 번에 모은 표 작성 → `docs/ref/CONTRACT.md §4` 시리얼 배선 표 갱신.
- ESP32/Nano 등으로 보드가 바뀌면 FQBN(`arduino:avr:uno` 부분)만 교체하면 됨.

## Scope Boundary (RPi 측 작업과의 경계)

본 스킬은 **Mac → Arduino UNO 컴파일/업로드/시리얼 검증**까지만 책임진다.

라즈베리파이 측 작업은 별도:

- **`/dev/tb3_arduino` 영구 식별** — `/etc/udev/rules.d/99-urhynix-arduino.rules` (vendor 2341, MODE=0666, SYMLINK `tb3_arduino`) + `usermod -aG dialout kim`. 2026-05-28 적용 완료. 라즈베리파이 측 시리얼 읽기 코드는 항상 `/dev/tb3_arduino` 사용.
- **RPi → DB insert** — `events` 테이블이 들어갈 DB가 **선정되어야** 진행 가능. 2026-05-28 시점 DB 미선정으로 차단됨 (`DECISION-LOG.md` 2026-05-28 "DB 선정 보류" 참조). 결정 후 별도 스킬화 예정.

## Related Skills

- `decision-broadcast` — 핀 매핑이나 보드 변경 결정이 생기면 5채널 동기화
- `ssot-board-sync` — CONTRACT.md/ARCHITECTURE.md 핀 매핑 변경 시 HTML 보드 재빌드
- `evidence-review` — 센서별 플래시 결과를 증거 파일로 남길 때
- `session-retro` — 새 센서를 추가하며 막힌 부분을 다음 세션 자산으로 환원
