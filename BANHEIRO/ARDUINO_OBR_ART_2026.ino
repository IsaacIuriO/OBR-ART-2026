const int entrada = 7;
const int saida = 8;

void setup() {
  pinMode(entrada, INPUT);
  pinMode(saida, OUTPUT);
}

void loop() {
  int estado = digitalRead(entrada);

  if (estado == HIGH) {
    // Ação quando entrada for alta
    digitalWrite(saida, HIGH);
  } else {
    digitalWrite(saida, LOW);
  }
}