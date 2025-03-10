/*
  Código para ESP32 para controle do servo motor via LEDC e aquisição de dados dos sensores.
  Utiliza:
    - LEDC para geração do sinal PWM para o servo
    - Leitura do sensor de corrente ACS712 (via analogRead)
    - Leitura do sensor de temperatura MAX6675 (com termopar)
  
  Comandos via Serial:
    "a" - Inicia o teste de carga típica (servo oscila entre neutralPWM ± offset)
    "d" - Semelhante a "a", mas a cada X minutos desvia para um PWM específico por Y segundos
    "s" - Interrompe o teste e posiciona o servo na posição mínima (ou máxima se INVERTE = true)
    Número inteiro (entre PWM_min e PWM_max) - Define o novo neutral (em PWM)
  
  A tarefa sampleTask é executada em um núcleo dedicado para coletar 100 amostras e enviá-las de uma só vez.
*/

#include <Arduino.h>
#include <SPI.h>
#include <max6675.h>  // Biblioteca compatível com ESP32 para MAX6675

// Definições de pinos
#define SERVO_PIN 13       // Pino de controle do servo
#define ACS712_PIN 34      // Pino analógico para sensor de corrente ACS712
#define THERMO_CLK 18
#define THERMO_CS 5
#define THERMO_DO 19

// Se verdadeiro, o "stop" coloca o servo em PWM_max em vez de PWM_min
#define INVERTE true

// Declara a instância do MAX6675 no escopo global
MAX6675 thermocouple(THERMO_CLK, THERMO_CS, THERMO_DO);

// Configurações do LEDC para o servo
const int ledcChannel = 0;
const int ledcFreq = 333;       // Frequência (~50 Hz para servo)
const int ledcResolution = 16;  // Resolução de 16 bits

// Parâmetros para conversão de ângulo para PWM (em microsegundos)
const float PWM_min = 1000;
const float PWM_max = 2000;
const float angle_min = 0;
const float angle_max = 100;

// Parâmetros gerais do teste
const float angle_plus = 10.5;   // Offset + em graus
const float angle_minus = 10.5;  // Offset - em graus
int neutralPWM = 1515;         // Neutral definido diretamente em PWM
const float speed = 10;        // Velocidade em °/s
float stepPWM = 1;             // Movimento suave (passo)

// Cálculo de limites e frequências
const float res = (angle_max - angle_min) / (PWM_max - PWM_min); // usado para algum cálculo custom
const float freq_att = (res == 0) ? 1 : speed / res;             // evitar div zero
unsigned long delay_ms = (freq_att == 0) ? 10 : (int)(stepPWM / (freq_att / 1000));

// Limites de PWM correspondentes aos offsets
// Note: se quiser offsets em graus, convém converter via map() em vez de dividir por res
int pwm_plus  = (int)(angle_plus  * (1.0 / res));
int pwm_minus = (int)(angle_minus * (1.0 / res));

// Booleans para controlar qual teste está rodando
bool testARunning = false;
bool testDRunning = false;

// Variáveis de oscilação
int currentPWM = neutralPWM;
int direction = 1;

// Timer de atualização do servo
unsigned long lastServoUpdateTime = 0;

// Variáveis para a tarefa de amostragem
String sampleBuffer = "";
int sampleCountGlobal = 0;
const unsigned long sampleInterval = 250; // Intervalo de amostragem (ms)

// Controle de tempo do teste na própria ESP
unsigned long testStartTime = 0; // Armazena o tempo em que o teste começou (millis)

// ---------- parâmetros do teste "d" -----------
float desvioIntervalMin = 20;  // Intervalo, em minutos, entre desvios (ex: 0.1 min = 6s)
float desvioDurationSec = 3.0;  // Duração do desvio, em segundos
const float AnguloCritico = 12.5;           // PWM para onde vamos desviar
const int desvioPWM = (int)(AnguloCritico * (1.0 / res) + PWM_min);           // PWM para onde vamos desviar
bool desvioActive = false;      // Indica se estamos atualmente em desvio
unsigned long lastDesvioTime = 0;      // Marca quando ocorreu o último desvio
unsigned long desvioStartTime = 0;     // Marca o início do desvio
int preDesvioPWM = 0;                 // Valor do PWM antes de iniciar o desvio

