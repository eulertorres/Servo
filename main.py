import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

# Se quiser listar portas seriais no Windows, Linux e macOS:
import serial
import serial.tools.list_ports

# Pillow >= 10.0 substituiu Image.ANTIALIAS por Resampling.LANCZOS
from PIL import Image, ImageTk, ImageOps

PROGRAMS_FOLDER = os.path.join("Assets")

# Caminhos dos scripts Python
MOLA_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_mola.py")
PESO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_peso.py")
CONTROLE_SCRIPT = os.path.join(PROGRAMS_FOLDER, "controle.py")
AVIAO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_aviao.py")

LOGO_PATH = os.path.join("Assets", "Xmobots_logo.png")
CAT_PATH = os.path.join("Assets", "gato.png")

PORT = "COM7"

INSTRUCTIONS = (
    "Selecione um dos programas abaixo para executar:\n\n"
    "1. Simulador Servo/Mola: Simulação de bancada do servo com mola.\n"
    "2. Simulador Servo/Peso: Simulação de bancada do servo puxando peso.\n"
    "3. Simulador Elevon: Mecanismo de Aileron/Profundor em 3D.\n"
    "4. Controle: Gerenciamento das bancadas via comunicação serial.\n"
    "\n"
    "Abaixo, você verá as mensagens de DEBUG (stdout e stderr) do script escolhido."
)

# Variáveis globais para controle do processo e do job "after" (leitura assíncrona)
current_process = None
current_after_job = None

def get_serial_ports():
    """
    Retorna uma lista das portas seriais encontradas no sistema (Windows, Linux, macOS).
    É necessário ter pyserial instalado (pip install pyserial).
    """
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

def kill_current_process():
    """
    Se houver um processo em execução ainda, tenta encerrá-lo.
    """
    global current_process
    if current_process and current_process.poll() is None:
        # Tenta matar o processo (em geral, não é 100% garantido no Windows sem outras flags)
        current_process.terminate()
    current_process = None

def run_program(program_path, debug_text, extra_arg=None):
    """
    Executa o script em 'program_path' e exibe as mensagens de stdout/stderr
    diretamente no Text 'debug_text'.
    Se 'extra_arg' for fornecido, passa como argumento ao script: ["python", program, "--COM5"], etc.
    """
    global current_process, current_after_job

    # Se já há um processo em execução, encerra.
    kill_current_process()

    # Limpa a área de debug antes de iniciar o novo script
    debug_text.delete("1.0", "end")

    # Monta o comando para subprocess
    cmd = ["python", program_path]
    if extra_arg:
        cmd.append(f"--{extra_arg}")  # Exemplo: --COM7

    try:
        # Cria o processo, redirecionando stdout e stderr para o mesmo "pipe"
        current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,    # para receber strings
            shell=False
        )
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao iniciar o programa:\n{e}")
        return

    def read_output():
        """
        Lê as linhas do subprocess e insere no debug_text.
        Usa after() para não travar a GUI.
        """
        global current_after_job

        if current_process:
            # .poll() == None se ainda está rodando
            if current_process.poll() is None:
                # Tenta ler 1024 caracteres (ou seja, um buffer) sem bloquear
                output = current_process.stdout.read(1024)
                if output:
                    debug_text.insert("end", output)
                    debug_text.see("end")  # rola para o final
                # Agenda próxima leitura
                current_after_job = debug_text.after(100, read_output)
            else:
                # Se o processo terminou, lê o resto que sobrou no buffer
                remaining = current_process.stdout.read()
                if remaining:
                    debug_text.insert("end", remaining)
                    debug_text.see("end")
                debug_text.insert("end", "\n[Processo finalizado]\n")
                debug_text.see("end")
                current_process.stdout.close()

    # Dispara a primeira leitura
    read_output()


def on_port_selected(selected_port, debug_text):
    """
    Callback para quando o usuário escolhe uma porta no dropdown.
    Executa o programa de controle com o argumento '--COMXYZ' ou '/dev/ttyS0', etc.
    """
    # Se o usuário selecionou algo diferente de "Selecione..."
    if selected_port and "Selecione" not in selected_port:
        #run_program(CONTROLE_SCRIPT, debug_text, extra_arg=selected_port)
        PORT = selected_port


