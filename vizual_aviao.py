import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, TextBox
from mpl_toolkits.mplot3d import Axes3D
from scipy.optimize import fsolve

# =============================================================================
# Parâmetros iniciais (dimensões do mecanismo)
# =============================================================================
# d: distância entre o eixo do aileron (ponto A) e o eixo do servo (ponto S)
# R: comprimento (raio) da roseta do servo
# L: comprimento da barra de ligação (entre o ponto B e o ponto de conexão na barra da superfície)
# a: comprimento da barra da superfície (do pivô A até a ponta C)
d_init = 69.32  
R_init = 19.00  
L_init = 68.31   
a_init = 42.33    

# Parâmetro do tilt do servo (rotação em torno do eixo X, em graus)
psi_init = 15.0

# Limites do movimento do servo (ângulos em graus)
phi_min = -35.0   # limite inferior
phi_max = 40.29   # limite superior
phi_neutro = 0.0  # posição neutra (roseta aponta para baixo)

# =============================================================================
# Cálculo da posição do eixo do servo (S) em neutro
# =============================================================================
def compute_servo_position(d, R, a, L):
    """
    Em neutro:
      - A barra da superfície está vertical para baixo: C = (0, -a)
      - A roseta também aponta para baixo, ou seja, B = S + (0, -R)
      - Impõe-se: ||B - C|| = L  e  ||S|| = d.
    Essa função resolve essas equações (escolhendo S_x > 0).
    """
    Sy = (L**2 - d**2 - (a - R)**2) / (2*(a - R))
    Sx = np.sqrt(d**2 - Sy**2)
    return np.array([Sx, Sy])

# =============================================================================
# Cálculo do ângulo do aileron (θ) para um ângulo do servo (φ) e tilt (ψ)
# =============================================================================
def compute_aileron_angle(phi, psi, S, R, a, L):
    """
    Dado o ângulo do servo φ (em graus) e o tilt do servo ψ (em graus),
    calcula:
      - O ponto B (ponta da roseta), considerando que a roseta é rotacionada pelo tilt ψ:
            B = S_3 + R * (R_x(ψ) * [cos(-90+φ), sin(-90+φ), 0])
        onde S_3 é S em 3D (com z=0) e R_x(ψ) é a matriz de rotação em torno do eixo X.
      - E determina numericamente θ (em radianos) tal que o ponto C da superfície,
            C = A + a*[cos(θ), sin(θ), 0]
        satisfaça ||C - B|| = L.
    """
    # Representa S em 3D (z=0)
    S_3 = np.array([S[0], S[1], 0])
    # Ângulo base da roseta (em radianos)
    theta_servo = np.deg2rad(-90 + phi)
    v = np.array([np.cos(theta_servo), np.sin(theta_servo), 0])
    # Rotaciona v em torno do eixo X pelo ângulo ψ
    psi_rad = np.deg2rad(psi)
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(psi_rad), -np.sin(psi_rad)],
                    [0, np.sin(psi_rad),  np.cos(psi_rad)]])
    v_rot = R_x.dot(v)
    B = S_3 + R * v_rot

    # Encontra θ para que a distância entre C e B seja L (com C no plano XY)
    def f(theta_array):
        theta_val = theta_array[0]
        C = np.array([a * np.cos(theta_val), a * np.sin(theta_val), 0])
        return [np.linalg.norm(C - B) - L]
    theta0 = np.deg2rad(-90)  # palpite inicial (posição neutra)
    theta_solution = fsolve(f, [theta0])[0]
    C = np.array([a * np.cos(theta_solution), a * np.sin(theta_solution), 0])
    return theta_solution, B, C

def angle_diff(angle):
    # Normaliza uma diferença de ângulos para o intervalo [-180, 180] (em graus)
    angle = (angle + np.pi) % (2 * np.pi) - np.pi
    return np.rad2deg(angle)

# =============================================================================
# Função para desenhar um arco representando um ângulo
# =============================================================================
def draw_angle_arc(ax, center, vec1, vec2, radius, color):
    """
    Desenha um arco (em 2D) com centro em 'center' que inicia na direção de vec1
    e termina na direção de vec2. 'radius' define o tamanho do arco.
    """
    angle1 = np.arctan2(vec1[1], vec1[0])
    angle2 = np.arctan2(vec2[1], vec2[0])
    # Calcula o deslocamento angular (menor variação)
    diff = (angle2 - angle1 + 2*np.pi) % (2*np.pi)
    if diff > np.pi:
        diff = diff - 2*np.pi
    arc_angles = np.linspace(angle1, angle1 + diff, 50)
    x_arc = center[0] + radius * np.cos(arc_angles)
    y_arc = center[1] + radius * np.sin(arc_angles)
    ax.plot(x_arc, y_arc, zs=0, color=color, linestyle='-', lw=1.5)

