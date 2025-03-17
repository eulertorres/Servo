import json
import matplotlib.pyplot as plt

def plot_servo_torque_vs_weight(json_file_path):
    # 1) Ler o arquivo JSON
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 2) Extrair os valores de peso (em kg) e torque (em kgf.cm)
    weights_kg = []
    torques_kgfcm = []
    labels = []

    # Percorrer cada servo no JSON
    for servo in data["servos"]:
        # Converter peso de gramas para kg
        try:
            weight_g = float(servo["Weight (g)"])
        except ValueError:
            # Se estiver vazio ou inválido, ignorar
            continue

        weight_kg = weight_g / 1000.0
        
        # Ler o torque1 (kgf.cm)
        # (vamos assumir que TensãoTorque1 e Torque1 (kgf.cm) são os valores principais)
        torque_str = servo["Torque1 (kgf.cm)"]
        if torque_str:
            try:
                torque_kgfcm = float(torque_str)
            except ValueError:
                # Se estiver vazio ou inválido, ignorar
                continue

            # Armazenar nos vetores
            weights_kg.append(weight_kg)
            torques_kgfcm.append(torque_kgfcm)
            # Guardar algum rótulo para identificar no gráfico
            labels.append(f"{servo['Model']}")
    
    # 3) Plotar o gráfico de dispersão
    plt.figure(figsize=(8, 6))
    plt.scatter(weights_kg, torques_kgfcm, color='blue', alpha=0.7, s=50)

    # 4) Adicionar rótulos de eixo e título
    plt.xlabel("Peso (kg)", fontsize=12)
    plt.ylabel("Torque (kgf.cm)", fontsize=12)
    plt.title("Relação Peso (kg) vs. Torque (kgf.cm) - Servos", fontsize=14)

    # 5) Tornar o gráfico mais informativo
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Opcional: anotar cada ponto com o modelo do servo
    #for i, label in enumerate(labels):
    #    plt.annotate(label,
    #                 (weights_kg[i], torques_kgfcm[i]),
    #                 textcoords="offset points",
    #                 xytext=(5, 5),
    #                 ha='left',
    #                 fontsize=9,
    #                 alpha=0.8)
    
    # Exibir o gráfico
    plt.tight_layout()
    plt.show()

# Exemplo de uso:
plot_servo_torque_vs_weight('servos.json')
