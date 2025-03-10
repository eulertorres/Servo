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
phi_min = -50.0   # limite inferior
phi_max = 50.0    # limite superior
phi_neutro = 0.0  # posição neutra (servo e aileron neutros)

# =============================================================================
# Cálculo da posição do eixo do servo (S) em neutro
# =============================================================================
def compute_servo_position(d, R, a, L):
    """
    Em neutro:
      - A barra da superfície está horizontal (aileron neutro): C = (a, 0)
      - A roseta também aponta para "frente", isto é, B = S + (0, -R) (antes do tilt)
      - Impõe-se: ||B - C|| = L  e  ||S|| = d.
    Resolve as equações, escolhendo S_x > 0.
    """
    Sy = (L**2 - d**2 - (a - R)**2) / (2*(a - R))
    Sx = np.sqrt(d**2 - Sy**2)
    return np.array([Sx, Sy])

# =============================================================================
# Cálculo do ângulo do aileron (θ) para um ângulo do servo (φ) e tilt (ψ)
# =============================================================================
def compute_aileron_angle(phi, psi, S, R, a, L):
    """
    Dado o ângulo do servo φ (graus) e o tilt do servo ψ (graus), calcula:
      - O ponto B (ponta da roseta) considerando o tilt:
            B = S_3 + R * (R_x(ψ) * [cos(-90+φ), sin(-90+φ), 0])
        onde S_3 é S estendido para 3D (z = 0).
      - Determina numericamente θ (em radianos) para que o ponto C, definido por
            C = A + a*[cos(θ), sin(θ), 0],
        satisfaça ||C - B|| = L.
      
      **Importante:** Agora o neutro do aileron corresponde a θ = 0 (C = (a,0,0)).
    """
    S_3 = np.array([S[0], S[1], 0])
    theta_servo = np.deg2rad(-90 + phi)
    v = np.array([np.cos(theta_servo), np.sin(theta_servo), 0])
    psi_rad = np.deg2rad(psi)
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(psi_rad), -np.sin(psi_rad)],
                    [0, np.sin(psi_rad),  np.cos(psi_rad)]])
    v_rot = R_x.dot(v)
    B = S_3 + R * v_rot

    def f(theta_array):
        theta_val = theta_array[0]
        C = np.array([a * np.cos(theta_val), a * np.sin(theta_val), 0])
        return [np.linalg.norm(C - B) - L]
    # Para manter a referência anterior (neutro com deflexão -90°), usamos:
    theta0 = np.deg2rad(-90)
    theta_solution = fsolve(f, [theta0])[0]
    C = np.array([a * np.cos(theta_solution), a * np.sin(theta_solution), 0])
    return theta_solution, B, C

def angle_diff(angle):
    angle = (angle + np.pi) % (2 * np.pi) - np.pi
    return np.rad2deg(angle)

# =============================================================================
# Função para desenhar um arco representando um ângulo (em 2D)
# =============================================================================
def draw_angle_arc(ax, center, vec1, vec2, radius, color):
    angle1 = np.arctan2(vec1[1], vec1[0])
    angle2 = np.arctan2(vec2[1], vec2[0])
    diff = (angle2 - angle1 + 2*np.pi) % (2*np.pi)
    if diff > np.pi:
        diff = diff - 2*np.pi
    arc_angles = np.linspace(angle1, angle1 + diff, 50)
    x_arc = center[0] + radius * np.cos(arc_angles)
    y_arc = center[1] + radius * np.sin(arc_angles)
    ax.plot(x_arc, y_arc, color=color, linestyle='-', lw=1.5)

# =============================================================================
# Função para computar a circunferência de atuação do servo em 3D (com tilt)
# =============================================================================
def compute_servo_circle(S, R, psi):
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
# Configuração da figura com dois subplots:
# - Axes 3D para o mecanismo (à esquerda)
# - Axes 2D para a relação aileron x servo (à direita)
# =============================================================================
fig = plt.figure(figsize=(14, 8))
# Axes 3D – ajustado para ter mais área horizontal
ax = fig.add_axes([0.05, 0.15, 0.65, 0.8], projection='3d')
# Axes 2D (reposicionado para não conflitar com os menus)
ax2 = fig.add_axes([0.75, 0.15, 0.2, 0.5])

# Ajuste inicial dos limites do 3D (aumentando horizontalmente)
ax.set_xlim(-20, 150)
ax.set_ylim(-100, 40)
ax.set_zlim(-50, 50)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_title("Mecanismo 4 Barras - Simulação")

