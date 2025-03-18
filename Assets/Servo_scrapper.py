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

SERVOS_JSON = os.path.join(repo_dir, "Database", "servos.json")

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

        # Para dropdown de servo
        self.servo_file_var = ctk.StringVar(value="")
        self.servo_files = []

        # Nesta dict guardaremos quais labels interessam
        # Exemplo: {"Operating Voltage (V)": True, "Weight (g)": True, ...}
        # Ou poderíamos mapear label -> "campo do JSON".
        self.found_labels = {}

        # Constrói interface
        self.load_cat_image()
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

        btn_paste = ctk.CTkButton(
            download_frame,
            text="Colar do Clipboard",
            command=self.paste_from_clipboard,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_paste.grid(row=0, column=2, padx=5, pady=5)

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
        # Frame de Página
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

        # Frame de Servo
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

        # Campos de exemplo
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

        self.scrollable_servo_results = ctk.CTkScrollableFrame(self.servo_config_frame, width=400, height=200)
        self.scrollable_servo_results.pack(fill="both", expand=True, padx=5, pady=5)

        btn_confirm_servo = ctk.CTkButton(
            self.servo_config_frame,
            text="Confirmar Garimpo (Servo)",
            command=self.servo_confirm_garimpo,
            fg_color="#228B22", hover_color="#006400"
        )
        btn_confirm_servo.pack(pady=5)

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
        url = self.entry_url.get().strip()
        min_page = self.entry_min.get().strip()
        max_page = self.entry_max.get().strip()

        if not url or "[P]" not in url:
            self.show_scary_alert("Erro", "A URL deve conter o placeholder [P].")
            return

        try:
            min_page = int(min_page)
            max_page = int(max_page)
        except ValueError:
            self.show_scary_alert("Erro", "Páginas mínima e máxima devem ser números inteiros.")
            return

        if min_page > max_page:
            self.show_scary_alert("Erro", "Página mínima não pode ser maior que a página máxima.")
            return

        match = re.search(r'www\.([^.]+)\.', url)
        if match:
            folder_name = match.group(1)
        else:
            self.show_scary_alert("Erro", "Não foi possível extrair o nome da nova pasta da URL.")
            return

        target_dir = os.path.join(DATABASE_DIR, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Baixando HTML...")
        progress_label = ctk.CTkLabel(progress_window, text="Iniciando downloads...")
        progress_label.pack(pady=10, padx=10)
        progress_bar = ctk.CTkProgressBar(progress_window, width=300)
        progress_bar.pack(pady=10, padx=10)
        progress_bar.set(0)

        total_pages = max_page - min_page + 1
        count = 0

        for page in range(min_page, max_page + 1):
            page_url = url.replace("[P]", str(page))
            try:
                resp = requests.get(page_url, headers=headers)
                resp.raise_for_status()
                html_content = resp.text
                file_name = f"page_{page}.html"
                file_path = os.path.join(target_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
            except Exception as e:
                progress_window.destroy()
                self.show_scary_alert("Erro", f"Erro ao baixar a página {page}:\n{e}")
                return

            count += 1
            progress_label.configure(text=f"Baixando página {page} / {max_page}...")
            progress_bar.set(count / total_pages)
            progress_window.update()

        progress_window.destroy()
        self.show_scary_alert("Sucesso", f"Download concluído!\nArquivos salvos em: {target_dir}")
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
        1) Lê o arquivo HTML selecionado no dropdown (servo_file_var).
        2) Usa BeautifulSoup para encontrar <tr> com label e valor.
        3) Se o "valor" contiver algum dos exemplos que o usuário digitou,
           consideramos que esse 'label' é interessante -> self.found_labels[label_text] = True
        4) Mostra no scrollable_servo_results o que foi encontrado.
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

        # Lê HTML e pega os exemplos
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")

        examples = {}
        for field_name, var in self.servo_fields_vars.items():
            val = var.get().strip()
            if val:
                examples[field_name] = val

        # Limpa scrollable
        for widget in self.scrollable_servo_results.winfo_children():
            widget.destroy()

        if not examples:
            ctk.CTkLabel(self.scrollable_servo_results, text="Nenhum valor de exemplo preenchido.").pack()
            return

        # 1) Percorre todas as linhas <tr> em qualquer <table>
        # 2) label_td = a primeira <td>
        # 3) value_td = a segunda <td> (se existir)
        # 4) Se "value_td" contiver o valor de exemplo, guardamos a label no self.found_labels
        #    Exemplo: self.found_labels["Operating Voltage (V)"] = True
        #    Assim, saberemos que essa label é de interesse.
        found_lines = []
        all_trs = soup.find_all("tr")
        for tr in all_trs:
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            label_text = tds[0].get_text(strip=True)
            value_text = tds[1].get_text(strip=True)

            # Verifica se esse 'value_text' contém algum dos exemplos
            for field, example_val in examples.items():
                if example_val in value_text:
                    # Marcamos que esse label é de interesse
                    self.found_labels[label_text] = True
                    found_lines.append(f"[OK] '{example_val}' encontrado na linha: label={label_text}")

        if not found_lines:
            ctk.CTkLabel(self.scrollable_servo_results, text="Não encontramos nenhuma correspondência.").pack()
            return

        for line in found_lines:
            ctk.CTkLabel(self.scrollable_servo_results, text=line).pack(anchor="w")

        self.show_scary_alert("Info", "Localização de padrão para servo concluída (arquivo selecionado).")

    # ----------------------------------------------------------
    #     "Confirmar Garimpo (Servo)" => Aplica em TODOS
    # ----------------------------------------------------------
    def servo_confirm_garimpo(self):
        """
        - Abre todos os .html em servoshtml
        - Para cada <tr>, se label_text estiver em self.found_labels, salva no JSON
          Exemplo: servo_dict[label_text] = value_text
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

        # Carrega JSON existente ou cria
        data = {"servos": []}
        if os.path.exists(SERVOS_JSON):
            try:
                with open(SERVOS_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "servos" not in data:
                        data["servos"] = []
            except:
                pass

        for file in html_files:
            full_path = os.path.join(servo_dir, file)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            soup = BeautifulSoup(content, "html.parser")

            servo_name = os.path.splitext(file)[0]
            servo_dict = {
                "Make": "",
                "Model": servo_name,
                "Modulation": "",
                "Weight (g)": "",
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
                "Motor Type": "",
                "Rotation": "",
                "Gear Material": "",
                "Typical Price": ""
            }

            # Parse do HTML
            all_trs = soup.find_all("tr")
            for tr in all_trs:
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                label_text = tds[0].get_text(strip=True)
                value_text = tds[1].get_text(strip=True)

                # Se essa label está em self.found_labels, guardamos no servo_dict
                if label_text in self.found_labels:
                    # Para demonstrar, salvamos no servo_dict com a própria label como chave
                    # Se quiser mapear p/ "Torque1 (kgf.cm)", faça algo como:
                    # if label_text == "Stall Torque (kgf•cm / oz•in)": servo_dict["Torque1 (kgf.cm)"] = ...
                    servo_dict[label_text] = value_text

            data["servos"].append(servo_dict)

        try:
            with open(SERVOS_JSON, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.show_scary_alert("Sucesso", f"Garimpo de servos concluído!\nSalvo em {SERVOS_JSON}")
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

    def load_cat_image(self):
        try:
            cat_path = os.path.join("gato_desconfiado.png")
            if os.path.exists(cat_path):
                cat_img = Image.open(cat_path)
                cat_img.thumbnail((80, 80))
                self.cat_imgtk = ctk.CTkImage(dark_image=cat_img, size=(80, 80))
                self.cat_label = ctk.CTkLabel(self, image=self.cat_imgtk, text="")
                self.cat_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        except Exception as e:
            print(f"Não foi possível carregar a imagem do gato: {e}")

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
