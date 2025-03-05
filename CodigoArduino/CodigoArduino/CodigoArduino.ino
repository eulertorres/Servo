#include <Arduino.h>
#include <Servo.h>

// --------------------- Definições de pinos ---------------------
#define SERVO_PIN       9    // Pino de controle do servo
#define MCP9701A1_PIN   A0   // Primeiro sensor de temperatura
#define MCP9701A2_PIN   A1   // Segundo sensor de temperatura (adicionado)
#define ACS712_PIN      A5   // Pino analógico para sensor de corrente (realocado)

// Se verdadeiro, o "stop" coloca o servo em PWM_max em vez de PWM_min
#define INVERTE false

// ---------------------- Variáveis e constantes -----------------
Servo servo;

// Parâmetros para conversão de ângulo para PWM (em microsegundos)
const float PWM_min = 1000;
const float PWM_max = 2000;
const float angle_min = 0;
const float angle_max = 100;

// Parâmetros gerais do teste
float angle_plus = 17.02;   // Offset + em graus (pode ser alterado via Serial com +XX)
float angle_minus = 0;      // Offset - em graus (pode ser alterado via Serial com -XX)
int   neutralPWM = 1000;    // Neutro definido diretamente em PWM
float speed = 10;           // Velocidade em °/s (pode ser alterado via Serial com vXX)
float stepPWM = 1;          // Movimento suave (passo)

// Cálculo de limites e frequências (variáveis que serão recalculadas quando mudarmos parâmetros)
float res;       // (angle_max - angle_min) / (PWM_max - PWM_min)
float freq_att;  // speed / res
unsigned long delay_ms; // Determina a cadência de atualização do servo

// Limites de PWM correspondentes aos offsets
int pwm_plus;
int pwm_minus;

// Booleans para controle dos testes
bool testARunning = false;
bool testDRunning = false;
bool testFRunning = false;

// Variáveis de oscilação
int currentPWM = 0;
int direction = 1;

// Timer de atualização do servo
unsigned long lastServoUpdateTime = 0;

// Variáveis para a tarefa de amostragem
const unsigned long sampleInterval = 250; // Intervalo de amostragem (ms)

// Controle de tempo do teste
unsigned long testStartTime = 0;

// ---------- Parâmetros do teste "d" e "f" -----------
// - A cada 'desvioIntervalMin' minutos, desviar para 'desvioPWM' por 'desvioDurationSec' segundos
float desvioIntervalMin = 0.3;    // 0.1 min = 6s (exemplo)
float desvioDurationSec = 20;    // Duração do desvio, em segundos
const float AnguloCritico = 0;  // Em graus
// Converte ângulo crítico p/ PWM: (AnguloCritico * (1/res)) + PWM_min
int desvioPWM = 0;
bool desvioActive = false;
unsigned long lastDesvioTime = 0;
unsigned long lastDesvioTime2 = 0;
unsigned long desvioStartTime = 0;
int preDesvioPWM = 0;

// ----------- Parâmetros do teste "f" -----------
// Offsets para o teste F
float angle_plusF = 0;   // Offset + em graus para teste F
float angle_minusF = 51.22;      // Offset - em graus para teste F
int lastNeutralPWM = 1000;
float lastangle_plus = angle_plus;
float lastangle_minus = angle_minus;

// ---------- Variáveis de transição para o Teste F ----------
// Estados da transição entre oscilação normal e com desvio F
enum TransitionState { NO_TRANSITION, TRANSITION_TO_F, TRANSITION_FROM_F };
TransitionState transitionState = NO_TRANSITION;
unsigned long transitionStartTime = 0; // Momento que a transição começou
unsigned long transitionDuration = 0;    // Duração da transição (em ms)

// -------------------- Funções auxiliares --------------------

// Recalcula variáveis derivadas de angle_plus, angle_minus e speed.
// Chame esta função sempre que mudar um desses parâmetros via Serial.
void recalcularVariaveis()
{
  // Recalcula res
  res = (angle_max - angle_min) / (PWM_max - PWM_min);

  // Evita divisão por zero
  if (res == 0) res = 1.0;

  // Freq de atualização
  freq_att = speed / res;
  if (freq_att == 0) freq_att = 1.0;

  // delay_ms depende de freq_att e do step
  delay_ms = (unsigned long)(stepPWM / (freq_att / 1000.0));
  if (delay_ms == 0) delay_ms = 10;

  // Limites de PWM correspondentes aos novos offsets
  pwm_plus  = (int)(angle_plus  * (1.0 / res));
  pwm_minus = (int)(angle_minus * (1.0 / res));

  // Recalcula desvioPWM (porque depende de res)
  desvioPWM = (int)(AnguloCritico * (1.0 / res) + PWM_min);
}

// Função genérica para ler temperatura de um MCP9701A em qualquer pino analógico
float readMCP9701A(uint8_t pin) {
    // Conversão para tensão (assumindo referência de 5 V)
    float readingVolts = (float)analogRead(pin) * 5.0 / 1023.0;

    // Fórmula para MCP9701A: (VOUT - 0,4 V) / 19,5 mV/°C
    float temperatureCelsius = (readingVolts - 0.4) / 0.0195;

    return temperatureCelsius;
}

