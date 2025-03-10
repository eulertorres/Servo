import sys
import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider, TextBox
from matplotlib.patches import Rectangle, Circle

NEWTON_TO_KGF = 0.101971621
KGFCM_TO_NM = 0.0980665
g = 9.81

def parse_float(txt, fallback=0.0):
    # Substitui vírgula por ponto se houver
    txt = txt.replace(",", ".")
    try:
        return float(txt)
    except:
        return fallback

def rot90(a):
    return (-a[1], a[0])

def vec_length(a):
    return math.hypot(a[0], a[1])

def vec_scale(a, s):
    return (a[0]*s, a[1]*s)

def vec_add(a, b):
    return (a[0]+b[0], a[1]+b[1])

def vec_dot(a, b):
    return a[0]*b[0] + a[1]*b[1]

def calcular_sistema(R, M, L, tau_max, theta_graus, leitura):
    theta = math.radians(theta_graus)
    Ax = R * math.cos(theta)
    Ay = R * math.sin(theta)
    A = (Ax, Ay)
    P = (Ax, Ay - L)

    T = M*g + leitura
    if T < 0: T = 0

    tau_Nm = R * T * math.cos(theta)
    tau_kgfcm = tau_Nm / KGFCM_TO_NM

    radial_dir = (math.cos(theta), math.sin(theta))
    tang_dir   = rot90(radial_dir)
    F_servo = (0, T)
    F_rad_mag = vec_dot(F_servo, radial_dir)
    F_tan_mag = vec_dot(F_servo, tang_dir)
    F_rad_vec = vec_scale(radial_dir, F_rad_mag)
    F_tan_vec = vec_scale(tang_dir, F_tan_mag)

    return {
        "A": A,
        "P": P,
        "T": T,
        "tau_Nm": tau_Nm,
        "tau_kgfcm": tau_kgfcm,
        "theta": theta,
        "theta_graus": theta_graus,
        "F_servo": F_servo,
        "F_rad_vec": F_rad_vec,
        "F_tan_vec": F_tan_vec,
    }

# Parâmetros globais
PARAMS = {
    "R": 0.0226,
    "M": 4.774,
    "L": 0.10,
    "tau_max": 20,
    "Balanca": 0.0
}

theta_val = -90.0

fig_main, ax_main = plt.subplots(figsize=(7,7))
fig_main.canvas.manager.set_window_title("Simulação Principal")

plt.subplots_adjust(left=0.1, bottom=0.3)
ax_main.set_title("Servo puxando peso", fontsize=11)

servo_height = 0.02
servo_width  = 0.04
servo_patch = Rectangle((-servo_width/2, -servo_height/2),
                        servo_width, servo_height,
                        facecolor='lightblue', edgecolor='blue',
                        label='Servo')
ax_main.add_patch(servo_patch)

servo_arm_line, = ax_main.plot([], [], 'o-', lw=3, color='blue')
cable_line, = ax_main.plot([], [], 'o-', lw=2, color='black')
peso_patch = Circle((0,0), radius=0.02, facecolor='gray', edgecolor='black')
ax_main.add_patch(peso_patch)

info_text = ax_main.text(0.02, 0.98, '', transform=ax_main.transAxes,
                         fontsize=9, color='red', va='top')

ax_main.legend(loc="upper right")

ax_slider_angle = plt.axes([0.15, 0.22, 0.65, 0.03])
slider_angle = Slider(ax_slider_angle, "Ângulo (°)", -90, 90, valinit=theta_val, valstep=1)

ax_slider_scale = plt.axes([0.15, 0.15, 0.65, 0.03])
slider_force_scale = Slider(ax_slider_scale, "Escala Força", 0.0, 0.02, valinit=0.005, valstep=0.0005)

ax_btn_torque = plt.axes([0.25, 0.07, 0.2, 0.06])
btn_torque = Button(ax_btn_torque, "Visualizar Torque")

ax_btn_anim = plt.axes([0.48, 0.07, 0.15, 0.06])
btn_anim = Button(ax_btn_anim, "Animar")
animating = False

arrow_weight   = None
arrow_servoF   = None
arrow_servoRad = None
arrow_servoTan = None
txt_weight     = None
txt_servoF     = None
txt_servoRad   = None
txt_servoTan   = None

