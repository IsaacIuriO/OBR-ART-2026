#include <Servo.h>

//======================
// PINOS
//======================

// Servos
const byte SERVO1 = 7;
const byte SERVO2 = 9;

// Alimentação do Servo 2
const byte SERVO2_VCC = 10;

// Sensor ultrassônico
const byte TRIG = 6;
const byte ECHO = 4;

// Alimentação do sensor
const byte SENSOR_VCC = 3;
const byte SENSOR_GND = 2;

//======================
// CONFIGURAÇÕES
//======================

// Distância de acionamento (cm)
int distanciaAcionamento = 25;

// Tempo que os servos permanecem acionados (ms)
unsigned long tempoAcionado = 10000;

// Tempo de espera ao ligar (s)
const int tempoInicial = 10;

// Ângulos
const int POS_INICIAL = 0;
const int POS_ACIONADA = 80;

//======================

Servo servo1;
Servo servo2;

//======================

float medirDistancia() {

  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  long tempo = pulseIn(ECHO, HIGH, 30000);

  if (tempo == 0)
    return -1;

  return tempo * 0.0343 / 2.0;
}

//======================

void setup() {

  Serial.begin(9600);

  // Alimentação do sensor
  pinMode(SENSOR_VCC, OUTPUT);
  pinMode(SENSOR_GND, OUTPUT);

  digitalWrite(SENSOR_VCC, HIGH);
  digitalWrite(SENSOR_GND, LOW);

  // Alimentação do Servo 2
  pinMode(SERVO2_VCC, OUTPUT);
  digitalWrite(SERVO2_VCC, HIGH);

  // Sensor
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  // Servos
  servo1.attach(SERVO1);
  servo2.attach(SERVO2);

  // Posição inicial
  servo1.write(POS_INICIAL);
  servo2.write(POS_INICIAL);

  Serial.println("--------------------------------");
  Serial.println("Sistema iniciando...");
  Serial.println("--------------------------------");

  // Contagem regressiva de 10 segundos
  for (int i = tempoInicial; i > 0; i--) {
    Serial.print("Iniciando em ");
    Serial.print(i);
    Serial.println(" segundo(s)...");
    delay(1000);
  }

  Serial.println("Sistema iniciado!");
  Serial.println("--------------------------------");
}

//======================

void loop() {

  float distancia = medirDistancia();

  Serial.print("Distancia: ");
  Serial.print(distancia);
  Serial.println(" cm");

  if (distancia > 0 && distancia <= distanciaAcionamento) {

    Serial.println(">>> OBJETO DETECTADO <<<");

    // Aciona os servos
    servo1.write(POS_ACIONADA);
    servo2.write(POS_ACIONADA);

    Serial.println("Servos acionados por 10 segundos.");
    delay(tempoAcionado);

    // Retorna
    servo1.write(POS_INICIAL);
    servo2.write(POS_INICIAL);

    Serial.println("Servos retornaram à posição inicial.");

    // Aguarda o objeto sair da frente do sensor
    while (true) {
      distancia = medirDistancia();

      if (distancia < 0 || distancia > distanciaAcionamento) {
        break;
      }

      delay(100);
    }

    Serial.println("Aguardando nova detecção...");
    delay(300);
  }

  delay(100);
}
