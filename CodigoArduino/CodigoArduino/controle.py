import serial
import threading
import csv
import time
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from threading import Lock

# Listas para armazenar tempo (em segundos) e temperatura para plotagem
times_list = []
temps_list = []

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

def read_serial(port):
    """
    Lê dados da serial e salva no CSV.
    Espera receber linhas no formato:
    [PWM, temperature1, temperature2, angleVal, currentMeasurement, timeStr]
    Exemplo: "1500,25.3,25.7,45,2.3,00:07"
    """
    with open("data.csv", "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        while True:
            if port.in_waiting:
                try:
                    # Lê a linha bruta
                    line = port.readline().decode('utf-8').strip()
                    if line:
                        # Pode conter múltiplas amostras se a placa enviar várias juntas
                        lines = line.split("\n")
                        for l in lines:
                            l = l.strip()
                            if not l:
                                continue
                            data = l.split(",")
                            # Grava tudo no CSV
                            writer.writerow(data)
                            csvfile.flush()
                            
                            print("Recebido:", data)
                            
                            # Precisamos de pelo menos 6 colunas para fazer o parsing correto
                            if len(data) >= 6:
                                try:
                                    temperature1 = float(data[1])
                                    t_seconds = parse_time_str(data[5])
                                    
                                    # Atualiza as listas em memória (para plot)
                                    with data_lock:
                                        times_list.append(t_seconds)
                                        temps_list.append(temperature1)
                                except Exception as e:
                                    print("Erro ao converter dados:", e)
                except Exception as e:
                    print("Erro ao ler dados:", e)

def update_plot():
    """Atualiza em tempo real o gráfico Temperatura (Temp1) x Tempo."""
    plt.ion()
    fig, ax = plt.subplots()
    ax.set_xlabel("Tempo (mm:ss)")
    ax.set_ylabel("Temperatura1 (°C)")
    ax.xaxis.set_major_formatter(FuncFormatter(format_time))
    line, = ax.plot([], [], 'r-', marker='o')
    
    while True:
        # Bloqueia as listas para leitura
        with data_lock:
            # Copiamos os dados para evitar leituras simultâneas
            xdata = list(times_list)
            ydata = list(temps_list)
        
        if xdata and ydata:
            line.set_data(xdata, ydata)
            ax.relim()
            ax.autoscale_view()
        
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.5)

def write_serial(port):
    """Thread para envio de comandos à placa via console."""
    while True:
        cmd = input("Digite o comando (a, d, s ou valor PWM entre 1000 e 2000): ")
        if cmd:
            port.write(cmd.encode())

if __name__ == "__main__":
    try:
        ser = serial.Serial("COM9", 115200, timeout=1)
        print("Conectado à placa na porta COM9.")
    except Exception as e:
        print("Erro ao conectar na porta COM9:", e)
        exit(1)
    
    # Thread para leitura da serial e gravação no CSV
    reader_thread = threading.Thread(target=read_serial, args=(ser,), daemon=True)
    reader_thread.start()
    
    # Thread para envio de comandos
    write_thread = threading.Thread(target=write_serial, args=(ser,), daemon=True)
    write_thread.start()
    
    # Plotagem em tempo real no thread principal
    update_plot()
