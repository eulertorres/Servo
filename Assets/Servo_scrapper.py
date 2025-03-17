import os
import re
import requests
import customtkinter as ctk
from tkinter import messagebox, END
from PIL import Image

# Diretórios conforme solicitado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(BASE_DIR)
DATABASE_DIR = os.path.join(repo_dir, "Database", "Data")
os.makedirs(DATABASE_DIR, exist_ok=True)

class HTMLDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gerenciador de Downloads e Extração de HTML")
        self.geometry("1000x600")

        # --------------- CONFIGURA APARÊNCIA ---------------
        # (para deixar tudo no estilo "dark" e botões verdes)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # --------------- ORGANIZAÇÃO PRINCIPAL ---------------
        # Vamos criar um frame que ocupará toda a janela
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True)

        # Configura o grid para dividir em 2 colunas: ESQUERDA e DIREITA
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=1)

        # Frame da esquerda
        self.left_frame = ctk.CTkFrame(main_container)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame da direita
        self.right_frame = ctk.CTkFrame(main_container)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # --------------- COLOCA O GATO NO CANTO SUPERIOR DIREITO ---------------
        self.load_cat_image()

        # --------------- COMPONENTES DO FRAME ESQUERDO ---------------
        self.build_left_frame()

        # --------------- COMPONENTES DO FRAME DIREITO ---------------
        self.build_right_frame()

        # --------------- VARIÁVEIS AUXILIARES ---------------
        self.selected_site = None     # Nome do site selecionado no dropdown
        self.result_checkboxes = []   # Lista de (checkbox, var, url, name) para o resultado
        self.matches_by_file = {}     # Armazena todos os pares encontrados, caso precise

        # Atualiza o dropdown de sites inicialmente
        self.update_site_dropdown()

    # ----------------------------------------------------------
    #                PARTE 1: FRAME ESQUERDO
    # ----------------------------------------------------------
    def build_left_frame(self):
        """
        Constrói a parte esquerda da janela:
        - Inputs para baixar HTML (URL com [P], páginas min/max)
        - Botão para colar do clipboard
        - Dropdown de sites
        - Botão 'Configurar'
        - Botão 'Garimpar'
        """
        # Título
        title_label = ctk.CTkLabel(self.left_frame, text="Baixar HTML", font=("Helvetica", 18, "bold"))
        title_label.pack(pady=5)

        # Frame para inputs de download
        download_frame = ctk.CTkFrame(self.left_frame)
        download_frame.pack(fill="x", padx=5, pady=5)

        # URL
        lbl_url = ctk.CTkLabel(download_frame, text="URL com [P]:")
        lbl_url.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_url = ctk.CTkEntry(download_frame, width=220)
        self.entry_url.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Botão colar
        btn_paste = ctk.CTkButton(
            download_frame, 
            text="Colar do Clipboard", 
            command=self.paste_from_clipboard,
            fg_color="#228B22",
            hover_color="#006400"
        )
        btn_paste.grid(row=0, column=2, padx=5, pady=5)

        # Página mínima
        lbl_min = ctk.CTkLabel(download_frame, text="Página Mínima:")
        lbl_min.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_min = ctk.CTkEntry(download_frame, width=80)
        self.entry_min.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Página máxima
        lbl_max = ctk.CTkLabel(download_frame, text="Página Máxima:")
        lbl_max.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.entry_max = ctk.CTkEntry(download_frame, width=80)
        self.entry_max.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Botão Baixar HTML
        btn_download = ctk.CTkButton(
            download_frame,
            text="Baixar HTML",
            command=self.download_html,
            fg_color="#228B22",
            hover_color="#006400"
        )
        btn_download.grid(row=3, column=0, columnspan=3, pady=5)

        # ---------------- DROPDOWN DE SITES ----------------
        dropdown_frame = ctk.CTkFrame(self.left_frame)
        dropdown_frame.pack(fill="x", padx=5, pady=5)

        lbl_sites = ctk.CTkLabel(dropdown_frame, text="Sites baixados:", font=("Helvetica", 14))
        lbl_sites.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.site_var = ctk.StringVar(value="")  # valor inicial
        self.dropdown_sites = ctk.CTkOptionMenu(
            dropdown_frame,
            values=[],
            variable=self.site_var,
            fg_color="#228B22",
            button_color="#228B22",
            button_hover_color="#006400",
            dropdown_fg_color="#333333",
            dropdown_hover_color="#444444"
        )
        self.dropdown_sites.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Botão para atualizar a lista de sites
        btn_update_sites = ctk.CTkButton(
            dropdown_frame,
            text="Atualizar Lista",
            command=self.update_site_dropdown,
            fg_color="#228B22",
            hover_color="#006400"
        )
        btn_update_sites.grid(row=1, column=0, columnspan=2, pady=5)

        # Botão "Configurar"
        btn_configurar = ctk.CTkButton(
            self.left_frame,
            text="Configurar",
            command=self.configure_site,
            fg_color="#228B22",
            hover_color="#006400"
        )
        btn_configurar.pack(pady=5)

        # Botão "Garimpar" (para baixar URLs marcados na lista de resultados)
        btn_garimpar = ctk.CTkButton(
            self.left_frame,
            text="Garimpar",
            command=self.garimpar_checked_results,
            fg_color="#228B22",
            hover_color="#006400"
        )
        btn_garimpar.pack(pady=5)

    # ----------------------------------------------------------
    #                PARTE 2: FRAME DIREITO
    # ----------------------------------------------------------
    def build_right_frame(self):
        """
        Constrói a parte direita da janela:
        - Inputs para "Exemplo de Nome" e "Exemplo de URL"
        - Botão para localizar padrão
        - Área para exibir resultados (checkboxes)
        """
        # Título
        config_title = ctk.CTkLabel(self.right_frame, text="Configuração de Padrão", font=("Helvetica", 18, "bold"))
        config_title.pack(pady=5)

        # Frame para inputs de exemplo
        config_inputs_frame = ctk.CTkFrame(self.right_frame)
        config_inputs_frame.pack(fill="x", padx=5, pady=5)

        lbl_nome_ex = ctk.CTkLabel(config_inputs_frame, text="Exemplo de Nome:")
        lbl_nome_ex.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.entry_nome_ex = ctk.CTkEntry(config_inputs_frame, width=220)
        self.entry_nome_ex.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        lbl_url_ex = ctk.CTkLabel(config_inputs_frame, text="Exemplo de URL:")
        lbl_url_ex.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_url_ex = ctk.CTkEntry(config_inputs_frame, width=220)
        self.entry_url_ex.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Botão para localizar padrão
        btn_find_pattern = ctk.CTkButton(
            config_inputs_frame,
            text="Localizar Padrão e Listar",
            command=self.find_pattern_and_list,
            fg_color="#228B22",
            hover_color="#006400"
        )
        btn_find_pattern.grid(row=2, column=0, columnspan=2, pady=10)

        # Label para resultados
        lbl_result = ctk.CTkLabel(self.right_frame, text="Resultados Encontrados:", font=("Helvetica", 14, "bold"))
        lbl_result.pack(pady=5)

        # Frame rolável para colocar checkboxes
        self.scrollable_results = ctk.CTkScrollableFrame(self.right_frame, width=400, height=300)
        self.scrollable_results.pack(fill="both", expand=True, padx=5, pady=5)

    # ----------------------------------------------------------
    #         EXIBIR IMAGEM DO GATO NO CANTO SUPERIOR DIREITO
    # ----------------------------------------------------------
    def load_cat_image(self):
        try:
            cat_path = os.path.join("gato_desconfiado.png")
            if os.path.exists(cat_path):
                cat_img = Image.open(cat_path)
                cat_img.thumbnail((80, 80))
                self.cat_imgtk = ctk.CTkImage(dark_image=cat_img, size=(80, 80))
                self.cat_label = ctk.CTkLabel(self, image=self.cat_imgtk, text="")
                # Posiciona no canto superior direito
                self.cat_label.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        except Exception as e:
            print(f"Não foi possível carregar a imagem do gato: {e}")

    # ----------------------------------------------------------
    #       BOTÃO "COLAR DO CLIPBOARD" NA CAIXA DE URL
    # ----------------------------------------------------------
    def paste_from_clipboard(self):
        """Tenta colar o texto do clipboard na entry de URL."""
        try:
            text = self.clipboard_get()
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, text)
        except:
            pass  # Se não conseguir colar, ignora

    # ----------------------------------------------------------
    #           ATUALIZAR DROPDOWN DE SITES
    # ----------------------------------------------------------
    def update_site_dropdown(self):
        """Lista as subpastas em DATABASE_DIR e atualiza o dropdown."""
        if not os.path.exists(DATABASE_DIR):
            return
        dirs = [d for d in os.listdir(DATABASE_DIR) if os.path.isdir(os.path.join(DATABASE_DIR, d))]
        dirs.sort()
        if dirs:
            self.dropdown_sites.configure(values=dirs)
            # Se não tiver nada selecionado, seleciona o primeiro
            if self.site_var.get() not in dirs:
                self.site_var.set(dirs[0])
        else:
            self.dropdown_sites.configure(values=["(Nenhum)"])
            self.site_var.set("(Nenhum)")

    # ----------------------------------------------------------
    #       DOWNLOAD HTML: BOTÃO "Baixar HTML"
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
    #        BOTÃO "Configurar": Seleciona site e prepara
    # ----------------------------------------------------------
    def configure_site(self):
        """
        Lê qual site está selecionado no dropdown e "seleciona" para configurar.
        """
        selection = self.site_var.get()
        if not selection or selection == "(Nenhum)":
            messagebox.showwarning("Aviso", "Nenhum site válido selecionado.")
            return

        self.selected_site = selection
        messagebox.showwarning("AVISO [ALERA]", f"O SITE '{selection}' FOI SELECIONADO SEM PROBLEMAS!!!.")

    # ----------------------------------------------------------
    #       BOTÃO "Localizar Padrão e Listar"
    # ----------------------------------------------------------
    def find_pattern_and_list(self):
        """Usa o exemplo de nome/URL para identificar um padrão e extrair todos."""
        if not self.selected_site:
            messagebox.showerror("Erro", "Nenhum site selecionado. Clique em 'Configurar' antes.")
            return

        nome_ex = self.entry_nome_ex.get().strip()
        url_ex = self.entry_url_ex.get().strip()
        if not nome_ex or not url_ex:
            messagebox.showerror("Erro", "Insira exemplo de nome e URL.")
            return

        # Carrega arquivos HTML do site selecionado
        site_dir = os.path.join(DATABASE_DIR, self.selected_site)
        if not os.path.isdir(site_dir):
            messagebox.showerror("Erro", f"Pasta '{site_dir}' não existe.")
            return

        html_files = [f for f in os.listdir(site_dir) if f.endswith(".html")]
        html_files.sort()
        if not html_files:
            messagebox.showerror("Erro", f"Nenhum arquivo HTML encontrado em {site_dir}")
            return

        # Carrega primeiro HTML para checar se encontra nome/URL de exemplo
        first_html_path = os.path.join(site_dir, html_files[0])
        with open(first_html_path, "r", encoding="utf-8") as f:
            first_html_content = f.read()

        # Verifica se o URL e o Nome existem no primeiro HTML
        if url_ex not in first_html_content:
            messagebox.showwarning("Aviso", "Não foi possível encontrar a URL de exemplo no primeiro HTML.")
        if nome_ex not in first_html_content:
            messagebox.showwarning("Aviso", "Não foi possível encontrar o nome de exemplo no primeiro HTML.")

        # Define uma REGEX simples que procura:
        # <a href="alguma_url" ...> ... <h2>algum_nome</h2>
        pattern = re.compile(r'<a\s+href="([^"]+)"[^>]*>.*?<h2>([^<]+)</h2>', re.DOTALL)

        self.matches_by_file.clear()
        all_results = []

        # Percorre todos os HTMLs e coleta resultados
        for html_file in html_files:
            full_path = os.path.join(site_dir, html_file)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            matches = pattern.findall(content)  # lista de (url, nome)
            if matches:
                self.matches_by_file[html_file] = matches
                # Acumula no "all_results" para exibir
                for (u, n) in matches:
                    all_results.append((html_file, u, n))

        # Limpa o frame de resultados e a lista de checkboxes
        for widget in self.scrollable_results.winfo_children():
            widget.destroy()
        self.result_checkboxes = []

        if not all_results:
            label_no_result = ctk.CTkLabel(self.scrollable_results, text="Nenhum resultado encontrado.")
            label_no_result.pack()
            return

        # Exibe cada resultado com checkbox
        for (html_file, url_found, name_found) in all_results:
            # Monta texto
            line_text = f"{html_file}: {name_found} -> {url_found}"
            var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(
                self.scrollable_results,
                text=line_text,
                variable=var,
                fg_color="#228B22",
                hover_color="#006400",
                border_color="#228B22"
            )
            chk.pack(anchor="w", padx=5, pady=2)
            # Armazena pra uso posterior
            self.result_checkboxes.append((chk, var, url_found, name_found))

    # ----------------------------------------------------------
    #   BOTÃO "Garimpar": Baixar HTML dos resultados marcados
    # ----------------------------------------------------------
    def garimpar_checked_results(self):
        """
        Para cada resultado cujo checkbox estiver marcado, baixa o HTML da URL
        e salva em [site_dir]/servoshtml/<nome>.html
        """
        if not self.selected_site:
            messagebox.showerror("Erro", "Nenhum site selecionado para garimpar.")
            return

        site_dir = os.path.join(DATABASE_DIR, self.selected_site)
        servo_dir = os.path.join(site_dir, "servoshtml")
        os.makedirs(servo_dir, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        count_downloaded = 0
        for (chk, var, url_found, name_found) in self.result_checkboxes:
            if var.get():  # está marcado
                try:
                    r = requests.get(url_found, headers=headers)
                    r.raise_for_status()
                    # Sanitiza o nome para criar arquivo
                    safe_name = re.sub(r'[^\w_-]+', '_', name_found)
                    file_path = os.path.join(servo_dir, f"{safe_name}.html")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(r.text)
                    count_downloaded += 1
                except Exception as e:
                    print(f"Falha ao garimpar URL {url_found}: {e}")

        messagebox.showinfo("Garimpo Concluído", f"Total de arquivos baixados: {count_downloaded}")

def main():
    app = HTMLDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
