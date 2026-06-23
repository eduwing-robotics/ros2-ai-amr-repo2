// sound_a1_debug.ino — 사운드 모듈 DO(D8)+AO(A1) 동시 진단
// 목적: DO 상시 HIGH 의심 → DO 토글 여부 + AO raw 피크를 동시에 보고 어느 쪽으로 갈지 확정
// 배선: DO->D8(디지털), AO->A1(아날로그), VCC->5V, GND->공통 (현 배선 그대로)
// 판정: 박수 때 DO가 0/1 바뀌면 DO 사용 / A1 max가 크게 튀면 AO 사용. 둘 다 변화 적으면 모듈/감도 문제.
const int SOUND_DO = 8;
const int SOUND_AO = A1;

void setup() {
  pinMode(SOUND_DO, INPUT);
  Serial.begin(9600);
  delay(300);
  Serial.println(F("=== SOUND DO(D8)+AO(A1) DEBUG ==="));
  Serial.println(F("조용히 -> 박수 세게 반복. DO 토글 또는 A1 max 튐 확인"));
}

void loop() {
  int mn = 1023, mx = 0;
  for (int i = 0; i < 200; i++) {           // ~100ms 윈도우 AO 피크 포착
    int v = analogRead(SOUND_AO);
    if (v < mn) mn = v;
    if (v > mx) mx = v;
    delayMicroseconds(400);
  }
  int d = digitalRead(SOUND_DO);
  Serial.print(F("DO(D8)=")); Serial.print(d);
  Serial.print(F("  AO(A1) min=")); Serial.print(mn);
  Serial.print(F(" max="));         Serial.print(mx);
  Serial.print(F(" swing="));       Serial.print(mx - mn);
  if (mx - mn > 40) Serial.println(F("   <-- AO 신호!"));
  else              Serial.println();
  delay(80);
}
