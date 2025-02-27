import sys
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button, Slider
from matplotlib.patches import Rectangle, Arc

# ---------------------------------------------------
# VERIFICA SE O ARGUMENTO --D ESTÁ PRESENTE
# ---------------------------------------------------
DEBUG_MODE = ("--D" in sys.argv)

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
def calcular_sistema(R, d, k, L0, L1, L2, anchor_y, tau_max, theta_graus):
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
    T = k * delta
    if DEBUG_MODE:
        print(f"Tensão (T) = k * delta = {k:.1f} * {delta:.4f} = {T:.4f} N")

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
    gamma_rads = 3.1415 - angle_between(AD, AO)
    Fx_real = T * math.sin(gamma_rads)
    Fy_real = T * math.cos(gamma_rads)

    if DEBUG_MODE:
        print(f"AO = {AO},  |AO| = {vec_length(AO):.4f}")
        print(f"gamma_rads = {gamma_rads:.4f} rad = {math.degrees(gamma_rads):.4f}°")
        print(f"Fx_real = {Fx_real:.4f} N")
        print(f"Fy_real = {Fy_real:.4f} N")

    # ---------------------------------------------------
    # Torque no servo
    # ---------------------------------------------------
    tau_Nm = abs(A[0]*Fy_real - A[1]*Fx_real)
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
        "beta_rads": beta_rads
    }

