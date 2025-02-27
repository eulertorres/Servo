#include <Arduino.h>
#include <Servo.h>
 
// --------------------- Definições de pinos ---------------------
#define SERVO_PIN       9    // Pino de controle do servo
#define MCP9701A1_PIN   A0   // Primeiro sensor de temperatura
#define MCP9701A2_PIN   A1   // Segundo sensor de temperatura (adicionado)
#define ACS712_PIN      A2   // Pino analógico para sensor de corrente (realocado)

// Se verdadeiro, o "stop" coloca o servo em PWM_max em vez de PWM_min
#define INVERTE true
 
// ---------------------- Variáveis e constantes -----------------
Servo servo;
 
// Parâmetros para conversão de ângulo para PWM (em microsegundos)
const float PWM_min = 1000;
const float PWM_max = 2000;
const float angle_min = 0;
const float angle_max = 100;
 
// Parâmetros gerais do teste
const float angle_plus = 40;   // Offset + em graus
const float angle_minus = 40;  // Offset - em graus
int   neutralPWM = 1515;         // Neutro definido diretamente em PWM
const float speed = 10;          // Velocidade em °/s
float stepPWM = 1;               // Movimento suave (passo)
 
// Cálculo de limites e frequências
const float res = (angle_max - angle_min) / (PWM_max - PWM_min); // Conversão personalizada
const float freq_att = (res == 0) ? 1 : speed / res;             // Evitar divisão por zero
unsigned long delay_ms = (freq_att == 0) ? 10 : (int)(stepPWM / (freq_att / 1000));
 
// Limites de PWM correspondentes aos offsets
int pwm_plus  = (int)(angle_plus  * (1.0 / res));
int pwm_minus = (int)(angle_minus * (1.0 / res));
 
// Booleans para controle dos testes
bool testARunning = false;
bool testDRunning = false;
 
// Variáveis de oscilação
int currentPWM = 0;
int direction = 1;
 
// Timer de atualização do servo
unsigned long lastServoUpdateTime = 0;
 
// Variáveis para a tarefa de amostragem
const unsigned long sampleInterval = 250; // Intervalo de amostragem (ms)
 
// Controle de tempo do teste
unsigned long testStartTime = 0;
 
// ---------- Parâmetros do teste "d" -----------
// - A cada 'desvioIntervalMin' minutos, desviar para 'desvioPWM' por 'desvioDurationSec' segundos
float desvioIntervalMin = 0.1;    // 0.1 min = 6s (exemplo)
float desvioDurationSec = 2.0;    // Duração do desvio, em segundos
const float AnguloCritico = 0.5;  // Em graus, ou equivalente
// Converte ângulo crítico p/ PWM: (AnguloCritico * (1/res)) + PWM_min
const int desvioPWM = (int)(AnguloCritico * (1.0 / res) + PWM_min);
bool desvioActive = false;
unsigned long lastDesvioTime = 0;
unsigned long desvioStartTime = 0;
int preDesvioPWM = 0;

// -------------------- Funções auxiliares --------------------

// Função genérica para ler temperatura de um MCP9701A em qualquer pino analógico
float readMCP9701A(uint8_t pin) {
    uint16_t reading = analogRead(pin);
    // Conversão para tensão (assumindo referência de 5 V)
    float readingVolts = (float)reading * 5.0 / 1023.0;
    // Fórmula para MCP9701A: (VOUT - 0,4 V) / 19,5 mV/°C
    float temperatureCelsius = (readingVolts - 0.4) / 0.0195;
    return temperatureCelsius;
}
 
// Aplica PWM no servo
void setServoPWM(int pwmValue) {
    servo.writeMicroseconds(pwmValue);
}
 
// Converte um valor PWM -> Ângulo
int pwmToAngle(int pwm) {
    return map(pwm, (int)PWM_min, (int)PWM_max, (int)angle_min, (int)angle_max);
}
 
// Converte Ângulo -> PWM
int angleToPWM(int angle) {
    return map(angle, (int)angle_min, (int)angle_max, (int)PWM_min, (int)PWM_max);
}
 
// Processa comandos via Serial
void processSerial() {
    while (Serial.available() > 0) {
        if (isDigit(Serial.peek())) {
            int pwmValue = Serial.parseInt();
            if (pwmValue >= PWM_min && pwmValue <= PWM_max) {
                // Para qualquer teste se definimos PWM diretamente
                testARunning = false;
                testDRunning = false;
                desvioActive  = false;
               
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
                // Inicia teste A
                testARunning   = true;
                testDRunning   = false;
                desvioActive   = false;
                currentPWM     = neutralPWM;
                direction      = 1;
                testStartTime  = millis();
                lastDesvioTime = testStartTime; // Só pra zerar
                Serial.println("Teste A iniciado.");
            } 
            else if (cmd == 'd') {
                // Inicia teste D
                testARunning   = false;
                testDRunning   = true;
                desvioActive   = false;
                currentPWM     = neutralPWM;
                direction      = 1;
                testStartTime  = millis();
                lastDesvioTime = testStartTime; // zera para começar a contagem
                Serial.println("Teste D iniciado (desvios periódicos).");
            } 
            else if (cmd == 's') {
                // Stop
                testARunning = false;
                testDRunning = false;
                desvioActive = false;
                currentPWM   = INVERTE ? (int)PWM_max : (int)PWM_min;
                setServoPWM(currentPWM);
                Serial.println("Teste interrompido.");
            }
        }
    }
}
 
