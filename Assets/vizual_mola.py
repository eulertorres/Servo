import sys
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button, Slider
from matplotlib.patches import Rectangle, Arc

# ---------------------------------------------------
# VERIFICA SE O ARGUMENTO --D ESTÁ PRESENTE
# ---------------------------------------------------
DEBUG_MODE = ("-D" in sys.argv)

# ---------------------------------------------------
# CONSTANTES E FUNÇÕES AUXILIARES
# ---------------------------------------------------
NEWTON_TO_KGF = 0.101971621  # 1 N ≈ 0.101971621 kgf
KGFCM_TO_NM = 0.0980665      # 1 kgf·cm = 0.0980665 N·m

def vec_sub(v1, v2):
    return (v1[0] - v2[0], v1[1] - v2[1])

def vec_add(v1, v2):
    return (v1[0] + v2[0], v1[1] + v2[1])

def vec_scale(v, s):
    return (v[0]*s, v[1]*s)

def vec_length(v):
    return math.hypot(v[0], v[1])

def vec_dot(v1, v2):
    return v1[0]*v2[0] + v1[1]*v2[1]

def vec_unit(v):
    l = vec_length(v)
    if l < 1e-12:
        return (0.0,0.0)
    return (v[0]/l, v[1]/l)

def rot90(v):
    """Rotaciona o vetor 90 graus no sentido anti-horário."""
    return (-v[1], v[0])

def vec_angle_x(v):
    """Ângulo (em rad) de um vetor v em relação ao eixo x."""
    return math.atan2(v[1], v[0])

def angle_between(v1, v2):
    """
    Retorna o ângulo em radianos entre v1 e v2.
    """
    u1 = vec_unit(v1)
    u2 = vec_unit(v2)
    dot_ = vec_dot(u1, u2)
    # forçar limite para evitar ValueError de acos fora de [-1,1]
    dot_ = max(-1.0, min(1.0, dot_))
    return math.acos(dot_)

