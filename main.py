import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys
import csv

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
    "4. Controle de Servos: Gerenciamento via comunicação serial\n"
    "5. Consulta Database: Procura o servo perfeito\n\n"
    "Abaixo, você verá as mensagens de DEBUG de cada script.\n"
    "Quando o script controle.py estiver ativo, você pode enviar comandos."
)

current_process = None
current_after_job = None

# Porta COM selecionada
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
    selected_com_port = port
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


# ---------------------------
# Consulta Database
# ---------------------------

def safe_float(value):
    """ Tenta converter 'value' para float. Se falhar, retorna None. """
    if value is None:
        return None
    try:
        return float(value)
    except:
        return None

def create_db_frame(parent):
    """
    Cria o frame de consulta de database dentro de 'parent'.
    Retorna o frame criado, contendo campos de filtros e um botão 'Aplicar'.
    
    Esse frame vai ocupar toda a área do 'parent' (fill='both', expand=True).
    """
    db_frame = tk.Frame(parent, bg="#3d3d3d")
    db_frame.pack(fill="both", expand=True)

    # Configura grid para expandir (linhas e colunas)
    db_frame.grid_rowconfigure(9, weight=1)
    # Se quisermos que a coluna de resultados também se expanda, podemos:
    db_frame.grid_columnconfigure(1, weight=1)

    lbl_title = tk.Label(
        db_frame, text="Consulta Database de Servos",
        bg="#3d3d3d", fg="white", font=("Helvetica", 14, "bold")
    )
    lbl_title.grid(row=0, column=0, columnspan=3, pady=(5, 10), sticky="n")

    tk.Label(db_frame, text="Torque mínimo (kgf.cm):", bg="#3d3d3d", fg="white").grid(row=1, column=0, sticky="e")
    torque_min_entry = tk.Entry(db_frame, width=10)
    torque_min_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    tk.Label(db_frame, text="Peso máximo (g):", bg="#3d3d3d", fg="white").grid(row=2, column=0, sticky="e")
    weight_max_entry = tk.Entry(db_frame, width=10)
    weight_max_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

    tk.Label(db_frame, text="Comprimento máx (mm):", bg="#3d3d3d", fg="white").grid(row=3, column=0, sticky="e")
    length_max_entry = tk.Entry(db_frame, width=10)
    length_max_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")

    tk.Label(db_frame, text="Largura máx (mm):", bg="#3d3d3d", fg="white").grid(row=4, column=0, sticky="e")
    width_max_entry = tk.Entry(db_frame, width=10)
    width_max_entry.grid(row=4, column=1, padx=5, pady=2, sticky="w")

    tk.Label(db_frame, text="Altura máx (mm):", bg="#3d3d3d", fg="white").grid(row=5, column=0, sticky="e")
    height_max_entry = tk.Entry(db_frame, width=10)
    height_max_entry.grid(row=5, column=1, padx=5, pady=2, sticky="w")

    tk.Label(db_frame, text="Vel. angular mínima (°/s):", bg="#3d3d3d", fg="white").grid(row=6, column=0, sticky="e")
    speed_min_entry = tk.Entry(db_frame, width=10)
    speed_min_entry.grid(row=6, column=1, padx=5, pady=2, sticky="w")

    tk.Label(db_frame, text="Preço máximo ($):", bg="#3d3d3d", fg="white").grid(row=7, column=0, sticky="e")
    price_max_entry = tk.Entry(db_frame, width=10)
    price_max_entry.grid(row=7, column=1, padx=5, pady=2, sticky="w")

    # Botão Aplicar
    def aplicar_filtros():
        results_text.delete("1.0", "end")

        # Lendo valores dos filtros (se vazio, None)
        try:
            torque_min = float(torque_min_entry.get()) if torque_min_entry.get().strip() else None
        except ValueError:
            torque_min = None

        try:
            weight_max = float(weight_max_entry.get()) if weight_max_entry.get().strip() else None
        except ValueError:
            weight_max = None

        try:
            length_max = float(length_max_entry.get()) if length_max_entry.get().strip() else None
        except ValueError:
            length_max = None

        try:
            width_max = float(width_max_entry.get()) if width_max_entry.get().strip() else None
        except ValueError:
            width_max = None

        try:
            height_max = float(height_max_entry.get()) if height_max_entry.get().strip() else None
        except ValueError:
            height_max = None

        try:
            speed_min = float(speed_min_entry.get()) if speed_min_entry.get().strip() else None
        except ValueError:
            speed_min = None

        try:
            price_max = float(price_max_entry.get()) if price_max_entry.get().strip() else None
        except ValueError:
            price_max = None

        csv_path = os.path.join("Database", "servos.csv")
        # results_text.insert("end", f"[DEBUG] Tentando abrir CSV: {csv_path}\n")

        if not os.path.exists(csv_path):
            results_text.insert("end", "Arquivo de database não encontrado.\n")
            return

        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                # Ignora a primeira linha "sep=," se houver
                first_line = f.readline().strip()
                if not first_line.startswith("sep="):
                    # Se a primeira linha não é "sep=", voltamos ao começo
                    f.seek(0)

                # Lê com delimitador de vírgula
                reader = csv.DictReader(f, delimiter=",")

                count = 0
                for row in reader:
                    # Debug: exibe a linha lida
                    #results_text.insert("end", f"[DEBUG] Linha lida: {row}\n")

                    # Tente extrair as colunas por nome
                    # Ajuste os nomes conforme aparecem no seu CSV
                    make = row.get("Make", "")
                    model = row.get("Model", "")
                    weight = safe_float(row.get("Weight (g)"))
                    L = safe_float(row.get("L (mm)"))
                    C = safe_float(row.get("C (mm)"))
                    A = safe_float(row.get("A (mm)"))

                    torque_cols = [
                        safe_float(row.get("Torque1 (kgf.cm)")),
                        safe_float(row.get("Torque2 (kgf.cm)")),
                        safe_float(row.get("Torque3 (kgf.cm)")),
                        safe_float(row.get("Torque4 (kgf.cm)")),
                        safe_float(row.get("Torque5 (kgf.cm)")),
                    ]
                    max_torque = max([t for t in torque_cols if t is not None] or [0])

                    speed_cols = [
                        safe_float(row.get("Speed1 (°/s)")),
                        safe_float(row.get("Speed2 (°/s)")),
                        safe_float(row.get("Speed3 (°/s)")),
                        safe_float(row.get("Speed4 (°/s)")),
                        safe_float(row.get("Speed5 (°/s)")),
                    ]
                    max_speed = max([s for s in speed_cols if s is not None] or [0])

                    price_str = row.get("Typical Price", "").replace("$", "")
                    price_val = safe_float(price_str)

                    # Filtros
                    if torque_min is not None and max_torque < torque_min:
                        continue
                    if weight_max is not None and weight is not None and weight > weight_max:
                        continue
                    if length_max is not None and L is not None and L > length_max:
                        continue
                    if width_max is not None and C is not None and C > width_max:
                        continue
                    if height_max is not None and A is not None and A > height_max:
                        continue
                    if speed_min is not None and max_speed < speed_min:
                        continue
                    if price_max is not None and price_val is not None and price_val > price_max:
                        continue

                    count += 1
                    info = (
                        f"{count}) {make} {model}\n"
                        f"   Peso: {weight} g | Dimensões: {L} x {C} x {A} mm\n"
                        f"   Torque máx: {max_torque} kgf.cm | Vel máx: {max_speed} °/s\n"
                        f"   Preço: {row.get('Typical Price','n/a')}\n\n"
                    )
                    results_text.insert("end", info)

                if count == 0:
                    results_text.insert("end", "Nenhum resultado encontrado (após filtros).\n")

        except Exception as e:
            results_text.insert("end", f"[ERRO] Falha ao ler CSV: {e}\n")

    apply_btn = tk.Button(db_frame, text="Aplicar", bg="#403c3c", fg="white", command=aplicar_filtros)
    apply_btn.grid(row=8, column=0, columnspan=2, pady=5)

    # Área de resultados
    results_text = tk.Text(db_frame, bg="#2f2f2f", fg="white")
    results_text.grid(row=9, column=0, columnspan=3, padx=5, pady=10, sticky="nsew")

    scrollbar = tk.Scrollbar(db_frame, command=results_text.yview)
    results_text.configure(yscrollcommand=scrollbar.set)
    # Deixe a scrollbar na mesma "linha" mas em outra coluna (ou ao lado)
    scrollbar.grid(row=9, column=3, sticky="ns")

    return db_frame