// Atualiza oscilação do servo (movimento igual ao Teste A)
void updateOscillation() {
    unsigned long now = millis();
    if (now - lastServoUpdateTime >= delay_ms) {
        lastServoUpdateTime = now;
        currentPWM += direction * (int)stepPWM;
       
        int limUp   = neutralPWM + pwm_plus;
        int limDown = neutralPWM - pwm_minus;
       
        if (direction > 0 && currentPWM >= limUp) {
            currentPWM = limUp;
            direction = -1;
        }
        else if (direction < 0 && currentPWM <= limDown) {
            currentPWM = limDown;
            direction = 1;
        }
        setServoPWM(currentPWM);
    }
}
 
// Amostragem e envio de dados pela Serial
void sampleTask() {
    // Apenas amostra se algum teste estiver em andamento
    if (testARunning || testDRunning) {
        // Leitura de corrente (ACS712)
        int acsValue = analogRead(ACS712_PIN);
        float currentMeasurement = acsValue;  // Ajuste a conversão conforme necessário

        // Leitura dos dois sensores de temperatura
        float temperature1 = readMCP9701A(MCP9701A1_PIN);
        float temperature2 = readMCP9701A(MCP9701A2_PIN);

        // Cálculo do ângulo (a partir do PWM atual)
        int angleVal = pwmToAngle(currentPWM);

        // Cálculo do tempo decorrido
        unsigned long elapsedMs = millis() - testStartTime;
        unsigned int totalSec = elapsedMs / 1000;
        unsigned int mm = totalSec / 60;
        unsigned int ss = totalSec % 60;
 
        char timeStr[6];
        snprintf(timeStr, sizeof(timeStr), "%02d:%02d", mm, ss);

        // Monta linha de dados para envio
        // Formato: PWM,Temp1,Temp2,Ângulo,Corrente,Tempo
        String sampleLine =  String(currentPWM)    + "," +
                             String(temperature1)  + "," +
                             String(temperature2)  + "," +
                             String(angleVal)      + "," +
                             String(currentMeasurement) + "," +
                             timeStr + "\n";
 
        // Envia a linha pelo Serial
        Serial.print(sampleLine);
    }
}
 
void setup() {
    Serial.begin(115200);
    delay(100);

    pinMode(SERVO_PIN, OUTPUT);
    servo.attach(SERVO_PIN);

    // Inicializa o servo na posição mínima ou máxima
    currentPWM = INVERTE ? (int)PWM_max : (int)PWM_min;
    setServoPWM(currentPWM);
    delay(300);

    Serial.println("=== Sistema Iniciado ===");
    Serial.print("res = "); Serial.println(res);
    Serial.print("delay_ms = "); Serial.println(delay_ms);
    Serial.print("desvioPWM = "); Serial.println(desvioPWM);
    Serial.println("========================");
}
 
void loop() {
    // Lê comandos da Serial
    processSerial();

    // ======================== TESTE A =========================
    if (testARunning) {
        updateOscillation();
    }

    // ======================== TESTE D =========================
    if (testDRunning) {
        // 1) Se estamos em desvio, verificar se já acabou o tempo
        if (desvioActive) {
            unsigned long now = millis();
            unsigned long desvioDurationMs = (unsigned long)(desvioDurationSec * 1000.0);

            if ((now - desvioStartTime) >= desvioDurationMs) {
                // Fim do desvio → retorna ao PWM anterior
                desvioActive = false;
                currentPWM   = preDesvioPWM; // Volta de onde parou
                setServoPWM(currentPWM);
                // Marca quando acabou este desvio
                lastDesvioTime = now;
            }
        }
        else {
            // 2) Se não estamos em desvio, verificar se está na hora de iniciar um
            unsigned long now = millis();
            unsigned long desvioIntervalMs = (unsigned long)(desvioIntervalMin * 60.0 * 1000.0);

            if ((now - lastDesvioTime) >= desvioIntervalMs) {
                // Inicia o desvio
                desvioActive     = true;
                preDesvioPWM     = currentPWM;   // guarda PWM atual para voltar depois
                desvioStartTime  = now;
                
                // Move o servo para desvio
                currentPWM = desvioPWM;
                setServoPWM(currentPWM);
            } 
            else {
                // Se não é hora de desvio, faz a mesma oscilação do teste "a"
                updateOscillation();
            }
        }
    }

    // Tarefa de amostragem periódica
    static unsigned long lastSampleTime = 0;
    if (millis() - lastSampleTime >= sampleInterval) {
        lastSampleTime = millis();
        sampleTask();
    }
}
