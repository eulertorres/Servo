import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

import serial
import serial.tools.list_ports

from PIL import Image, ImageTk, ImageOps

PROGRAMS_FOLDER = os.path.join("Assets")

# Scripts Python
MOLA_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_mola.py")
PESO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_peso.py")
AVIAO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_aviao.py")
CONTROLE_SCRIPT = os.path.join(PROGRAMS_FOLDER, "controle.py")

LOGO_PATH = os.path.join("Assets", "Xmobots_logo.png")
CAT_PATH = os.path.join("Assets", "gato.png")

INSTRUCTIONS = (
    "Selecione um dos programas abaixo para executar:\n\n"
    "1. Simulador Servo/Mola\n"
    "2. Simulador Servo/Peso\n"
    "3. Simulador Elevon (3D)\n"
    "4. Controle de Servos: Gerenciamento via comunicação serial\n\n"
    "Abaixo, você verá as mensagens de DEBUG de cada script.\n"
    "Quando o script controle.py estiver ativo, você pode enviar comandos."
)

current_process = None
current_after_job = None

# Aqui armazenaremos a porta selecionada no dropdown
selected_com_port = None

def get_serial_ports():
    """
    Retorna a lista de portas seriais encontradas no sistema.
    Necessário 'pyserial' instalado (pip install pyserial).
    """
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

def kill_current_process():
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate()
    current_process = None

def run_program(program_path, debug_text, extra_arg=None):
    """
    Executa o script em 'program_path' e redireciona stdout/stderr
    para o Text 'debug_text'. Se 'extra_arg' for fornecido,
    adiciona como argumento, ex.: ["python", program_path, "--COM7"].
    """
    global current_process, current_after_job

    # Se já há processo rodando, mata
    kill_current_process()

    # Limpa Text
    debug_text.delete("1.0", "end")

    cmd = ["python", program_path]
    if extra_arg:
        cmd.append(f"--{extra_arg}")

    try:
        current_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False
        )
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao iniciar o programa:\n{e}")
        return

    def read_output():
        global current_after_job

        if current_process:
            if current_process.poll() is None:
                output = current_process.stdout.read(1024)
                if output:
                    debug_text.insert("end", output)
                    debug_text.see("end")
                current_after_job = debug_text.after(100, read_output)
            else:
                # Finalizado
                remaining = current_process.stdout.read()
                if remaining:
                    debug_text.insert("end", remaining)
                    debug_text.see("end")
                debug_text.insert("end", "\n[Processo finalizado]\n")
                debug_text.see("end")
                if current_process.stdout:
                    current_process.stdout.close()

    read_output()

def on_port_selected(port):
    """
    Guarda a porta selecionada em 'selected_com_port' sem executar nada ainda.
    """
    global selected_com_port
    selected_com_port = port  # ex.: COM7 ou /dev/ttyUSB0
    print("Porta selecionada:", selected_com_port)

def on_controle_button(debug_text):
    """
    Chamado quando o usuário clica no botão "Controle de Servo".
    Se 'selected_com_port' for válida, roda controle.py com esse argumento.
    """
    global selected_com_port
    if not selected_com_port or "Selecione" in selected_com_port or "Nenhuma" in selected_com_port:
        messagebox.showwarning("Aviso", "Selecione uma porta COM válida antes de iniciar o controle.")
        return

    # Inicia controle.py com '--COMxx'
    run_program(CONTROLE_SCRIPT, debug_text, extra_arg=selected_com_port)

