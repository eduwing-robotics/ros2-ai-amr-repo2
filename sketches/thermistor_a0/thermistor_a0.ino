// thermistor_a0.ino — PP-A017 서미스터 온도모듈 AO(아날로그)->A0 읽기 검증
// 목적: DS18B20/DHT 실패 후 서미스터 모듈로 교체. A0 raw가 온도에 반응하는지 확인.
// 배선: 모듈 AO->A0, VCC(+)->5V, GND(-)->GND (DO는 안 써도 됨)
// 검증: 센서 손으로 잡으면 A0 raw 값이 변함(상승/하강) = 정상
const int THERM = A0;
const int DOUT = 13;

void setup() {
  Serial.begin(9600);
  pinMode(DOUT, INPUT);
  delay(300);
  Serial.println(F("=== PP-A017 THERMISTOR (A0) read ==="));
  Serial.println(F("Ready. 센서 손으로 잡으면 raw 값이 변하면 정상"));
}

void loop() {
  long acc = 0;
  for (int i = 0; i < 16; i++) { acc += analogRead(THERM); delay(2); }
  int raw = acc / 16;

  Serial.print(F("[TEMP] A0 raw=")); Serial.print(raw);
  Serial.print(F("  D13=")); Serial.print(digitalRead(DOUT));

  if (raw <= 3)       Serial.print(F("  (0근처-AO 미연결/GND단락 의심)"));
  else if (raw >= 1020) Serial.print(F("  (최대-AO 미연결/5V단락 의심)"));
  else {
    // 대략 추정값 (10k NTC, B=3950, 10k 분압, 5V 가정 — 모듈마다 다름, 참고용)
    float v = raw / 1023.0;
    float r = 10000.0 * (1.0 / v - 1.0);
    float tK = 1.0 / (1.0 / 298.15 + (1.0 / 3950.0) * log(r / 10000.0));
    Serial.print(F("  ~")); Serial.print(tK - 273.15, 1); Serial.print(F("C(추정)"));
  }
  Serial.println();
  delay(1000);
}
