/*
  HW-740 PIR 인체감지 + LDR 조도 + LED 점등
  - D7: PIR OUT
  - D2: LED (+ 220Ω 저항 → GND)
  - A0: LDR (5V — LDR — A0 — 10kΩ — GND 분압, SSOT 일치)
  - 시리얼 모니터(9600 baud)로 상태 로그 확인
*/

const int LED    = 2;    // LED 출력 핀
const int SENSOR = 7;    // PIR 센서 입력 핀
const int LDR    = A0;   // LDR 아날로그 입력 (URHYNIX SSOT 정렬)

const unsigned long WARMUP_MS = 8000;     // 검증용 단축 워밍업
const unsigned long LDR_INTERVAL = 2000;  // LDR 보고 주기 2초

int value     = 0;
int lastValue = LOW;
unsigned long lastLdrMs = 0;

void setup() {
  pinMode(LED, OUTPUT);
  pinMode(SENSOR, INPUT);
  digitalWrite(LED, LOW);

  Serial.begin(9600);
  Serial.println(F("=== PIR + LDR Test ==="));
  Serial.print(F("Warming up"));

  unsigned long start = millis();
  while (millis() - start < WARMUP_MS) {
    Serial.print('.');
    delay(1000);
  }
  Serial.println();
  Serial.println(F("Ready. Wave hand / cover sensor."));
}

void loop() {
  // --- PIR (디지털, 엣지 트리거) ---
  value = digitalRead(SENSOR);
  if (value != lastValue) {
    if (value == HIGH) {
      digitalWrite(LED, HIGH);
      Serial.println(F("[MOTION] detected -> LED ON"));
    } else {
      digitalWrite(LED, LOW);
      Serial.println(F("[CLEAR ] no motion -> LED OFF"));
    }
    lastValue = value;
  }

  // --- LDR (아날로그, 2초 주기) ---
  if (millis() - lastLdrMs >= LDR_INTERVAL) {
    int lux = analogRead(LDR);
    Serial.print(F("[LDR] A0="));
    Serial.print(lux);
    if (lux < 200)        Serial.println(F("  (dark)"));
    else if (lux < 600)   Serial.println(F("  (dim)"));
    else if (lux < 900)   Serial.println(F("  (bright)"));
    else                  Serial.println(F("  (very bright)"));
    lastLdrMs = millis();
  }

  delay(50);
}
