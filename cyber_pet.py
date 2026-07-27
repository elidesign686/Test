"""CyberPet — mascota de escritorio animada.

Un robotito blanco y azul (estilo kawaii) que pasea por TODA la pantalla:
camina hacia puntos aleatorios, rebota al andar, parpadea, se balancea y
de vez en cuando saluda con la mano.

Controles:
  - Arrastrar con clic izquierdo: mover al robot.
  - Doble clic: saluda.
  - Clic derecho: menú (Saludar / Salir).

En Windows la ventana es 100% transparente (solo se ve el robot flotando).
En Linux/macOS tkinter no soporta color de transparencia, así que se ve
sobre un pequeño recuadro de color.
"""

import os
import random
import tkinter as tk
from math import cos, pi, sin

# Color "llave" que Windows vuelve transparente
TRANSPARENT = "#ff00fe"

# Paleta (fiel a la imagen de referencia)
WHITE = "#f7f7f5"       # carcasa
SHADE = "#dcdcd8"       # cuello / sombras
OUTLINE = "#c9c9c4"     # contorno suave de la carcasa
BLUE = "#2f7fd6"        # azul principal
BLUE_MED = "#3f8fe0"    # insignia del pecho
BLUE_DARK = "#1f5fae"
BLUE_LIGHT = "#7fc4f8"  # cejas / aros
GLOW = "#a5dcff"        # brillo de ojos y sonrisa
VISOR = "#0d1420"       # pantalla de la cara
EYE = "#05080d"

W, H = 200, 244
FPS_MS = 33


