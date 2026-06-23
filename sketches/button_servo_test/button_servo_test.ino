// button_servo_test.ino
// 새 Arduino UNO 단발 테스트 — 버튼(D2) 누를 때마다 서보(D3)를 0°<->90° 토글.
// 외부 저항(풀업/풀다운) 어느 쪽이든 동작하도록 엣지(상태변화) 기반으로 처리.
// 시리얼 9600: 버튼 raw 값 + 서보 각도 출력. URHYNIX SSOT 핀맵 아님(테스트 전용).

#include <Servo.h>

const int BTN = 2;   // 버튼 (외부 저항 결선)
const int SVO = 3;   // 서보 신호선 (PWM 핀)

Servo servo;
int lastBtn = -1;        // 직전 버튼 상태 (초기값 강제 출력용)
int angle = 0;           // 현재 서보 각도
unsigned long lastBounce = 0;
const unsigned long DEBOUNCE_MS = 50;

void setup() {
  Serial.begin(9600);
  pinMode(BTN, INPUT);   // 외부 저항이 있으므로 INPUT (PULLUP 아님)
  servo.attach(SVO);
  servo.write(angle);
  Serial.println(F("=== Button + Servo Test ==="));
  Serial.println(F("Press button -> servo toggles 0 <-> 90 deg"));
}

void loop() {
  int btn = digitalRead(BTN);

  // 상태가 바뀌면 (디바운스 후) 처리
  if (btn != lastBtn && (millis() - lastBounce) > DEBOUNCE_MS) {
    lastBounce = millis();
    Serial.print(F("[BTN] D2=")); Serial.print(btn);

    // 눌림 엣지로 간주되는 한쪽 전이에서만 토글 (둘 다 찍어 raw 확인 가능)
    angle = (angle == 0) ? 90 : 0;
    servo.write(angle);
    Serial.print(F("  -> servo ")); Serial.print(angle); Serial.println(F(" deg"));

    lastBtn = btn;
  }
}
