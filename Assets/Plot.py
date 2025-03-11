# -*- coding: utf-8 -*-

import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.optimize import curve_fit
import numpy as np
from math import sqrt
from matplotlib.ticker import MaxNLocator

# 1) Caminhos com base no local do script (Plot.py)
script_dir = os.path.dirname(os.path.abspath(__file__))  # pasta do Plot.py
repo_dir   = os.path.dirname(script_dir)                 # pasta raiz do repositório

# A pasta com os CSVs brutos
csv_directory = os.path.join(repo_dir, 'Dados_bruto')

# Pasta na qual desejamos salvar resultados organizados por servo
database_dir  = os.path.join(repo_dir, 'Database')
os.makedirs(database_dir, exist_ok=True)

# 2) Selecionar arquivos CSV
csv_files = [
    f for f in os.listdir(csv_directory)
    if f.endswith('.csv') and f.count("_") > 3
]

print("Arquivos CSV encontrados em 'Dados_bruto':")
print("\n".join(csv_files))

# 3) Remoção de linhas fora do intervalo de teste ("Teste A iniciado." / "Teste interrompido.")
for csv_file in csv_files:
    if "data" in csv_file:
        continue

    csv_path = os.path.join(csv_directory, csv_file)
    test_start = 0
    test_end   = 0

    with open(csv_path, 'r') as file:
        # Acha onde começa
        for i, line in enumerate(file):
            if line.strip() == "Teste A iniciado.":
                test_start = i + 1

        # Volta para o começo, acha onde termina
        file.seek(0)
        for i, line in enumerate(file):
            if line.strip() == "Teste interrompido." and i > test_start:
                test_end = i
                break

    # Lê tudo e reescreve só o trecho [test_start:test_end]
    with open(csv_path, 'r') as file:
        lines = file.readlines()

    with open(csv_path, 'w') as file:
        file.writelines(lines[test_start:test_end])

# 4) Leitura dos CSV em DataFrames
dfs = {}
columns = None
for csv_file in csv_files:
    csv_path = os.path.join(csv_directory, csv_file)
    if "data" in csv_file:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8')
        if not columns:
            columns = df.columns.tolist()
    else:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8', header=None)
        # Atribui cabeçalhos compatíveis com o CSV "data"
        if columns:
            df.columns = columns
    dfs[csv_file] = df

sample_time_s = 0.25

# 5) Inserir colunas adicionais: tempo e delta de temperatura
for csv_file, df in dfs.items():
    df['time_s']    = [i * sample_time_s for i in range(len(df))]
    df['temp_rise'] = df['TempServo'] - df['TempAmbiente']

# 6) Funções utilitárias
def temperature_model(t, T0, tau):
    return T0 * (1 - np.exp(-t / tau))

def format_seconds_to_hhmmss(seconds: int) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours,   minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}"

def set_time_axis(ax, max_time_s, time_step):
    x_ticks = [x * time_step for x in range(0, int(max_time_s / time_step) + 2)]
    x_tick_labels = [format_seconds_to_hhmmss(t) for t in x_ticks]
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_tick_labels)
    ax.set_xlabel("Tempo [hh:mm]")
    ax.set_xlim([0, max_time_s])
    ax.yaxis.set_major_locator(MaxNLocator(nbins=8))