def main():
    root = tk.Tk()
    root.title("Super Validador de Servos")
    root.geometry("1600x920")
    root.configure(bg="#212121")

    top_frame = tk.Frame(root, bg="#212121")
    top_frame.pack(side="top", fill="x")

    title_label = tk.Label(
        top_frame,
        text="SUPER VALIDADOR DE SERVOS",
        font=("Helvetica", 32, "bold"),
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

    # Frame esquerdo
    left_frame = tk.Frame(main_frame, bg="#212121")
    left_frame.pack(side="left", fill="y")

    btn_style = {
        "width": 25,
        "height": 2,
        "bg": "#403c3c",
        "fg": "white",
        "font": ("Helvetica", 12, "bold"),
        "relief": "raised"
    }

    # Frame direito (onde alternamos debug x db)
    right_frame = tk.Frame(main_frame, bg="#212121")
    right_frame.pack(side="right", fill="both", expand=True)

    # ========== Frame de Debug ==========
    debug_frame = tk.Frame(right_frame, bg="#212121")
    debug_frame.pack(fill="both", expand=True)  # visível inicialmente

    instructions_label = tk.Label(
        debug_frame,
        text=INSTRUCTIONS,
        font=("Helvetica", 12),
        bg="#2f2f2f",
        fg="white",
        justify="left",
        anchor="n"
    )
    instructions_label.pack(padx=20, pady=(20, 5), anchor="n", fill="x")

    debug_text = tk.Text(debug_frame, height=10, bg="#1e1e1e", fg="white")
    debug_text.pack(padx=10, pady=(0, 10), fill="both", expand=True)

    scrollbar = tk.Scrollbar(debug_text, command=debug_text.yview)
    debug_text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    command_frame = tk.Frame(debug_frame, bg="#2f2f2f")
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

    # ========== Frame de Database ==========
    db_frame = create_db_frame(right_frame)
    db_frame.pack_forget()  # escondido inicialmente

    def toggle_db_view():
        if debug_frame.winfo_ismapped():
            debug_frame.pack_forget()
            db_frame.pack(fill="both", expand=True)
        else:
            db_frame.pack_forget()
            debug_frame.pack(fill="both", expand=True)

    # Botões do lado esquerdo
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
        command=on_port_selected
    )
    port_menu.config(width=15, bg="#403c3c", fg="white", font=("Helvetica", 10))
    port_menu.pack(side="left", padx=5)

    tk.Button(
        left_frame,
        text="Controle de Servo",
        command=lambda: on_controle_button(debug_text),
        **btn_style
    ).pack(pady=10)

    tk.Button(
        left_frame,
        text="Consulta Database",
        command=toggle_db_view,
        **btn_style
    ).pack(pady=10)

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

    # Gato no canto (opcional)
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
