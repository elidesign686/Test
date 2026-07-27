"""CyberPet — mascota de escritorio animada.

Un robotito blanco y azul (estilo kawaii, acabado de plástico brillante)
que pasea por TODA la pantalla: camina hacia puntos aleatorios, rebota al
andar, parpadea, se balancea y de vez en cuando saluda con la mano.

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
from math import atan2, cos, pi, sin

# Color "llave" que Windows vuelve transparente
TRANSPARENT = "#ff00fe"

# Paleta (fiel a la imagen de referencia: plástico blanco glossy + azul)
SHELL_D = "#e3e3df"     # carcasa: tono base sombreado
SHELL_M = "#efefec"     # carcasa: tono medio
SHELL_L = "#fbfbf9"     # carcasa: brillo
SHADE = "#dcdcd8"       # cuello / sombras
OUTLINE = "#c9c9c4"     # contorno suave de la carcasa
BLUE = "#2f7fd6"        # azul principal
BLUE_MED = "#3f8fe0"    # insignia del pecho
BLUE_DARK = "#1f5fae"
BLUE_GLOSS = "#8fc6f2"  # cejas / brillos azules
GLOW = "#a5dcff"        # brillo de ojos y sonrisa
VISOR_D = "#0a0f18"     # pantalla de la cara (base)
VISOR_M = "#141e2e"     # pantalla: banda superior con reflejo
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

        def shell_oval(x1, y1, x2, y2):
            """Óvalo con capas de luz: efecto de plástico blanco glossy."""
            ow, oh = x2 - x1, y2 - y1
            c.create_oval(x1, y1, x2, y2, fill=SHELL_D, outline=OUTLINE, width=2)
            c.create_oval(x1 + ow * 0.05, y1 + oh * 0.04,
                          x2 - ow * 0.10, y2 - oh * 0.16, fill=SHELL_M, outline="")
            c.create_oval(x1 + ow * 0.12, y1 + oh * 0.08,
                          x2 - ow * 0.24, y2 - oh * 0.38, fill=SHELL_L, outline="")

        def limb(x1, y1, x2, y2, thick=13):
            """Cápsula con contorno (doble línea) para brazos y dedos."""
            c.create_line(x1, y1, x2, y2, width=thick + 4, fill=OUTLINE,
                          capstyle=tk.ROUND)
            c.create_line(x1, y1, x2, y2, width=thick, fill=SHELL_M,
                          capstyle=tk.ROUND)

        # ---- pies (se quedan "en el suelo" y alternan al caminar)
        lf = -abs(sin(self.walk_phase)) * 5 if walking else 0.0
        rf = -abs(sin(self.walk_phase + pi)) * 5 if walking else 0.0
        shell_oval(cx - 40, 212 + lf, cx - 6, 236 + lf)
        shell_oval(cx + 6, 212 + rf, cx + 40, 236 + rf)

        # ---- brazo trasero (cuelga; se balancea al caminar)
        sway = sin(self.walk_phase) * 5 if walking else 0.0
        bx, by = cx + f * 44, 158 + oy
        bhx, bhy = cx + f * 62 + sway, 198 + oy
        limb(bx, by, bhx, bhy)
        circle(bhx, bhy, 11, fill=SHELL_L, outline=OUTLINE, width=2)
        circle(bx, by, 8, fill=SHELL_L, outline=BLUE, width=3)

        # ---- cuello y cuerpo
        c.create_oval(cx - 16, 132 + oy, cx + 16, 148 + oy, fill="#c4c4bf", outline="")
        c.create_oval(cx - 13, 136 + oy, cx + 13, 150 + oy, fill=SHADE, outline="")
        shell_oval(cx - 50, 140 + oy, cx + 50, 224 + oy)

        # ---- insignia del pecho: halo, disco azul, casita blanca y corazón
        circle(cx, 182 + oy, 31, fill="#e6f2fc", outline="#cfe3f4", width=2)
        circle(cx, 182 + oy, 26, fill=BLUE_MED, outline="")
        c.create_oval(cx - 21, 160 + oy, cx + 21, 184 + oy, fill="#56a0e6", outline="")
        c.create_polygon(cx - 17, 183 + oy, cx, 166 + oy, cx + 17, 183 + oy,
                         fill=SHELL_L, outline="")
        c.create_rectangle(cx - 13, 183 + oy, cx + 13, 198 + oy,
                           fill=SHELL_L, outline="")
        hx, hy = cx + 9, 189 + oy
        c.create_polygon(hx - 8.4, hy - 0.5, hx + 8.4, hy - 0.5, hx, hy + 9,
                         fill=BLUE_MED, outline="#ffffff")
        circle(hx - 4, hy - 2, 4.8, fill=BLUE_MED, outline="#ffffff", width=2)
        circle(hx + 4, hy - 2, 4.8, fill=BLUE_MED, outline="#ffffff", width=2)
        c.create_polygon(hx - 7.2, hy + 0.5, hx + 7.2, hy + 0.5, hx, hy + 8,
                         fill=BLUE_MED, outline="")

        # ---- orejas (discos azules con profundidad)
        for side in (-1, 1):
            c.create_oval(cx + side * 88, 62 + oy, cx + side * 58, 106 + oy,
                          fill=SHELL_M, outline=OUTLINE, width=2)
            c.create_oval(cx + side * 82, 70 + oy, cx + side * 64, 98 + oy,
                          fill=BLUE_MED, outline=BLUE_DARK, width=2)
            c.create_oval(cx + side * 77, 77 + oy, cx + side * 69, 91 + oy,
                          fill=BLUE_DARK, outline="")

        # ---- antena con bolita brillante
        c.create_line(cx + lean, 34 + oy, cx + lean, 8 + oy,
                      width=4, fill="#b0b0ab")
        circle(cx + lean, 8 + oy, 8, fill=BLUE, outline=BLUE_DARK, width=2)
        circle(cx + lean - 3, 5 + oy, 2.5, fill="#bfe2ff", outline="")

        # ---- cabeza con brillo en el borde superior
        shell_oval(cx - 70 + lean, 26 + oy, cx + 70 + lean, 140 + oy)
        c.create_arc(cx - 60 + lean, 32 + oy, cx + 60 + lean, 130 + oy,
                     start=55, extent=55, style=tk.ARC,
                     outline="#ffffff", width=3)

        # ---- visor (pantalla oscura con reflejo)
        vx1, vy1 = cx - 54 + lean, 44 + oy
        vx2, vy2 = cx + 54 + lean, 128 + oy
        c.create_oval(vx1, vy1, vx2, vy2, fill=VISOR_D, outline="#22303f", width=2)
        c.create_oval(vx1 + 10, vy1 + 5, vx2 - 10, vy1 + 40,
                      fill=VISOR_M, outline="")
        c.create_arc(vx1 + 12, vy1 + 8, vx2 - 12, vy2 - 26, start=45, extent=80,
                     style=tk.ARC, outline="#3e556f", width=3)

        # ---- cejas
        for side in (-1, 1):
            c.create_arc(cx + side * 40 + lean, 56 + oy,
                         cx + side * 10 + lean, 76 + oy,
                         start=40, extent=100, style=tk.ARC,
                         outline=BLUE_GLOSS, width=5)

        # ---- ojos (pupila glossy con aro luminoso y destellos)
        for side in (-1, 1):
            ex, ey = cx + side * 25 + lean, 88 + oy
            if self.blink > 0:
                c.create_line(ex - 12, ey, ex + 12, ey,
                              fill=GLOW, width=4, capstyle=tk.ROUND)
            else:
                circle(ex, ey, 18, fill=EYE, outline="#5d9fd8", width=2)
                circle(ex, ey, 15, fill=EYE, outline="#cfeaff", width=2)
                c.create_arc(ex - 11, ey - 11, ex + 11, ey + 11,
                             start=215, extent=110, style=tk.ARC,
                             outline="#2f6fb4", width=3)
                circle(ex - 6, ey - 6, 5, fill="#ffffff", outline="")
                circle(ex + 5, ey + 4, 2.4, fill="#ffffff", outline="")

        # ---- sonrisa
        c.create_arc(cx - 13 + lean, 100 + oy, cx + 13 + lean, 120 + oy,
                     start=200, extent=140, style=tk.ARC,
                     outline=GLOW, width=4)

        # ---- brazo delantero: saluda (con dedos abiertos) o cuelga
        sx, sy = cx - f * 44, 158 + oy
        if waving:
            ang = -2.03 + 0.3 * sin(self.wave_phase)
            hax = sx + f * 70 * cos(ang)
            hay = sy + 70 * sin(ang)
        else:
            hax, hay = cx - f * 62 - sway, 198 + oy
        limb(sx, sy, hax, hay)
        if waving:
            base_a = atan2(hay - sy, hax - sx)
            for da in (-0.5, 0.0, 0.5):
                a2 = base_a + da
                limb(hax + 5 * cos(a2), hay + 5 * sin(a2),
                     hax + 20 * cos(a2), hay + 20 * sin(a2), thick=6)
        circle(hax, hay, 11, fill=SHELL_L, outline=OUTLINE, width=2)
        circle(sx, sy, 8, fill=SHELL_L, outline=BLUE, width=3)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CyberPet().run()