# ---------------------------------------------------
# PARÂMETROS GLOBAIS
# ---------------------------------------------------
PARAMS = {
    "R": 0.02,
    "d": 0.42,
    "anchor_y": 0.035,
    "k": 1167.0,
    "L0": 0.05,
    "L1": 0.36,
    "L2": 0.001,
    "tau_max": 20.0
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

labels = ["R","d","anchor_y","k","L0","L1", "L2","tau_max"]
initials = [str(PARAMS[l]) for l in labels]
textboxes = {}
box_height = 0.07
current_y = 0.75
for label,initv in zip(labels,initials):
    axb = fig_params.add_axes([0.2, current_y, 0.6, box_height])
    tb = TextBox(axb, label+": ", initial=initv)
    textboxes[label] = tb
    current_y -= (box_height+0.01)

ax_btn_apply = fig_params.add_axes([0.3, 0.05, 0.4, 0.1])
btn_apply = Button(ax_btn_apply,"Apply")

def parse_float(txt, fallback=0.0):
    try: 
        return float(txt)
    except:
        return fallback

def on_apply(event):
    for l in labels:
        PARAMS[l] = parse_float(textboxes[l].text, PARAMS[l])
    update_main_figure()

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
wall_width = 0.05
wall_height = 0.4
wall_patch = Rectangle(
    (PARAMS["d"], PARAMS["anchor_y"] - wall_height/2),
    wall_width, wall_height,
    facecolor='none',
    edgecolor='black',
    hatch='////',
    label='Parede'
)
ax.add_patch(wall_patch)

# Servo (quadrado na origem)
servo_patch = Rectangle(
    (-0.05, -0.05), 0.1, 0.1,
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
    
    # ---- Chama a função de cálculo (com prints só se --D) ----
    res = calcular_sistema(
        R=PARAMS["R"],
        d=PARAMS["d"],
        k=PARAMS["k"],
        L0=PARAMS["L0"],
        L1=PARAMS["L1"],
        L2=PARAMS["L2"],
        anchor_y=PARAMS["anchor_y"],
        tau_max=PARAMS["tau_max"],
        theta_graus=theta_val
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
    T_val = res["T"]
    T_kgf = T_val * NEWTON_TO_KGF

    # Vetor AD e vetores unitários para desenhar setas
    AD = vec_sub(D, A)
    u_rope = vec_unit(AD)
    u_rope_perp = rot90(u_rope)

    if T_val > 1e-9:
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
            color='blue', fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle="round", fc="white", ec="blue", alpha=0.6)
        )
        
        # -- Desenho da seta Fy (perpendicular ao cabo) --
        vec_fy = vec_scale(u_rope_perp, Fy)
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
            color='orange', fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle="round", fc="white", ec="orange", alpha=0.6)
        )
        
        # -- Desenho da seta representando a força de torque --
        Ft_mag = res["torqueForce_mag"]
        Ft_kgf = Ft_mag * NEWTON_TO_KGF
        u_t = res["u_torque"]
        arrow_torque = ax.arrow(
            A[0], A[1],
            u_t[0]*T_val*force_scale_val, u_t[1]*T_val*force_scale_val,
            head_width=0.007, head_length=0.01,
            fc='magenta', ec='magenta'
        )
        tip_torque = (A[0] + u_t[0]*T_val*force_scale_val*1.1,
                      A[1] + u_t[1]*T_val*force_scale_val*1.1)
        txt_torque = ax.text(
            tip_torque[0], tip_torque[1],
            f"Tq={T_val*NEWTON_TO_KGF:.2f} kgf",
            color='magenta', fontsize=8, ha='center', va='center',
            bbox=dict(boxstyle="round", fc="white", ec="magenta", alpha=0.6)
        )

    # ---------------------------------------------------
    # Arcos e textos de ângulos (theta, gamma, beta)
    # ---------------------------------------------------

    # 1) theta em torno da origem (0,0)
    theta_rads = res["theta_rads"]
    theta_degs = math.degrees(theta_rads)
    arc_theta = Arc((0,0), 0.4, 0.4,  # tamanho do arco
                    angle=0,
                    theta1=0, theta2=theta_degs,
                    color='red', lw=2)
    ax.add_patch(arc_theta)
    mid_theta = theta_rads/2
    r_ = 0.25
    x_txt = r_*math.cos(mid_theta)
    y_txt = r_*math.sin(mid_theta)
    txt_theta = ax.text(x_txt, y_txt, 
                        f"θ={theta_val:.1f}°",
                        color='red', fontsize=8,
                        ha='center', va='center')

    # 2) gamma em torno de A, entre AO e AD
    angle_AO_deg = math.degrees(math.atan2(-A[1], -A[0]))  # AO = ( -A[0], -A[1] )
    angle_AD_deg = math.degrees(math.atan2(AD[1], AD[0]))
    start_g = min(angle_AO_deg, angle_AD_deg)
    end_g   = max(angle_AO_deg, angle_AD_deg)

    arc_gamma = Arc(
        A, 0.2, 0.2,
        angle=0,
        theta1=start_g,
        theta2=end_g,
        color='purple', lw=2
    )
    ax.add_patch(arc_gamma)

    meio_g_deg = (start_g + end_g)/2
    meio_g_rad = math.radians(meio_g_deg)
    r_g = 0.18
    x_gamma = A[0] + r_g*math.cos(meio_g_rad)
    y_gamma = A[1] + r_g*math.sin(meio_g_rad)
    txt_gamma = ax.text(
        x_gamma, y_gamma,
        f"γ={abs(end_g - start_g):.1f}°",
        color='purple', fontsize=8,
        ha='center', va='center'
    )

    # 3) beta em torno de D, entre vertical (90°) e CD
    C = res["C"]
    CD = vec_sub(D, C)
    angle_vert = 90.0
    angle_CD_deg = math.degrees(math.atan2(CD[1], CD[0]))
    start_b = min(angle_vert, angle_CD_deg)
    end_b   = max(angle_vert, angle_CD_deg)

    arc_beta = Arc(
        D, 0.2, 0.2,
        angle=0,
        theta1=start_b,
        theta2=end_b,
        color='green', lw=2
    )
    ax.add_patch(arc_beta)

    meio_b_deg = (start_b + end_b)/2
    meio_b_rad = math.radians(meio_b_deg)
    r_b = 0.18
    x_beta = D[0] + r_b*math.cos(meio_b_rad)
    y_beta = D[1] + r_b*math.sin(meio_b_rad)
    txt_beta = ax.text(
        x_beta, y_beta,
        f"β={abs(end_b - start_b):.1f}°",
        color='green', fontsize=8,
        ha='center', va='center'
    )

    # ---------------------------------------------------
    # Texto info no canto
    # ---------------------------------------------------
    info_text.set_text(
       f"θ = {theta_val:.1f}°\n"
       f"Tensão (T) = {T_val:.1f} N = {T_kgf:.2f} kgf\n"
       f"Delta (mola) = {res['delta']*1000:.1f} mm\n"
       f"Fx = {Fx:.2f} N\n"
       f"Fy = {Fy:.2f} N\n"
       f"Torque = {res['tau_kgfcm']:.2f} kgf·cm\n"
       f"τ_max = {PARAMS['tau_max']:.2f} kgf·cm\n"
       f"Escala Força = {force_scale_val:g}"
    )
    if res['tau_kgfcm'] > PARAMS['tau_max']:
        info_text.set_color('red')
    else:
        info_text.set_color('black')
    
    ax.set_xlim(-0.3, 1.3)
    ax.set_ylim(-0.2, 0.8)
    ax.set_aspect('equal', 'box')

    fig_ani.canvas.draw_idle()

slider_angle.on_changed(update_main_figure)
slider_force_scale.on_changed(update_main_figure)

# Primeira atualização
update_main_figure()
plt.show()
