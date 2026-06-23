// ds18b20_pinscan.ino — DS18B20 DATA선이 어느 핀에 꽂혔는지 전 핀 자동 스캔
// 목적: 1-Wire reset+search를 D2~D13, A0~A5에 돌려 디바이스 발견 핀 찾기
// 해석: "FOUND on Dn" 나오면 그 핀이 DATA / 전 핀 없음=전원/풀업/센서 문제
#include <OneWire.h>

const uint8_t pins[] = {2,3,4,5,6,7,9,10,11,12,13, A0,A1,A2,A3,A4,A5, 8};
const uint8_t N = sizeof(pins)/sizeof(pins[0]);

void scanOnce() {
  bool any = false;
  for (uint8_t i = 0; i < N; i++) {
    OneWire ow(pins[i]);
    byte addr[8];
    ow.reset_search();
    if (ow.reset() && ow.search(addr)) {
      any = true;
      Serial.print(F("FOUND on pin "));
      Serial.print(pins[i] >= A0 ? F("A") : F("D"));
      Serial.print(pins[i] >= A0 ? (pins[i]-A0) : pins[i]);
      Serial.print(F("  ROM="));
      for (byte j = 0; j < 8; j++) {
        if (addr[j] < 16) Serial.print('0');
        Serial.print(addr[j], HEX); Serial.print(' ');
      }
      bool crcOK = (OneWire::crc8(addr,7) == addr[7]);
      Serial.println(crcOK ? F("[CRC OK]") : F("[CRC BAD-노이즈]"));
    }
  }
  if (!any) Serial.println(F("어느 핀에서도 1-Wire 디바이스 못 찾음 -> 전원/풀업/센서/케이블 확인"));
}

void setup() {
  Serial.begin(9600);
  delay(300);
  Serial.println(F("=== DS18B20 PIN SCAN (D2-D13, A0-A5) ==="));
}

void loop() {
  Serial.println(F("--- scan ---"));
  scanOnce();
  delay(2000);
}