# =============================================================================
# Função para computar a circunferência de atuação do servo em 3D (considerando tilt)
# =============================================================================
def compute_servo_circle(S, R, psi):
    """
    Retorna os pontos da circunferência de raio R centrada em S (convertido para 3D)
    no plano obtido ao rotacionar o plano XY em torno do eixo X pelo ângulo ψ.
    """
    S_3 = np.array([S[0], S[1], 0])
    psi_rad = np.deg2rad(psi)
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(psi_rad), -np.sin(psi_rad)],
                    [0, np.sin(psi_rad),  np.cos(psi_rad)]])
    t = np.linspace(0, 2*np.pi, 100)
    circle_points = np.array([R_x.dot(np.array([np.cos(tt), np.sin(tt), 0])) for tt in t])
    circle_points = S_3 + R * circle_points
    return circle_points

# =============================================================================
# Parâmetros globais iniciais e cálculo do ponto S
# =============================================================================
d, R, L, a = d_init, R_init, L_init, a_init
psi = psi_init
S = compute_servo_position(d, R, a, L)
A = np.array([0, 0, 0])  # pivô do aileron (em 3D)

# =============================================================================
# Configuração da figura e dos eixos 3D
# =============================================================================
fig = plt.figure(figsize=(12, 8))
ax = fig.add_axes([0.05, 0.15, 0.65, 0.8], projection='3d')

# Define uma vista inicial (o usuário pode alterá-la, e ela será preservada)
ax.view_init(elev=20, azim=-60)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Mecanismo 4 Barras - Simulação")

