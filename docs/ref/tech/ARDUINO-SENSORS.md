# Arduino Sensors Tech Ref

Arduino Uno R3, PIR/LDR/sound/flame sensors, serial bridge 작업의 빠른 진입점이다.

⚠️ **정본 v18(2026-06-16)에서 LDR·불꽃 → 온도·레이저·워터펌프로 변경 결정됨. 아래는 구 LDR 기준 as-built이며 하드웨어 물리 교체 후 갱신 예정. 출처: DECISION-LOG 2026-06-16.**

## Read First

1. `docs/ref/TECH-INDEX.md`
2. `docs/ref/ARCHITECTURE.md` hardware stack and pin table
3. `.claude/skills/arduino-flash/SKILL.md`
4. `scripts/arduino_bridge.py`

## Current Truth

- Sensor board: Arduino Uno R3 + mini breadboard on TurtleBot3 Burger top plate.
- Data path: Arduino USB serial -> Raspberry Pi -> ROS2/DB bridge.
- Power: OpenCR 5V pin -> Arduino 5V pin, not Vin.
- Pins:
  - PIR: `D2`
  - LDR: `A0`
  - sound: `D3`
  - flame: `D4`
  - fire mock button: `D5`
- udev target: `/dev/tb3_arduino`.

## Verify

- Local flash/capture via `arduino-cli` or the `arduino-flash` skill.
- Robot serial device check: `/dev/tb3_arduino` exists and streams sensor lines.
- DB/ROS bridge check: PIR or LDR event becomes an `events` row or `/security/event` message.
- Doc sync: if pins change, update `docs/ref/ARCHITECTURE.md`, `docs/ref/CONTRACT.md`, and this file.

