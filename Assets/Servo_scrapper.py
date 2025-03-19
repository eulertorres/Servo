import os
import re
import json
import requests
import customtkinter as ctk
from tkinter import messagebox, END
from PIL import Image
import webbrowser
import winsound  # Som de alerta no Windows

# Precisamos do BeautifulSoup
try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("É necessário instalar beautifulsoup4 (pip install beautifulsoup4)")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(BASE_DIR)
DATABASE_DIR = os.path.join(repo_dir, "Database", "Data")
os.makedirs(DATABASE_DIR, exist_ok=True)

class HTMLDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gerenciador de Downloads e Extração de HTML")
        self.geometry("1000x600")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True)

        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)

        # Frames
        self.left_frame = ctk.CTkFrame(main_container)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.right_frame = ctk.CTkFrame(main_container)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Variáveis
        self.site_var = ctk.StringVar(value="")
        self.selected_site = None
        self.result_checkboxes = []
        self.matches_by_file = {}

        # Dropdown de servo
        self.servo_file_var = ctk.StringVar(value="")
        self.servo_files = []

        # Guardaremos aqui as "labels" que identificamos como importantes.
        # Por exemplo, se o HTML tiver uma linha <td>Operating Voltage (V)</td> e for interessante, salvamos aqui.
        self.found_labels = {}

        # Constrói interface
        self.build_left_frame()
        self.build_right_frame()

        self.update_site_dropdown()

    # ----------------------------------------------------------
    #                FRAME ESQUERDO
    # ----------------------------------------------------------
    def build_left_frame(self):
        title_label = ctk.CTkLabel(self.left_frame, text="Baixar HTML", font=("Helvetica", 18, "bold"))
        title_label.pack(pady=5)

        download_frame = ctk.CTkFrame(self.left_frame)
        download_frame.pack(fill="x", padx=5, pady=5)

        lbl_url = ctk.CTkLabel(download_frame, text="URL com [P]:")
        lbl_url.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_url = ctk.CTkEntry(download_frame, width=220)
        self.entry_url.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.btn_paste = ctk.CTkButton(
            download_frame,
            text="Colar do Clipboard",
            command=self.paste_from_clipboard,
            fg_color="#228B22", hover_color="#006400"
        )
        self.btn_paste.grid(row=0, column=2, padx=5, pady=5)

        lbl_min = ctk.CTkLabel(download_frame, text="Página Mínima:")
        lbl_min.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_min = ctk.CTkEntry(download_frame, width=80)
        self.entry_min.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        lbl_max = ctk.CTkLabel(download_frame, text="Página Máxima:")
        lbl_max.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.entry_max = ctk.CTkEntry(download_frame, width=80)
        self.entry_max.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        btn_download = ctk.CTkButton(
            download_frame,
            text="Baixar HTML",
            command=self.download_html,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_download.grid(row=3, column=0, columnspan=3, pady=5)

        dropdown_frame = ctk.CTkFrame(self.left_frame)
        dropdown_frame.pack(fill="x", padx=5, pady=5)

        lbl_sites = ctk.CTkLabel(dropdown_frame, text="Sites baixados:", font=("Helvetica", 14))
        lbl_sites.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.dropdown_sites = ctk.CTkOptionMenu(
            dropdown_frame,
            values=[],
            variable=self.site_var,
            fg_color="#228B22", button_color="#228B22",
            button_hover_color="#006400", dropdown_fg_color="#333333",
            dropdown_hover_color="#444444"
        )
        self.dropdown_sites.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        btn_update_sites = ctk.CTkButton(
            dropdown_frame,
            text="Atualizar Lista",
            command=self.update_site_dropdown,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_update_sites.grid(row=1, column=0, columnspan=2, pady=5)

        btn_configurar_pagina = ctk.CTkButton(
            self.left_frame,
            text="Configurar Página",
            command=self.configure_page,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_configurar_pagina.pack(pady=5)

        btn_configurar_servo = ctk.CTkButton(
            self.left_frame,
            text="Configurar Servo",
            command=self.configure_servo,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_configurar_servo.pack(pady=5)

        btn_garimpar = ctk.CTkButton(
            self.left_frame,
            text="Garimpar",
            command=self.garimpar_checked_results,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_garimpar.pack(pady=5)

    # ----------------------------------------------------------
    #                FRAME DIREITO
    # ----------------------------------------------------------
    def build_right_frame(self):
        # Frame para Configurar Página
        self.page_config_frame = ctk.CTkFrame(self.right_frame)
        self.page_config_frame.pack(fill="both", expand=True)

        config_title = ctk.CTkLabel(self.page_config_frame, text="Configuração de Padrão (Página)", font=("Helvetica", 18, "bold"))
        config_title.pack(pady=5)

        config_inputs_frame = ctk.CTkFrame(self.page_config_frame)
        config_inputs_frame.pack(fill="x", padx=5, pady=5)

        lbl_nome_ex = ctk.CTkLabel(config_inputs_frame, text="Exemplo de Nome:")
        lbl_nome_ex.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_nome_ex = ctk.CTkEntry(config_inputs_frame, width=220)
        self.entry_nome_ex.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        lbl_url_ex = ctk.CTkLabel(config_inputs_frame, text="Exemplo de URL:")
        lbl_url_ex.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_url_ex = ctk.CTkEntry(config_inputs_frame, width=220)
        self.entry_url_ex.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        btn_find_pattern = ctk.CTkButton(
            config_inputs_frame,
            text="Localizar Padrão e Listar",
            command=self.find_pattern_and_list,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_find_pattern.grid(row=2, column=0, columnspan=2, pady=10)

        lbl_result = ctk.CTkLabel(self.page_config_frame, text="Resultados Encontrados:", font=("Helvetica", 14, "bold"))
        lbl_result.pack(pady=5)

        self.scrollable_results = ctk.CTkScrollableFrame(self.page_config_frame, width=400, height=300)
        self.scrollable_results.pack(fill="both", expand=True, padx=5, pady=5)

        # Frame para Configurar Servo
        self.servo_config_frame = ctk.CTkFrame(self.right_frame)

        servo_title = ctk.CTkLabel(self.servo_config_frame, text="Configuração de Servo", font=("Helvetica", 18, "bold"))
        servo_title.pack(pady=5)

        self.servo_dropdown_frame = ctk.CTkFrame(self.servo_config_frame)
        self.servo_dropdown_frame.pack(pady=5)

        lbl_servo_file = ctk.CTkLabel(self.servo_dropdown_frame, text="Arquivo de Servo HTML:")
        lbl_servo_file.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.servo_file_dropdown = ctk.CTkOptionMenu(
            self.servo_dropdown_frame,
            values=[],
            variable=self.servo_file_var,
            fg_color="#228B22", button_color="#228B22",
            button_hover_color="#006400", dropdown_fg_color="#333333",
            dropdown_hover_color="#444444"
        )
        self.servo_file_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        btn_open_browser = ctk.CTkButton(
            self.servo_dropdown_frame,
            text="Abrir no Navegador",
            command=self.open_servo_in_browser,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_open_browser.grid(row=0, column=2, padx=5, pady=5)

        # Campos de exemplo que o usuário pode digitar
        self.servo_fields_vars = {
            "Tensão Operação": ctk.StringVar(),
            "Tensão Operação2": ctk.StringVar(),
            "Peso": ctk.StringVar(),
            "Dimensões": ctk.StringVar(),
            "Torque1": ctk.StringVar(),
            "Torque2": ctk.StringVar(),
            "Material": ctk.StringVar(),
            "Velocidade1": ctk.StringVar(),
            "Velocidade2": ctk.StringVar(),
            "Tipo Motor": ctk.StringVar(),
            "Preço": ctk.StringVar(),
        }

        servo_inputs_frame = ctk.CTkFrame(self.servo_config_frame)
        servo_inputs_frame.pack(pady=10, padx=10, fill="x")

        row_i = 0
        for field_name in self.servo_fields_vars:
            lbl = ctk.CTkLabel(servo_inputs_frame, text=field_name + ":")
            lbl.grid(row=row_i, column=0, padx=5, pady=5, sticky="e")
            ent = ctk.CTkEntry(servo_inputs_frame, width=220, textvariable=self.servo_fields_vars[field_name])
            ent.grid(row=row_i, column=1, padx=5, pady=5, sticky="w")
            row_i += 1

        btn_find_servo_pattern = ctk.CTkButton(
            self.servo_config_frame,
            text="Localizar Padrão (Servo)",
            command=self.servo_find_pattern_and_list,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_find_servo_pattern.pack(pady=5)

        btn_confirm_servo = ctk.CTkButton(
            self.servo_config_frame,
            text="Confirmar Garimpo (Servo)",
            command=self.servo_confirm_garimpo,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_confirm_servo.pack(pady=5)

        self.scrollable_servo_results = ctk.CTkScrollableFrame(self.servo_config_frame, width=400, height=200)
        self.scrollable_servo_results.pack(fill="both", expand=True, padx=5, pady=5)

        self.show_page_config_frame()

    # ----------------------------------------------------------
    #           MOSTRAR FRAME DE PÁGINA / SERVO
    # ----------------------------------------------------------
    def show_page_config_frame(self):
        self.servo_config_frame.pack_forget()
        self.page_config_frame.pack(fill="both", expand=True)

    def show_servo_config_frame(self):
        self.page_config_frame.pack_forget()
        self.servo_config_frame.pack(fill="both", expand=True)

    # ----------------------------------------------------------
    #           BOTÕES "Configurar Página"/"Servo"
    # ----------------------------------------------------------
    def configure_page(self):
        selection = self.site_var.get()
        if not selection or selection == "(Nenhum)":
            self.show_scary_alert("Aviso", "Nenhum site válido selecionado.")
            return
        self.selected_site = selection
        self.show_scary_alert("Info", f"Site '{selection}' selecionado para configuração de página.")
        self.show_page_config_frame()

    def configure_servo(self):
        selection = self.site_var.get()
        if not selection or selection == "(Nenhum)":
            self.show_scary_alert("Aviso", "Nenhum site válido selecionado.")
            return
        self.selected_site = selection
        self.show_scary_alert("Info", f"Site '{selection}' selecionado para configuração de servo.")

        servo_dir = os.path.join(DATABASE_DIR, self.selected_site, "servoshtml")
        if not os.path.isdir(servo_dir):
            os.makedirs(servo_dir, exist_ok=True)

        self.servo_files = [f for f in os.listdir(servo_dir) if f.endswith(".html")]
        self.servo_files.sort()
        if self.servo_files:
            self.servo_file_dropdown.configure(values=self.servo_files)
            self.servo_file_var.set(self.servo_files[0])
        else:
            self.servo_file_dropdown.configure(values=["(Nenhum)"])
            self.servo_file_var.set("(Nenhum)")

        self.show_servo_config_frame()

    # ----------------------------------------------------------
    #          ABRIR HTML SELECIONADO NO NAVEGADOR
    # ----------------------------------------------------------
    def open_servo_in_browser(self):
        if not self.selected_site:
            return
        servo_dir = os.path.join(DATABASE_DIR, self.selected_site, "servoshtml")
        selected_file = self.servo_file_var.get()
        if not selected_file or selected_file == "(Nenhum)":
            return
        full_path = os.path.join(servo_dir, selected_file)
        if os.path.exists(full_path):
            webbrowser.open(f"file://{full_path}")

    # ----------------------------------------------------------
    #                 DOWNLOAD HTML
    # ----------------------------------------------------------
    def download_html(self):
        """Baixa páginas HTML de URL com [P], salva em Database/Data/<nome_site>."""
        url = self.entry_url.get().strip()
        min_page = self.entry_min.get().strip()
        max_page = self.entry_max.get().strip()

        if not url or "[P]" not in url:
            messagebox.showerror("Erro", "A URL deve conter o placeholder [P].")
            return

        try:
            min_page = int(min_page)
            max_page = int(max_page)
        except ValueError:
            messagebox.showerror("Erro", "Páginas mínima e máxima devem ser números inteiros.")
            return

        if min_page > max_page:
            messagebox.showerror("Erro", "Página mínima não pode ser maior que a página máxima.")
            return

        # Extrair nome da pasta (entre "www." e o próximo ".")
        match = re.search(r'www\.([^.]+)\.', url)
        if match:
            folder_name = match.group(1)
        else:
            messagebox.showerror("Erro", "Não foi possível extrair o nome da nova pasta da URL.")
            return

        target_dir = os.path.join(DATABASE_DIR, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        # Cabeçalhos para evitar erro 406, etc.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        for page in range(min_page, max_page + 1):
            page_url = url.replace("[P]", str(page))
            try:
                response = requests.get(page_url, headers=headers)
                response.raise_for_status()
                html_content = response.text
                file_name = f"page_{page}.html"
                file_path = os.path.join(target_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao baixar a página {page}:\n{e}")
                return

        messagebox.showinfo("Sucesso", f"Download concluído!\nArquivos salvos em: {target_dir}")
        self.update_site_dropdown()

    # ----------------------------------------------------------
    #      Localizar Padrão e Listar (Página)
    # ----------------------------------------------------------
    def find_pattern_and_list(self):
        if not self.selected_site:
            self.show_scary_alert("Erro", "Nenhum site selecionado. Clique em 'Configurar Página' antes.")
            return

        nome_ex = self.entry_nome_ex.get().strip()
        url_ex = self.entry_url_ex.get().strip()
        if not nome_ex or not url_ex:
            self.show_scary_alert("Erro", "Insira exemplo de nome e URL.")
            return

        site_dir = os.path.join(DATABASE_DIR, self.selected_site)
        if not os.path.isdir(site_dir):
            self.show_scary_alert("Erro", f"Pasta '{site_dir}' não existe.")
            return

        html_files = [f for f in os.listdir(site_dir) if f.endswith(".html")]
        html_files.sort()
        if not html_files:
            self.show_scary_alert("Erro", f"Nenhum arquivo HTML encontrado em {site_dir}")
            return

        first_html_path = os.path.join(site_dir, html_files[0])
        with open(first_html_path, "r", encoding="utf-8") as f:
            first_html_content = f.read()
            print("Lendo: ", first_html_content)

        if url_ex not in first_html_content:
            self.show_scary_alert("Aviso", "URL de exemplo não encontrada no primeiro HTML.")
        if nome_ex not in first_html_content:
            self.show_scary_alert("Aviso", "Nome de exemplo não encontrado no primeiro HTML.")

        pattern = re.compile(r'<a\s+href="([^"]+)"[^>]*>.*?<h2>([^<]+)</h2>', re.DOTALL)

        self.matches_by_file.clear()
        all_results = []

        for html_file in html_files:
            full_path = os.path.join(site_dir, html_file)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            matches = pattern.findall(content)
            if matches:
                self.matches_by_file[html_file] = matches
                for (u, n) in matches:
                    all_results.append((html_file, u, n))

        for widget in self.scrollable_results.winfo_children():
            widget.destroy()
        self.result_checkboxes = []

        if not all_results:
            ctk.CTkLabel(self.scrollable_results, text="Nenhum resultado encontrado.").pack()
            return

        for (html_file, url_found, name_found) in all_results:
            line_text = f"{html_file}: {name_found} -> {url_found}"
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(
                self.scrollable_results,
                text=line_text,
                variable=var,
                fg_color="#228B22", hover_color="#006400", border_color="#228B22"
            )
            chk.pack(anchor="w", padx=5, pady=2)
            self.result_checkboxes.append((chk, var, url_found, name_found))

    # ----------------------------------------------------------
    #        BOTÃO "Garimpar" (baixar HTMLs marcados)
    # ----------------------------------------------------------
    def garimpar_checked_results(self):
        if not self.selected_site:
            self.show_scary_alert("Erro", "Nenhum site selecionado para garimpar.")
            return

        site_dir = os.path.join(DATABASE_DIR, self.selected_site)
        servo_dir = os.path.join(site_dir, "servoshtml")
        os.makedirs(servo_dir, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Garimpando HTMLs...")
        progress_label = ctk.CTkLabel(progress_window, text="Iniciando garimpo...")
        progress_label.pack(pady=10, padx=10)
        progress_bar = ctk.CTkProgressBar(progress_window, width=300)
        progress_bar.pack(pady=10, padx=10)
        progress_bar.set(0)

        checked = [(u, n) for (_, var, u, n) in self.result_checkboxes if var.get()]
        total = len(checked)
        if total == 0:
            progress_window.destroy()
            self.show_scary_alert("Aviso", "Nenhum item marcado para garimpar.")
            return

        downloaded_count = 0
        skipped_count = 0

        for i, (url_found, name_found) in enumerate(checked, start=1):
            safe_name = re.sub(r'[^\w_-]+', '_', name_found)
            file_path = os.path.join(servo_dir, f"{safe_name}.html")

            if os.path.exists(file_path):
                skipped_count += 1
            else:
                try:
                    r = requests.get(url_found, headers=headers)
                    r.raise_for_status()
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(r.text)
                    downloaded_count += 1
                except Exception as e:
                    print(f"Falha ao garimpar URL {url_found}: {e}")

            progress_label.configure(text=f"Garimpando {i}/{total}...")
            progress_bar.set(i / total)
            progress_window.update()

        progress_window.destroy()
        msg = f"Garimpo concluído.\nBaixados: {downloaded_count}, Já existiam: {skipped_count}."
        self.show_scary_alert("Garimpo Concluído", msg)

    # ----------------------------------------------------------
    #    "Configurar Servo" => Localizar Padrão (Exemplo c/ BS4)
    # ----------------------------------------------------------
    def servo_find_pattern_and_list(self):
        """
        1) Lê o arquivo HTML selecionado.
        2) Usa BeautifulSoup para encontrar <tr> com label e valor.
        3) Se o 'value_text' contiver o EXEMPLO do usuário, marcamos a label como interessante.
        4) Printamos (com clareza) as labels e o que foi encontrado.
        """
        if not self.selected_site:
            self.show_scary_alert("Erro", "Nenhum site selecionado.")
            return

        servo_dir = os.path.join(DATABASE_DIR, self.selected_site, "servoshtml")
        if not os.path.isdir(servo_dir):
            self.show_scary_alert("Erro", "Pasta servoshtml não existe.")
            return

        selected_file = self.servo_file_var.get()
        if not selected_file or selected_file == "(Nenhum)":
            self.show_scary_alert("Aviso", "Nenhum arquivo servo selecionado.")
            return

        full_path = os.path.join(servo_dir, selected_file)
        if not os.path.exists(full_path):
            self.show_scary_alert("Erro", f"Arquivo {selected_file} não existe.")
            return

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")

        # Coleta os exemplos que o usuário digitou
        examples = {}
        for field_name, var in self.servo_fields_vars.items():
            val = var.get().strip()
            if val:
                examples[field_name] = val

        # Limpa a área de resultados
        for widget in self.scrollable_servo_results.winfo_children():
            widget.destroy()

        if not examples:
            ctk.CTkLabel(self.scrollable_servo_results, text="Nenhum valor de exemplo preenchido.").pack()
            return

        all_trs = soup.find_all("tr")
        self.found_labels.clear()  # zera o dicionário de labels interessantes
        lines_found = []

        for tr in all_trs:
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            label_text = tds[0].get_text(strip=True)
            value_text = tds[1].get_text(strip=True)

            # Se "value_text" contiver algum exemplo, marcamos essa label
            for field, example_val in examples.items():
                if example_val in value_text:
                    self.found_labels[label_text] = True
                    lines_found.append(f"Label: '{label_text}' -> valor: '{value_text}' (contém exemplo '{example_val}')")

        if not lines_found:
            ctk.CTkLabel(self.scrollable_servo_results, text="Nenhuma correspondência encontrada.").pack()
        else:
            for line in lines_found:
                ctk.CTkLabel(self.scrollable_servo_results, text=line).pack(anchor="w")

        # Printar no console com mais clareza
        print("========== DETALHES DO PADRÃO ENCONTRADO ==========")
        for line in lines_found:
            print(line)
        print("Labels marcadas como interessantes:", list(self.found_labels.keys()))

        self.show_scary_alert("Info", "Localização de padrão para servo concluída (arquivo selecionado).")

    def transform_servo_dict(self, raw_dict, site_name):
        """
        Recebe um dicionário com valores "brutos" e retorna
        um novo dicionário no formato final desejado.
        """

        final = {
            "Make": site_name,  # por exemplo, "hiteccs"
            "Model": raw_dict.get("Model", ""),
            "Modulation": raw_dict.get("Modulation", ""),  # preencha se necessário
            "Weight (g)": raw_dict.get("Weight (g)", ""),
            "L (mm)": "",
            "C (mm)": "",
            "A (mm)": "",
            "TensãoTorque1": "",
            "Torque1 (kgf.cm)": "",
            "TensãoTorque2": "",
            "Torque2 (kgf.cm)": "",
            "TensãoTorque3": "",
            "Torque3 (kgf.cm)": "",
            "TensãoTorque4": "",
            "Torque4 (kgf.cm)": "",
            "TensãoTorque5": "",
            "Torque5 (kgf.cm)": "",
            "TensãoSpeed1": "",
            "Speed1 (°/s)": "",
            "TensãoSpeed2": "",
            "Speed2 (°/s)": "",
            "TensãoSpeed3": "",
            "Speed3 (°/s)": "",
            "TensãoSpeed4": "",
            "Speed4 (°/s)": "",
            "TensãoSpeed5": "",
            "Speed5 (°/s)": "",
            "Motor Type": raw_dict.get("Motor Type", ""),
            "Rotation": raw_dict.get("Rotation", ""),
            "Gear Material": raw_dict.get("Gear Material", ""),
            "Typical Price": ""
        }

        # ---------- 1) Separar Dimensions (mm) em L, C, A ----------
        dims = raw_dict.get("Dimensions (mm)", "").strip()
        # Exemplo: "30.0 x 10.0 x 29.5"
        parts = dims.split("x")
        if len(parts) == 3:
            final["L (mm)"] = parts[0].strip()
            final["C (mm)"] = parts[1].strip()
            final["A (mm)"] = parts[2].strip()

        # ---------- 2) Parse TensãoTorque1 (ex.: "Min: 6.00Max: 7.40") ----------
        tensao_str = raw_dict.get("TensãoTorque1", "").replace(" ", "")
        # Queremos capturar "Min: 6.00" e "Max: 7.40"
        match_tensao = re.search(r"Min:\s*([\d.]+).*Max:\s*([\d.]+)", tensao_str)
        if match_tensao:
            min_v = match_tensao.group(1)  # ex.: "6.00"
            max_v = match_tensao.group(2)  # ex.: "7.40"
            final["TensãoTorque1"] = min_v
            final["TensãoTorque2"] = max_v
            # Para Speed, é o mesmo
            final["TensãoSpeed1"] = min_v
            final["TensãoSpeed2"] = max_v

        # ---------- 3) Parse Torque1 (ex.: "Min: 5.7 / 79.16Max: 8.2 / 113.88") ----------
        torque_str = raw_dict.get("Torque1 (kgf.cm)", "").replace(" ", "")
        # Precisamos de "Min: 5.7" e "Max: 8.2"
        match_torque = re.search(r"Min:\s*([\d.]+).*Max:\s*([\d.]+)", torque_str)
        if match_torque:
            min_t = match_torque.group(1)
            max_t = match_torque.group(2)
            final["Torque1 (kgf.cm)"] = min_t
            final["Torque2 (kgf.cm)"] = max_t

        # ---------- 4) Parse Speed1 (ex.: "Min: 0.14Max: 0.09") e converter p/ °/s ----------
        speed_str = raw_dict.get("Speed1 (°/s)", "").replace(" ", "")
        # Exemplo: "Min:0.14Max:0.09" => speed_min = 60/0.14 => 428.57 => "428"
        match_speed = re.search(r"Min:\s*([\d.]+).*Max:\s*([\d.]+)", speed_str)
        if match_speed:
            speed_min = match_speed.group(1)  # ex.: "0.14"
            speed_max = match_speed.group(2)  # ex.: "0.09"
            try:
                s1 = 60.0 / float(speed_min)
                s2 = 60.0 / float(speed_max)
                final["Speed1 (°/s)"] = str(int(round(s1)))  # ex.: "428"
                final["Speed2 (°/s)"] = str(int(round(s2)))  # ex.: "666"
            except:
                pass

        # ---------- 5) Imprimir o resultado final ----------
        print("===== SERVO REFORMATADO =====")
        for k, v in final.items():
            print(f"{k}: {v}")
        print("================================\n")

        return final

    def servo_confirm_garimpo(self):
        """
        Lê todos os .html de servo no diretório do site,
        faz o parse das <tr> e monta um dicionário 'bruto'.
        Em seguida, chama transform_servo_dict(...) para
        formatar no padrão final e salva em JSON.
        """
        if not self.selected_site:
            self.show_scary_alert("Erro", "Nenhum site selecionado.")
            return

        servo_dir = os.path.join(DATABASE_DIR, self.selected_site, "servoshtml")
        if not os.path.isdir(servo_dir):
            self.show_scary_alert("Erro", "Pasta servoshtml não existe ou está vazia.")
            return

        html_files = [f for f in os.listdir(servo_dir) if f.endswith(".html")]
        html_files.sort()
        if not html_files:
            self.show_scary_alert("Erro", "Nenhum arquivo HTML de servo encontrado.")
            return

        # JSON final será salvo na pasta do site
        saved_json = os.path.join(servo_dir, "servos.json")

        data = {"servos": []}
        if os.path.exists(saved_json):
            try:
                with open(saved_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "servos" not in data:
                        data["servos"] = []
            except:
                pass

        from bs4 import BeautifulSoup

        for file in html_files:
            full_path = os.path.join(servo_dir, file)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")
            servo_name = os.path.splitext(file)[0]

            # Monta um dicionário "bruto" pegando as linhas <tr>
            raw_dict = {
                "Model": servo_name,
                "Make": "",  # se existir no HTML, preencha, senão deixamos vazio
                "Modulation": "",
                "Weight (g)": "",
                "Dimensions (mm)": "",
                "TensãoTorque1": "",
                "Torque1 (kgf.cm)": "",
                "Speed1 (°/s)": "",
                "Motor Type": "",
                "Rotation": "",
                "Gear Material": "",
                # ... se quiser mais campos
            }

            # Exemplo de parse: para cada <tr>, se a label for "Weight (g)", salvamos em raw_dict["Weight (g)"] = ...
            all_trs = soup.find_all("tr")
            for tr in all_trs:
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                label_text = tds[0].get_text(strip=True)
                value_text = tds[1].get_text(strip=True)

                # Exemplo de correspondências
                if label_text == "Weight (g)":
                    raw_dict["Weight (g)"] = value_text
                elif label_text == "Dimensions (mm)":
                    raw_dict["Dimensions (mm)"] = value_text
                elif label_text == "Operating Voltage (V)":  # ou "Tensão Operação"
                    raw_dict["TensãoTorque1"] = value_text
                elif label_text == "Stall Torque (kgf•cm / oz•in)":
                    raw_dict["Torque1 (kgf.cm)"] = value_text
                elif label_text == "No Load Speed (sec/60°)":
                    raw_dict["Speed1 (°/s)"] = value_text
                elif label_text == "Motor Type":
                    raw_dict["Motor Type"] = value_text
                elif label_text == "Gear Material":
                    raw_dict["Gear Material"] = value_text
                elif label_text == "Circuit":
                    # se for "Digital", "Analog" etc.
                    raw_dict["Modulation"] = value_text
                elif label_text == "Rotation":
                    raw_dict["Rotation"] = value_text
                # etc.

            # Agora chamamos a função de formatação
            final_servo = self.transform_servo_dict(raw_dict, self.selected_site)

            # Adiciona ao data
            data["servos"].append(final_servo)

        # Salva no servos.json
        try:
            with open(saved_json, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.show_scary_alert("Sucesso", f"Garimpo de servos concluído!\nSalvo em {saved_json}")
        except Exception as e:
            self.show_scary_alert("Erro", f"Falha ao salvar JSON: {e}")


    # ----------------------------------------------------------
    #                FUNÇÕES AUXILIARES
    # ----------------------------------------------------------
    def update_site_dropdown(self):
        if not os.path.exists(DATABASE_DIR):
            return
        dirs = [d for d in os.listdir(DATABASE_DIR) if os.path.isdir(os.path.join(DATABASE_DIR, d))]
        dirs.sort()
        if dirs:
            self.dropdown_sites.configure(values=dirs)
            if self.site_var.get() not in dirs:
                self.site_var.set(dirs[0])
        else:
            self.dropdown_sites.configure(values=["(Nenhum)"])
            self.site_var.set("(Nenhum)")

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get()
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, text)
        except:
            pass

    def show_page_config_frame(self):
        self.servo_config_frame.pack_forget()
        self.page_config_frame.pack(fill="both", expand=True)

    def show_servo_config_frame(self):
        self.page_config_frame.pack_forget()
        self.servo_config_frame.pack(fill="both", expand=True)

    def show_scary_alert(self, title, message):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass
        messagebox.showwarning(title, message)

def main():
    app = HTMLDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