// Converte o PWM (em µs) para o duty cycle do LEDC
uint32_t pwmMicrosecondsToDuty(int pwm_us) {
  int period_us = 1000000 / ledcFreq;  // Período em µs
  uint32_t maxDuty = (1 << ledcResolution) - 1;
  return (uint32_t)(((uint64_t)pwm_us * maxDuty) / period_us);
}

// Aplica o PWM no servo via LEDC
void setServoPWM(int pwmValue) {
  uint32_t duty = pwmMicrosecondsToDuty(pwmValue);
  ledcWrite(ledcChannel, duty);
}

// Converte um valor PWM -> Ângulo
int pwmToAngle(int pwm) {
  return map(pwm, (int)PWM_min, (int)PWM_max, (int)angle_min, (int)angle_max);
}

// Converte Ângulo -> PWM
int angleToPWM(int angle) {
  return map(angle, (int)angle_min, (int)angle_max, (int)PWM_min, (int)PWM_max);
}

// Processa os comandos recebidos via Serial
void processSerial() {
  while (Serial.available() > 0) {
    if (isDigit(Serial.peek())) {
      // Recebe um comando numérico (PWM)
      int pwmValue = Serial.parseInt();
      if (pwmValue >= PWM_min && pwmValue <= PWM_max) {
        // Define neutral
        testARunning = false;
        testDRunning = false;
        desvioActive = false;
        
        neutralPWM = pwmValue;
        currentPWM = neutralPWM;
        setServoPWM(currentPWM);
        int angleVal = pwmToAngle(currentPWM);
        
        Serial.print("Novo Neutro - Servo posicionado para PWM: ");
        Serial.print(pwmValue);
        Serial.print(" - Ângulo: ");
        Serial.println(angleVal);
      }
    } else {
      char cmd = Serial.read();
      if (cmd == 'a') {
        // Inicia o teste "a"
        testARunning = true;
        testDRunning = false;
        desvioActive = false;
        
        currentPWM = neutralPWM;
        setServoPWM(currentPWM);
        direction = 1;
        testStartTime = millis();
        lastDesvioTime = testStartTime; // não utilizado em 'a', mas zera por segurança
        Serial.println("Teste A iniciado.");
      }
      else if (cmd == 'd') {
        // Inicia o teste "d"
        testARunning = false;
        testDRunning = true;
        desvioActive = false;
        
        currentPWM = neutralPWM;
        setServoPWM(currentPWM);
        direction = 1;
        testStartTime = millis();
        lastDesvioTime = testStartTime; // zera para começar a contar
        Serial.println("Teste D iniciado (com desvios periódicos).");
      }
      else if (cmd == 's') {
        // Stop em qualquer teste
        testARunning = false;
        testDRunning = false;
        desvioActive = false;

        if (!INVERTE) {
          currentPWM = (int)PWM_min;
        } else {
          currentPWM = (int)PWM_max;
        }
        setServoPWM(currentPWM);
        Serial.println("Teste interrompido. Servo na posição mínima (ou máxima).");
      }
    }
  }
}

// Lógica de oscilação (igual ao teste "a")
void updateOscillation() {
  // Move o servo a cada 'delay_ms'
  unsigned long now = millis();
  if (now - lastServoUpdateTime >= delay_ms) {
    lastServoUpdateTime = now;
    
    // Atualiza currentPWM em passos equivalentes ao stepPWM
    currentPWM += direction * (int)stepPWM;
    
    // Verifica os limites de oscilação
    int limUp   = neutralPWM + pwm_plus;
    int limDown = neutralPWM - pwm_minus;
    
    if (direction > 0 && currentPWM >= limUp) {
      currentPWM = limUp;
      direction = -1;
    } else if (direction < 0 && currentPWM <= limDown) {
      currentPWM = limDown;
      direction = 1;
    }
    setServoPWM(currentPWM);
  }
}

