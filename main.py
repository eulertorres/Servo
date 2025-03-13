import os
import csv
import sys
import subprocess
import requests
import threading  # importado para carregamento assíncrono
from io import BytesIO

import customtkinter as ctk
from PIL import Image
from tkinter import messagebox  # <-- Usando messagebox do tkinter

# Se quiser usar pyserial, lembre-se: pip install pyserial
import serial
import serial.tools.list_ports

# Se quiser usar icrawler, lembre-se: pip install icrawler
from icrawler.builtin import GoogleImageCrawler

###############################################################################
#                                  CONFIG                                     #
###############################################################################
ctk.set_appearance_mode("dark")  # "light" ou "system"
ctk.set_default_color_theme("dark-blue")  # tema default ou custom

PROGRAMS_FOLDER = "Assets"

MOLA_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_mola.py")
PESO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_peso.py")
AVIAO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "vizual_aviao.py")
CONTROLE_SCRIPT = os.path.join(PROGRAMS_FOLDER, "controle.py")
CADASTRO_SCRIPT = os.path.join(PROGRAMS_FOLDER, "Add_servo.py")  # <-- script de cadastro

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

# Pasta onde salvaremos as imagens baixadas
ICRAWLER_STORAGE = os.path.join("Database", "Images")
if not os.path.exists(ICRAWLER_STORAGE):
    os.makedirs(ICRAWLER_STORAGE)

###############################################################################
#                           FUNÇÃO DE BUSCA DE IMAGENS                        #
###############################################################################
def fetch_image_for_model(model_name):
    safe_model_name = model_name.replace(" ", "_").replace("/", "_")
    local_filename = safe_model_name + ".jpg"
    print("Procurando imagem servo: ", local_filename)
    local_path = os.path.join(ICRAWLER_STORAGE, local_filename)

    if os.path.exists(local_path):
        return local_path

    try:
        google_crawler = GoogleImageCrawler(
            parser_threads=1,
            downloader_threads=1,
            storage={'root_dir': ICRAWLER_STORAGE}
        )
        google_crawler.crawl(keyword=f"{model_name} servo", max_num=1)
    except Exception as e:
        print(f"[AVISO] Falha ao baixar imagem de '{model_name}': {e}")
        return None

    downloaded_file = os.path.join(ICRAWLER_STORAGE, "000001.jpg")
    if os.path.exists(downloaded_file):
        try:
            os.rename(downloaded_file, local_path)
            return local_path
        except Exception as e:
            print(f"Erro ao renomear 000001.jpg para {local_filename}: {e}")
            return None

    return None

###############################################################################
#                           FUNÇÕES DE LAYOUT (FLOW)                          #
###############################################################################
def flow_layout(parent, blocks, padding_x=10, padding_y=10, margin_left=10):
    parent_width = parent.winfo_width()
    if parent_width <= 0:
        return

    x_cursor = margin_left
    y_cursor = padding_y
    line_height = 0

    for block in blocks:
        block.update_idletasks()
        bw = block.winfo_reqwidth()
        bh = block.winfo_reqheight()

        if x_cursor + bw + padding_x > parent_width:
            x_cursor = margin_left
            y_cursor += line_height + padding_y
            line_height = 0

        block.place(x=x_cursor, y=y_cursor)
        x_cursor += bw + padding_x
        if bh > line_height:
            line_height = bh

###############################################################################
#                           CÓDIGO PARA PROCESSOS                             #
###############################################################################
current_process = None
current_after_job = None

def kill_current_process():
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate()
    current_process = None

def run_program(program_path, debug_text, extra_arg=None):
    global current_process, current_after_job
    kill_current_process()
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
                remaining = current_process.stdout.read()
                if remaining:
                    debug_text.insert("end", remaining)
                    debug_text.see("end")
                debug_text.insert("end", "\n[Processo finalizado]\n")
                debug_text.see("end")
                if current_process.stdout:
                    current_process.stdout.close()

    read_output()

def send_command_to_process(entry_widget, debug_text):
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

###############################################################################
#                        SERIAL / PORTAS                                      #
###############################################################################
import serial
import serial.tools.list_ports

selected_com_port = None

def get_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

def on_port_selected(choice):
    global selected_com_port
    selected_com_port = choice
    print("Porta selecionada:", selected_com_port)

def on_controle_button(debug_text):
    global selected_com_port
    if not selected_com_port or "Selecione" in selected_com_port or "Nenhuma" in selected_com_port:
        messagebox.showwarning("Aviso", "Selecione uma porta COM válida antes de iniciar o controle.")
        return
    run_program(CONTROLE_SCRIPT, debug_text, extra_arg=selected_com_port)

###############################################################################
#                      FUNÇÕES AUXILIARES CSV / FILTROS                       #
###############################################################################
def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except:
        return None