# ---------------------------------------------------
# FUNÇÃO PRINCIPAL DE CÁLCULO DO SISTEMA
# ---------------------------------------------------
def calcular_sistema(R, d, k, L0, L1, L2, anchor_y, tau_max, theta_graus, leitura):
    """
    Só imprime dados de debug se DEBUG_MODE == True.
    """
    if DEBUG_MODE:
        print("========== DEBUG calcular_sistema ==========")

    # --- Ângulo do servo (theta) em rad ---
    theta = math.radians(theta_graus)

    # Coordenadas do ponto A (ponta do braço do servo)
    A = (R*math.cos(theta), R*math.sin(theta))

    # Ponto D (ancoragem na parede)
    D = (d, anchor_y)

    # Vetor A->D e magnitude
    AD = vec_sub(D, A)
    dist_AD = vec_length(AD)

    if DEBUG_MODE:
        print(f"Ângulo do servo (theta) = {theta_graus:.1f}° ({theta:.4f} rad)")
        print(f"Ponto A (na ponta do braço do servo) = {A}")
        print(f"Ponto D (ancoragem na parede)        = {D}")
        print(f"distância AD = {dist_AD:.4f} m")

    # Comprimento total "solto" da corda + mola (sem esticar) = L1 + L0 + L2
    slack_length = L1 + L0 + L2

    # Deformação da mola (delta): quando dist_AD ultrapassa slack_length
    if dist_AD > slack_length:
        delta = dist_AD - slack_length
    else:
        delta = 0.0

    if DEBUG_MODE:
        print(f"Comprimento 'solto' (slack_length) = {slack_length:.4f} m")
        print(f"Delta (deformação da mola)         = {delta:.4f} m")

    # --- Tensão gerada pela mola ---
    T = k * delta + leitura  # soma a leitura da "balança" como offset, se desejar
    if DEBUG_MODE:
        print(f"Tensão (T) = k * delta = {k:.1f} * {delta:.4f} + leitura = {T:.4f} N")

    # Direção (unitária) A->D (ou seja, da corda)
    u_rope = vec_unit(AD)

    # Força total no cabo = T na direção u_rope
    F_total = vec_scale(u_rope, T)
    if DEBUG_MODE:
        print(f"Direção do cabo (u_rope) = {u_rope}")
        print(f"F_total (vetor) = {F_total} (N)")

    # ---------------------------------------------------
    # Cálculo de Fx e Fy "reais" em eixos globais X e Y
    # ---------------------------------------------------
    AO = vec_sub((0, 0), A)  # Vetor A->O
    AO_defasado90 = rot90(AO)  # Rotaciona AO em 90°
    gamma_rads = angle_between(AD, AO_defasado90)
    alpha_rads = math.pi/2 - gamma_rads
    zeta_rads = angle_between(AD, AO) # A força é resultante do produto vetorial. 
    Fservo = T * math.sin(zeta_rads)
    Fx_real = Fservo * math.cos(gamma_rads)
    Fy_real = Fservo * math.cos(alpha_rads)

    if DEBUG_MODE:
        print(f"AO = {AO},  |AO| = {vec_length(AO):.4f}")
        print(f"gamma_rads = {gamma_rads:.4f} rad = {math.degrees(gamma_rads):.4f}°")
        print(f"Fx_real/Tração = {Fx_real*NEWTON_TO_KGF:.4f} Kgf")
        print(f"Fy_real = {Fy_real*NEWTON_TO_KGF:.4f} kgf")
        print(f"Fservo = {Fservo*NEWTON_TO_KGF:.4f} kgf")

    # ---------------------------------------------------
    # Torque no servo
    # ---------------------------------------------------
    tau_Nm = R * Fservo
    tau_kgfcm = tau_Nm / KGFCM_TO_NM

    if DEBUG_MODE:
        print(f"Torque no servo (tau) em N·m = {tau_Nm:.4f} N·m")
        print(f"Torque no servo (tau) em kgf·cm = {tau_kgfcm:.4f} kgf·cm")

    # ---------------------------------------------------
    # Cálculo do ponto B e do ponto C
    # ---------------------------------------------------
    B = vec_add(A, vec_scale(u_rope, L1))   # A->B
    length_mola = L0 + delta               # tamanho atual da mola
    C = vec_add(B, vec_scale(u_rope, length_mola))

    # ---------------------------------------------------
    # Força perpendicular ao braço (p/ visualização do "torqueForce_mag")
    # ---------------------------------------------------
    u_arm = vec_unit(A)
    proj_par_arm = vec_scale(u_arm, vec_dot(F_total, u_arm))
    F_perp_arm_vec = vec_sub(F_total, proj_par_arm)
    torqueForce_mag = vec_length(F_perp_arm_vec)
    if torqueForce_mag > 1e-9:
        u_torque = vec_unit(vec_scale(F_perp_arm_vec, -1.0))
    else:
        u_torque = (0.0, 0.0)

    if DEBUG_MODE:
        print(f"u_arm = {u_arm}")
        print(f"F_perp_arm_vec = {F_perp_arm_vec}")
        print(f"torqueForce_mag (magnitude) = {torqueForce_mag:.4f} N")
        print(f"u_torque (direção p/ visual) = {u_torque}\n")

    # ---------------------------------------------------
    # Ângulo beta = entre corda 2 (C->D) e a vertical
    # ---------------------------------------------------
    CD = vec_sub(D, C)
    vertical = (0.0, 1.0)
    beta_rads = angle_between(vertical, CD)

    if DEBUG_MODE:
        print(f"CD = {CD}, |CD| = {vec_length(CD):.4f}")
        print(f"beta_rads = {beta_rads:.4f} rad = {math.degrees(beta_rads):.4f}°")
        print("============================================\n")

    return {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "T": T,
        "delta": delta,
        "Fx_real": Fx_real,
        "Fy_real": Fy_real,
        "tau_Nm": tau_Nm,
        "tau_kgfcm": tau_kgfcm,
        "torqueForce_mag": torqueForce_mag,
        "u_torque": u_torque,
        "theta_rads": theta,
        "gamma_rads": gamma_rads,
        "beta_rads": beta_rads,
        "gamme_rads": gamma_rads,  # (parece duplicado, mas está no código original)
        "Fservo": Fservo
    }