def main():
    root = tk.Tk()
    root.title("Super Validador de Servos")
    root.geometry("1080x600")
    root.configure(bg="#212121")

    top_frame = tk.Frame(root, bg="#212121")
    top_frame.pack(side="top", fill="x")

    title_label = tk.Label(
        top_frame,
        text="SUPER VALIDADOR DE SERVOS",
        font=("Helvetica", 24, "bold"),
        bg="#212121",
        fg="white"
    )
    title_label.pack(side="left", padx=20, pady=20)

    # Tenta carregar a logo
    try:
        logo_img_raw = Image.open(LOGO_PATH)
        # Se quiser redimensionar a logo:
        # from PIL import Resampling
        # logo_img_raw = logo_img_raw.resize((200, 50), Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(logo_img_raw)
        logo_label = tk.Label(top_frame, image=logo_img, bg="#212121")
        logo_label.image = logo_img
        logo_label.pack(side="right", padx=20)
    except Exception as e:
        print(f"Não foi possível carregar a imagem de logo: {e}")

    main_frame = tk.Frame(root, bg="#212121")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    left_frame = tk.Frame(main_frame, bg="#212121")
    left_frame.pack(side="left", fill="both", expand=True)

    # Botões de execução (sem o controle, que agora terá o dropdown)
    btn_style = {
        "width": 25,
        "height": 2,
        "bg": "#403c3c",
        "fg": "white",
        "font": ("Helvetica", 12, "bold"),
        "relief": "raised"
    }

    # ---- Botão: Simulador Mola ----
    tk.Button(
        left_frame,
        text="Simulador Servo/Mola",
        command=lambda: run_program(MOLA_SCRIPT, debug_text),
        **btn_style
    ).pack(pady=10)

    # ---- Botão: Simulador Peso ----
    tk.Button(
        left_frame,
        text="Simulador Servo/Peso",
        command=lambda: run_program(PESO_SCRIPT, debug_text),
        **btn_style
    ).pack(pady=10)

    # ---- Botão: Simulador Elevon ----
    tk.Button(
        left_frame,
        text="Simulador Elevon",
        command=lambda: run_program(AVIAO_SCRIPT, debug_text),
        **btn_style
    ).pack(pady=10)

    # ---- Botão: Controle ----
    tk.Button(
        left_frame,
        text="Controle de servo",
        command=lambda: run_program(CONTROLE_SCRIPT, debug_text, extra_arg=PORT),
        **btn_style
    ).pack(pady=5)

    # =========================================================
    # Dropdown + Botão "Controle" lado a lado
    # =========================================================
    control_frame = tk.Frame(left_frame, bg="#212121")
    control_frame.pack(pady=5)

    # Listar portas seriais disponíveis
    ports = get_serial_ports()
    if not ports:
        ports = ["Nenhuma Porta Encontrada"]

    # Valor inicial do dropdown
    selected_port_var = tk.StringVar(control_frame)
    selected_port_var.set("Selecione a Porta")

    # Cria OptionMenu
    port_menu = tk.OptionMenu(
        control_frame,
        selected_port_var,
        *ports,
        command=lambda val: on_port_selected(val, debug_text)  # callback
    )
    port_menu.config(width=15, bg="#403c3c", fg="white", font=("Helvetica", 10))
    port_menu.pack(side="left", padx=5)

    # Botão de sair
    tk.Button(
        left_frame,
        text="Sair",
        command=lambda: [kill_current_process(), root.quit()],
        bg="#dd0734",
        fg="white",
        font=("Helvetica", 12, "bold"),
        relief="groove",
        width=25,
        height=2
    ).pack(side="bottom", pady=(40, 10))

    # Frame à direita: Instruções + Área de Debug
    right_frame = tk.Frame(main_frame, bg="#2f2f2f")
    right_frame.pack(side="right", fill="both", expand=True)

    instructions_label = tk.Label(
        right_frame,
        text=INSTRUCTIONS,
        font=("Helvetica", 12),
        bg="#2f2f2f",
        fg="white",
        justify="left",
        anchor="n"
    )
    instructions_label.pack(padx=20, pady=(20, 5), anchor="n")

    # ---- Área de debug (Text) logo abaixo das instruções ----
    debug_text = tk.Text(right_frame, height=10, bg="#1e1e1e", fg="white")
    debug_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    # -- Scrollbar (opcional) --
    scrollbar = tk.Scrollbar(debug_text, command=debug_text.yview)
    debug_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Carrega a imagem do gato (pequena) no canto inferior direito
    try:
        cat_img_raw = Image.open(CAT_PATH)
        cat_img_raw = cat_img_raw.resize((50, 50), Image.LANCZOS)
        cat_img = ImageTk.PhotoImage(cat_img_raw)
        cat_label = tk.Label(root, image=cat_img, bg="#212121")
        cat_label.image = cat_img
        cat_label.place(relx=1.0, rely=1.0, x=-5, y=-5, anchor="se")
    except Exception as e:
        print(f"Não foi possível carregar a imagem do gato: {e}")

    root.mainloop()

if __name__ == "__main__":
    main()