###############################################################################
#                             JANELA PRINCIPAL                                #
###############################################################################
class ServoValidatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Super Validador de Servos")
        self.geometry("1600x920")

        # Frame top
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(side="top", fill="x", padx=5, pady=5)

        self.title_label = ctk.CTkLabel(
            self.top_frame,
            text="SUPER VALIDADOR DE SERVOS",
            font=("Helvetica", 32, "bold")
        )
        self.title_label.pack(side="left", padx=20, pady=20)

        # Logo
        try:
            logo_img = Image.open(LOGO_PATH)
            self.logo_img_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(200, 50))
            self.logo_label = ctk.CTkLabel(self.top_frame, image=self.logo_img_ctk, text="")
            self.logo_label.pack(side="right", padx=20)
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")

        # Main frame (split left/right)
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left side: botões
        self.left_frame = ctk.CTkFrame(self.main_frame)
        self.left_frame.pack(side="left", fill="y", padx=5)

        self.btn_mola = ctk.CTkButton(
            self.left_frame, text="Simulador Servo/Mola",
            command=lambda: self.run_script(MOLA_SCRIPT)
        )
        self.btn_mola.pack(pady=10)

        self.btn_peso = ctk.CTkButton(
            self.left_frame, text="Simulador Servo/Peso",
            command=lambda: self.run_script(PESO_SCRIPT)
        )
        self.btn_peso.pack(pady=10)

        self.btn_aviao = ctk.CTkButton(
            self.left_frame, text="Simulador Elevon",
            command=lambda: self.run_script(AVIAO_SCRIPT)
        )
        self.btn_aviao.pack(pady=10)

        # Botão de Cadastro de Servo
        self.btn_cadastro = ctk.CTkButton(
            self.left_frame,
            text="Cadastrar Servo",
            command=lambda: self.run_script(CADASTRO_SCRIPT)
        )
        self.btn_cadastro.pack(pady=10)

        # Dropdown de portas
        self.dropdown_frame = ctk.CTkFrame(self.left_frame)
        self.dropdown_frame.pack(pady=(15,5))
        ctk.CTkLabel(self.dropdown_frame, text="Portas:").pack(side="left", padx=5)

        ports = get_serial_ports()
        if not ports:
            ports = ["Nenhuma Porta Encontrada"]

        self.port_var = ctk.StringVar(value="Selecione a Porta")
        self.combo_port = ctk.CTkOptionMenu(
            self.dropdown_frame,
            values=ports,
            command=on_port_selected,
            variable=self.port_var
        )
        self.combo_port.pack(side="left", padx=5)

        self.btn_controle = ctk.CTkButton(
            self.left_frame, text="Controle de Servo",
            command=lambda: on_controle_button(self.debug_text)
        )
        self.btn_controle.pack(pady=10)

        self.btn_db = ctk.CTkButton(
            self.left_frame, text="Consulta Database",
            command=self.toggle_db_view
        )
        self.btn_db.pack(pady=10)

        self.btn_sair = ctk.CTkButton(
            self.left_frame, text="Sair", fg_color="red",
            command=self.on_sair
        )
        self.btn_sair.pack(side="bottom", pady=(40, 10))

        # Right side: area switch
        self.right_frame = ctk.CTkFrame(self.main_frame)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # Debug Frame
        self.debug_frame = ctk.CTkFrame(self.right_frame)
        self.debug_frame.pack(fill="both", expand=True)

        self.instructions_label = ctk.CTkLabel(
            self.debug_frame,
            text=INSTRUCTIONS,
            height=100,
            justify="left"
        )
        self.instructions_label.pack(padx=20, pady=10, fill="x")

        self.debug_text = ctk.CTkTextbox(self.debug_frame, width=800, height=300)
        self.debug_text.pack(padx=10, pady=5, fill="both", expand=True)

        self.command_frame = ctk.CTkFrame(self.debug_frame)
        self.command_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(self.command_frame, text="Comando:").pack(side="left", padx=5)
        self.entry_cmd = ctk.CTkEntry(self.command_frame, width=180)
        self.entry_cmd.pack(side="left", padx=5)

        self.btn_enviar = ctk.CTkButton(
            self.command_frame, text="Enviar",
            command=lambda: send_command_to_process(self.entry_cmd, self.debug_text)
        )
        self.btn_enviar.pack(side="left", padx=5)

        # DB Frame (filtros + resultados)
        self.db_frame = ctk.CTkFrame(self.right_frame)
        self.create_db_area()

        # Gato no canto
        try:
            cat_img_raw = Image.open(CAT_PATH).resize((50, 50))
            self.cat_img_ctk = ctk.CTkImage(light_image=cat_img_raw, dark_image=cat_img_raw, size=(50, 50))
            self.cat_label = ctk.CTkLabel(self, image=self.cat_img_ctk, text="")
            self.cat_label.place(relx=1.0, rely=1.0, x=-5, y=-5, anchor="se")
        except Exception as e:
            print(f"Erro ao carregar gato.png: {e}")

    def on_sair(self):
        kill_current_process()
        self.quit()

    def run_script(self, script_path):
        run_program(script_path, self.debug_text)

    def toggle_db_view(self):
        if self.debug_frame.winfo_ismapped():
            self.debug_frame.pack_forget()
            self.db_frame.pack(fill="both", expand=True)
        else:
            self.db_frame.pack_forget()
            self.debug_frame.pack(fill="both", expand=True)

    # -------------------------------
    # Seção Database
    # -------------------------------
    def create_db_area(self):
        self.db_title = ctk.CTkLabel(self.db_frame, text="Consulta Database de Servos", font=("Helvetica", 18, "bold"))
        self.db_title.pack(pady=10)

        self.filters_flow_frame = ctk.CTkFrame(self.db_frame, height=120)
        self.filters_flow_frame.pack(fill="x", padx=10, pady=5)
        self.filters_flow_frame.bind("<Configure>", self.on_filters_flow_configure)

        self.filter_blocks = []

        def add_filter_block(label_text):
            block_frame = ctk.CTkFrame(self.filters_flow_frame)
            lbl = ctk.CTkLabel(block_frame, text=label_text)
            ent = ctk.CTkEntry(block_frame, width=100)
            lbl.pack(side="left", padx=5, pady=5)
            ent.pack(side="left", padx=5, pady=5)
            block_frame.update_idletasks()
            return block_frame, ent

        self.block_torque_min, self.ent_torque_min = add_filter_block("Torque mín (kgf.cm):")
        self.block_weight_max, self.ent_weight_max = add_filter_block("Peso máx (g):")
        self.block_length_max, self.ent_length_max = add_filter_block("Compr. máx (mm):")
        self.block_width_max, self.ent_width_max = add_filter_block("Larg. máx (mm):")
        self.block_height_max, self.ent_height_max = add_filter_block("Altura máx (mm):")
        self.block_speed_min, self.ent_speed_min = add_filter_block("Vel. ang mín (°/s):")
        self.block_price_max, self.ent_price_max = add_filter_block("Preço máx ($):")

        self.filter_blocks = [
            self.block_torque_min,
            self.block_weight_max,
            self.block_length_max,
            self.block_width_max,
            self.block_height_max,
            self.block_speed_min,
            self.block_price_max
        ]

        self.btn_aplicar = ctk.CTkButton(self.db_frame, text="Aplicar Filtros", command=self.aplicar_filtros)
        self.btn_aplicar.pack(pady=5)

        self.results_frame = ctk.CTkFrame(self.db_frame)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame rolável para exibir resultados
        self.servos_scrollable_frame = ctk.CTkScrollableFrame(self.results_frame)
        self.servos_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.servo_blocks = []

    def on_filters_flow_configure(self, event):
        flow_layout(self.filters_flow_frame, self.filter_blocks, padding_x=10, padding_y=5)

    def aplicar_filtros(self):
        for sb in self.servo_blocks:
            sb.destroy()
        self.servo_blocks.clear()

        def readfloat(entry):
            txt = entry.get().strip()
            if not txt:
                return None
            try:
                return float(txt)
            except:
                return None

        torque_min = readfloat(self.ent_torque_min)
        weight_max = readfloat(self.ent_weight_max)
        length_max = readfloat(self.ent_length_max)
        width_max = readfloat(self.ent_width_max)
        height_max = readfloat(self.ent_height_max)
        speed_min = readfloat(self.ent_speed_min)
        price_max = readfloat(self.ent_price_max)

        csv_path = os.path.join("Database", "servos.csv")
        if not os.path.exists(csv_path):
            messagebox.showerror("Erro", "Arquivo de database não encontrado.")
            return

        matched_results = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line.startswith("sep="):
                    f.seek(0)
                reader = csv.DictReader(f, delimiter=",")

                for row in reader:
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

                    matched_results.append(row)
        except Exception as e:
            messagebox.showerror("Erro CSV", f"Falha ao ler CSV: {e}")
            return

        if not matched_results:
            msg = ctk.CTkLabel(self.servos_scrollable_frame, text="Nenhum resultado encontrado.", font=("Helvetica", 14))
            msg.pack(padx=10, pady=10)
            self.servo_blocks.append(msg)
            return

        for idx, row in enumerate(matched_results):
            block = self.create_servo_block(row, parent=self.servos_scrollable_frame)
            row_idx = idx // 7
            col_idx = idx % 7
            block.grid(row=row_idx, column=col_idx, padx=10, pady=10, sticky="n")
            self.servo_blocks.append(block)

    def create_servo_block(self, row, parent):
        block_frame = ctk.CTkFrame(parent, corner_radius=8, fg_color="#333333")
        block_frame.configure(width=200, height=300)

        make = row.get("Make", "")
        model = row.get("Model", "")
        title_str = f"{make} {model}"
        lbl_title = ctk.CTkLabel(block_frame, text=title_str, font=("Helvetica", 20, "bold"))
        lbl_title.pack(padx=5, pady=5)

        lbl_img = ctk.CTkLabel(block_frame, text="(Carregando imagem...)")
        lbl_img.pack(padx=5, pady=5)

        # Carrega a imagem de forma assíncrona
        def load_image_async():
            image_path = fetch_image_for_model(model)
            if image_path and os.path.exists(image_path):
                try:
                    img_raw = Image.open(image_path)
                    img_raw.thumbnail((80, 80))
                    servo_imgtk = ctk.CTkImage(light_image=img_raw, dark_image=img_raw, size=(80, 80))
                    def update_label():
                        lbl_img.configure(image=servo_imgtk, text="")
                        lbl_img.image = servo_imgtk
                    lbl_img.after(0, update_label)
                except Exception as e:
                    def update_label_error():
                        lbl_img.configure(text="(Erro na imagem)")
                    lbl_img.after(0, update_label_error)
            else:
                def update_label_no_image():
                    lbl_img.configure(text="(Sem imagem)")
                lbl_img.after(0, update_label_no_image)

        threading.Thread(target=load_image_async, daemon=True).start()

        desc_lines = []
        if row.get("Make"):
            desc_lines.append(f"Fabricante: {row.get('Make')}")
        if row.get("Model"):
            desc_lines.append(f"Modelo: {row.get('Model')}")
        if row.get("Modulacao"):
            desc_lines.append(f"Modulacao: {row.get('Modulacao')}")
        if row.get("Typical Price"):
            desc_lines.append(f"Preço: {row.get('Typical Price')}")
        if row.get("Weight (g)"):
            desc_lines.append(f"Peso (g): {row.get('Weight (g)')}")

        L = row.get("L (mm)") or ""
        C = row.get("C (mm)") or ""
        A = row.get("A (mm)") or ""
        if L or C or A:
            desc_lines.append(f"LxCxA (mm): {L}x{C}x{A}")

        torque_lines = []
        for i in range(1, 6):
            tensao_key = f"TensãoTorque{i}"
            torque_key = f"Torque{i} (kgf.cm)"
            tensao = row.get(tensao_key)
            torque = row.get(torque_key)
            if tensao or torque:
                torque_lines.append(f"{tensao or ''} {torque or ''}".strip())
        if torque_lines:
            desc_lines.append("Tensão (V) | Torque (kgf.cm):")
            desc_lines.extend(torque_lines)

        speed_lines = []
        for i in range(1, 6):
            tensao_key = f"TensãoSpeed{i}"
            speed_key = f"Speed{i} (°/s)"
            tensao_speed = row.get(tensao_key)
            speed_val = row.get(speed_key)
            if tensao_speed or speed_val:
                speed_lines.append(f"{tensao_speed or ''} {speed_val or ''}".strip())
        if speed_lines:
            desc_lines.append("Tensão (V) | Velocidade (°/s):")
            desc_lines.extend(speed_lines)

        if row.get("Tipo motor"):
            desc_lines.append(f"Tipo motor: {row.get('Tipo motor')}")
        if row.get("Rotação"):
            desc_lines.append(f"Rotação: {row.get('Rotação')}")
        if row.get("Material eng."):
            desc_lines.append(f"Material eng.: {row.get('Material eng.')}")

        desc_text = "\n".join(desc_lines)
        lbl_desc = ctk.CTkLabel(block_frame, text=desc_text, font=("Helvetica", 15), justify="left")
        lbl_desc.pack(padx=5, pady=5)

        def open_datasheet():
            datasheet_path = os.path.join("Database", "Datasheets", f"{model}.pdf")
            if os.path.exists(datasheet_path):
                try:
                    if sys.platform.startswith('win'):
                        os.startfile(datasheet_path)
                    elif sys.platform.startswith('darwin'):
                        subprocess.call(['open', datasheet_path])
                    else:
                        subprocess.call(['xdg-open', datasheet_path])
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao abrir PDF:\n{e}")
            else:
                messagebox.showwarning("Aviso", "Num tem pra esse :(")

        btn_pdf = ctk.CTkButton(block_frame, text="Datasheet", command=open_datasheet)
        btn_pdf.pack(pady=(0, 5))

        return block_frame

def main():
    app = ServoValidatorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