# ---------------------------------------------------
# PARÂMETROS GLOBAIS
# ---------------------------------------------------
PARAMS = {
    "R": 0.02,      # Raio do braço do servo
    "d": 0.42,      # Distância em X do ponto de ancoragem
    "anchor_y": 0.035, # Distância em Y do ponto de ancoragem
    "k": 1167.0,    # Constante elástica da mola
    "L0": 0.05,     # Tamanho da mola sem carga
    "L1": 0.36,     # Comprimento corda1 (cabo + balança)
    "L2": 0.001,    # Comprimento corda 2 (entre mola e ancoragem)
    "tau_max": 20.0,# Torque máximo do servo (referência)
    "Balanca": 0.370# Valor (N) que você está somando como "leitura" (caso queira simular)
}
theta_val = 0.0

# ---------------------------------------------------
# JANELA DE PARÂMETROS
# ---------------------------------------------------
fig_params = plt.figure(figsize=(4,5))
fig_params.canvas.manager.set_window_title("Janela de Parâmetros")

ax_title = fig_params.add_axes([0.1, 0.84, 0.8, 0.1])
ax_title.axis("off")
ax_title.text(0.5, 0.5, "Parâmetros do Sistema\n(Depois clique em 'Apply')", 
              ha="center", va="center", fontsize=9)

labels = ["R","d","anchor_y","k","L0","L1", "L2","tau_max", "Balanca"]
initials = [str(PARAMS[l]) for l in labels]
textboxes = {}
box_height = 0.07
current_y = 0.75
for label,initv in zip(labels,initials):
    axb = fig_params.add_axes([0.2, current_y, 0.6, box_height])
    tb = TextBox(axb, label+": ", initial=initv)
    textboxes[label] = tb
    current_y -= (box_height+0.01)

ax_btn_apply = fig_params.add_axes([0.3, 0.06, 0.4, 0.1])
btn_apply = Button(ax_btn_apply,"Apply")

def parse_float(txt, fallback=0.0):
    try: 
        return float(txt)
    except:
        return fallback

def on_apply(event):
    for l in labels:
        PARAMS[l] = parse_float(textboxes[l].text, PARAMS[l])
    update_main_figure()  # atualiza a simulação
    update_torque_plot()  # e também o gráfico de torque

btn_apply.on_clicked(on_apply)

# ---------------------------------------------------
# JANELA DE ANIMAÇÃO
# ---------------------------------------------------
fig_ani, ax = plt.subplots(figsize=(7,7))
fig_ani.canvas.manager.set_window_title("Janela de Animação")
plt.subplots_adjust(left=0.1, bottom=0.3)

ax.set_title("Simulação: Servo, Balança, Mola e Cordas", fontsize=11)
ax.set_xlabel("x (m)", fontsize=10)
ax.set_ylabel("y (m)", fontsize=10)

# Parede (retângulo)
wall_width = 0.025
wall_height = 0.06
wall_patch = Rectangle(
    (PARAMS["d"], PARAMS["anchor_y"] - wall_height/2),
    wall_width, wall_height,
    facecolor='none',
    edgecolor='black',
    hatch='////',
    label='Parede'
)
ax.add_patch(wall_patch)

Servo_height = 0.02
servo_width = 0.055
# Servo (quadrado na origem)
servo_patch = Rectangle(
    (-servo_width/2 + 0.001, -Servo_height/2), servo_width, Servo_height,
    facecolor='lightblue',
    edgecolor='blue',
    label='Servo'
)
ax.add_patch(servo_patch)

servo_line, = ax.plot([], [], 'o-', lw=3, color='blue', label="Braço Servo")
rope1_line, = ax.plot([], [], 'o-', lw=2, color='black', label="Corda 1")
spring_line, = ax.plot([], [], 'o--', lw=2, color='green', label="Mola")
rope2_line, = ax.plot([], [], 'o-', lw=2, color='black', label="Corda 2")
scale_marker, = ax.plot([], [], 's', markersize=8, color='orange', label="Balança")

info_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                    fontsize=9, color='red',
                    verticalalignment='top')

ax.legend(loc="upper right")

# Variáveis para setas e textos adicionais
arrow_Fx = None
arrow_Fy = None
arrow_torque = None
txt_Fx = None
txt_Fy = None
txt_torque = None

# Variáveis para os arcos dos ângulos
arc_theta = None
arc_gamma = None
arc_beta = None
txt_theta = None
txt_gamma = None
txt_beta = None

# Slider Ângulo
ax_slider_angle = plt.axes([0.2, 0.22, 0.65, 0.03])
slider_angle = Slider(ax_slider_angle, "Ângulo (graus)", 0, 180, valinit=theta_val, valstep=1)