def update_main_figure(_=None):
    global arrow_weight, arrow_servoF, arrow_servoRad, arrow_servoTan
    global txt_weight, txt_servoF, txt_servoRad, txt_servoTan
    global theta_val

    for arr in [arrow_weight, arrow_servoF, arrow_servoRad, arrow_servoTan]:
        if arr: arr.remove()
    arrow_weight = arrow_servoF = arrow_servoRad = arrow_servoTan = None

    for txt_ in [txt_weight, txt_servoF, txt_servoRad, txt_servoTan]:
        if txt_: txt_.remove()
    txt_weight = txt_servoF = txt_servoRad = txt_servoTan = None

    theta_val = slider_angle.val
    force_scale_val = slider_force_scale.val

    res = calcular_sistema(
        R=PARAMS["R"],
        M=PARAMS["M"],
        L=PARAMS["L"],
        tau_max=PARAMS["tau_max"],
        theta_graus=theta_val,
        leitura=PARAMS["Balanca"]
    )

    A = res["A"]
    P = res["P"]
    T = res["T"]
    tau_kgfcm = res["tau_kgfcm"]

    servo_arm_line.set_data([0, A[0]], [0, A[1]])
    cable_line.set_data([A[0], P[0]], [A[1], P[1]])
    peso_patch.center = (P[0], P[1])

    if T > 1e-6:
        arrow_len = T * force_scale_val
        arrow_weight = ax_main.arrow(A[0], A[1], 0, -arrow_len,
                                     head_width=0.01, head_length=0.02,
                                     fc='red', ec='red')
        txt_weight = ax_main.text(A[0], A[1] - arrow_len * 1.3,
                                  f"P={T * NEWTON_TO_KGF:.2f} kgf",
                                  color='red', fontsize=8, ha='center',
                                  bbox=dict(fc="white", ec="red", alpha=0.7))

        arrow_servoF = ax_main.arrow(A[0], A[1], 0, arrow_len,
                                     head_width=0.01, head_length=0.02,
                                     fc='blue', ec='blue')
        txt_servoF = ax_main.text(A[0], A[1] + arrow_len * 1.3,
                                  f"F={T * NEWTON_TO_KGF:.2f} kgf",
                                  color='blue', fontsize=8, ha='center',
                                  bbox=dict(fc="white", ec="blue", alpha=0.7))

    F_rad_vec = res["F_rad_vec"]
    F_tan_vec = res["F_tan_vec"]
    rad_arrow = vec_scale(F_rad_vec, force_scale_val)
    tan_arrow = vec_scale(F_tan_vec, force_scale_val)

    arrow_servoRad = ax_main.arrow(A[0], A[1],
                                   rad_arrow[0], rad_arrow[1],
                                   head_width=0.01, head_length=0.02,
                                   fc='green', ec='green')
    tip_rad = vec_add(A, rad_arrow)
    txt_servoRad = ax_main.text(tip_rad[0] + 0.01, tip_rad[1] + 0.01,
                                f"F_rad={vec_length(F_rad_vec)*NEWTON_TO_KGF:.2f}",
                                color='green', fontsize=7, ha='center',
                                bbox=dict(fc="white", ec="green", alpha=0.7))

    arrow_servoTan = ax_main.arrow(A[0], A[1],
                                   tan_arrow[0], tan_arrow[1],
                                   head_width=0.01, head_length=0.02,
                                   fc='orange', ec='orange')
    tip_tan = vec_add(A, tan_arrow)
    txt_servoTan = ax_main.text(tip_tan[0] + 0.01, tip_tan[1] + 0.01,
                                f"F_tan={vec_length(F_tan_vec)*NEWTON_TO_KGF:.2f}",
                                color='orange', fontsize=7, ha='center',
                                bbox=dict(fc="white", ec="orange", alpha=0.7))

    info_text.set_text(
        f"Ângulo = {theta_val:.1f}°\n"
        f"Tensão = {T:.2f} N ({T * NEWTON_TO_KGF:.2f} kgf)\n"
        f"Torque = {tau_kgfcm:.2f} kgf·cm\n"
        f"τ_max  = {PARAMS['tau_max']:.2f} kgf·cm\n"
        f"Massa  = {PARAMS['M']} kg\n"
        f"R(braço)= {PARAMS['R']} m\n"
    )
    if tau_kgfcm > PARAMS["tau_max"]:
        info_text.set_color('red')
    else:
        info_text.set_color('black')

    ax_main.set_xlim(-0.3, 0.3)
    ax_main.set_ylim(-0.35, 0.25)
    ax_main.set_aspect('equal', 'box')
    fig_main.canvas.draw_idle()

slider_angle.on_changed(update_main_figure)
slider_force_scale.on_changed(update_main_figure)

