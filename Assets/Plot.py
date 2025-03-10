# -*- coding: utf-8 -*-

import os
import pandas as pd
from copy import deepcopy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.optimize import curve_fit
import numpy as np
from math import floor, sqrt
from matplotlib.ticker import MaxNLocator

#-----------------------------------------------------------------------------
# 1) Caminhos de pastas com base no local do script
#-----------------------------------------------------------------------------

# Caminho do script (Plot.py)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Caminho da raiz do repositório (uma pasta acima de Assets/)
repo_dir = os.path.dirname(script_dir)

# A pasta de dados brutos
directory = os.path.join(repo_dir, 'Dados_bruto')

# Pastas de saída para PDF e plots
pdfs_dir  = os.path.join(repo_dir, 'pdfs')
plots_dir = os.path.join(repo_dir, 'plots')

# Cria se não existir
os.makedirs(pdfs_dir,  exist_ok=True)
os.makedirs(plots_dir, exist_ok=True)

#-----------------------------------------------------------------------------
# 2) Carregamento dos arquivos CSV na pasta Dados_bruto
#-----------------------------------------------------------------------------

csv_files = [
    f for f in os.listdir(directory)
    if f.endswith('.csv') and f.count("_") > 3
]

print("Arquivos CSV encontrados em Dados_bruto:")
print("\n".join(csv_files))

#-----------------------------------------------------------------------------
# 3) Remoção de linhas anteriores e posteriores ao teste
#-----------------------------------------------------------------------------

for csv_file in csv_files:
    if "data" in csv_file:
        continue

    test_start = 0
    test_end   = 0
    csv_path   = os.path.join(directory, csv_file)

    with open(csv_path, 'r') as file:
        for i, line in enumerate(file):
            if line.strip() == "Teste A iniciado.":
                test_start = i + 1

        file.seek(0)

        for i, line in enumerate(file):
            if line.strip() == "Teste interrompido." and i > test_start:
                test_end = i
                break

    with open(csv_path, 'r') as file:
        lines = file.readlines()

    with open(csv_path, 'w') as file:
        file.writelines(lines[test_start:test_end])

#-----------------------------------------------------------------------------
# 4) Leitura de arquivos em DataFrames
#-----------------------------------------------------------------------------

dfs = []
dfs_dict = {}
columns = None

for csv_file in csv_files:
    csv_path = os.path.join(directory, csv_file)
    if "data" in csv_file:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8')
        dfs.append(df)
        if not columns:
            columns = df.columns.tolist()
    else:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8', header=None)
        df.columns = columns
        dfs.append(df)
    dfs_dict[csv_file] = df

sample_time_s = 0.25

#-----------------------------------------------------------------------------
# 5) Inserção de colunas de tempo e delta de temperatura
#-----------------------------------------------------------------------------

for df in dfs:
    df['time_s']   = [i * sample_time_s for i in range(len(df))]
    df['temp_rise'] = df['TempServo'] - df['TempAmbiente']

# Exemplo de DataFrame
print("Exemplo de DataFrame carregado:")
print(dfs_dict[csv_files[0]].head())

#-----------------------------------------------------------------------------
# 6) Funções utilitárias
#-----------------------------------------------------------------------------

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

#-----------------------------------------------------------------------------
# 7) Função para gerar PDF (4 gráficos) de um único CSV
#-----------------------------------------------------------------------------