# Slider Escala de Força
ax_slider_scale = plt.axes([0.2, 0.15, 0.65, 0.03])
slider_force_scale = Slider(ax_slider_scale, "Escala Força", 
                            0.0001, 0.1, valinit=0.004, valstep=0.0001)

# Botão Animar
ax_btn_ani = plt.axes([0.8, 0.19, 0.1, 0.06])
btn_ani = Button(ax_btn_ani, "Animar")
animating = False

def animate():
    """Incrementa o ângulo e atualiza (animação simples)."""
    global animating
    if not animating:
        return
    v = slider_angle.val
    v_next = v + 1
    if v_next > 180:
        v_next = 0
    slider_angle.set_val(v_next)
    plt.pause(0.05)
    if animating:
        animate()

def on_toggle_anim(event):
    global animating
    animating = not animating
    if animating:
        btn_ani.label.set_text("Pausar")
        animate()
    else:
        btn_ani.label.set_text("Animar")

btn_ani.on_clicked(on_toggle_anim)

def update_main_figure(_=None):
    """Atualiza a figura principal quando parâmetros ou sliders mudam."""
    global arrow_Fx, arrow_Fy, arrow_torque, txt_Fx, txt_Fy, txt_torque
    global arc_theta, arc_gamma, arc_beta, txt_theta, txt_gamma, txt_beta

    # Remove setas/rotulos antigos
    for arr in [arrow_Fx, arrow_Fy, arrow_torque]:
        if arr:
            arr.remove()
    arrow_Fx = arrow_Fy = arrow_torque = None
    
    for txt in [txt_Fx, txt_Fy, txt_torque]:
        if txt:
            txt.remove()
    txt_Fx = txt_Fy = txt_torque = None

    # Remove arcos e textos de ângulo antigos
    for arc_ in [arc_theta, arc_gamma, arc_beta]:
        if arc_:
            arc_.remove()
    arc_theta = arc_gamma = arc_beta = None

    for txt_ in [txt_theta, txt_gamma, txt_beta]:
        if txt_:
            txt_.remove()
    txt_theta = txt_gamma = txt_beta = None

    # Atualiza patch da parede
    wall_patch.set_x(PARAMS["d"])
    wall_patch.set_y(PARAMS["anchor_y"] - wall_height/2)
    
    # Lê parâmetros e ângulo
    global theta_val
    theta_val = slider_angle.val
    force_scale_val = slider_force_scale.val
    
    # ---- Chama a função de cálculo ----
    res = calcular_sistema(
        R=PARAMS["R"],
        d=PARAMS["d"],
        k=PARAMS["k"],
        L0=PARAMS["L0"],
        L1=PARAMS["L1"],
        L2=PARAMS["L2"],
        anchor_y=PARAMS["anchor_y"],
        tau_max=PARAMS["tau_max"],
        theta_graus=theta_val,
        leitura=PARAMS["Balanca"],
    )
    
    A = res["A"]
    B = res["B"]
    C = res["C"]
    D = res["D"]
    
    # Atualiza os segmentos (braço, cordas, mola etc.)
    servo_line.set_data([0, A[0]], [0, A[1]])
    rope1_line.set_data([A[0], B[0]], [A[1], B[1]])
    spring_line.set_data([B[0], C[0]], [B[1], C[1]])
    rope2_line.set_data([C[0], D[0]], [C[1], D[1]])
    scale_marker.set_data([B[0]], [B[1]])  # B é a balança
    
    Fx = res["Fx_real"]
    Fy = res["Fy_real"]
    Fservo_val = res["Fservo"]
    T_kgf = Fservo_val * NEWTON_TO_KGF

    # Vetor AD e vetores unitários para desenhar setas
    AD = vec_sub(D, A)
    u_rope = vec_unit(AD)
    u_rope_perp = rot90(u_rope)

    if Fservo_val > 1e-9:
        # -- Desenho da seta Fx (no sentido da corda) --
        vec_fx = vec_scale(u_rope, -Fx)
        arrow_Fx = ax.arrow(
            A[0], A[1],
            vec_fx[0]*force_scale_val, vec_fx[1]*force_scale_val,
            head_width=0.007, head_length=0.01,
            fc='blue', ec='blue'
        )
        tip_fx = (A[0] + vec_fx[0]*force_scale_val*1.1,
                  A[1] + vec_fx[1]*force_scale_val*1.1)
        txt_Fx = ax.text(
            tip_fx[0], tip_fx[1],
            f"Fx={abs(Fx*NEWTON_TO_KGF):.2f} kgf",
            color='blue', fontsize=7, ha='center', va='center',
            bbox=dict(boxstyle="round", fc="white", ec="blue", alpha=0.6)
        )
        
        # -- Desenho da seta Fy (perpendicular ao cabo) --
        vec_fy = vec_scale(u_rope_perp, -Fy)
        arrow_Fy = ax.arrow(
            A[0], A[1],
            vec_fy[0]*force_scale_val, vec_fy[1]*force_scale_val,
            head_width=0.007, head_length=0.01,
            fc='orange', ec='orange'
        )
        tip_fy = (A[0] + vec_fy[0]*force_scale_val*1.1,
                  A[1] + vec_fy[1]*force_scale_val*1.1)
        txt_Fy = ax.text(
            tip_fy[0], tip_fy[1],
            f"Fy={abs(Fy*NEWTON_TO_KGF):.2f} kgf",
            color='orange', fontsize=7, ha='center', va='center',
            bbox=dict(boxstyle="round", fc="white", ec="orange", alpha=0.6)
        )
        
        # -- Desenho da seta representando a força de torque --
        u_t = res["u_torque"]
        arrow_torque = ax.arrow(
            A[0], A[1],
            u_t[0]*Fservo_val*force_scale_val, u_t[1]*Fservo_val*force_scale_val,
            head_width=0.007, head_length=0.01,
            fc='magenta', ec='magenta'
        )
        tip_torque = (A[0] + u_t[0]*Fservo_val*force_scale_val*1.1,
                      A[1] + u_t[1]*Fservo_val*force_scale_val*1.1)
        txt_torque = ax.text(
            tip_torque[0], tip_torque[1],
            f"Tq={Fservo_val*NEWTON_TO_KGF:.2f} kgf",
            color='magenta', fontsize=7, ha='center', va='center',
            bbox=dict(boxstyle="round", fc="white", ec="magenta", alpha=0.6)
        )

    # ---------------------------------------------------
    # Arcos e textos de ângulos (theta, gamma, beta)
    # ---------------------------------------------------
    # 1) theta em torno da origem (0,0)
    theta_rads = res["theta_rads"]
    theta_degs = math.degrees(theta_rads)
    arc_theta = Arc((0,0), PARAMS["R"]*2, PARAMS["R"]*2,
                    angle=0, theta1=0, theta2=theta_degs,
                    color='red', lw=2)
    ax.add_patch(arc_theta)
    mid_theta = theta_rads/2
    r_ = 0.04
    x_txt = r_*math.cos(mid_theta)
    y_txt = r_*math.sin(mid_theta)
    txt_theta = ax.text(x_txt, y_txt, 
                        f"θ={theta_val:.1f}°",
                        color='red', fontsize=8,
                        ha='center', va='center')

    # 2) gamma em torno de A, entre AO e AD
    gamma_rads= res["gamma_rads"]
    gamma_degs = math.degrees(gamma_rads)
    arc_gamma = Arc(
        A, PARAMS["R"]*2, PARAMS["R"]*2,
        angle=theta_degs+90,
        theta1=-gamma_degs,
        theta2=0,
        color='purple', lw=2
    )
    ax.add_patch(arc_gamma)

    meio_g_rad = gamma_rads/2
    r_g = 0.05
    x_gamma = A[0] + r_g*math.cos(meio_g_rad)
    y_gamma = A[1] + r_g*math.sin(meio_g_rad)
    txt_gamma = ax.text(
        x_gamma, y_gamma,
        f"γ={gamma_degs:.1f}°",
        color='purple', fontsize=8,
        ha='center', va='center'
    )

    # 3) beta em torno de D, entre vertical (90°) e CD
    beta_rads = res["beta_rads"]
    beta_degs = math.degrees(beta_rads)
    arc_beta = Arc(
        D, 0.05, 0.05,
        angle=-90,
        theta1=-beta_degs,
        theta2=0,
        color='green', lw=2
    )
    ax.add_patch(arc_beta)

    meio_b_deg = beta_degs/2
    meio_b_rad = math.radians(meio_b_deg)
    r_b = 0.05
    x_beta = D[0] + r_b*math.cos(meio_b_rad)
    y_beta = D[1] + r_b*math.sin(meio_b_rad)
    txt_beta = ax.text(
        x_beta, y_beta,
        f"β={meio_b_deg:.1f}°",
        color='green', fontsize=8,
        ha='center', va='center'
    )

    # ---------------------------------------------------
    # Texto info no canto
    # ---------------------------------------------------
    info_text.set_text(
       f"θ = {theta_val:.1f}°\n"
       f"Tensão (T) = {Fservo_val:.1f} N = {T_kgf:.2f} kgf\n"
       f"Delta (mola) = {res['delta']*1000:.1f} mm\n"
       f"Fx (Balança)= {Fx*NEWTON_TO_KGF:.2f} Kgf\n"
       f"Fy = {Fy*NEWTON_TO_KGF:.2f} Kgf\n"
       f"Torque = {res['tau_kgfcm']:.2f} kgf·cm\n"
       f"τ_max = {PARAMS['tau_max']:.2f} kgf·cm\n"
       f"Escala Força = {force_scale_val:g}"
    )
    if res['tau_kgfcm'] > PARAMS['tau_max']:
        info_text.set_color('red')
    else:
        info_text.set_color('black')
    
    ax.set_xlim(-0.2, 0.6)
    ax.set_ylim(-0.1, 0.15)
    ax.set_aspect('equal', 'box')

    fig_ani.canvas.draw_idle()

