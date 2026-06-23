// quad_security.ino — PIR + 레이저 + 사운드 + 온도(PP-A017) 4센서 통합 (URHYNIX 경비)
// 핀맵: PIR=D2(IN) / 레이저=D4(OUT) / 사운드 AO=A1(아날로그) / 온도 AO=A0(아날로그) / LED=D7(OUT,옵션)
// 배선: 네 모듈 VCC->5V 레일, GND->공통 레일. 사운드 DO·온도 DO 미사용.
// 금지핀: D0/D1(USB 시리얼), D13(SCK) — 아무것도 꽂지 말 것.
// 동작: PIR 감지->LED+레이저 ON, 박수->[SOUND], 온도 1초 주기->[TEMP] raw+추정C. 시리얼 9600.
const int PIR    = 2;    // PIR OUT (입력)
const int LASER  = 4;    // 레이저 송신 모듈 DATA
const int LED    = 7;    // 경광 LED (+220Ω->GND), 옵션
const int SOUND  = A1;   // 사운드 모듈 AO (아날로그 swing 감지)
const int THERM  = A0;   // PP-A017 서미스터 AO (아날로그)

const unsigned long WARMUP_MS = 8000;   // PIR 워밍업(검증용 단축)
const unsigned long TEMP_INTERVAL = 1000;
const int SOUND_TH = 60;                 // 사운드 swing 임계 (무음~8, 큰소리 160+)

int lastPir   = LOW;
int lastSound = -1;
unsigned long lastTemp = 0;

void setup() {
  pinMode(PIR, INPUT);
  pinMode(SOUND, INPUT);
  pinMode(LASER, OUTPUT);
  pinMode(LED, OUTPUT);
  digitalWrite(LASER, LOW);
  digitalWrite(LED, LOW);

  Serial.begin(9600);
  delay(300);
  Serial.println(F("=== QUAD: PIR(D2)+LASER(D4)+SOUND(A1)+TEMP(A0) ==="));
  Serial.print(F("Warming up PIR"));
  unsigned long start = millis();
  while (millis() - start < WARMUP_MS) { Serial.print('.'); delay(1000); }
  Serial.println();
  Serial.println(F("Ready. 움직임/박수/센서잡기로 검증"));
}

void loop() {
  // --- PIR -> LED + 레이저 동시 ---
  int p = digitalRead(PIR);
  if (p != lastPir) {
    digitalWrite(LED, p);
    digitalWrite(LASER, p);
    Serial.println(p == HIGH ? F("[MOTION] detected -> LED+LASER ON")
                             : F("[CLEAR ] no motion -> LED+LASER OFF"));
    lastPir = p;
  }

  // --- 사운드 AO swing 감지 (무음~2, 큰소리 60+) ---
  int smn = 1023, smx = 0;
  for (int i = 0; i < 50; i++) { int v = analogRead(SOUND); if (v < smn) smn = v; if (v > smx) smx = v; }
  int swing = smx - smn;
  int sdet = (swing >= SOUND_TH) ? 1 : 0;
  if (sdet != lastSound) {
    Serial.print(F("[SOUND] ")); Serial.print(sdet ? F("DETECTED") : F("quiet"));
    Serial.print(F(" (swing=")); Serial.print(swing); Serial.println(F(")"));
    lastSound = sdet;
  }

  // --- 온도 A0 (1초 주기, 16샘플 평균) ---
  if (millis() - lastTemp >= TEMP_INTERVAL) {
    lastTemp = millis();
    long acc = 0;
    for (int i = 0; i < 16; i++) { acc += analogRead(THERM); delay(2); }
    int raw = acc / 16;
    Serial.print(F("[TEMP] A0 raw=")); Serial.print(raw);
    if (raw <= 3)         Serial.println(F("  (0근처-AO 미연결/GND단락 의심)"));
    else if (raw >= 1020) Serial.println(F("  (최대-AO 미연결/5V단락 의심)"));
    else {
      // 10k NTC, B=3950, 10k 분압, 5V 가정 (모듈마다 다름, 참고용)
      float v = raw / 1023.0;
      float r = 10000.0 * (1.0 / v - 1.0);
      float tK = 1.0 / (1.0 / 298.15 + (1.0 / 3950.0) * log(r / 10000.0));
      Serial.print(F("  ~")); Serial.print(tK - 273.15, 1); Serial.println(F("C(추정)"));
    }
  }
}
