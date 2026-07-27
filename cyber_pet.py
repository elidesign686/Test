"""CyberPet — mascota de escritorio animada.

Un robotito blanco y azul (estilo cartoon kawaii, contornos definidos)
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

# Paleta (fiel a la imagen de referencia: cartoon blanco/azul con contorno)
OUT = "#23262b"         # contorno oscuro estilo cartoon
INK = "#0b0d10"         # negro del visor y pupilas
W_SHELL = "#fdfdfd"     # blanco de la carcasa
W_SHADE = "#e8ecef"     # sombra suave
BLUE = "#3d85d8"        # azul principal
BLUE_DARK = "#1f5fae"
BLUE_SOFT = "#66aef0"
BLUE_PALE = "#cfe8fc"   # halo de la insignia
GLOW_HEART = "#8fd0ff"  # corazón luminoso
SILVER = "#c9ced4"      # antena / metal

W, H = 224, 258
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
        oy = 8 - bounce + bob
        lean = f * 4 if walking else 0  # la cabeza se adelanta al caminar

        def circle(x, y, r, **kw):
            c.create_oval(x - r, y - r, x + r, y + r, **kw)

        def round_rect(x1, y1, x2, y2, r, **kw):
            pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                   x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                   x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
            c.create_polygon(pts, smooth=True, **kw)

        def limb(x1, y1, x2, y2, thick=12):
            """Cápsula blanca con contorno oscuro (doble línea)."""
            c.create_line(x1, y1, x2, y2, width=thick + 5, fill=OUT,
                          capstyle=tk.ROUND)
            c.create_line(x1, y1, x2, y2, width=thick, fill=W_SHELL,
                          capstyle=tk.ROUND)

        def band(x1, y1, x2, y2, frac, half=9):
            """Anillo azul cruzado sobre un brazo (a la altura frac)."""
            px, py = x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac
            dx, dy = x2 - x1, y2 - y1
            length = (dx * dx + dy * dy) ** 0.5 or 1.0
            nx, ny = -dy / length, dx / length
            c.create_line(px - nx * half, py - ny * half,
                          px + nx * half, py + ny * half,
                          width=5, fill=BLUE, capstyle=tk.ROUND)

        # ---- piernas y botas (alternan al caminar)
        lf = -abs(sin(self.walk_phase)) * 5 if walking else 0.0
        rf = -abs(sin(self.walk_phase + pi)) * 5 if walking else 0.0
        round_rect(cx - 34, 214 + oy, cx - 10, 240 + oy, 10,
                   fill=W_SHELL, outline=OUT, width=3)
        round_rect(cx + 10, 214 + oy, cx + 34, 240 + oy, 10,
                   fill=W_SHELL, outline=OUT, width=3)
        for bx1, bx2, step in ((cx - 44, cx - 2, lf), (cx + 2, cx + 44, rf)):
            c.create_oval(bx1, 228 + step, bx2, 254 + step,
                          fill=W_SHELL, outline=OUT, width=3)
            bw = bx2 - bx1
            c.create_arc(bx1 - bw * 0.45, 230 + step, bx1 + bw * 0.55,
                         252 + step, start=-62, extent=124, style=tk.ARC,
                         outline=OUT, width=2)

        # ---- brazo trasero (cuelga con puño cerrado; se balancea al andar)
        sway = sin(self.walk_phase) * 5 if walking else 0.0
        bx, by = cx + f * 44, 176 + oy
        bhx, bhy = cx + f * 60 + sway, 214 + oy
        limb(bx, by, bhx, bhy)
        band(bx, by, bhx, bhy, 0.72)
        circle(bhx, bhy, 11, fill=W_SHELL, outline=OUT, width=3)
        c.create_arc(bhx - 7, bhy - 8, bhx + 7, bhy + 2, start=200,
                     extent=140, style=tk.ARC, outline=OUT, width=2)

        # ---- cuerpo
        c.create_oval(cx - 48, 162 + oy, cx + 48, 236 + oy,
                      fill=W_SHELL, outline=OUT, width=3)
        c.create_arc(cx - 44, 168 + oy, cx + 44, 232 + oy, start=205,
                     extent=90, style=tk.ARC, outline=W_SHADE, width=6)

        # ---- insignia del pecho: aro azul luminoso, casita y corazón
        circle(cx, 199 + oy, 28, fill=BLUE_PALE, outline="")
        circle(cx, 199 + oy, 24, fill="#4d9df0", outline="#2c6cbe", width=3)
        circle(cx, 199 + oy, 19, fill="#7fc0f4", outline="")
        circle(cx, 199 + oy, 14, fill="#a5d4fa", outline="")
        c.create_polygon(cx - 15, 200 + oy, cx, 185 + oy, cx + 15, 200 + oy,
                         fill="#ffffff", outline="")
        c.create_rectangle(cx - 11, 200 + oy, cx + 11, 213 + oy,
                           fill="#ffffff", outline="")
        hx, hy = cx + 8, 203 + oy
        heart = [(0, 9), (0, 9), (-8, 2), (-10.5, -3), (-7, -8), (-2.5, -6.5),
                 (0, -3.5), (0, -3.5), (2.5, -6.5), (7, -8), (10.5, -3), (8, 2)]
        c.create_polygon([(hx + px, hy + py) for px, py in heart],
                         smooth=True, fill=GLOW_HEART,
                         outline="#ffffff", width=2)

        # ---- cuello
        round_rect(cx - 20, 152 + oy, cx + 20, 166 + oy, 7,
                   fill=W_SHELL, outline=OUT, width=3)

        # ---- orejas (cápsulas laterales con disco azul)
        for side in (-1, 1):
            c.create_oval(cx + side * 88, 70 + oy, cx + side * 58, 116 + oy,
                          fill=W_SHELL, outline=OUT, width=3)
            c.create_oval(cx + side * 81, 78 + oy, cx + side * 64, 108 + oy,
                          fill=BLUE, outline=BLUE_DARK, width=2)

        # ---- antena
        c.create_line(cx + lean, 20 + oy, cx + lean, 36 + oy,
                      width=5, fill=SILVER)
        circle(cx + lean, 12 + oy, 9, fill=BLUE, outline=OUT, width=2)
        circle(cx + lean - 3, 9 + oy, 2.6, fill=BLUE_SOFT, outline="")

        # ---- cabeza (casco)
        c.create_oval(cx - 68 + lean, 30 + oy, cx + 68 + lean, 150 + oy,
                      fill=W_SHELL, outline=OUT, width=3)

        # ---- visor: marco azul, pantalla negra y destello
        round_rect(cx - 58 + lean, 52 + oy, cx + 58 + lean, 136 + oy, 30,
                   fill=BLUE, outline=OUT, width=3)
        round_rect(cx - 54 + lean, 56 + oy, cx + 54 + lean, 132 + oy, 26,
                   fill=INK, outline="")
        c.create_arc(cx - 50 + lean, 58 + oy, cx + 50 + lean, 118 + oy,
                     start=32, extent=36, style=tk.ARC,
                     outline="#ffffff", width=5)

        # ---- cejas
        for side in (-1, 1):
            c.create_arc(cx + side * 38 + lean, 66 + oy,
                         cx + side * 12 + lean, 84 + oy,
                         start=45, extent=90, style=tk.ARC,
                         outline=BLUE, width=5)

        # ---- ojos (blancos con pupila negra y destellos)
        for side in (-1, 1):
            ex, ey = cx + side * 26 + lean, 98 + oy
            if self.blink > 0:
                c.create_line(ex - 12, ey, ex + 12, ey,
                              fill="#ffffff", width=5, capstyle=tk.ROUND)
            else:
                circle(ex, ey, 15, fill="#ffffff", outline="")
                circle(ex, ey, 10, fill=INK, outline="")
                circle(ex - 3.5, ey - 3.5, 3.4, fill="#ffffff", outline="")
                circle(ex + 3, ey + 3, 1.7, fill="#ffffff", outline="")

        # ---- boca (sonrisa abierta)
        c.create_arc(cx - 10 + lean, 108 + oy, cx + 10 + lean, 126 + oy,
                     start=180, extent=180, style=tk.CHORD,
                     fill="#ffffff", outline="")

        # ---- brazo delantero: saluda (guante con dedos) o cuelga
        sx, sy = cx - f * 44, 176 + oy
        if waving:
            ang = -2.12 + 0.3 * sin(self.wave_phase)
            hax = sx + f * 80 * cos(ang)
            hay = sy + 80 * sin(ang)
        else:
            hax, hay = cx - f * 60 - sway, 214 + oy
        limb(sx, sy, hax, hay)
        band(sx, sy, hax, hay, 0.72)
        if waving:
            base_a = atan2(hay - sy, hax - sx)
            for da in (-0.55, -0.18, 0.18, 0.55):
                a2 = base_a + da
                limb(hax + 5 * cos(a2), hay + 5 * sin(a2),
                     hax + 26 * cos(a2), hay + 26 * sin(a2), thick=7)
            a2 = base_a + 1.05
            limb(hax + 4 * cos(a2), hay + 4 * sin(a2),
                 hax + 17 * cos(a2), hay + 17 * sin(a2), thick=7)
            circle(hax, hay, 13, fill=W_SHELL, outline=OUT, width=3)
        else:
            circle(hax, hay, 11, fill=W_SHELL, outline=OUT, width=3)
            c.create_arc(hax - 7, hay - 8, hax + 7, hay + 2, start=200,
                         extent=140, style=tk.ARC, outline=OUT, width=2)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CyberPet().run()