class CyberPet:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("CyberPet")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        bg = os.environ.get("CYBERPET_BG", TRANSPARENT)  # útil para pruebas
        self.canvas = tk.Canvas(self.root, width=W, height=H, bg=bg,
                                highlightthickness=0)
        self.canvas.pack()
        try:
            self.root.wm_attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass  # Linux/macOS: sin transparencia por color

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.x = float(random.randint(0, max(0, self.sw - W)))
        self.y = float(random.randint(0, max(0, self.sh - H)))
        pos = os.environ.get("CYBERPET_POS")  # útil para pruebas: "x,y"
        if pos:
            px, py = pos.split(",")
            self.x, self.y = float(px), float(py)

        self.t = 0.0             # reloj de animación
        self.facing = 1          # 1 mira a la derecha, -1 a la izquierda
        self.state = "idle"      # idle | walk | wave | drag
        self.state_until = 0     # cuadros restantes del estado actual
        self.target = (self.x, self.y)
        self.walk_phase = 0.0
        self.wave_phase = 0.0
        self.blink = 0           # cuadros restantes de parpadeo
        self.next_blink = random.randint(60, 150)
        self.drag_dx = 0
        self.drag_dy = 0

        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", lambda e: self.start_wave())
        self.canvas.bind("<Button-3>", self.on_menu)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Saludar", command=self.start_wave)
        self.menu.add_separator()
        self.menu.add_command(label="Salir", command=self.root.destroy)

        if os.environ.get("CYBERPET_WAVE"):  # útil para pruebas
            self.start_wave()
        else:
            self.set_idle()
        self.move_window()
        self.tick()

    # ------------------------------------------------------------- estados
    def set_idle(self):
        self.state = "idle"
        self.state_until = random.randint(45, 140)

    def pick_target(self):
        margin = 10
        tx = random.uniform(margin, max(margin, self.sw - W - margin))
        ty = random.uniform(margin, max(margin, self.sh - H - margin))
        self.target = (tx, ty)
        self.facing = 1 if tx >= self.x else -1
        self.state = "walk"

    def start_wave(self):
        self.state = "wave"
        self.wave_phase = 0.0
        self.state_until = 80

    # ----------------------------------------------------------- eventos
    def on_press(self, event):
        self.state = "drag"
        self.drag_dx = event.x_root - int(self.x)
        self.drag_dy = event.y_root - int(self.y)

    def on_drag(self, event):
        self.x = float(event.x_root - self.drag_dx)
        self.y = float(event.y_root - self.drag_dy)
        self.move_window()

    def on_release(self, _event):
        if self.state == "drag":
            self.set_idle()

    def on_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    # -------------------------------------------------------------- bucle
    def move_window(self):
        self.x = max(-40.0, min(self.x, float(self.sw - W + 40)))
        self.y = max(-20.0, min(self.y, float(self.sh - H + 20)))
        self.root.geometry(f"{W}x{H}+{int(self.x)}+{int(self.y)}")

    def tick(self):
        self.t += 1

        if self.blink > 0:
            self.blink -= 1
        else:
            self.next_blink -= 1
            if self.next_blink <= 0:
                self.blink = 5
                self.next_blink = random.randint(70, 200)

        if self.state == "idle":
            self.state_until -= 1
            if self.state_until <= 0:
                if random.random() < 0.25:
                    self.start_wave()
                else:
                    self.pick_target()
        elif self.state == "wave":
            self.wave_phase += 0.35
            self.state_until -= 1
            if self.state_until <= 0:
                self.set_idle()
        elif self.state == "walk":
            tx, ty = self.target
            dx, dy = tx - self.x, ty - self.y
            dist = (dx * dx + dy * dy) ** 0.5
            speed = 3.2
            if dist <= speed:
                self.x, self.y = tx, ty
                self.set_idle()
            else:
                self.x += speed * dx / dist
                self.y += speed * dy / dist
                self.walk_phase += 0.45
                self.facing = 1 if dx >= 0 else -1
            self.move_window()

        self.draw()
        self.root.after(FPS_MS, self.tick)

    # -------------------------------------------------------------- dibujo
    def draw(self):
        c = self.canvas
        c.delete("all")
        f = self.facing
        cx = W // 2

        walking = self.state == "walk"
        waving = self.state == "wave"
        bounce = abs(sin(self.walk_phase)) * 4 if walking else 0.0
        bob = sin(self.t * 0.08) * 2 if not walking else 0.0
        oy = 10 - bounce + bob
        lean = f * 4 if walking else 0  # la cabeza se adelanta al caminar

        def circle(x, y, r, **kw):
            c.create_oval(x - r, y - r, x + r, y + r, **kw)

        # ---- pies (se quedan "en el suelo" y alternan al caminar)
        lf = -abs(sin(self.walk_phase)) * 5 if walking else 0.0
        rf = -abs(sin(self.walk_phase + pi)) * 5 if walking else 0.0
        c.create_oval(cx - 40, 212 + lf, cx - 6, 236 + lf,
                      fill=WHITE, outline=OUTLINE, width=2)
        c.create_oval(cx + 6, 212 + rf, cx + 40, 236 + rf,
                      fill=WHITE, outline=OUTLINE, width=2)

        # ---- brazo que cuelga (el trasero; el otro saluda o también cuelga)
        sway = sin(self.walk_phase) * 5 if walking else 0.0
        sx, sy = cx + f * 44, 158 + oy
        c.create_line(sx, sy, cx + f * 62 + sway, 198 + oy,
                      width=15, fill=WHITE, capstyle=tk.ROUND)
        circle(cx + f * 62 + sway, 198 + oy, 11, fill=WHITE, outline=OUTLINE, width=2)
        circle(sx, sy, 8, fill=WHITE, outline=BLUE, width=3)

        # ---- cuerpo
        c.create_rectangle(cx - 14, 136 + oy, cx + 14, 150 + oy,
                           fill=SHADE, outline="")
        c.create_oval(cx - 50, 140 + oy, cx + 50, 224 + oy,
                      fill=WHITE, outline=OUTLINE, width=2)

        # ---- insignia del pecho: casita blanca con corazón azul
        circle(cx, 182 + oy, 28, fill=BLUE_MED, outline=BLUE_LIGHT, width=3)
        c.create_polygon(cx - 17, 183 + oy, cx, 166 + oy, cx + 17, 183 + oy,
                         fill=WHITE, outline="")
        c.create_rectangle(cx - 13, 183 + oy, cx + 13, 198 + oy,
                           fill=WHITE, outline="")
        hx, hy = cx + 9, 189 + oy
        c.create_polygon(hx - 8.4, hy - 0.5, hx + 8.4, hy - 0.5, hx, hy + 9,
                         fill=BLUE_MED, outline="#ffffff")
        circle(hx - 4, hy - 2, 4.8, fill=BLUE_MED, outline="#ffffff", width=2)
        circle(hx + 4, hy - 2, 4.8, fill=BLUE_MED, outline="#ffffff", width=2)
        c.create_polygon(hx - 7.2, hy + 0.5, hx + 7.2, hy + 0.5, hx, hy + 8,
                         fill=BLUE_MED, outline="")

        # ---- orejas (discos azules a los lados de la cabeza)
        for side in (-1, 1):
            c.create_oval(cx + side * 88, 62 + oy, cx + side * 58, 106 + oy,
                          fill=WHITE, outline=BLUE, width=3)
            c.create_oval(cx + side * 81, 72 + oy, cx + side * 65, 96 + oy,
                          fill=BLUE, outline="")

        # ---- antena
        c.create_line(cx + lean, 34 + oy, cx + lean, 8 + oy,
                      width=4, fill="#b9b9b4")
        circle(cx + lean, 8 + oy, 8, fill=BLUE, outline=BLUE_DARK, width=2)

        # ---- cabeza
        c.create_oval(cx - 70 + lean, 26 + oy, cx + 70 + lean, 140 + oy,
                      fill=WHITE, outline=OUTLINE, width=2)

        # ---- visor (pantalla oscura de la cara)
        c.create_oval(cx - 54 + lean, 44 + oy, cx + 54 + lean, 128 + oy,
                      fill=VISOR, outline="#233042", width=2)

        # ---- cejas
        for side in (-1, 1):
            c.create_arc(cx + side * 40 + lean, 56 + oy,
                         cx + side * 10 + lean, 76 + oy,
                         start=40, extent=100, style=tk.ARC,
                         outline=BLUE_LIGHT, width=4)

        # ---- ojos
        for side in (-1, 1):
            ex, ey = cx + side * 25 + lean, 88 + oy
            if self.blink > 0:
                c.create_line(ex - 12, ey, ex + 12, ey,
                              fill=GLOW, width=4, capstyle=tk.ROUND)
            else:
                circle(ex, ey, 17, fill=EYE, outline=GLOW, width=3)
                circle(ex, ey, 12, fill=EYE, outline="#ffffff", width=2)
                circle(ex - 5, ey - 5, 4.5, fill="#ffffff", outline="")
                circle(ex + 5, ey + 4, 2, fill="#ffffff", outline="")

        # ---- sonrisa
        c.create_arc(cx - 13 + lean, 100 + oy, cx + 13 + lean, 120 + oy,
                     start=200, extent=140, style=tk.ARC,
                     outline=GLOW, width=4)

        # ---- brazo delantero: saluda o cuelga
        sx, sy = cx - f * 44, 158 + oy
        if waving:
            ang = -2.03 + 0.3 * sin(self.wave_phase)
            hx = cx - f * 44 + f * 70 * cos(ang)
            hy = sy + 70 * sin(ang)
        else:
            hx, hy = cx - f * 62 - sway, 198 + oy
        c.create_line(sx, sy, hx, hy, width=15, fill=WHITE, capstyle=tk.ROUND)
        circle(hx, hy, 12, fill=WHITE, outline=OUTLINE, width=2)
        circle(sx, sy, 8, fill=WHITE, outline=BLUE, width=3)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CyberPet().run()
