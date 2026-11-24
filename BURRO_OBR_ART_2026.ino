#include <Servo.h>

// =========================
// Configuração do Servo
// =========================
Servo meuServo;
const int pinoServo = 9;

// =========================
// Configuração do Sensor Ultrassônico HC-SR04
// =========================
const int trigPin = 2;
const int echoPin = 3;

// Variáveis globais
long duracao;
float distancia;

// Função para medir a distância
float medirDistancia() {
  // Gera pulso no TRIG
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Lê o tempo do ECHO
  duracao = pulseIn(echoPin, HIGH);

  // Calcula a distância em cm
  return duracao * 0.034 / 2;
  
}

void setup() {
  meuServo.attach(pinoServo);
  meuServo.write(90);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  Serial.begin(9600);
  delay(20000);
}

void loop() {
  // Mede a distância inicial
  distancia = medirDistancia();
  
  if(distancia <= 15 && distancia > 5)
  {
    while (true) {

      meuServo.write(0);
      delay(1000);

      meuServo.write(90);
      delay(1000);

      meuServo.write(180);
      delay(1000);
    }
  }

  // Quando não houver objeto próximo,
  // retorna o servo para 0°
  meuServo.write(90);

  Serial.print("Distancia: ");
  Serial.print(distancia);
  Serial.println(" cm - Parado.");

  delay(200);
}