# 7) Função para gerar um PDF com 4 gráficos
def generate_pdf(title_label, df):
    fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(10, 15))
    fig.suptitle(title_label, fontsize=16, y=0.97)
    fig.subplots_adjust(top=0.92, hspace=0.3)

    max_time_s = df['time_s'].iloc[-1]
    if max_time_s < 2400:
        time_step = 300
    elif max_time_s < 6000:
        time_step = 600
    else:
        time_step = 1800

    # Plot 1 - Temperaturas
    axes[0].plot(df['time_s'], df['TempServo'],    label="Servo",    color='tab:blue')
    axes[0].plot(df['time_s'], df['TempAmbiente'], label="Ambiente", color='darkturquoise')
    axes[0].set_ylabel('Temperatura [°C]')
    axes[0].legend(loc='center right', framealpha=1.0)
    axes[0].set_title('Temperaturas Medidas')

    # Plot 2 - Ajuste exponencial do aquecimento (temp_rise)
    params, _ = curve_fit(temperature_model, df['time_s'], df['temp_rise'], p0=[15, 2])
    T0_fit, tau_fit = params
    axes[1].plot(df['time_s'], df['temp_rise'], label='Servo', color='lightsalmon')
    axes[1].plot(df['time_s'], temperature_model(df['time_s'], T0_fit, tau_fit), label="Fit", color='red', linewidth=2)
    axes[1].text(
        0.98, 0.08,
        f"Temperatura Final: {T0_fit:.2f}°C\nConstante de Tempo: {tau_fit:.2f}s",
        ha='right', va='bottom',
        bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'),
        transform=axes[1].transAxes
    )
    axes[1].grid(True)
    axes[1].set_ylabel('Temperatura [°C]')
    axes[1].legend(loc='center right', framealpha=1.0)
    axes[1].set_title('Aquecimento do Servo')

    # Plot 3 - Corrente e RMS
    axes[2].plot(df['time_s'], df['Corrente'], color='darkseagreen', label="Corrente", linewidth=0.5)
    rolling_window = int(10.0 / 0.25)  # 10s / 0.25s = 40 amostras
    rms_current = df['Corrente'].rolling(window=rolling_window).apply(
        lambda x: np.sqrt(np.mean(np.square(x))),
        raw=True
    )
    rms_unique = np.sqrt(np.mean(np.square(df['Corrente'])))
    axes[2].plot(df['time_s'], rms_current, label="RMS", color='tab:green')
    axes[2].legend(loc='lower left', framealpha=1.0)

    if rms_unique < 1.0:
        text_rms = f"RMS: {rms_unique * 1000.0:.2f} mA"
    else:
        text_rms = f"RMS: {rms_unique:.2f} A"

    axes[2].text(
        0.98, 0.08,
        text_rms,
        ha='right', va='bottom',
        bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'),
        transform=axes[2].transAxes
    )
    axes[2].set_ylabel('Corrente [A]')
    axes[2].set_title('Corrente Medida')

    # Plot 4 - Zoom em torno do ângulo mínimo
    max_value_index = np.argmin(df['Angle'])
    # Se o índice estiver muito no começo, shift para o meio
    if max_value_index < 150.0 / 0.25:  
        max_value_index = len(df['Angle']) // 2
    starting_time_zoom = max_value_index * 0.25 - 120
    ending_time_zoom   = max_value_index * 0.25 + 120

    axes[3].set_xlim([starting_time_zoom, ending_time_zoom])
    axes[3].plot(df['time_s'], df['Corrente'], label="Corrente", color='darkseagreen', linewidth=0.5)
    axes[3].plot(df['time_s'], rms_current,   label="RMS",      color='tab:green')

    twin3 = axes[3].twinx()
    twin3.plot(df['time_s'], df['Angle'], label="Ângulo", color='teal')
    # Para que Corrente/RMS apareçam na legenda do twin também
    twin3.plot([0], [0], label="Corrente", color='darkseagreen', linewidth=0.5)
    twin3.plot([0], [0], label="RMS",      color='tab:green')

    axes[3].set_title(
        f"Corrente e Ângulo [{format_seconds_to_hhmmss(int(starting_time_zoom))}"
        f" - {format_seconds_to_hhmmss(int(ending_time_zoom))}]"
    )
    axes[3].set_xlabel("Tempo [s]")
    axes[3].set_ylabel("Corrente [A]")
    twin3.set_ylabel("Ângulo [°]")
    twin3.set_ylim([0, 90])
    twin3.set_yticks([15*x for x in range(7)])
    corr_min, corr_max = df['Corrente'].min(), df['Corrente'].max()
    axes[3].set_yticks(np.linspace(corr_min - 0.2, corr_max + 0.2, 7))
    axes[3].set_ylim([corr_min - 0.2, corr_max + 0.2])
    twin3.grid(True)
    twin3.legend(loc='lower left', framealpha=1.0)

    # Ajuste de eixos de tempo
    x_ticks = [x * time_step for x in range(0, int(max_time_s / time_step) + 2)]
    x_tick_labels = [format_seconds_to_hhmmss(t) for t in x_ticks]

    for ax in axes:
        if ax.get_autoscale_on():
            ax.set_xticks(x_ticks)
            ax.set_xticklabels(x_tick_labels)
            ax.set_xlabel("Tempo [hh:mm]")
            ax.set_xlim([0, max_time_s])
            ax.yaxis.set_major_locator(MaxNLocator(nbins=8))
        ax.grid(True)

    return fig

