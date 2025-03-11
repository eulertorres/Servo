import os
import sys
import requests
from bs4 import BeautifulSoup
import csv
import re

def download_html_pages():
    # Cria a pasta "Data" se não existir
    os.makedirs("Data", exist_ok=True)
    total_pages = 147  # total de páginas a serem baixadas
    for page in range(1, total_pages + 1):
        if page == 1:
            url = "https://servodatabase.com/servos/all"
            filename = "servos_page1.html"
        else:
            url = f"https://servodatabase.com/servos/all?page={page}"
            filename = f"servos_page{page}.html"
        file_path = os.path.join("Data", filename)

        # Se o arquivo já existe, pula o download
        if os.path.exists(file_path):
            print(f"{file_path} já existe, pulando o download.")
            continue

        print(f"Baixando {url} ...")
        response = requests.get(url)
        # Tenta ajustar a codificação (caso a página não retorne utf-8 corretamente)
        response.encoding = response.apparent_encoding

        if response.status_code != 200:
            print(f"Erro ao acessar {url}. Código de status: {response.status_code}")
            continue

        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Arquivo salvo em {file_path}")

def parse_weight_grams(weight_str):
    """
    Remove 'oz' e converte o valor para gramas (1 oz = 28.3495 g).
    Retorna string vazia se não for possível converter.
    """
    weight_str = weight_str.replace("(add)", "-")  # substitui (add) por -
    match = re.search(r"([\d\.]+)\s*oz", weight_str, re.IGNORECASE)
    if match:
        try:
            oz_value = float(match.group(1))
            grams = oz_value * 28.3495
            return f"{grams:.2f}"  # ex: 119.46
        except ValueError:
            return ""
    return ""

def parse_dimensions_mm(dim_str):
    """
    Recebe algo como "1.59Ã—0.81Ã—1.54 in" e retorna (L, C, A) em mm.
    Se não for possível, retorna três strings vazias.
    """
    dim_str = dim_str.replace("(add)", "-")  # substitui (add) por -
    # remove "in" e espaços extras
    dim_str = dim_str.replace("in", "").strip()

    # Substitui possíveis caracteres "×" ou "Ã—" por "x"
    dim_str = (dim_str
               .replace("×", "x")
               .replace("Ã—", "x"))

    parts = dim_str.split("x")
    if len(parts) != 3:
        return "", "", ""

    dims_mm = []
    for p in parts:
        p = p.strip()
        try:
            val_in = float(p)
            val_mm = val_in * 25.4
            dims_mm.append(f"{val_mm:.2f}")
        except ValueError:
            dims_mm.append("")
    if len(dims_mm) != 3:
        return "", "", ""
    return dims_mm[0], dims_mm[1], dims_mm[2]

def parse_torque(torque_str):
    """
    Recebe algo como:
      "6.0V 499.9 oz-in 7.4V 583.3 oz-in 8.4V 763.8 oz-in"
    e retorna [V1, T1, V2, T2, ..., V5, T5],
    convertendo oz-in para kgf.cm (1 oz-in = 0.0720078 kgf.cm).
    """
    torque_str = torque_str.replace("(add)", "-")
    pattern = r"(\d+(?:\.\d+)?)\s*V\s+(\d+(?:\.\d+))\s*oz-in"
    pairs = re.findall(pattern, torque_str, re.IGNORECASE)

    result = []
    for i, (voltage, torque_ozin) in enumerate(pairs):
        if i == 5:  # só pegamos 5 pares
            break
        try:
            v = float(voltage)
            t_oz = float(torque_ozin)
            # Converte oz-in -> kgf.cm
            t_kgf_cm = t_oz * 0.0720078
            result.append(f"{v}")                # Tensão
            result.append(f"{t_kgf_cm:.2f}")     # Torque em kgf.cm
        except ValueError:
            result.append("")
            result.append("")

    # Preenche o resto com vazio até 10 colunas
    while len(result) < 10:
        result.append("")

    return result

def parse_speed(speed_str):
    """
    Recebe algo como:
      "6.0V 0.15 s/60° 7.4V 0.12 s/60° 8.4V 0.10 s/60°"
    e retorna [V1, S1, V2, S2, ..., V5, S5].
    Onde S é em °/s (graus por segundo).
    Exemplo: 0.15 s/60° -> 60 / 0.15 = 400 (°/s).
    """
    speed_str = speed_str.replace("(add)", "-")

    # Para capturar, por ex: "6.0V 0.15 s/60°"
    # O '(?:°)?' no final só para evitar problemas com simbolo corrompido.
    pattern = r"(\d+(?:\.\d+)?)\s*V\s+(\d+(?:\.\d+))\s*s\s*/\s*60(?:°)?"
    pairs = re.findall(pattern, speed_str, re.IGNORECASE)

    result = []
    for i, (voltage, speed_s60) in enumerate(pairs):
        if i == 5:  # só pegamos 5 pares
            break
        try:
            v = float(voltage)
            s = float(speed_s60)
            # Converte s/60° para °/s => 60° / s
            deg_per_s = 60 / s if s != 0 else 0
            result.append(f"{v}")
            result.append(f"{deg_per_s:.2f}")
        except ValueError:
            result.append("")
            result.append("")

    while len(result) < 10:
        result.append("")

    return result

