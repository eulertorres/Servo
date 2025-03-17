import os
import json
import shutil
import customtkinter as ctk
from tkinter import filedialog as fd
from tkinter import messagebox  # Para exibir mensagens de aviso/erro
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# 1) Caminhos com base no local do script (Add_servo.py)
script_dir = os.path.dirname(os.path.abspath(__file__))  # pasta do Add_servo.py
repo_dir   = os.path.dirname(script_dir)                 # pasta raiz do repositório

# Diretórios de destino
JSON_PATH   = os.path.join(repo_dir, "Database", "servos.json")   # <-- Agora é JSON
IMAGES_DIR  = os.path.join(repo_dir, "Database", "Images")
DATASHEETS_DIR = os.path.join(repo_dir, "Database", "Datasheets")

# Cria as pastas caso não existam
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(DATASHEETS_DIR, exist_ok=True)

class ServoRegistrationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cadastro de Servos")
        self.geometry("1450x600")

        # Variáveis para armazenar os caminhos de arquivo selecionados
        self.selected_image_path = None
        self.selected_pdf_path = None

        # =============== TOPO: LOGO + TÍTULO ===============
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(side="top", fill="x", pady=10)

        title_label = ctk.CTkLabel(
            top_frame, 
            text="CADASTRO DE UM NOVO SERVO",
            font=("Helvetica", 32, "bold")
        )
        title_label.pack(side="left", padx=10)

        # Tenta carregar a logo
        try:
            logo_path = os.path.join(script_dir, "Xmobots_logo.png")
            logo_img = Image.open(logo_path)
            logo_img.thumbnail((240, 120))  # Redimensiona
            self.logo_imgtk = ctk.CTkImage(dark_image=logo_img, size=(240, 80))
            logo_label = ctk.CTkLabel(top_frame, image=self.logo_imgtk, text="")
            logo_label.pack(side="right", padx=20)
        except Exception as e:
            print(f"Não foi possível carregar a logo: {e}")
            self.logo_imgtk = None

        # =============== FRAME PRINCIPAL (inputs) ===============
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        inputs_frame = ctk.CTkFrame(main_frame)
        inputs_frame.pack(fill="both", expand=True, pady=10)

        def create_labeled_entry(parent, label_text, row, column, width=150):
            lbl = ctk.CTkLabel(parent, text=label_text)
            lbl.grid(row=row, column=column*2, padx=5, pady=5, sticky="e")
            entry = ctk.CTkEntry(parent, width=width)
            entry.grid(row=row, column=column*2 + 1, padx=5, pady=5, sticky="w")
            return entry

        # ========== Primeira linha de campos ==========
        self.entry_make  = create_labeled_entry(inputs_frame, "Fabricante:", 0, 0)
        self.entry_model = create_labeled_entry(inputs_frame, "Modelo:",     0, 1)

        # Opções de modulação
        modulation_options = ["Analog", "Digital"]
        self.modulation_var = ctk.StringVar(value=modulation_options[0])
        lbl_mod = ctk.CTkLabel(inputs_frame, text="Modulação:")
        lbl_mod.grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.option_modulation = ctk.CTkOptionMenu(
            inputs_frame,
            values=modulation_options,
            variable=self.modulation_var,
            width=100,
            fg_color="green",
            button_color="green",
            button_hover_color="#006400",
            dropdown_fg_color="green",
            dropdown_hover_color="#006400"
        )
        self.option_modulation.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        self.entry_weight = create_labeled_entry(inputs_frame, "Peso (g):", 0, 3)

        # ========== Segunda linha ==========
        self.entry_l = create_labeled_entry(inputs_frame, "Largura (mm):",     1, 0)
        self.entry_c = create_labeled_entry(inputs_frame, "Comprimento (mm):", 1, 1)
        self.entry_a = create_labeled_entry(inputs_frame, "Altura (mm):",      1, 2)

        # ========== Tensão e Torque (1 a 5) ==========
        self.entry_tensao_torque1 = create_labeled_entry(inputs_frame, "Tensão1 (V):",      2, 0)
        self.entry_torque1        = create_labeled_entry(inputs_frame, "Torque1 (kgf.cm):", 3, 0)

        self.entry_tensao_torque2 = create_labeled_entry(inputs_frame, "Tensão2 (V):",      2, 1)
        self.entry_torque2        = create_labeled_entry(inputs_frame, "Torque2 (kgf.cm):", 3, 1)

        self.entry_tensao_torque3 = create_labeled_entry(inputs_frame, "Tensão3 (V):",      2, 2)
        self.entry_torque3        = create_labeled_entry(inputs_frame, "Torque3 (kgf.cm):", 3, 2)

        self.entry_tensao_torque4 = create_labeled_entry(inputs_frame, "Tensão4 (V):",      2, 3)
        self.entry_torque4        = create_labeled_entry(inputs_frame, "Torque4 (kgf.cm):", 3, 3)

        self.entry_tensao_torque5 = create_labeled_entry(inputs_frame, "Tensão5 (V):",      2, 4)
        self.entry_torque5        = create_labeled_entry(inputs_frame, "Torque5 (kgf.cm):", 3, 4)

        # ========== Velocidades (°/s) ==========
        self.entry_speed1 = create_labeled_entry(inputs_frame, "Speed1 (°/s):", 4, 0)
        self.entry_speed2 = create_labeled_entry(inputs_frame, "Speed2 (°/s):", 4, 1)
        self.entry_speed3 = create_labeled_entry(inputs_frame, "Speed3 (°/s):", 4, 2)
        self.entry_speed4 = create_labeled_entry(inputs_frame, "Speed4 (°/s):", 4, 3)
        self.entry_speed5 = create_labeled_entry(inputs_frame, "Speed5 (°/s):", 4, 4)

        # ========== Linha final: Motor, rotação, engrenagem e preço ==========
        motor_type_options = ["Coreless", "3-Pole", "Brushed", "Brushless", "DC"]
        self.motor_type_var = ctk.StringVar(value=motor_type_options[0])
        lbl_motor = ctk.CTkLabel(inputs_frame, text="Tipo Motor:")
        lbl_motor.grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.option_motor_type = ctk.CTkOptionMenu(
            inputs_frame,
            values=motor_type_options,
            variable=self.motor_type_var,
            width=100,
            fg_color="green",
            button_color="green",
            button_hover_color="#006400",
            dropdown_fg_color="green",
            dropdown_hover_color="#006400"
        )
        self.option_motor_type.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        rotation_options = ["Sigle Bearings", "Dual Bearings", "Bushing"]
        self.rotation_var = ctk.StringVar(value=rotation_options[0])
        lbl_rot = ctk.CTkLabel(inputs_frame, text="Rotação:")
        lbl_rot.grid(row=5, column=2, padx=5, pady=5, sticky="e")
        self.option_rotation = ctk.CTkOptionMenu(
            inputs_frame,
            values=rotation_options,
            variable=self.rotation_var,
            width=120,
            fg_color="green",
            button_color="green",
            button_hover_color="#006400",
            dropdown_fg_color="green",
            dropdown_hover_color="#006400"
        )
        self.option_rotation.grid(row=5, column=3, padx=5, pady=5, sticky="w")

        gear_mat_options = ["Plastic", "Metal"]
        self.gear_material_var = ctk.StringVar(value=gear_mat_options[0])
        lbl_gear = ctk.CTkLabel(inputs_frame, text="Material Engrenagem:")
        lbl_gear.grid(row=5, column=4, padx=5, pady=5, sticky="e")
        self.option_gear_material = ctk.CTkOptionMenu(
            inputs_frame,
            values=gear_mat_options,
            variable=self.gear_material_var,
            width=100,
            fg_color="green",
            button_color="green",
            button_hover_color="#006400",
            dropdown_fg_color="green",
            dropdown_hover_color="#006400"
        )
        self.option_gear_material.grid(row=5, column=5, padx=5, pady=5, sticky="w")

        self.entry_price = create_labeled_entry(inputs_frame, "Preço típico:", 6, 0)

        # Nova caixa de texto maior para Link, ao lado de Price
        lbl_link = ctk.CTkLabel(inputs_frame, text="Link de compra:")
        lbl_link.grid(row=6, column=2, padx=5, pady=5, sticky="e")
        self.entry_link = ctk.CTkEntry(inputs_frame, width=300)  # maior largura
        self.entry_link.grid(row=6, column=3, columnspan=3, padx=5, pady=5, sticky="w")

        # =============== Botões para selecionar imagem e PDF ===============
        file_buttons_frame = ctk.CTkFrame(main_frame)
        file_buttons_frame.pack(pady=10)

        btn_select_image = ctk.CTkButton(
            file_buttons_frame,
            text="Selecionar Imagem",
            command=self.select_image,
            fg_color="green",
            hover_color="#006400"
        )
        btn_select_image.grid(row=0, column=0, padx=10)

        btn_select_pdf = ctk.CTkButton(
            file_buttons_frame,
            text="Selecionar PDF",
            command=self.select_pdf,
            fg_color="green",
            hover_color="#006400"
        )
        btn_select_pdf.grid(row=0, column=1, padx=10)

        self.label_image_path = ctk.CTkLabel(file_buttons_frame, text="Nenhuma imagem selecionada")
        self.label_image_path.grid(row=1, column=0, columnspan=2, pady=5)

        self.label_pdf_path = ctk.CTkLabel(file_buttons_frame, text="Nenhum PDF selecionado")
        self.label_pdf_path.grid(row=2, column=0, columnspan=2, pady=5)

        # Botão para cadastrar
        btn_cadastrar = ctk.CTkButton(
            main_frame,
            text="Cadastrar",
            fg_color="green",
            hover_color="#006400",
            command=self.cadastrar_servo
        )
        btn_cadastrar.pack(pady=10)

        # =============== GATO NO CANTO INFERIOR-DIREITO ===============
        try:
            cat_path = os.path.join(script_dir, "gato_terno.png")
            cat_img = Image.open(cat_path)
            cat_img.thumbnail((80, 80))
            self.cat_imgtk = ctk.CTkImage(dark_image=cat_img, size=(80, 80))
            self.cat_label = ctk.CTkLabel(self, image=self.cat_imgtk, text="")
            self.cat_label.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")
        except Exception as e:
            print(f"Não foi possível carregar gato_terno.png: {e}")

        # =============== CONVERSOR NO CANTO INFERIOR-ESQUERDO ===============
        converter_frame = ctk.CTkFrame(self, corner_radius=8)
        converter_frame.place(relx=0, rely=1, anchor="sw", x=10, y=-10)

        label_converter_title = ctk.CTkLabel(converter_frame, text="N.m -> kgf.cm", font=("Helvetica", 12, "bold"))
        label_converter_title.pack(pady=5, padx=5)

        self.entry_nm = ctk.CTkEntry(converter_frame, width=80, placeholder_text="N.m")
        self.entry_nm.pack(pady=5, padx=5)

        self.label_result = ctk.CTkLabel(converter_frame, text="Resultado: ")
        self.label_result.pack(pady=5, padx=5)

        btn_convert = ctk.CTkButton(
            converter_frame,
            text="Converter",
            command=self.do_conversion,
            fg_color="green",
            hover_color="#006400"
        )
        btn_convert.pack(pady=5)

    def do_conversion(self):
        try:
            nm = float(self.entry_nm.get())
            kgfcm = nm * 10.19716213
            self.label_result.configure(text=f"{kgfcm:.2f} kgf.cm")
        except ValueError:
            self.label_result.configure(text="Valor inválido")

    def select_image(self):
        filetypes = [("Arquivos de Imagem", "*.jpg *.jpeg *.png *.bmp *.gif"), ("Todos os arquivos", "*.*")]
        path = fd.askopenfilename(title="Selecione a imagem do servo", filetypes=filetypes)
        if path:
            self.selected_image_path = path
            self.label_image_path.configure(text=f"Imagem selecionada: {path}")

    def select_pdf(self):
        filetypes = [("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
        path = fd.askopenfilename(title="Selecione o datasheet em PDF", filetypes=filetypes)
        if path:
            self.selected_pdf_path = path
            self.label_pdf_path.configure(text=f"PDF selecionado: {path}")

    def cadastrar_servo(self):
        """Coleta dados, salva no JSON e copia arquivos (imagem e PDF) para as pastas apropriadas."""
        model_name = self.entry_model.get().strip()
        if not model_name:
            messagebox.showwarning("Aviso", "Campo 'Modelo' não pode ficar vazio.")
            return

        # Monta o dicionário com todos os campos (igual as colunas do CSV)
        servo_dict = {
            "Make":            self.entry_make.get().strip(),
            "Model":           model_name,
            "Modulation":      self.modulation_var.get().strip(),
            "Weight (g)":      self.entry_weight.get().strip(),
            "L (mm)":          self.entry_l.get().strip(),
            "C (mm)":          self.entry_c.get().strip(),
            "A (mm)":          self.entry_a.get().strip(),

            "TensãoTorque1":   self.entry_tensao_torque1.get().strip(),
            "Torque1 (kgf.cm)": self.entry_torque1.get().strip(),
            "TensãoTorque2":   self.entry_tensao_torque2.get().strip(),
            "Torque2 (kgf.cm)": self.entry_torque2.get().strip(),
            "TensãoTorque3":   self.entry_tensao_torque3.get().strip(),
            "Torque3 (kgf.cm)": self.entry_torque3.get().strip(),
            "TensãoTorque4":   self.entry_tensao_torque4.get().strip(),
            "Torque4 (kgf.cm)": self.entry_torque4.get().strip(),
            "TensãoTorque5":   self.entry_tensao_torque5.get().strip(),
            "Torque5 (kgf.cm)": self.entry_torque5.get().strip(),

            # TensãoSpeed1 = TensãoTorque1
            "TensãoSpeed1":    self.entry_tensao_torque1.get().strip(),
            "Speed1 (°/s)":    self.entry_speed1.get().strip(),
            # TensãoSpeed2 = TensãoTorque2
            "TensãoSpeed2":    self.entry_tensao_torque2.get().strip(),
            "Speed2 (°/s)":    self.entry_speed2.get().strip(),
            # TensãoSpeed3 = TensãoTorque3
            "TensãoSpeed3":    self.entry_tensao_torque3.get().strip(),
            "Speed3 (°/s)":    self.entry_speed3.get().strip(),
            # TensãoSpeed4 = TensãoTorque4
            "TensãoSpeed4":    self.entry_tensao_torque4.get().strip(),
            "Speed4 (°/s)":    self.entry_speed4.get().strip(),
            # TensãoSpeed5 = TensãoTorque5
            "TensãoSpeed5":    self.entry_tensao_torque5.get().strip(),
            "Speed5 (°/s)":    self.entry_speed5.get().strip(),

            "Motor Type":      self.motor_type_var.get().strip(),
            "Rotation":        self.rotation_var.get().strip(),
            "Gear Material":   self.gear_material_var.get().strip(),
            "Typical Price":   self.entry_price.get().strip(),
            "Link":            self.entry_link.get().strip()
        }

        # Carrega (ou cria) o JSON
        data = {"servos": []}  # estrutura inicial
        if os.path.exists(JSON_PATH):
            try:
                with open(JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Esperamos que data tenha a chave "servos" como lista
                    if "servos" not in data:
                        data["servos"] = []
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao ler JSON:\n{e}")
                return

        # Adiciona o novo servo
        data["servos"].append(servo_dict)

        # Salva de volta no JSON
        try:
            with open(JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao escrever JSON:\n{e}")
            return

        # Substitui espaços por underscores no nome do modelo ao salvar os arquivos
        safe_model_name = model_name.replace(" ", "_")

        # Copiar imagem selecionada
        if self.selected_image_path:
            destination_image = os.path.join(IMAGES_DIR, f"{safe_model_name}.jpg")
            try:
                shutil.copy(self.selected_image_path, destination_image)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao copiar imagem:\n{e}")

        # Copiar PDF selecionado
        if self.selected_pdf_path:
            destination_pdf = os.path.join(DATASHEETS_DIR, f"{safe_model_name}.pdf")
            try:
                shutil.copy(self.selected_pdf_path, destination_pdf)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao copiar PDF:\n{e}")

        # Limpar os campos
        self.clear_fields()

        # Mensagem de sucesso
        messagebox.showinfo("Sucesso", "Servo cadastrado com sucesso!")

    def clear_fields(self):
        self.entry_make.delete(0, "end")
        self.entry_model.delete(0, "end")
        self.modulation_var.set("Analog")
        self.entry_weight.delete(0, "end")
        self.entry_l.delete(0, "end")
        self.entry_c.delete(0, "end")
        self.entry_a.delete(0, "end")

        self.entry_tensao_torque1.delete(0, "end")
        self.entry_torque1.delete(0, "end")
        self.entry_tensao_torque2.delete(0, "end")
        self.entry_torque2.delete(0, "end")
        self.entry_tensao_torque3.delete(0, "end")
        self.entry_torque3.delete(0, "end")
        self.entry_tensao_torque4.delete(0, "end")
        self.entry_torque4.delete(0, "end")
        self.entry_tensao_torque5.delete(0, "end")
        self.entry_torque5.delete(0, "end")

        self.entry_speed1.delete(0, "end")
        self.entry_speed2.delete(0, "end")
        self.entry_speed3.delete(0, "end")
        self.entry_speed4.delete(0, "end")
        self.entry_speed5.delete(0, "end")

        self.motor_type_var.set("Coreless")
        self.rotation_var.set("Sigle Bearings")
        self.gear_material_var.set("Plastic")
        self.entry_price.delete(0, "end")
        self.entry_link.delete(0, "end")

        self.selected_image_path = None
        self.selected_pdf_path = None
        self.label_image_path.configure(text="Nenhuma imagem selecionada")
        self.label_pdf_path.configure(text="Nenhum PDF selecionado")

def main():
    app = ServoRegistrationApp()
    app.mainloop()

if __name__ == "__main__":
    main()