# =============================================================================
# Função de atualização do gráfico (3D e 2D)
# =============================================================================
def update_plot(phi):
    global S, A, d, R, L, a, psi
    cur_elev = ax.elev
    cur_azim = ax.azim
    cur_xlim = ax.get_xlim()
    cur_ylim = ax.get_ylim()
    cur_zlim = ax.get_zlim()
    
    theta, B, C = compute_aileron_angle(phi, psi, S, R, a, L)
    
    S_3 = np.array([S[0], S[1], 0])
    A_proj = A[:2]
    S_proj = S_3[:2]
    B_proj = B[:2]
    C_proj = C[:2]
    
    # Ângulo da barra A-C
    angle_AC = np.arctan2(C_proj[1]-A_proj[1], C_proj[0]-A_proj[0])
    
    # Ângulos em S, B, A e C (projeção em XY)
    angle_AS = np.arctan2(S_proj[1]-A_proj[1], S_proj[0]-A_proj[0])
    angle_SB = np.arctan2(B_proj[1]-S_proj[1], B_proj[0]-S_proj[0])
    angle_S = angle_diff(angle_SB - angle_AS)
    
    psi_rad = np.deg2rad(psi)
    R_x_inv = np.array([[1, 0, 0],
                        [0, np.cos(psi_rad), np.sin(psi_rad)],
                        [0, -np.sin(psi_rad), np.cos(psi_rad)]])
    B_corr = R_x_inv.dot(B)
    B_corr_proj = B_corr[:2]
    angle_SB_corr = np.arctan2(B_corr_proj[1]-S_proj[1], B_corr_proj[0]-S_proj[0])
    angle_BC = np.arctan2(C_proj[1]-B_corr_proj[1], C_proj[0]-B_corr_proj[0])
    angle_B = angle_diff(angle_BC - angle_SB_corr)
    
    angle_C1 = np.arctan2(C_proj[1]-B_proj[1], C_proj[0]-B_proj[0])
    angle_C2 = np.arctan2(C_proj[1]-A_proj[1], C_proj[0]-A_proj[0])
    angle_C = angle_diff(angle_C2 - angle_C1)
    
    angle_A1 = np.arctan2(S_proj[1]-A_proj[1], S_proj[0]-A_proj[0])
    angle_A2 = np.arctan2(C_proj[1]-A_proj[1], C_proj[0]-A_proj[0])
    angle_A = angle_diff(angle_A2 - angle_A1)
    
    length_AS = np.linalg.norm(S_3 - A)
    length_SB = np.linalg.norm(B - S_3)
    length_BC = np.linalg.norm(C - B)
    length_AC = np.linalg.norm(C - A)
    
    ax.cla()
    ax.set_xlim(cur_xlim)
    ax.set_ylim(cur_ylim)
    ax.set_zlim(cur_zlim)
    ax.view_init(elev=cur_elev, azim=cur_azim)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Mecanismo 4 Barras - Simulação")
    
    ax.plot([A[0], S_3[0]], [A[1], S_3[1]], [A[2], S_3[2]], 'k-', lw=2, label="A-S (base)")
    ax.plot([S_3[0], B[0]], [S_3[1], B[1]], [S_3[2], B[2]], 'r-', lw=2, label="S-B (servo)")
    ax.plot([B[0], C[0]], [B[1], C[1]], [B[2], C[2]], 'g-', lw=2, label="B-C (ligação)")
    ax.plot([A[0], C[0]], [A[1], C[1]], [A[2], C[2]], 'b-', lw=2, label="A-C (superfície)")
    
    servo_circle = compute_servo_circle(S, R, psi)
    ax.plot(servo_circle[:,0], servo_circle[:,1], servo_circle[:,2], color='magenta', linestyle='--', lw=1, label="Circ. do Servo")
    t_vals = np.linspace(0, 2*np.pi, 100)
    circle_A_x = A[0] + a * np.cos(t_vals)
    circle_A_y = A[1] + a * np.sin(t_vals)
    circle_A_z = np.zeros(100)
    ax.plot(circle_A_x, circle_A_y, circle_A_z, color='cyan', linestyle='--', lw=1, label="Circ. da Deflexão")
    
    for point, label in zip([A, S_3, B, C], ["A", "S", "B", "C"]):
        ax.scatter(point[0], point[1], point[2], s=50)
        ax.text(point[0], point[1], point[2], f" {label}", fontsize=10)
    
    arc_radius_A = 0.2 * min(length_AS, length_AC)
    draw_angle_arc(ax, A_proj, S_proj - A_proj, C_proj - A_proj, arc_radius_A, 'purple')
    arc_radius_S = 0.2 * min(length_AS, R)
    draw_angle_arc(ax, S_proj, A_proj - S_proj, B_proj - S_proj, arc_radius_S, 'red')
    arc_radius_B = 0.2 * min(length_SB, L)
    draw_angle_arc(ax, B_corr_proj, S_proj - B_corr_proj, C_proj - B_corr_proj, arc_radius_B, 'green')
    arc_radius_C = 0.2 * min(length_BC, a)
    draw_angle_arc(ax, C_proj, B_proj - C_proj, A_proj - C_proj, arc_radius_C, 'blue')
    
    psi_rad = np.deg2rad(psi)
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(psi_rad), -np.sin(psi_rad)],
                    [0, np.sin(psi_rad),  np.cos(psi_rad)]])
    v0 = np.array([0, -1, 0])
    v_tilt = R_x.dot(v0)
    arrow_length = 0.5 * R
    ax.quiver(S_3[0], S_3[1], S_3[2],
              arrow_length*v_tilt[0], arrow_length*v_tilt[1], arrow_length*v_tilt[2],
              color='orange', arrow_length_ratio=0.1)
    ax.text(S_3[0] + arrow_length*v_tilt[0],
            S_3[1] + arrow_length*v_tilt[1],
            S_3[2] + arrow_length*v_tilt[2],
            f"ψ = {psi:.1f}°", color='orange')
    
    info_text = (
        f"Ângulo do Servo (φ): {phi:.2f}°\n"
        f"Tilt do Servo (ψ): {psi:.2f}°\n"
        f"Ângulo da Superfície (A-C): {np.rad2deg(angle_AC):.2f}°\n"
        f"θ (solução): {np.rad2deg(theta):.2f}°\n\n"
        f"∠AS (S): {angle_S:.1f}°\n"
        f"∠B (corrigido): {angle_B:.1f}°\n"
        f"∠C: {angle_C:.1f}°\n"
        f"∠A (entre AS e AC): {angle_A:.1f}°\n\n"
        f"|A-S| = {length_AS:.2f}    |S-B| = {length_SB:.2f}\n"
        f"|B-C| = {length_BC:.2f}    |A-C| = {length_AC:.2f}"
    )
    ax.text2D(-0.22, 0.95, info_text, transform=ax.transAxes, fontsize=10,
              verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8))
    ax.legend(loc="lower left")
    
    # Atualiza o subplot 2D: relação entre ângulo do servo (φ) e deflexão do aileron
    ax2.cla()
    phi_range = np.linspace(phi_min, phi_max, 200)
    deflection = []
    for phi_val in phi_range:
        theta_val, _, C_val = compute_aileron_angle(phi_val, psi, S, R, a, L)
        deflection.append(np.rad2deg(np.arctan2(C_val[1]-A[1], C_val[0]-A[0])))
    deflection = np.array(deflection)
    # Aqui adicionamos um offset de +90 apenas para visualização
    ax2.plot(phi_range, deflection + 90, 'k-', lw=1.5)
    current_deflection = np.rad2deg(np.arctan2(C[1]-A[1], C[0]-A[0]))
    current_deflection_offset = current_deflection + 90
    ax2.plot(phi, current_deflection_offset, 'ro', markersize=8)
    ax2.set_xlabel("Ângulo do Servo (φ) [°]")
    ax2.set_ylabel("Deflexão do Aileron [°]")
    ax2.set_title("Relação Aileron x Servo")
    ax2.grid(True)
    ax2.set_xlim(phi_min, phi_max)
    
    # Adiciona linhas verticais pontilhadas em φ para deflexão = -75° e -105° 
    # (correspondentes a -90° neutro +15 e -15 deflexão)
    # Usamos a interpolação nos valores calculados:
    phi_for_minus75 = np.interp(-75, deflection, phi_range)
    phi_for_minus105 = np.interp(-105, deflection, phi_range)
    ax2.axvline(phi_for_minus75, color='r', linestyle='--')
    ax2.axvline(phi_for_minus105, color='r', linestyle='--')
    
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
ax_slider_phi = fig.add_axes([0.1, 0.05, 0.65, 0.03])
slider_phi = Slider(ax_slider_phi, 'Ângulo do Servo (φ)', phi_min, phi_max, valinit=phi_neutro)
slider_phi.on_changed(slider_update)

# =============================================================================
# Criação das caixas de texto para configuração (reposicionadas no canto superior direito)
# =============================================================================
text_boxes = {}
pos_configs = {
    "d": [0.75, 0.92, 0.2, 0.04],
    "R": [0.75, 0.87, 0.2, 0.04],
    "L": [0.75, 0.82, 0.2, 0.04],
    "a": [0.75, 0.77, 0.2, 0.04],
    "psi": [0.75, 0.72, 0.2, 0.04]
}
labels = ["d", "R", "L", "a", "psi"]
init_values = [str(d), str(R), str(L), str(a), str(psi)]
for lab in labels:
    pos = pos_configs[lab]
    ax_box = fig.add_axes(pos)
    tb = TextBox(ax_box, lab, initial=init_values[labels.index(lab)])
    tb.on_submit(update_config)
    text_boxes[lab] = tb

# =============================================================================
# Plot inicial (posição neutra)
# =============================================================================
update_plot(phi_neutro)
plt.show()