def scrape_servodatabase(save_csv_path="servos.csv", advanced_format=False):
    data_dir = "Data"
    if not os.path.exists(data_dir):
        print(f"Diretório '{data_dir}' não encontrado. Execute o script com o argumento '--D' para baixar os arquivos HTML.")
        return

    # -------------------------
    # Definição dos cabeçalhos
    # -------------------------
    if not advanced_format:
        # Formato simples
        header = [
            "Make", 
            "Model", 
            "Modulation", 
            "Weight", 
            "Dimensions", 
            "Torque", 
            "Speed", 
            "Motor Type", 
            "Rotation", 
            "Gear Material", 
            "Typical Price"
        ]
    else:
        # Formato avançado
        torque_headers = []
        for i in range(1, 6):
            torque_headers += [f"TensãoTorque{i}", f"Torque{i} (kgf.cm)"]
        speed_headers = []
        for i in range(1, 6):
            speed_headers += [f"TensãoSpeed{i}", f"Speed{i} (°/s)"]

        header = [
            "Make", 
            "Model", 
            "Modulation", 
            "Weight (g)",
            "L (mm)", 
            "C (mm)", 
            "A (mm)",
        ] + torque_headers + speed_headers + [
            "Motor Type", 
            "Rotation", 
            "Gear Material", 
            "Typical Price"
        ]
    # -------------------------

    all_rows = []

    # Itera por todos os arquivos HTML na pasta Data
    for filename in sorted(os.listdir(data_dir)):
        if not filename.startswith("servos_page") or not filename.endswith(".html"):
            continue

        file_path = os.path.join(data_dir, filename)
        with open(file_path, mode="r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Procura a tabela
        table = soup.find("table", class_="servos")
        if not table:
            print(f"Tabela não encontrada em {file_path}.")
            continue

        tbodies = table.find_all("tbody")
        if not tbodies:
            print(f"Seções <tbody> não encontradas em {file_path}.")
            continue

        # Para cada <tbody> extrai os dados da linha
        for tbody in tbodies:
            row = tbody.find("tr")
            if not row:
                continue

            cells = row.find_all("td")
            # Verifica se existem células suficientes
            if len(cells) < 11:
                continue

            # Lê dados (com strip e substituição)
            make           = cells[0].get_text(strip=True).replace("(add)", "-")
            model          = cells[1].get_text(strip=True).replace("(add)", "-")
            modulation     = cells[2].get_text(strip=True).replace("(add)", "-")
            weight         = cells[3].get_text(strip=True).replace("(add)", "-")
            dimensions     = cells[4].get_text(strip=True).replace("(add)", "-")
            torque_str     = cells[5].get_text(" ", strip=True).replace("\n", " ").replace("\r", " ")
            speed_str      = cells[6].get_text(" ", strip=True).replace("\n", " ").replace("\r", " ")
            motor_type     = cells[7].get_text(strip=True).replace("(add)", "-")
            rotation       = cells[8].get_text(strip=True).replace("(add)", "-")
            gear_material  = cells[9].get_text(strip=True).replace("(add)", "-")
            typical_price  = cells[10].get_text(strip=True).replace("(add)", "-")

            if not advanced_format:
                # Formato básico
                all_rows.append([
                    make, model, modulation, weight, dimensions,
                    torque_str, speed_str, motor_type, rotation, gear_material,
                    typical_price
                ])
            else:
                # Formato avançado
                w_grams = parse_weight_grams(weight)
                L, C, A = parse_dimensions_mm(dimensions)
                torque_cols = parse_torque(torque_str)
                speed_cols = parse_speed(speed_str)

                row_adv = [
                    make,
                    model,
                    modulation,
                    w_grams,
                    L, C, A
                ] + torque_cols + speed_cols + [
                    motor_type,
                    rotation,
                    gear_material,
                    typical_price
                ]
                all_rows.append(row_adv)

    if not all_rows:
        print("Nenhum dado foi extraído.")
        return

    # Gera o CSV
    with open(save_csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
        # Linha "sep=," para Excel reconhecer vírgula
        csv_file.write("sep=,\n")
        writer = csv.writer(csv_file, delimiter=",")
        writer.writerow(header)
        writer.writerows(all_rows)

    print(f"Arquivo CSV '{save_csv_path}' criado com sucesso com {len(all_rows)} registros!")

if __name__ == "__main__":
    # Se o argumento --D for passado, baixa os arquivos HTML
    if "--D" in sys.argv:
        download_html_pages()

    # Se o argumento --F for passado, formatação avançada
    advanced_format = ("--F" in sys.argv)

    scrape_servodatabase("servos.csv", advanced_format=advanced_format)
