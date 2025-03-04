import serial
import threading
import csv
import time
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from threading import Lock

# ------------------------- CONFIGURACOES -------------------------
# Tempo máximo do teste (em minutos). Ao ultrapassar, envia 's'
max_time_minutes = 480.0  # Exemplo: 1 minuto
# Porta serial onde seu Arduino está conectado
PORTA_SERIAL = "COM9"
# Velocidade de comunicação
BAUDRATE = 115200
# -----------------------------------------------------------------

# Variáveis globais de controle
current_csv_file = None
current_csv_writer = None
recording = False     # Se estamos gravando dados no CSV
test_stopped = True   # Se o teste está parado ou rodando

# Vetores para plot
times_list = []
servo_temps_list = []
ambient_temps_list = []
currents_list = []

# Lock para proteger acesso às listas
data_lock = Lock()

def parse_time_str(time_str):
    """Converte 'mm:ss' em segundos (int)."""
    try:
        mm, ss = time_str.split(":")
        mm = int(mm)
        ss = int(ss)
        return mm * 60 + ss
    except:
        return 0

def format_time(x, pos):
    """Formata um valor de tempo (em segundos) para mm:ss no eixo X."""
    minutes = int(x // 60)
    seconds = int(x % 60)
    return f"{minutes:02d}:{seconds:02d}"

def create_new_csv_file():
    """
    Fecha o CSV anterior (se aberto) e cria um novo arquivo .csv
    com base na data_hh_mm atual. Seta 'recording = True'.
    """
    global current_csv_file, current_csv_writer, recording, test_stopped
    
    # Fecha o CSV anterior se ainda estiver aberto
    if current_csv_file and not current_csv_file.closed:
        current_csv_file.close()
    
    # Gera nome com data/hora (até minuto)
    filename_time = time.strftime("%Y%m%d_%H%M")
    filename = f"data_{filename_time}.csv"
    
    current_csv_file = open(filename, "w", newline="", encoding="utf-8")
    current_csv_writer = csv.writer(current_csv_file)
    
    # Opcional: escrever cabeçalho no CSV
    header = ["PWM", "TempAmbiente", "TempServo", "Angle", "Corrente", "Tempo(mm:ss)"]
    current_csv_writer.writerow(header)
    
    # Estamos gravando a partir de agora
    recording = True
    test_stopped = False
    print(f"Novo arquivo CSV criado: {filename}")

def stop_test(port=None):
    global current_csv_file, recording, test_stopped
    
    print("Encerrando teste (mesmo que ja estivesse parado).")
    test_stopped = True
    recording = False
    
    if port is not None:
        port.write(b"s")
    
    if current_csv_file and not current_csv_file.closed:
        current_csv_file.close()
        print("CSV fechado.")


def start_test(port, cmd):
    """
    Inicia um teste (A ou D).
    - Cria novo CSV, limpa dados de plot, zera variáveis de controle.
    - Envia comando 'cmd' para a placa ('a' ou 'd').
    """
    global times_list, servo_temps_list, ambient_temps_list, currents_list
    
    # Cria novo CSV
    create_new_csv_file()
    
    # Limpa dados dos gráficos
    with data_lock:
        times_list.clear()
        servo_temps_list.clear()
        ambient_temps_list.clear()
        currents_list.clear()
    
    # Envia comando para iniciar
    port.write(cmd.encode())
    print("Teste iniciado com comando:", cmd)

def read_serial(port):
    """
    Lê dados da serial e salva no CSV aberto, se 'recording' estiver True.
    Espera receber linhas no formato:
      PWM, tempServo, tempAmbiente, angleVal, corr, timeStr
    Exemplo: "1500,25.3,25.7,45,2.3,00:07"
    """
    global recording, current_csv_writer, test_stopped
    
    while True:
        if port.in_waiting:
            try:
                line = port.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # Pode conter multiplas linhas juntas, se enviadas muito rápido
                    lines = line.split("\n")
                    for l in lines:
                        l = l.strip()
                        if not l:
                            continue
                        data = l.split(",")
                        
                        # Log no console para debug
                        print("Recebido:", data)
                        
                        # Se estamos gravando e temos writer aberto
                        if recording and current_csv_writer and len(data) >= 6:
                            # Escreve no CSV
                            current_csv_writer.writerow(data)
                            current_csv_file.flush()
                            
                            try:
                                # Parse
                                temp_servo = float(data[2])      # temperature do servo
                                temp_amb = float(data[1])        # temperature ambiente
                                corrente = float(data[4])        # corrente
                                t_seconds = parse_time_str(data[5])
                                
                                # Armazena para plot
                                with data_lock:
                                    times_list.append(t_seconds)
                                    servo_temps_list.append(temp_servo)
                                    ambient_temps_list.append(temp_amb)
                                    currents_list.append(corrente)
                            
                            except Exception as e:
                                print("Erro ao converter dados:", e)
            
            except Exception as e:
                print("Erro ao ler dados da serial:", e)

def update_plot(port):
    """
    Atualiza em tempo real o gráfico:
      - Subplot superior: Temperatura do servo e ambiente
      - Subplot inferior: Corrente
    Também verifica se o tempo máximo foi atingido
    e envia 's' caso seja ultrapassado.
    """
    global test_stopped
    
    plt.ion()
    fig, (ax_temp, ax_current) = plt.subplots(2, 1, figsize=(8, 6))
    fig.tight_layout(pad=3)
    
    # Configura subplots
    ax_temp.set_title("Temperaturas x Tempo")
    ax_temp.set_xlabel("Tempo (mm:ss)")
    ax_temp.set_ylabel("Temperatura (°C)")
    ax_temp.xaxis.set_major_formatter(FuncFormatter(format_time))
    
    ax_current.set_title("Corrente x Tempo")
    ax_current.set_xlabel("Tempo (mm:ss)")
    ax_current.set_ylabel("Corrente (A)")
    ax_current.xaxis.set_major_formatter(FuncFormatter(format_time))
    
    # Duas linhas no subplot de temperatura (servo e ambiente)
    line_servo, = ax_temp.plot([], [], 'r-', marker='o', label="Servo")
    line_amb,   = ax_temp.plot([], [], 'b-', marker='o', label="Ambiente")
    ax_temp.legend()
    
    # Linha de corrente
    line_current, = ax_current.plot([], [], 'g-', marker='o', label="Corrente")
    ax_current.legend()
    
    max_time_seconds = max_time_minutes * 60.0
    
    while True:
        # Pega cópia dos dados protegida por lock
        with data_lock:
            xdata = times_list[:]
            ydata_servo = servo_temps_list[:]
            ydata_amb   = ambient_temps_list[:]
            ydata_curr  = currents_list[:]
        
        # Atualiza linhas
        if xdata:
            line_servo.set_data(xdata, ydata_servo)
            line_amb.set_data(xdata, ydata_amb)
            line_current.set_data(xdata, ydata_curr)
            
            ax_temp.relim()
            ax_temp.autoscale_view()
            
            ax_current.relim()
            ax_current.autoscale_view()
            
            # Verifica se atingimos tempo limite
            last_time = xdata[-1]
            if (not test_stopped) and (last_time >= max_time_seconds):
                # Dispara stop
                print(f"Tempo maximo de {max_time_minutes} min atingido.")
                stop_test(port)  # Isso fecha CSV e manda 's'
        
        # Redesenha
        plt.pause(0.5)  # ou plt.show(block=False), mas pause(0.5) é suficiente

def write_serial(port):
    """
    Thread para envio de comandos à placa via console.
    - a: inicia Teste A
    - d: inicia Teste D
    - s: stop
    - 1000..2000: define PWM
    - +XX.xx: angle_plus
    - -XX.xx: angle_minus
    - vXX.xx: speed
    etc.
    """
    while True:
        cmd = input("Digite comando (a, d, s, ou outro): ").strip()
        if not cmd:
            continue
        
        # Se for 'a' ou 'd', iniciamos um novo teste
        if cmd == 'a' or cmd == 'd':
            start_test(port, cmd)  # Cria novo CSV e envia comando
        elif cmd == 's':
            # Para o teste
            stop_test(port)
        else:
            # Comandos genéricos (PWM ou +XX, -XX, vXX etc.)
            port.write(cmd.encode())
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        ser = serial.Serial(PORTA_SERIAL, BAUDRATE, timeout=1)
        print(f"Conectado à placa na porta {PORTA_SERIAL}.")
    except Exception as e:
        print(f"Erro ao conectar na porta {PORTA_SERIAL}:", e)
        exit(1)
    
    # Thread para leitura da serial (grava em CSV se recording=True)
    reader_thread = threading.Thread(target=read_serial, args=(ser,), daemon=True)
    reader_thread.start()
    
    # Thread para envio de comandos via console
    write_thread = threading.Thread(target=write_serial, args=(ser,), daemon=True)
    write_thread.start()
    
    # Plotagem e controle do tempo máximo no thread principal
    update_plot(ser)