def generate_pdf(filename, df, file_mapping):
    fig, axes = plt.subplots(nrows=4, ncols=1, figsize=(10, 15))
    fig.suptitle(file_mapping[filename], fontsize=16, y=0.97)
    fig.subplots_adjust(top=0.92, hspace=0.3)

    max_time_s = df['time_s'].iloc[-1]
    if max_time_s < 2400:
        time_step = 300
    elif max_time_s < 6000:
        time_step = 600
    else:
        time_step = 1800

    # Plot 1 - Temperaturas
    axes[0].plot(df['time_s'], df['TempServo'],     label="Servo",    color='tab:blue')
    axes[0].plot(df['time_s'], df['TempAmbiente'],  label="Ambiente", color='darkturquoise')
    axes[0].set_ylabel('Temperatura[°C]')
    axes[0].legend(loc='center right', framealpha=1.0)
    axes[0].set_title('Temperaturas Medidas')

    # Plot 2 - Ajuste exponencial (temp_rise)
    initial_guess = [15, 2]
    params, covariance = curve_fit(temperature_model, df['time_s'], df['temp_rise'], p0=initial_guess)
    T0_fit, tau_fit = params

    axes[1].plot(df['time_s'], df['temp_rise'], label='Servo', color='lightsalmon')
    axes[1].plot(df['time_s'], temperature_model(df['time_s'], T0_fit, tau_fit), label="Fit", color='red', linewidth=2)
    axes[1].text(
        0.98, 0.08,
        f"Temperatura Final: {T0_fit:.2f}°C\n Constante de Tempo: {tau_fit:.2f}s",
        ha='right', va='bottom',
        bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'),
        transform=axes[1].transAxes
    )
    axes[1].grid(True)
    axes[1].set_ylabel('Temperatura[°C]')
    axes[1].legend(loc='center right', framealpha=1.0)
    axes[1].set_title('Aquecimento do Servo')

    # Plot 3 - Corrente e RMS
    axes[2].plot(df['time_s'], df['Corrente'], color='darkseagreen', label="Corrente", linewidth=0.5)
    rms_current = df['Corrente'].rolling(window=int(10.0 / sample_time_s)).apply(
        lambda x: np.sqrt(np.mean(np.square(x))), raw=True
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
    if max_value_index < 150.0 / sample_time_s:
        max_value_index = len(df['Angle']) // 2

    starting_time_zoom = max_value_index * sample_time_s - 120
    ending_time_zoom   = max_value_index * sample_time_s + 120

    axes[3].set_xlim([starting_time_zoom, ending_time_zoom])
    axes[3].plot(df['time_s'], df['Corrente'], label="Corrente", color='darkseagreen', linewidth=0.5)
    axes[3].plot(df['time_s'], rms_current,   label="RMS",      color='tab:green')

    twin3 = axes[3].twinx()
    twin3.plot(df['time_s'], df['Angle'], label="Ângulo", color='teal')
    # Para que a legenda mostre Corrente/RMS no twin também:
    twin3.plot([0], [0], label="Corrente", color='darkseagreen', linewidth=0.5)
    twin3.plot([0], [0], label="RMS",      color='tab:green')

    axes[3].set_title(
        f"Corrente e Ângulo [{format_seconds_to_hhmmss(int(starting_time_zoom))} - {format_seconds_to_hhmmss(int(ending_time_zoom))}]"
    )
    axes[3].set_xlabel("Tempo [s]")
    axes[3].set_ylabel("Corrente [A]")
    twin3.set_ylabel("Ângulo [°]")
    twin3.set_ylim([0, 90])
    twin3.set_yticks([15*x for x in range(7)])
    axes[3].set_yticks(
        np.linspace(min(df['Corrente']) - 0.2, max(df['Corrente']) + 0.2, 7)
    )
    axes[3].set_ylim([min(df['Corrente']) - 0.2, max(df['Corrente']) + 0.2])
    twin3.grid(True)
    twin3.legend(loc='lower left', framealpha=1.0)

    # Eixo de tempo
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

#-----------------------------------------------------------------------------
# 8) Mapeamento de nomes de servos e criação de legendas personalizadas
#-----------------------------------------------------------------------------

servo_name_mapping = {
    'Leao'        : 'B1',
    'Capricornio' : 'B2',
    '11'          : 'B3',
    '18'          : 'B4',
    'Escorpiao'   : 'X1',
    'Aquario'     : 'X2',
    '10'          : 'X3',
    '7'           : 'X4'
}

file_mapping = {}
for csv_file in csv_files:
    args = csv_file.replace("-", "_").split("_")

    if 'data' in csv_file:
        servo_type = args[3]
        servo_name = args[4]
        test_name  = args[5].split('.')[0]
    else:
        servo_type = args[1]
        servo_name = args[2]
        test_name  = args[0]

    servo_label = servo_name_mapping.get(servo_name, servo_name)
    file_mapping[csv_file] = f"{servo_type}_{test_name}_{servo_label}"

#-----------------------------------------------------------------------------
# 9) Geração de PDF (único ou múltiplos)
#-----------------------------------------------------------------------------

single_file = True

if single_file:
    pdf_filename = os.path.join(pdfs_dir, 'single_output.pdf')
    pdf_pages = PdfPages(pdf_filename)
    for csv_file, df in zip(csv_files, dfs):
        fig = generate_pdf(csv_file, df, file_mapping)
        pdf_pages.savefig(fig)
        plt.close(fig)
    pdf_pages.close()
    print(f"PDF único gerado em: {pdf_filename}")
else:
    for csv_file, df in zip(csv_files, dfs):
        pdf_filename = os.path.join(pdfs_dir, f"{csv_file.split('.')[0]}.pdf")
        pdf_pages = PdfPages(pdf_filename)
        fig = generate_pdf(csv_file, df, file_mapping)
        pdf_pages.savefig(fig)
        pdf_pages.close()
        plt.close(fig)
        print(f"PDF gerado para {csv_file} em {pdf_filename}")

#-----------------------------------------------------------------------------
# 10) Geração de plots individuais (PNG) dentro de subpastas
#-----------------------------------------------------------------------------

def generate_plots(df):
    max_time_s = df['time_s'].iloc[-1]
    if max_time_s < 2400:
        time_step = 300
    elif max_time_s < 6000:
        time_step = 600
    else:
        time_step = 1800

    def temperature_model(t, T0, tau):
        return T0 * (1 - np.exp(-t / tau))

    # Plot 1: Temperaturas
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    fig1.suptitle('Temperaturas Medidas', fontsize=14)
    ax1.plot(df['time_s'], df['TempServo'],    label="Servo",    color='tab:blue')
    ax1.plot(df['time_s'], df['TempAmbiente'], label="Ambiente", color='darkturquoise')
    ax1.set_ylabel('Temperatura [°C]')
    ax1.legend(loc='center right', framealpha=1.0)
    ax1.grid(True)
    set_time_axis(ax1, max_time_s, time_step)

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

    # Plot 3: Corrente Medida
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    fig3.suptitle('Corrente Medida', fontsize=14)
    rolling_window = int(10.0 / sample_time_s)
    rms_current = df['Corrente'].rolling(window=rolling_window).apply(lambda x: np.sqrt(np.mean(np.square(x))), raw=True)
    rms_unique = np.sqrt(np.mean(np.square(df['Corrente'])))
    ax3.plot(df['time_s'], df['Corrente'], color='darkseagreen', label="Corrente", linewidth=0.5)
    ax3.plot(df['time_s'], rms_current,     label="RMS",      color='tab:green')

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

    # Plot 4: Zoom no ângulo
    fig4, ax4 = plt.subplots(figsize=(10, 5))
    max_value_index = np.argmin(df['Angle'])
    if max_value_index < 150.0 / sample_time_s:
        max_value_index = len(df['Angle']) // 2

    starting_time_zoom = max_value_index * sample_time_s - 120
    ending_time_zoom   = max_value_index * sample_time_s + 120

    fig4.suptitle(
        f'Corrente e Ângulo (Zoom: {format_seconds_to_hhmmss(int(starting_time_zoom))} '
        f'a {format_seconds_to_hhmmss(int(ending_time_zoom))})',
        fontsize=14
    )
    ax4.set_xlim([starting_time_zoom, ending_time_zoom])
    ax4.plot(df['time_s'], df['Corrente'], label="Corrente", color='darkseagreen', linewidth=0.5)
    ax4.plot(df['time_s'], rms_current,   label="RMS",      color='tab:green')

    twin4 = ax4.twinx()
    twin4.plot(df['time_s'], df['Angle'], label="Ângulo", color='teal')
    twin4.plot([0], [0], label="Corrente", color='darkseagreen', linewidth=0.5)
    twin4.plot([0], [0], label="RMS",      color='tab:green')

    ax4.set_ylabel("Corrente [A]")
    twin4.set_ylabel("Ângulo [°]")
    twin4.set_ylim([0, 90])
    twin4.set_yticks([15 * x for x in range(7)])
    ax4.set_yticks(
        np.linspace(min(df['Corrente']) - 0.2, max(df['Corrente']) + 0.2, 7)
    )
    ax4.set_ylim([min(df['Corrente']) - 0.2, max(df['Corrente']) + 0.2])
    twin4.grid(True)
    twin4.legend(loc='lower left', framealpha=1.0)

    ax4.set_xlabel("Tempo [s]")
    set_time_axis(ax4, max_time_s, time_step)

    return [fig1, fig2, fig3, fig4]

print("Gerando plots individuais em PNG...")

for csv_file in csv_files:
    folder_name = file_mapping[csv_file]
    df = dfs_dict[csv_file]
    figs = generate_plots(df)

    folder_path = os.path.join(plots_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for fig_idx, fig_tag in enumerate(['_Temp', '_AquecServo', '_RMS', '_Zoom']):
        path_plot = os.path.join(folder_path, f"{fig_tag}.png")
        figs[fig_idx].savefig(path_plot, dpi=300, bbox_inches='tight')
        plt.close(figs[fig_idx])

    plt.close('all')

print("Concluído com sucesso!")
