/*
  HW-740 PIR 인체감지 → LED + 레이저 동시 점등 (URHYNIX Gen.G)
  정본 v18(2026-06-16): 조도(LDR/A0) 제거, 레이저 송신 모듈 추가.
  - D7 : PIR OUT (입력)
  - D2 : LED (+ 220Ω → GND)
  - D8 : 레이저 송신 모듈 DATA (5V=브레드보드 레일, GND=공통 그라운드)
         ※ D13(SCK)은 업로드 시 부트로더 동기화를 방해해 D8로 이동함

  - PIR 감지 시 LED와 레이저를 동시에 ON, 해제 시 동시 OFF
  - 시리얼 9600 baud 상태 로그
*/

const int LED    = 2;    // LED 출력 핀
const int SENSOR = 7;    // PIR 센서 입력 핀
const int LASER  = 8;    // 레이저 송신 모듈 DATA 핀 (D13=SCK 업로드 충돌 회피)

const unsigned long WARMUP_MS = 8000;  // 검증용 단축 워밍업

int value     = 0;
int lastValue = LOW;

void setup() {
  pinMode(LED, OUTPUT);
  pinMode(LASER, OUTPUT);
  pinMode(SENSOR, INPUT);
  digitalWrite(LED, LOW);
  digitalWrite(LASER, LOW);

  Serial.begin(9600);
  Serial.println(F("=== PIR + LASER Test ==="));
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
  // --- PIR (디지털, 엣지 트리거) → LED + 레이저 동시 제어 ---
  value = digitalRead(SENSOR);
  if (value != lastValue) {
    if (value == HIGH) {
      digitalWrite(LED, HIGH);
      digitalWrite(LASER, HIGH);
      Serial.println(F("[MOTION] detected -> LED+LASER ON"));
    } else {
      digitalWrite(LED, LOW);
      digitalWrite(LASER, LOW);
      Serial.println(F("[CLEAR ] no motion -> LED+LASER OFF"));
    }
    lastValue = value;
  }

  delay(50);
}