def animate():
    global animating
    if not animating:
        return
    v = slider_angle.val
    v_next = v + 2
    if v_next > 90:
        v_next = -90
    slider_angle.set_val(v_next)
    plt.pause(0.05)
    if animating:
        animate()

def on_toggle_anim(event):
    global animating
    animating = not animating
    if animating:
        btn_anim.label.set_text("Pausar")
        animate()
    else:
        btn_anim.label.set_text("Animar")

btn_anim.on_clicked(on_toggle_anim)

# ============================================================
# Janela de Configuração – MODIFICADA para usar a mesma
# metodologia do exemplo enviado (sem depender de um
# botão "Configurar" e com layout semelhante)
# ============================================================
fig_config = plt.figure(figsize=(4,5))
fig_config.canvas.manager.set_window_title("Janela de Parâmetros")
ax_title = fig_config.add_axes([0.1, 0.84, 0.8, 0.1])
ax_title.axis("off")
ax_title.text(0.5, 0.5, "Parâmetros do Sistema\n(Depois clique em 'Apply')", 
              ha="center", va="center", fontsize=9)

labels_conf = ["R", "M", "L", "tau_max", "Balanca"]
textboxes = {}
box_height = 0.07
current_y = 0.75
for lab in labels_conf:
    axb = fig_config.add_axes([0.2, current_y, 0.6, box_height])
    tbox = TextBox(axb, lab+": ", initial=str(PARAMS[lab]))
    textboxes[lab] = tbox
    current_y -= (box_height + 0.01)

ax_btn_apply = fig_config.add_axes([0.3, 0.06, 0.4, 0.1])
btn_apply = Button(ax_btn_apply, "Apply")
def on_apply_config(event):
    for lab in labels_conf:
        PARAMS[lab] = parse_float(textboxes[lab].text, PARAMS[lab])
    update_main_figure()
    if fig_torque is not None and plt.fignum_exists(fig_torque.number):
        update_torque_plot()
btn_apply.on_clicked(on_apply_config)

# ============================================================
# Janela do Gráfico de Torque
# ============================================================
fig_torque = None
ax_torque = None
line_torque = None
marker_torque = None

def on_torque_close(evt):
    global fig_torque
    fig_torque = None

def show_torque_window(event):
    global fig_torque, ax_torque, line_torque, marker_torque
    if fig_torque is not None:
        if plt.fignum_exists(fig_torque.number):
            fig_torque.canvas.manager.window.lift()
            return
        else:
            fig_torque = None

    fig_torque, ax_torque = plt.subplots()
    fig_torque.canvas.manager.set_window_title("Torque x Ângulo")
    fig_torque.canvas.mpl_connect('close_event', on_torque_close)

    ax_torque.set_title("Torque (kgf·cm) vs. Ângulo ( -90° a +90° )")
    ax_torque.set_xlabel("Ângulo (°)")
    ax_torque.set_ylabel("Torque (kgf·cm)")

    line_torque, = ax_torque.plot([], [], label="Torque")
    marker_torque, = ax_torque.plot([], [], 'ro', label="Ângulo atual")
    ax_torque.legend(loc='best')

    update_torque_plot()
    fig_torque.show()

def update_torque_plot(*args):
    if fig_torque is None or ax_torque is None:
        return

    theta_array = np.arange(-90, 91, 1)
    torque_array = []
    for ang in theta_array:
        res_ = calcular_sistema(
            R=PARAMS["R"],
            M=PARAMS["M"],
            L=PARAMS["L"],
            tau_max=PARAMS["tau_max"],
            theta_graus=ang,
            leitura=PARAMS["Balanca"]
        )
        torque_array.append(res_["tau_kgfcm"])

    line_torque.set_data(theta_array, torque_array)
    ax_torque.relim()
    ax_torque.autoscale_view()

    ang_atual = slider_angle.val
    res_atual = calcular_sistema(
        R=PARAMS["R"],
        M=PARAMS["M"],
        L=PARAMS["L"],
        tau_max=PARAMS["tau_max"],
        theta_graus=ang_atual,
        leitura=PARAMS["Balanca"]
    )
    marker_torque.set_data([ang_atual], [res_atual["tau_kgfcm"]])
    fig_torque.canvas.draw_idle()

btn_torque.on_clicked(show_torque_window)
slider_angle.on_changed(update_torque_plot)

# ============================================================
# Inicialização
# ============================================================
update_main_figure()
plt.show()
