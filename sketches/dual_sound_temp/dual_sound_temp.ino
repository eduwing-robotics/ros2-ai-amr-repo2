// dual_sound_temp.ino — AS0025 사운드(DO->D3) + DS18B20 온도(D8) 결선 진단
// 목적: 두 모듈을 서로 다른 핀(D3/D8)에 갈라 충돌 없이 기능 검증
// 배선: 사운드 DO->D3 / DS18B20 DATA->D8 / 둘 다 5V·GND 공유 (베어센서면 D8-5V에 4.7k)
// 검증: 박수 -> [SOUND] D3 상태변화 / 센서 손으로 잡기 -> [TEMP] C 상승
#include <OneWire.h>
#include <DallasTemperature.h>

const int SOUND_DO = 3;
const int SOUND_AO = A0;   // 4핀 모듈이면 AO 참고값도 같이 출력
const int ONE_WIRE_BUS = 8;

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

unsigned long lastTemp = 0;
const unsigned long TEMP_INTERVAL = 2000;
int lastSoundState = -1;

void setup() {
  Serial.begin(9600);
  delay(300);
  pinMode(SOUND_DO, INPUT);
  Serial.println(F("=== SOUND(D3) + DS18B20(D8) Diagnostic ==="));

  sensors.begin();
  int n = sensors.getDeviceCount();
  Serial.print(F("DS18B20 found: ")); Serial.println(n);
  if (n == 0) Serial.println(F("[WARN] DS18B20 0개 - D8 결선/풀업/전원 확인"));

  Serial.print(F("Sound DO 초기 D3=")); Serial.print(digitalRead(SOUND_DO));
  Serial.print(F("  AO(A0)=")); Serial.println(analogRead(SOUND_AO));
  Serial.println(F("Ready. 박수 치면 D3 변화 / 센서 잡으면 온도 상승"));
}

void loop() {
  // 사운드: DO 상태 변화 감지 (포텐쇼미터 임계값 넘으면 토글)
  int s = digitalRead(SOUND_DO);
  if (s != lastSoundState) {
    Serial.print(F("[SOUND] D3 -> ")); Serial.print(s ? F("HIGH") : F("LOW"));
    Serial.print(F("  (A0=")); Serial.print(analogRead(SOUND_AO)); Serial.println(F(")"));
    lastSoundState = s;
  }

  // 온도: 2초 주기
  if (millis() - lastTemp >= TEMP_INTERVAL) {
    sensors.requestTemperatures();
    float c = sensors.getTempCByIndex(0);
    Serial.print(F("[TEMP] "));
    if (c == DEVICE_DISCONNECTED_C)
      Serial.println(F("DISCONNECTED(-127) - D8 결선/풀업/전원 확인"));
    else { Serial.print(c); Serial.println(F(" C")); }
    lastTemp = millis();
  }
}
