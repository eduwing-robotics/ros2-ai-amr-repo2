// dht_sound.ino — DHT11/DHT22 디지털 온도센서(DATA->D8) + AS0025 사운드(DO->D3)
// 목적: DS18B20 대신 DHT 계열로 교체 검증. DHT11/22 자동 판별.
// 배선(아두이노 직결): DHT DATA->D8, VCC(+)->5V, GND(-)->GND (모듈이면 풀업 내장)
// 검증: 센서 손으로 잡으면 [DHT] 온도 상승 / 박수 -> [SOUND] D3 변화
#include <DHT.h>

const int DHT_PIN = 7;  // D8 고장 의심 -> D7로 이동 테스트
const int SOUND_DO = 3;
const int SOUND_AO = A0;

DHT dht22(DHT_PIN, DHT22);
DHT dht11(DHT_PIN, DHT11);

unsigned long lastRead = 0;
const unsigned long READ_INTERVAL = 2500;
int lastSoundState = -1;

void setup() {
  Serial.begin(9600);
  delay(300);
  pinMode(SOUND_DO, INPUT);
  dht22.begin();
  dht11.begin();
  Serial.println(F("=== DHT(D8) + SOUND(D3) Diagnostic ==="));
  Serial.println(F("Ready. 센서 잡으면 온도 상승 / 박수치면 D3 변화"));
}

void loop() {
  int s = digitalRead(SOUND_DO);
  if (s != lastSoundState) {
    Serial.print(F("[SOUND] D3 -> ")); Serial.print(s ? F("HIGH") : F("LOW"));
    Serial.print(F("  (A0=")); Serial.print(analogRead(SOUND_AO)); Serial.println(F(")"));
    lastSoundState = s;
  }

  if (millis() - lastRead >= READ_INTERVAL) {
    lastRead = millis();
    float t22 = dht22.readTemperature();
    if (!isnan(t22)) {
      Serial.print(F("[DHT22] ")); Serial.print(t22); Serial.println(F(" C"));
      return;
    }
    float t11 = dht11.readTemperature();
    if (!isnan(t11)) {
      Serial.print(F("[DHT11] ")); Serial.print(t11); Serial.println(F(" C"));
      return;
    }
    Serial.println(F("[DHT] 읽기 실패(NaN) - DATA=D8/전원/센서종류 확인"));
  }
}
