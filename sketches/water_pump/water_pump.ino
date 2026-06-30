// water_pump.ino — URHYNIX 워터펌프 릴레이 결선 검증 스케치
// 릴레이 신호선 D8. 펌프 ON/OFF 주기 토글 + 시리얼 로그.
// 릴레이 모듈 대부분 active-LOW(LOW=ON). 보드가 active-HIGH면 RELAY_ACTIVE_LOW=false.
// 시리얼 9600. 검증 로그: [PUMP] ON / [PUMP] OFF

const int RELAY = 8;                  // 릴레이 IN (워터펌프)
const bool RELAY_ACTIVE_LOW = true;   // active-LOW 모듈 기준
const unsigned long ON_MS  = 3000;    // 펌프 켜둘 시간
const unsigned long OFF_MS = 3000;    // 펌프 꺼둘 시간

inline void pumpWrite(bool on) {
  digitalWrite(RELAY, (on ^ RELAY_ACTIVE_LOW) ? HIGH : LOW);
}

void setup() {
  Serial.begin(9600);
  pinMode(RELAY, OUTPUT);
  pumpWrite(false);                   // 부팅 시 펌프 OFF 보장
  Serial.println(F("=== Water Pump Relay Test (D8) ==="));
}

void loop() {
  pumpWrite(true);
  Serial.println(F("[PUMP] ON"));
  delay(ON_MS);

  pumpWrite(false);
  Serial.println(F("[PUMP] OFF"));
  delay(OFF_MS);
}