# 8) Dicionário de mapeamento do nome do servo
servo_name_mapping = {
    'Leao':        'B1',
    'Capricornio': 'B2',
    '11':          'B3',
    '18':          'B4',
    'Escorpiao':   'X1',
    'Aquario':     'X2',
    '10':          'X3',
    '7':           'X4'
}

# Descobrir servo e teste a partir do nome do arquivo
# file_mapping[csv_file] => Título a ser usado
# servo_mapping[csv_file] => retorna B1, B2 etc.
file_mapping   = {}
servo_mapping  = {}
test_mapping   = {}

for csv_file in csv_files:
    # Exemplo: "05-XYZ_Aquario_Arq.csv" -> args = ["05", "XYZ", "Aquario", "Arq.csv"]
    args = csv_file.replace("-", "_").split("_")

    if "data" in csv_file:
        # Ex.: ..._data_xxx_...   # Ajuste conforme seu padrão
        servo_type = args[3]
        servo_name = args[4]
        test_name  = args[5].split('.')[0]
    else:
        # Ex.: "05-xx_xxx_xxx.csv"
        servo_type = args[1]
        servo_name = args[2]
        test_name  = args[0]

    servo_label = servo_name_mapping.get(servo_name, servo_name)
    servo_mapping[csv_file] = servo_label
    test_mapping[csv_file]  = f"{servo_type}_{test_name}"
    file_mapping[csv_file]  = f"{servo_type}_{test_name}_{servo_label}"