# =============================================================================
# Função de atualização do gráfico (preservando a vista atual)
# =============================================================================
def update_plot(phi):
    global S, A, d, R, L, a, psi
    # Captura a vista atual (limites e ângulos de elevação/azimute)
    cur_elev = ax.elev
    cur_azim = ax.azim
    cur_xlim = ax.get_xlim()
    cur_ylim = ax.get_ylim()
    cur_zlim = ax.get_zlim()
    
    # Calcula B, C e o ângulo θ (em radianos) de forma que ||C - B|| = L,
    # considerando o tilt ψ no cálculo de B.
    theta, B, C = compute_aileron_angle(phi, psi, S, R, a, L)
    
    # Cálculo dos ângulos das direções das barras (projetados no plano XY)
    angle_AS = np.arctan2(S[1]-A[1], S[0]-A[0])
    angle_SB = np.arctan2(B[1]-S[1], B[0]-S[0])
    angle_BC = np.arctan2(C[1]-B[1], C[0]-B[0])
    angle_AC = np.arctan2(C[1]-A[1], C[0]-A[0])
    
    angle_AS_SB = angle_diff(angle_SB - angle_AS)
    angle_SB_BC = angle_diff(angle_BC - angle_SB)
    angle_BC_AC = angle_diff(angle_AC - angle_BC)
    
    # Cálculo dos comprimentos medidos de cada barra (para visualização em tempo real)
    length_AS = np.linalg.norm(np.array([S[0], S[1], 0]) - A)
    length_SB = np.linalg.norm(B - np.array([S[0], S[1], 0]))
    length_BC = np.linalg.norm(C - B)
    length_AC = np.linalg.norm(C - A)
    
    # Limpa os eixos e reestabelece a vista atual
    ax.cla()
    ax.set_xlim(cur_xlim)
    ax.set_ylim(cur_ylim)
    ax.set_zlim(cur_zlim)
    ax.view_init(elev=cur_elev, azim=cur_azim)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Mecanismo 4 Barras - Simulação")
    
    # -------------------------------------------------------------------------
    # Plota as barras do mecanismo:
    #  1. Barra base A–S (fixa)
    #  2. Roseta/servo S–B
    #  3. Barra de ligação B–C (comprimento L fixo)
    #  4. Barra da superfície A–C (aileron)
    # -------------------------------------------------------------------------
    S_3 = np.array([S[0], S[1], 0])
    ax.plot([A[0], S_3[0]], [A[1], S_3[1]], [A[2], S_3[2]], 'k-', lw=2, label="A-S (base)")
    ax.plot([S_3[0], B[0]], [S_3[1], B[1]], [S_3[2], B[2]], 'r-', lw=2, label="S-B (servo)")
    ax.plot([B[0], C[0]], [B[1], C[1]], [B[2], C[2]], 'g-', lw=2, label="B-C (ligação)")
    ax.plot([A[0], C[0]], [A[1], C[1]], [A[2], C[2]], 'b-', lw=2, label="A-C (superfície)")
    
    # -------------------------------------------------------------------------
    # Plota as circunferências de atuação:
    #  - Para o servo: utiliza a circunferência obtida a partir do tilt ψ
    #  - Para a deflexão (aileron): permanece no plano XY
    # -------------------------------------------------------------------------
    servo_circle = compute_servo_circle(S, R, psi)
    ax.plot(servo_circle[:,0], servo_circle[:,1], servo_circle[:,2], color='magenta', linestyle='--', lw=1, label="Circ. do Servo")
    
    circle_A_x = A[0] + a * np.cos(np.linspace(0, 2*np.pi, 100))
    circle_A_y = A[1] + a * np.sin(np.linspace(0, 2*np.pi, 100))
    circle_A_z = np.zeros(100)
    ax.plot(circle_A_x, circle_A_y, circle_A_z, color='cyan', linestyle='--', lw=1, label="Circ. da Deflexão")
    
    # -------------------------------------------------------------------------
    # Plota os pontos (juntas)
    # -------------------------------------------------------------------------
    for point, label in zip([A, S_3, B, C], ["A", "S", "B", "C"]):
        ax.scatter(point[0], point[1], point[2], s=50)
        ax.text(point[0], point[1], point[2], f" {label}", fontsize=10)
    
    # -------------------------------------------------------------------------
    # Anota os comprimentos das barras (valores medidos em tempo real)
    # -------------------------------------------------------------------------
    def annotate_length(p1, p2, text):
        mid = (p1 + p2) / 2
        ax.text(mid[0], mid[1], mid[2], text, color='black', fontsize=9, backgroundcolor='w')
    
    annotate_length(A, S_3, f"d = {length_AS:.2f}")
    annotate_length(S_3, B, f"R = {length_SB:.2f}")
    annotate_length(B, C, f"L = {length_BC:.2f}")
    annotate_length(A, C, f"a = {length_AC:.2f}")
    
    # -------------------------------------------------------------------------
    # Plota os arcos que representam os ângulos em cada junta:
    #  - Em S: ângulo entre A–S e S–B (projetado no plano XY)
    #  - Em B: ângulo entre S–B e B–C (projetado no plano XY)
    #  - Em C: ângulo entre B–C e A–C (projetado no plano XY)
    # Utiliza-se um raio pequeno para os arcos.
    # -------------------------------------------------------------------------
    arc_radius_S = 0.2 * min(length_AS, R)
    draw_angle_arc(ax, S_3, A - S_3, B[:2] - S_3[:2], arc_radius_S, 'red')
    
    arc_radius_B = 0.2 * min(length_SB, L)
    draw_angle_arc(ax, B, S[:2] - B[:2], C[:2] - B[:2], arc_radius_B, 'green')
    
    arc_radius_C = 0.2 * min(length_BC, a)
    draw_angle_arc(ax, C, B[:2] - C[:2], A[:2] - C[:2], arc_radius_C, 'blue')
    
    # -------------------------------------------------------------------------
    # Exibe informações gerais na figura, incluindo o tilt do servo (ψ)
    # -------------------------------------------------------------------------
    info_text = (
        f"Ângulo do Servo (φ): {phi:.2f}°\n"
        f"Tilt do Servo (ψ): {psi:.2f}°\n"
        f"Ângulo da Superfície (A-C): {np.rad2deg(angle_AC):.2f}°\n"
        f"θ (solução): {np.rad2deg(theta):.2f}°\n\n"
        f"|A-S| = {length_AS:.2f}    |S-B| = {length_SB:.2f}\n"
        f"|B-C| = {length_BC:.2f}    |A-C| = {length_AC:.2f}"
    )
    ax.text2D(0.05, 0.95, info_text, transform=ax.transAxes, fontsize=10,
              verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    
    ax.legend(loc="lower left")
    plt.draw()

# =============================================================================
# Callbacks dos widgets
# =============================================================================
def slider_update(val):
    phi = slider_phi.val
    update_plot(phi)

def update_config(text):
    global d, R, L, a, psi, S
    try:
        d = float(text_boxes["d"].text)
        R = float(text_boxes["R"].text)
        L = float(text_boxes["L"].text)
        a = float(text_boxes["a"].text)
        psi = float(text_boxes["psi"].text)
        S = compute_servo_position(d, R, a, L)
        update_plot(slider_phi.val)
    except Exception as e:
        print("Erro ao atualizar configuração:", e)

# =============================================================================
# Criação do slider para controlar o ângulo do servo (φ)
# =============================================================================
ax_slider_phi = fig.add_axes([0.05, 0.05, 0.65, 0.03])
slider_phi = Slider(ax_slider_phi, 'Ângulo do Servo (φ)', phi_min, phi_max, valinit=phi_neutro)
slider_phi.on_changed(slider_update)

# =============================================================================
# Criação das caixas de texto para configuração das dimensões e do tilt (ψ)
# =============================================================================
text_boxes = {}
# Posições verticais para as caixas (incluindo a nova para ψ)
pos_y = [0.8, 0.7, 0.6, 0.5, 0.4]
labels = ["d", "R", "L", "a", "psi"]
init_values = [str(d), str(R), str(L), str(a), str(psi)]
for i, lab in enumerate(labels):
    ax_box = fig.add_axes([0.75, pos_y[i], 0.2, 0.05])
    tb = TextBox(ax_box, lab, initial=init_values[i])
    tb.on_submit(update_config)
    text_boxes[lab] = tb

# =============================================================================
# Plot inicial (posição neutra)
# =============================================================================
update_plot(phi_neutro)
plt.show()