float readACS712(const uint8_t sensorPin) {
    float readingVolts = (float)analogRead(sensorPin) * 5.0 / 1023.0;
    float readingAmps  = (readingVolts - 2.5) / 0.185;
    return readingAmps;
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

        // Se o próximo caractere for dígito, interpretamos como valor PWM (1000..2000)
        if (isDigit(Serial.peek())) {
            int pwmValue = Serial.parseInt();
            if (pwmValue >= PWM_min && pwmValue <= PWM_max) {
                // Para qualquer teste se definimos PWM diretamente
                testARunning = false;
                testDRunning = false;
                testFRunning = false;
                desvioActive = false;
                transitionState = NO_TRANSITION;

                neutralPWM = pwmValue;
                lastNeutralPWM = neutralPWM;
                currentPWM = neutralPWM;
                setServoPWM(currentPWM);
                int angleVal = pwmToAngle(currentPWM);

                Serial.print("Novo Neutro - Servo em PWM: ");
                Serial.print(pwmValue);
                Serial.print(" - Ângulo: ");
                Serial.println(angleVal);
            }
        }
        else {
            // Caso contrário, vamos ler o primeiro caractere para decidir o comando
            char cmd = Serial.read();

            // Testes pré-definidos
            if (cmd == 'a') {
                // Inicia teste A
                testARunning   = true;
                testDRunning   = false;
                testFRunning   = false;
                desvioActive   = false;
                transitionState = NO_TRANSITION;
                currentPWM     = neutralPWM;
                angle_plus = lastangle_plus;
                angle_minus = lastangle_minus;
                recalcularVariaveis();
                direction      = 1;
                testStartTime  = millis();
                lastDesvioTime = testStartTime; // Só pra zerar
                Serial.println("Teste A iniciado.");
            }
            else if (cmd == 'd') {
                // Inicia teste D
                testARunning   = false;
                testDRunning   = true;
                testFRunning   = false;
                desvioActive   = false;
                transitionState = NO_TRANSITION;
                currentPWM     = neutralPWM;
                angle_plus = lastangle_plus;
                angle_minus = lastangle_minus;
                recalcularVariaveis();
                direction      = 1;
                testStartTime  = millis();
                lastDesvioTime = testStartTime; // zera para começar a contagem
                Serial.println("Teste D iniciado (desvios periódicos, estaticos).");
            }
            else if (cmd == 'f') {
                // Inicia teste F
                testARunning   = false;
                testDRunning   = false;
                testFRunning   = true;
                desvioActive   = false;
                transitionState = NO_TRANSITION;
                currentPWM     = neutralPWM;
                // Reinicia os offsets para os valores normais
                angle_plus = lastangle_plus;
                angle_minus = lastangle_minus;
                recalcularVariaveis();
                direction      = 1;
                testStartTime  = millis();
                lastDesvioTime = testStartTime; // zera para começar a contagem
                Serial.println("Teste F iniciado (desvios periódicos, oscilatórios com transição suave).");
            }
            else if (cmd == 's') {
                // Stop
                testARunning = false;
                testDRunning = false;
                testFRunning = false;
                desvioActive = false;
                transitionState = NO_TRANSITION;
                currentPWM   = INVERTE ? (int)PWM_max : (int)PWM_min;
                setServoPWM(currentPWM);
                Serial.println("Teste interrompido.");
            }
            else if (cmd == '+') {
                // Define angle_plus (lê float após o '+')
                float val = Serial.parseFloat();
                angle_plus = val;
                lastangle_plus = angle_plus;
                recalcularVariaveis();
                Serial.print("Novo angle_plus = ");
                Serial.println(angle_plus);
            }
            else if (cmd == '-') {
                // Define angle_minus (lê float após o '-')
                float val = Serial.parseFloat();
                angle_minus = val;
                lastangle_minus = angle_minus;
                recalcularVariaveis();
                Serial.print("Novo angle_minus = ");
                Serial.println(angle_minus);
            }
            else if (cmd == 'v') {
                // Define velocidade (speed) em graus/s
                float val = Serial.parseFloat();
                speed = val;
                recalcularVariaveis();
                Serial.print("Nova speed = ");
                Serial.print(speed);
                Serial.println(" °/s");
            }
            // Se não for nenhuma das opções conhecidas, apenas descarta
            else {
                //Serial.println("COMANDO NÃO RECONHECIDO");
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
    if (testARunning || testDRunning || testFRunning) {
        // Leitura de corrente (ACS712)
        float currentMeasurement = readACS712(ACS712_PIN);

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

    // Primeiro cálculo das variáveis baseadas em angle_plus, angle_minus e speed
    recalcularVariaveis();

    // Impressão dos comandos disponíveis
    Serial.println("=== Sistema Iniciado ===");
    Serial.println("COMANDOS DISPONÍVEIS:");
    Serial.println(" - a: Inicia Teste A (oscilacao simples)");
    Serial.println(" - d: Inicia Teste D (desvios periodicos estaticos)");
    Serial.println(" - f: Inicia Teste F (desvios periodicos dinamicos com transição suave)");
    Serial.println(" - s: Stop (para e coloca servo em PWM_min ou PWM_max se INVERTE=true)");
    Serial.println(" - 1000..2000: Define diretamente o PWM do servo (ex: 1500)");
    Serial.println(" - +XX.xx: Define angle_plus em graus (ex: +35.4 -> 35.4 graus)");
    Serial.println(" - -XX.xx: Define angle_minus em graus (ex: -18  -> 18 graus)");
    Serial.println(" - vXX.xx: Define speed em graus/s (ex: v40   -> 40 graus/s)");
    Serial.println("=========================================");
}

void loop() {
    // Lê comandos da Serial
    processSerial();

    // ======================== TESTE A =========================
    if (testARunning) {
        neutralPWM = lastNeutralPWM;
        updateOscillation();
    }

    // ======================== TESTE D =========================
    if (testDRunning) {
        neutralPWM = lastNeutralPWM;
        // 1) Se estamos em desvio, verificar se já acabou o tempo
        if (desvioActive) {
            unsigned long now = millis();
            unsigned long desvioDurationMs = (unsigned long)(desvioDurationSec * 1000.0);

            if ((now - desvioStartTime) >= desvioDurationMs) {
                // Fim do desvio → retorna ao PWM anterior
                desvioActive = false;
                currentPWM   = preDesvioPWM; // Volta de onde parou
                setServoPWM(currentPWM);
                lastDesvioTime = now;
            }
            else {
                updateOscillation();
            }
        }
        else {
            // 2) Se não estamos em desvio, verificar se está na hora de iniciar um
            unsigned long now = millis();
            unsigned long desvioIntervalMs = (unsigned long)(desvioIntervalMin * 60.0 * 1000.0);

            if ((now - lastDesvioTime) >= desvioIntervalMs) {
                // Inicia o desvio imediatamente (teste D: desvio estático)
                desvioActive     = true;
                preDesvioPWM     = currentPWM;   // guarda PWM atual para voltar depois
                desvioStartTime  = now;
                currentPWM = desvioPWM;
                setServoPWM(currentPWM);
            }
            else {
                updateOscillation();
            }
        }
    }

    // ======================== TESTE F =========================
    if (testFRunning) {
        neutralPWM = lastNeutralPWM;
        unsigned long now = millis();
        unsigned long desvioIntervalMs = (unsigned long)(desvioIntervalMin * 60.0 * 1000.0);

        // Fases de transição para o Teste F:
        if (transitionState == TRANSITION_TO_F) {
            // Transição dos offsets normais para os offsets F
            unsigned long elapsed = now - transitionStartTime;
            float t = (float)elapsed / transitionDuration;
            if (t >= 1.0) {
                t = 1.0;
                transitionState = NO_TRANSITION;
                desvioActive = true;
                desvioStartTime = now;
                preDesvioPWM = currentPWM;
            }
            angle_plus = lastangle_plus + t * (angle_plusF - lastangle_plus);
            angle_minus = lastangle_minus + t * (angle_minusF - lastangle_minus);
            recalcularVariaveis();
            updateOscillation();
        }
        else if (transitionState == TRANSITION_FROM_F) {
            // Transição dos offsets F de volta para os offsets normais
            unsigned long elapsed = now - transitionStartTime;
            float t = (float)elapsed / transitionDuration;
            if (t >= 1.0) {
                t = 1.0;
                transitionState = NO_TRANSITION;
                desvioActive = false;
                lastDesvioTime = now;  // marca o fim do desvio
            }
            angle_plus = angle_plusF + t * (lastangle_plus - angle_plusF);
            angle_minus = angle_minusF + t * (lastangle_minus - angle_minusF);
            recalcularVariaveis();
            updateOscillation();
        }
        else if (desvioActive) {
            // Estamos na fase de desvio com offsets F definidos
            updateOscillation();
            unsigned long desvioDurationMs = (unsigned long)(desvioDurationSec * 1000.0);
            if ((now - desvioStartTime) >= desvioDurationMs) {
                // Ao terminar o desvio, inicia a transição de retorno
                transitionState = TRANSITION_FROM_F;
                transitionStartTime = now;
                float diff_plus = fabs(angle_plusF - lastangle_plus);
                float diff_minus = fabs(angle_minusF - lastangle_minus);
                float maxDiff = (diff_plus > diff_minus ? diff_plus : diff_minus);
                transitionDuration = (unsigned long)((maxDiff / speed) * 1000);
            }
        }
        else {
            // Se não estamos em desvio nem em transição: verifica se é hora de iniciar o desvio
            if ((now - lastDesvioTime) >= desvioIntervalMs) {
                // Inicia a transição para os offsets F
                transitionState = TRANSITION_TO_F;
                transitionStartTime = now;
                float diff_plus = fabs(angle_plusF - lastangle_plus);
                float diff_minus = fabs(angle_minusF - lastangle_minus);
                float maxDiff = (diff_plus > diff_minus ? diff_plus : diff_minus);
                transitionDuration = (unsigned long)((maxDiff / speed) * 1000);
            }
            else {
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