def send_command_to_process(entry_widget, debug_text):
    """
    Envia o texto digitado ao stdin do processo atual (ex: controle.py).
    """
    global current_process
    if not current_process or current_process.poll() is not None:
        messagebox.showinfo("Info", "Nenhum processo está em execução para receber comandos.")
        return

    cmd = entry_widget.get().strip()
    if cmd:
        try:
            current_process.stdin.write(cmd + "\n")
            current_process.stdin.flush()
            debug_text.insert("end", f"> {cmd}\n")
            debug_text.see("end")
        except Exception as e:
            debug_text.insert("end", f"[Erro ao enviar comando: {e}]\n")
            debug_text.see("end")

    entry_widget.delete(0, "end")

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

    try:
        logo_img_raw = Image.open(LOGO_PATH)
        logo_img = ImageTk.PhotoImage(logo_img_raw)
        logo_label = tk.Label(top_frame, image=logo_img, bg="#212121")
        logo_label.image = logo_img
        logo_label.pack(side="right", padx=20)
    except:
        pass

    main_frame = tk.Frame(root, bg="#212121")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    left_frame = tk.Frame(main_frame, bg="#212121")
    left_frame.pack(side="left", fill="both", expand=True)

    btn_style = {
        "width": 25,
        "height": 2,
        "bg": "#403c3c",
        "fg": "white",
        "font": ("Helvetica", 12, "bold"),
        "relief": "raised"
    }

    tk.Button(
        left_frame,
        text="Simulador Servo/Mola",
        command=lambda: run_program(MOLA_SCRIPT, debug_text),
        **btn_style
    ).pack(pady=10)

    tk.Button(
        left_frame,
        text="Simulador Servo/Peso",
        command=lambda: run_program(PESO_SCRIPT, debug_text),
        **btn_style
    ).pack(pady=10)

    tk.Button(
        left_frame,
        text="Simulador Elevon",
        command=lambda: run_program(AVIAO_SCRIPT, debug_text),
        **btn_style
    ).pack(pady=10)

    # Dropdown de portas
    dropdown_frame = tk.Frame(left_frame, bg="#212121")
    dropdown_frame.pack(pady=(15, 5))

    tk.Label(dropdown_frame, text="Portas:", bg="#212121", fg="white").pack(side="left", padx=5)

    ports = get_serial_ports()
    if not ports:
        ports = ["Nenhuma Porta Encontrada"]

    selected_port_var = tk.StringVar(dropdown_frame)
    selected_port_var.set("Selecione a Porta")

    port_menu = tk.OptionMenu(
        dropdown_frame,
        selected_port_var,
        *ports,
        command=on_port_selected  # Aqui só guardamos a porta selecionada
    )
    port_menu.config(width=15, bg="#403c3c", fg="white", font=("Helvetica", 10))
    port_menu.pack(side="left", padx=5)

    # Botão para iniciar controle de servo (usando a porta escolhida)
    tk.Button(
        left_frame,
        text="Controle de Servo",
        command=lambda: on_controle_button(debug_text),
        **btn_style
    ).pack(pady=10)

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

    # Frame à direita: Instruções + debug + envio de comandos
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

    debug_text = tk.Text(right_frame, height=10, bg="#1e1e1e", fg="white")
    debug_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    scrollbar = tk.Scrollbar(debug_text, command=debug_text.yview)
    debug_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    command_frame = tk.Frame(right_frame, bg="#2f2f2f")
    command_frame.pack(fill="x", pady=(0, 10))

    tk.Label(command_frame, text="Comando:", bg="#2f2f2f", fg="white").pack(side="left", padx=5)
    entry_cmd = tk.Entry(command_frame, width=30)
    entry_cmd.pack(side="left", padx=5)

    tk.Button(
        command_frame,
        text="Enviar",
        command=lambda: send_command_to_process(entry_cmd, debug_text),
        bg="#403c3c",
        fg="white",
        font=("Helvetica", 10, "bold")
    ).pack(side="left", padx=5)

    # Gato no canto
    try:
        cat_img_raw = Image.open(CAT_PATH)
        cat_img_raw = cat_img_raw.resize((50, 50), Image.LANCZOS)
        cat_img = ImageTk.PhotoImage(cat_img_raw)
        cat_label = tk.Label(root, image=cat_img, bg="#212121")
        cat_label.image = cat_img
        cat_label.place(relx=1.0, rely=1.0, x=-5, y=-5, anchor="se")
    except:
        pass

    root.mainloop()

if __name__ == "__main__":
    main()
