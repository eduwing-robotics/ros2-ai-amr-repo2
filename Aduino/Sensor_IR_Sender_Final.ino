#include <Servo.h>
#include <IRremote.hpp>

const int PIR_PIN=2;
const int IR_PIN=4;
const int SERVO_PIN=7;
const int SOUND_DO=8;
const int TEMP_DO=11;
const int TEMP_AO=A0;
const int SOUND_AO=A1;

const unsigned long IR_INTERVAL=3000;
unsigned long lastIRTime=0;

Servo myServo;

void setup(){
  Serial.begin(9600);
  pinMode(PIR_PIN,INPUT);
  pinMode(SOUND_DO,INPUT);
  pinMode(TEMP_DO,INPUT);
  myServo.attach(SERVO_PIN);
  myServo.write(0);
  IrSender.begin(IR_PIN);
  Serial.println("Sensor IR Sender Ready");
}

void loop(){
  int pir=digitalRead(PIR_PIN);
  int soundD=digitalRead(SOUND_DO);
  int soundA=analogRead(SOUND_AO);
  int tempD=digitalRead(TEMP_DO);
  int tempA=analogRead(TEMP_AO);
  static int lastTempA = tempA;

  // 온도 변화 방향 표시
  if (tempA < lastTempA - 2) {
    Serial.print("KY-028 : 온도 상승 중 (");
    Serial.print(tempA);
    Serial.println(")");
  }
  else if (tempA > lastTempA + 2) {
    Serial.print("KY-028 : 온도 하락 중 (");
    Serial.print(tempA);
    Serial.println(")");
  }
  else {
    Serial.print("KY-028 : 변화 없음 (");
    Serial.print(tempA);
    Serial.println(")");
  }

  lastTempA = tempA;

  if(pir==HIGH && millis()-lastIRTime>=IR_INTERVAL){
    Serial.println("================================");
    Serial.println("[PIR] 사람 감지");
    for(int a=0;a<=170;a++){
      myServo.write(a);
      delay(15);
    }
    Serial.println("[IR] SEND Address=0x01 Command=0x52");
    IrSender.sendNEC(0x01,0x52,0);
    Serial.println("[IR] DONE");
    lastIRTime=millis();
  }

  Serial.print("PIR: ");Serial.println(pir);
  Serial.print("KY028 DO: ");Serial.println(tempD);
  Serial.print("KY028 AO: ");Serial.println(tempA);
  Serial.print("KY037 DO: ");Serial.println(soundD);
  Serial.print("KY037 AO: ");Serial.println(soundA);
  delay(1000);
}

