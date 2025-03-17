import csv
import json
import os

def csv_to_json(csv_path, json_path):
    data = {"servos": []}

    with open(csv_path, "r", encoding="utf-8") as f:
        # Lê a primeira linha
        first_line = f.readline().strip()
        # Se começar com "sep=", ignoramos essa linha e prosseguimos
        if not first_line.startswith("sep="):
            # Caso não tenha "sep=", voltamos o ponteiro para reler como cabeçalho
            f.seek(0)
        
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            data["servos"].append(row)

    # Salva o JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    csv_file = "servos.csv"    # Ajuste o caminho se necessário
    json_file = "servos.json"  # Arquivo de saída

    if not os.path.exists(csv_file):
        print(f"Arquivo CSV não encontrado: {csv_file}")
        return

    csv_to_json(csv_file, json_file)
    print(f"Conversão concluída! Gerado: {json_file}")

if __name__ == "__main__":
    main()