slider_angle.on_changed(update_main_figure)
slider_force_scale.on_changed(update_main_figure)

# ---------------------------------------------------
# CRIANDO UMA JANELA PARA O GRÁFICO TORQUE x ÂNGULO
# ---------------------------------------------------
fig_torque, ax_torque = plt.subplots()
fig_torque.canvas.manager.set_window_title("Torque x Ângulo")
ax_torque.set_title("Torque (kgf·cm) vs. Ângulo do Servo (graus)")
ax_torque.set_xlabel("Ângulo (°)")
ax_torque.set_ylabel("Torque (kgf·cm)")

# Linha do gráfico de torque
line_torque, = ax_torque.plot([], [], label="Torque")
# Marcador do torque atual
marker_torque, = ax_torque.plot([], [], 'ro', label="Ângulo atual")

ax_torque.legend(loc='best')

def update_torque_plot():
    """
    Atualiza o gráfico de Torque x Ângulo (0 a 180°).
    E reposiciona o marcador no ângulo atual do slider.
    """
    # Prepara vetores de ângulo e torque
    theta_array = np.arange(0, 181, 1)  # de 0° a 180°, passo de 1°
    torque_array = []
    for ang in theta_array:
        res_ = calcular_sistema(
            R=PARAMS["R"],
            d=PARAMS["d"],
            k=PARAMS["k"],
            L0=PARAMS["L0"],
            L1=PARAMS["L1"],
            L2=PARAMS["L2"],
            anchor_y=PARAMS["anchor_y"],
            tau_max=PARAMS["tau_max"],
            theta_graus=ang,
            leitura=PARAMS["Balanca"],
        )
        torque_array.append(res_["tau_kgfcm"])
    
    # Atualiza a linha do gráfico
    line_torque.set_data(theta_array, torque_array)
    
    # Para ajustar o range dos eixos
    ax_torque.relim()
    ax_torque.autoscale_view()

    # Agora, calcula o torque no ângulo atual (do slider)
    ang_atual = slider_angle.val
    res_atual = calcular_sistema(
        R=PARAMS["R"],
        d=PARAMS["d"],
        k=PARAMS["k"],
        L0=PARAMS["L0"],
        L1=PARAMS["L1"],
        L2=PARAMS["L2"],
        anchor_y=PARAMS["anchor_y"],
        tau_max=PARAMS["tau_max"],
        theta_graus=ang_atual,
        leitura=PARAMS["Balanca"]
    )
    torque_atual = res_atual["tau_kgfcm"]
    
    # Atualiza posição do marcador
    marker_torque.set_data([ang_atual], [torque_atual])

    # Força redesenho
    fig_torque.canvas.draw_idle()

# Sempre que o ângulo mudar, atualiza também o gráfico
slider_angle.on_changed(lambda val: update_torque_plot())

# Primeira atualização
update_main_figure()
update_torque_plot()

plt.show()