# 9) Geração de PDFs e PNGs em [Repositorio]/Database/[Nome_do_servo]
for csv_file, df in dfs.items():
    # Identifica o servo e nome do teste
    servo_label = servo_mapping[csv_file]
    test_label  = test_mapping[csv_file]
    full_label  = file_mapping[csv_file]  # TipoTeste_Servo

    # Pasta do servo
    servo_folder = os.path.join(database_dir, servo_label)
    os.makedirs(servo_folder, exist_ok=True)

    # Gera e salva o PDF (um por teste)
    pdf_path = os.path.join(servo_folder, f"{full_label}.pdf")
    with PdfPages(pdf_path) as pdf_pages:
        fig_pdf = generate_pdf(full_label, df)
        pdf_pages.savefig(fig_pdf)
        plt.close(fig_pdf)

    # Gera plots individuais (como no seu código anterior)
    def generate_plots(df):
        max_time_s = df['time_s'].iloc[-1]
        if max_time_s < 2400:
            time_step = 300
        elif max_time_s < 6000:
            time_step = 600
        else:
            time_step = 1800

        # (idem à lógica que você já possuía)
        # Crie 4 figuras e retorne-as
        figs = []

        # Plot 1: Temperaturas
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        fig1.suptitle('Temperaturas Medidas', fontsize=14)
        ax1.plot(df['time_s'], df['TempServo'],    label="Servo",    color='tab:blue')
        ax1.plot(df['time_s'], df['TempAmbiente'], label="Ambiente", color='darkturquoise')
        ax1.set_ylabel('Temperatura [°C]')
        ax1.legend(loc='center right', framealpha=1.0)
        ax1.grid(True)
        set_time_axis(ax1, max_time_s, time_step)
        figs.append(fig1)

        # Plot 2: Aquecimento do Servo
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        fig2.suptitle('Aquecimento do Servo', fontsize=14)
        params, _ = curve_fit(temperature_model, df['time_s'], df['temp_rise'], p0=[15, 2])
        T0_fit, tau_fit = params
        ax2.plot(df['time_s'], df['temp_rise'], label='Servo', color='lightsalmon')
        ax2.plot(df['time_s'], temperature_model(df['time_s'], *params), label='Fit', color='red', linewidth=2)
        ax2.text(
            0.98, 0.08,
            f"Temperatura Final: {T0_fit:.2f}°C\nConstante de Tempo: {tau_fit:.2f}s",
            ha='right', va='bottom',
            bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'),
            transform=ax2.transAxes
        )
        ax2.set_ylabel('Temperatura [°C]')
        ax2.legend(loc='center right', framealpha=1.0)
        ax2.grid(True)
        set_time_axis(ax2, max_time_s, time_step)
        figs.append(fig2)

        # Plot 3: Corrente Medida
        fig3, ax3 = plt.subplots(figsize=(10, 5))
        fig3.suptitle('Corrente Medida', fontsize=14)
        rolling_window = int(10.0 / sample_time_s)
        rms_current = df['Corrente'].rolling(window=rolling_window).apply(lambda x: np.sqrt(np.mean(np.square(x))), raw=True)
        rms_unique  = np.sqrt(np.mean(np.square(df['Corrente'])))
        ax3.plot(df['time_s'], df['Corrente'], color='darkseagreen', label="Corrente", linewidth=0.5)
        ax3.plot(df['time_s'], rms_current,    label="RMS",      color='tab:green')

        if rms_unique < 1.0:
            text_rms = f"RMS: {rms_unique * 1000.0:.2f} mA"
        else:
            text_rms = f"RMS: {rms_unique:.2f} A"

        ax3.text(
            0.98, 0.08,
            text_rms,
            ha='right', va='bottom',
            bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'),
            transform=ax3.transAxes
        )
        ax3.legend(loc='lower left', framealpha=1.0)
        ax3.set_ylabel('Corrente [A]')
        ax3.grid(True)
        set_time_axis(ax3, max_time_s, time_step)
        figs.append(fig3)

        # Plot 4: Zoom no ângulo
        fig4, ax4 = plt.subplots(figsize=(10, 5))
        fig4.suptitle('Corrente e Ângulo (Zoom)', fontsize=14)
        max_value_index = np.argmin(df['Angle'])
        if max_value_index < 150.0 / sample_time_s:
            max_value_index = len(df['Angle']) // 2
        start_zoom = max_value_index * sample_time_s - 120
        end_zoom   = max_value_index * sample_time_s + 120

        ax4.set_xlim([start_zoom, end_zoom])
        ax4.plot(df['time_s'], df['Corrente'], label="Corrente", color='darkseagreen', linewidth=0.5)
        ax4.plot(df['time_s'], rms_current,    label="RMS",      color='tab:green')

        twin4 = ax4.twinx()
        twin4.plot(df['time_s'], df['Angle'], label="Ângulo", color='teal')
        twin4.plot([0], [0], label="Corrente", color='darkseagreen', linewidth=0.5)
        twin4.plot([0], [0], label="RMS",      color='tab:green')

        ax4.set_ylabel("Corrente [A]")
        twin4.set_ylabel("Ângulo [°]")
        twin4.set_ylim([0, 90])
        twin4.set_yticks([15 * x for x in range(7)])
        ax4.grid(True)
        twin4.grid(True)
        ax4.legend(loc='lower left', framealpha=1.0)
        twin4.legend(loc='lower right', framealpha=1.0)

        set_time_axis(ax4, max_time_s, time_step)
        figs.append(fig4)

        return figs

    figs = generate_plots(df)
    # Cria subpasta para cada teste, se quiser. Mas se deseja TUDO direto na pasta do servo, basta salvar ali:
    # Exemplo: [Repositorio]/Database/B1/NomeDoTeste_*.png
    for idx, suffix in enumerate(["_Temp", "_Aquec", "_Corrente", "_Zoom"]):
        png_name = f"{full_label}{suffix}.png"
        png_path = os.path.join(servo_folder, png_name)
        figs[idx].savefig(png_path, dpi=300, bbox_inches='tight')
        plt.close(figs[idx])

    print(f"Resultados do arquivo '{csv_file}' salvos em: {servo_folder}")

print("\nConcluído com sucesso!")
