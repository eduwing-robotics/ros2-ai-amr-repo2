#include <Servo.h>
#include <IRremote.hpp>

const int PIR_PIN=2;
const int IR_PIN=4;
const int SERVO_PIN=7;
const int SOUND_DO=8;
const int TEMP_DO=11;
const int TEMP_AO=A0;
const int SOUND_AO=A1;

Servo myServo;
bool lastPir=LOW;

void setup(){
 Serial.begin(9600);
 pinMode(PIR_PIN,INPUT);
 pinMode(SOUND_DO,INPUT);
 pinMode(TEMP_DO,INPUT);
 myServo.attach(SERVO_PIN);
 myServo.write(90);
 IrSender.begin(IR_PIN);
 Serial.println("Sensor IR Sender Ready");
}

void loop(){
 int pir=digitalRead(PIR_PIN);
 int soundD=digitalRead(SOUND_DO);
 int soundA=analogRead(SOUND_AO);
 int tempD=digitalRead(TEMP_DO);
 int tempA=analogRead(TEMP_AO);

 if(pir==HIGH && lastPir==LOW){
   Serial.println("PIR DETECTED");
   myServo.write(0);
   delay(500);
   myServo.write(90);

   // NEC Address=0x01 Command=0x10
   IrSender.sendNEC(0x01,0x52,0);
   Serial.println("IR SENT");
   delay(200);
 }
 lastPir=pir;

 Serial.println("----------------------");
 Serial.print("PIR : "); Serial.println(pir?"DETECTED":"NONE");

 Serial.print("KY-028 DO : ");
 Serial.println(tempD?"THRESHOLD":"NORMAL");
 Serial.print("KY-028 AO : ");
 Serial.println(tempA);

 Serial.print("KY-037 DO : ");
 Serial.println(soundD?"NOISE":"QUIET");
 Serial.print("KY-037 AO : ");
 Serial.println(soundA);

 delay(500);
}