// Tarefa de amostragem: coleta 100 amostras e envia todas de uma só vez via Serial.
// Rodando em core 1
void sampleTask(void * parameter) {
  for (;;) {
    // Amostra somente se estiver rodando A ou D
    if (testARunning || testDRunning) {
      // Leitura do sensor ACS712 (corrente) - valor bruto
      int acsValue = analogRead(ACS712_PIN);
      float currentMeasurement = acsValue;  // Conversão depende da calibração
      
      // Leitura da temperatura (°C)
      float temperature = thermocouple.readCelsius();
      
      // Calcula o ângulo atual do servo
      int angleVal = pwmToAngle(currentPWM);
      
      // Tempo decorrido
      unsigned long elapsedMs = millis() - testStartTime;
      unsigned int totalSec = elapsedMs / 1000;
      unsigned int mm = totalSec / 60;
      unsigned int ss = totalSec % 60;

      char timeStr[6];
      snprintf(timeStr, sizeof(timeStr), "%02d:%02d", mm, ss);

      // "PWM,temperatura,ângulo,corrente,tempo"
      String sampleLine = String(currentPWM) + "," 
                        + String(temperature) + "," 
                        + String(angleVal) + "," 
                        + String(currentMeasurement) + "," 
                        + timeStr + "\n";
      sampleBuffer += sampleLine;
      sampleCountGlobal++;
      
      if (sampleCountGlobal >= 100) {
        Serial.print(sampleBuffer);
        sampleBuffer = "";
        sampleCountGlobal = 0;
      }
    }
    vTaskDelay(sampleInterval / portTICK_PERIOD_MS);
  }
}

void setup() {
  Serial.begin(115200);
  
  // Configura o LEDC para o servo
  ledcSetup(ledcChannel, ledcFreq, ledcResolution);
  ledcAttachPin(SERVO_PIN, ledcChannel);

  // Inicializa o servo na posição mínima ou máxima conforme INVERTE
  currentPWM = INVERTE ? (int)PWM_max : (int)PWM_min;
  setServoPWM(currentPWM);
  delay(500);

  Serial.println("Inicializando sensores...");
  delay(500);

  // Exibe alguns valores de debug
  Serial.println("------ Valores de Config ------");
  Serial.print("res: ");       Serial.println(res);
  Serial.print("freq_att: ");  Serial.println(freq_att);
  Serial.print("delay_ms: ");  Serial.println(delay_ms);
  Serial.print("pwm_plus: ");  Serial.println(pwm_plus);
  Serial.print("pwm_minus: "); Serial.println(pwm_minus);
  Serial.print("pwm_critico: "); Serial.println(desvioPWM);
  Serial.println("--------------------------------");

  // Cria a tarefa de amostragem no núcleo 1
  xTaskCreatePinnedToCore(
    sampleTask,   // Função da tarefa
    "SampleTask", // Nome da tarefa
    4096,         // Tamanho da stack
    NULL,         // Parâmetro
    1,            // Prioridade
    NULL,         // Handle da tarefa
    1             // Núcleo (core) 1
  );
}

void loop() {
  processSerial();
  
  // =============== TESTE "A" ===============
  if (testARunning) {
    updateOscillation(); 
    return; // não verifica "d" se "a" está rodando
  }

  // =============== TESTE "D" ===============
  if (testDRunning) {
    // 1) Se estamos em desvio, verificar se já acabou o tempo
    if (desvioActive) {
      unsigned long now = millis();
      unsigned long desvioDurationMs = (unsigned long)(desvioDurationSec * 1000.0);
      
      if ((now - desvioStartTime) >= desvioDurationMs) {
        // Fim do desvio, retorna ao PWM anterior
        desvioActive = false;
        //currentPWM = preDesvioPWM; Volta para o último pwm antes da oscilação
        currentPWM = INVERTE ? (neutralPWM - pwm_plus) : (pwm_minus + neutralPWM);
        //currentPWM = INVERTE ? (pwm_plus + neutralPWM) : (pwm_minus - neutralPWM);
        setServoPWM(currentPWM);
        // Marca o último desvio para recomeçar a contagem
        lastDesvioTime = now;
      }
    }
    else {
      // 2) Se não estamos em desvio, pode ser hora de iniciar um
      unsigned long now = millis();
      unsigned long desvioIntervalMs = (unsigned long)(desvioIntervalMin * 60.0 * 1000.0);
      
      // Se passou do intervalo, inicia o desvio
      if ((now - lastDesvioTime) >= desvioIntervalMs) {
        desvioActive = true;
        preDesvioPWM = currentPWM; // guarda onde estava
        desvioStartTime = now;
        
        // Leva o servo para 'desvioPWM'
        currentPWM = desvioPWM;
        setServoPWM(currentPWM);
      }
      else {
        // Se não é hora de desvio, faz a mesma oscilação do teste "a"
        updateOscillation();
      }
    }
  }
}
