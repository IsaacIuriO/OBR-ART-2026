
#include "BluetoothSerial.h"

BluetoothSerial SerialBT;


void setup() {
  Serial.begin(115200);
  SerialBT.begin("ESP32_HAND");

  pinMode(18, OUTPUT);
  digitalWrite(18, LOW);
}

void loop() {

 if (SerialBT.available()) {
  String comando = SerialBT.readStringUntil('\n');
  comando.trim();

  if (comando.equals("GIRAR")) {
    digitalWrite(18, HIGH);
  }

  if (comando.equals("PARAR")) {
    digitalWrite(18, LOW);
  }
}
}
