"""Escenario: el lienzo animado donde la persona ve y toca las opciones del árbol.

Vista «opciones»: el tema actual es un orbe en el centro y sus hijos giran a su alrededor como
tarjetas conectadas por ramas con pulsos de luz. Al elegir una, vuela al centro y aparecen sus hijos.
Vista «ficha»: al llegar a un tema final se muestran qué es, un ejemplo y consejos (texto del árbol).
"""
import math
import random
import time
import tkinter as tk
from tkinter import font as tkfont
from types import SimpleNamespace

from componentes import rect_redondo
from estilos import BORDE, FONDO, PANEL, TARJETA, TENUE, TEXTO, color_de_nodo, mezclar

ANCHO_TARJETA, ALTO_TARJETA = 200, 68


# --- Curvas de animación ---------------------------------------------------------
def suave(t):
    return 1 - (1 - t) ** 3


def rebote(t):
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def lineal(t):
    return t


class Escenario(tk.Canvas):
    def __init__(self, master, al_elegir, al_pasar=lambda nodo: None):
        super().__init__(master, bg=FONDO, highlightthickness=0)
        self.al_elegir, self.al_pasar = al_elegir, al_pasar
        self.modo = "opciones"
        self.orbe = SimpleNamespace(nodo=None, color=TENUE, x=0, y=0, r=0, a=0)
        self.tarjetas, self.paneles, self.chips = [], [], []
        self.pensando = SimpleNamespace(v=0.0)
        self._pensar_objetivo = 0.0
        self.leyenda = ""
        self._hover = None
        self._tweens, self._pendientes = [], []
        self._t0 = time.perf_counter()
        self._estrellas = [(random.random(), random.random(), random.choice((1, 1, 1.5, 2)),
                            random.random() * 6.28) for _ in range(70)]
        self.f_nombre = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.f_chico = tkfont.Font(family="Segoe UI", size=8)
        self.f_orbe = tkfont.Font(family="Georgia", size=13, weight="bold")
        self.f_texto = tkfont.Font(family="Segoe UI", size=10)
        self.f_texto_b = tkfont.Font(family="Segoe UI", size=8, weight="bold")
        self.bind("<Configure>", self._al_cambiar_tamano)
        self.bind("<Motion>", self._al_mover)
        self.bind("<Leave>", lambda e: self._poner_hover(None))
        self.bind("<Button-1>", self._al_clic)
        self._tick()

    # ==================================================================
    # Animación (tweens + bucle de dibujo)
    # ==================================================================
    def _animar(self, obj, atributo, hasta, dur=0.4, curva=suave, demora=0.0):
        self._tweens = [t for t in self._tweens if not (t.obj is obj and t.atributo == atributo)]
        self._tweens.append(SimpleNamespace(obj=obj, atributo=atributo, desde=getattr(obj, atributo),
                                            hasta=hasta, t0=time.perf_counter() + demora, dur=dur, curva=curva))

    def _despues(self, segundos, funcion):
        self._pendientes.append((time.perf_counter() + segundos, funcion))

    def _fijar(self, obj, **valores):
        """Pone valores al instante y cancela animaciones pendientes de ese objeto."""
        self._tweens = [t for t in self._tweens if t.obj is not obj]
        for k, v in valores.items():
            setattr(obj, k, v)

    def _tick(self):
        ahora = time.perf_counter()
        vivos = []
        for tw in self._tweens:
            if ahora < tw.t0:
                vivos.append(tw)
                continue
            p = min(1.0, (ahora - tw.t0) / tw.dur)
            setattr(tw.obj, tw.atributo, tw.desde + (tw.hasta - tw.desde) * tw.curva(p))
            if p < 1.0:
                vivos.append(tw)
        self._tweens = vivos
        pendientes, self._pendientes = self._pendientes, []
        for cuando, funcion in pendientes:
            if ahora >= cuando:
                funcion()
            else:
                self._pendientes.append((cuando, funcion))
        for t in self.tarjetas + self.chips:      # el resalte al pasar el mouse se suaviza solo
            objetivo = 1.0 if t is self._hover else 0.0
            t.h += (objetivo - t.h) * 0.25
        self.pensando.v += (self._pensar_objetivo - self.pensando.v) * 0.12
        try:
            self._dibujar(ahora - self._t0)
        finally:
            self.after(16, self._tick)

    # ==================================================================
    # API pública
    # ==================================================================
    def pensar(self, activo):
        """Activa o desactiva la animación de «la IA está pensando»."""
        self._pensar_objetivo = 1.0 if activo else 0.0

    def poner_leyenda(self, texto):
        self.leyenda = texto

    def mostrar(self, nodo, opciones, elegido=None, hacia_arriba=False):
        """Muestra un nodo con sus opciones. Anima la salida de lo anterior y la entrada de lo nuevo."""
        self._poner_hover(None)
        salida = self._animar_salida(elegido, hacia_arriba)
        self._despues(salida, lambda: self._construir(nodo, opciones))

    def _animar_salida(self, elegido, hacia_arriba):
        cx, cy = self._centro()
        hay_algo = bool(self.tarjetas or self.paneles or self.orbe.nodo)
        if not hay_algo:
            return 0.0
        for t in self.tarjetas + self.chips:
            if t.nodo is elegido:
                self._animar(t, "x", cx, 0.34)
                self._animar(t, "y", cy, 0.34)
                self._animar(t, "s", 0.45, 0.34)
            else:
                self._animar(t, "x", cx + (t.x - cx) * 0.3, 0.3)
                self._animar(t, "y", cy + (t.y - cy) * 0.3, 0.3)
                self._animar(t, "s", 0.5, 0.3)
            self._animar(t, "a", 0.0, 0.3)
        for p in self.paneles:
            self._animar(p, "a", 0.0, 0.25)
        self._animar(self.orbe, "a", 0.0, 0.28)
        return 0.34

    def _construir(self, nodo, opciones):
        self.tarjetas, self.paneles, self.chips = [], [], []
        color = color_de_nodo(nodo)
        cx, cy = self._centro()
        self.orbe = SimpleNamespace(nodo=nodo, color=color, x=cx, y=cy, r=30, a=0.0)
        if nodo.hijos:
            self.modo = "opciones"
            self._animar(self.orbe, "a", 1.0, 0.3)
            self._animar(self.orbe, "r", 62, 0.5, rebote)
            for i, hijo in enumerate(opciones):
                t = self._nueva_tarjeta(hijo, i + 1, cx, cy)
                self.tarjetas.append(t)
            self._colocar_tarjetas(animar=True)
        else:
            self.modo = "ficha"
            self._animar(self.orbe, "a", 1.0, 0.3)
            self._animar(self.orbe, "r", 40, 0.5, rebote)
            self._animar(self.orbe, "y", 78, 0.55, suave)
            self.chips = [self._nueva_tarjeta(h, i + 1, cx, cy) for i, h in enumerate(opciones)]
            self._colocar_ficha(animar=True)

    @staticmethod
    def _nueva_tarjeta(nodo, indice, x, y):
        return SimpleNamespace(nodo=nodo, indice=indice, color=color_de_nodo(nodo), x=x, y=y,
                               s=0.4, a=0.0, h=0.0, tx=x, ty=y, w=ANCHO_TARJETA, alto=ALTO_TARJETA)

    # ==================================================================
    # Posiciones
    # ==================================================================
    def _centro(self):
        ancho, alto = max(self.winfo_width(), 700), max(self.winfo_height(), 520)
        return ancho / 2, alto / 2 - 14

    def _colocar_tarjetas(self, animar):
        n = len(self.tarjetas)
        if not n:
            return
        cx, cy = self._centro()
        ancho, alto = max(self.winfo_width(), 700), max(self.winfo_height(), 520)
        rx = min(ancho / 2 - ANCHO_TARJETA / 2 - 24, 300)
        ry = min(alto / 2 - ALTO_TARJETA / 2 - 56, 210)
        inicio = -90 if n % 2 else -90 - 180 / n
        for i, t in enumerate(self.tarjetas):
            ang = math.radians(inicio + 360 * i / n)
            t.tx, t.ty = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
            if animar:
                self._animar(t, "x", t.tx, 0.6, rebote, 0.12 + i * 0.07)
                self._animar(t, "y", t.ty, 0.6, rebote, 0.12 + i * 0.07)
                self._animar(t, "s", 1.0, 0.5, rebote, 0.12 + i * 0.07)
                self._animar(t, "a", 1.0, 0.35, suave, 0.12 + i * 0.07)
            else:
                self._fijar(t, x=t.tx, y=t.ty, s=1.0, a=1.0)

    def _envolver(self, texto, fuente, ancho):
        lineas = []
        for parrafo in texto.split("\n"):
            actual = ""
            for palabra in parrafo.split():
                prueba = f"{actual} {palabra}".strip()
                if fuente.measure(prueba) <= ancho or not actual:
                    actual = prueba
                else:
                    lineas.append(actual)
                    actual = palabra
            lineas.append(actual)
        return lineas

    def _colocar_ficha(self, animar):
        nodo = self.orbe.nodo
        ancho = max(self.winfo_width(), 700)
        margen, hueco = 34, 16
        ancho_total = ancho - 2 * margen
        ancho_col = (ancho_total - hueco) / 2
        interlinea = self.f_texto.metrics("linespace") + 3
        y = 140

        def panel(titulo, lineas, x, y, w, color):
            alto = 36 + len(lineas) * interlinea + 12
            return SimpleNamespace(titulo=titulo, lineas=lineas, x=x, y=y, w=w, alto=alto, color=color, a=0.0, dy=18)

        color = self.orbe.color
        que_es = panel("QUÉ ES", self._envolver(nodo.descripcion, self.f_texto, ancho_total - 32), margen, y,
                       ancho_total, color)
        y += que_es.alto + hueco
        ejemplo = panel("EJEMPLO", self._envolver(nodo.ejemplo, self.f_texto, ancho_col - 32), margen, y, ancho_col,
                        mezclar(color, "#FFFFFF", 0.25))
        consejos_texto = "\n".join(f"• {c}" for c in nodo.consejos)
        consejos = panel("CONSEJOS", self._envolver(consejos_texto, self.f_texto, ancho_col - 32),
                         margen + ancho_col + hueco, y, ancho_col, color)
        alto_fila = max(ejemplo.alto, consejos.alto)
        ejemplo.alto = consejos.alto = alto_fila
        self.paneles = [que_es, ejemplo, consejos]
        self._fila_chips = y + alto_fila + 22
        for i, p in enumerate(self.paneles):
            if animar:
                self._animar(p, "a", 1.0, 0.45, suave, 0.25 + i * 0.12)
                self._animar(p, "dy", 0.0, 0.5, suave, 0.25 + i * 0.12)
            else:
                self._fijar(p, a=1.0, dy=0.0)
        for i, c in enumerate(self.chips):
            c.w, c.alto = 190, 40
            c.tx = margen + 100 + i * (c.w + 14)
            c.ty = self._fila_chips + 40
            if animar:
                self._animar(c, "x", c.tx, 0.5, suave, 0.7 + i * 0.08)
                self._animar(c, "y", c.ty, 0.5, suave, 0.7 + i * 0.08)
                self._animar(c, "s", 1.0, 0.4, suave, 0.7 + i * 0.08)
                self._animar(c, "a", 1.0, 0.4, suave, 0.7 + i * 0.08)
            else:
                self._fijar(c, x=c.tx, y=c.ty, s=1.0, a=1.0)

    def _al_cambiar_tamano(self, _evento):
        if self.orbe.nodo is None:
            return
        cx, cy = self._centro()
        if self.modo == "opciones":
            self._fijar(self.orbe, x=cx, y=cy)
            self._colocar_tarjetas(animar=False)
        else:
            self._fijar(self.orbe, x=cx, y=78)
            self._colocar_ficha(animar=False)

    # ==================================================================
    # Ratón
    # ==================================================================
    def _tarjeta_en(self, x, y):
        for t in reversed(self.tarjetas + self.chips):
            if t.a < 0.6:
                continue
            if abs(x - t.x) <= t.w * t.s / 2 and abs(y - t.y) <= t.alto * t.s / 2:
                return t
        return None

    def _al_mover(self, evento):
        self._poner_hover(self._tarjeta_en(evento.x, evento.y))

    def _poner_hover(self, tarjeta):
        if tarjeta is self._hover:
            return
        self._hover = tarjeta
        self.config(cursor="hand2" if tarjeta else "")
        self.al_pasar(tarjeta.nodo if tarjeta else None)

    def _al_clic(self, evento):
        tarjeta = self._tarjeta_en(evento.x, evento.y)
        if tarjeta:
            self.al_elegir(tarjeta.nodo)

    # ==================================================================
    # Dibujo
    # ==================================================================
    def _dibujar(self, t):
        self.delete("all")
        ancho, alto = self.winfo_width(), self.winfo_height()
        if ancho < 50:
            return
        self._fondo(ancho, alto, t)
        if self.orbe.nodo is None:
            return
        self._resplandor()
        if self.modo == "opciones":
            self._ramas(t)
        self._orbe(t)
        for tarjeta in self.tarjetas:
            self._tarjeta(tarjeta)
        for panel in self.paneles:
            self._panel(panel)
        if self.chips:
            self.create_text(34, self._fila_chips + 4, text="OTROS TEMAS CERCANOS  ·  toca uno para ir allí",
                             anchor="w", fill=TENUE, font=self.f_texto_b)
        for chip in self.chips:
            self._tarjeta(chip, chip=True)
        self._titulo_escena()
        self._leyenda(ancho, alto)

    def _titulo_escena(self):
        """Rótulo fijo arriba: explica qué se está viendo en el escenario."""
        o = self.orbe
        if o.nodo is None:
            return
        if self.modo == "opciones":
            texto = f"OPCIONES DESDE «{o.nodo.valor.upper()}»  ·  toca una tarjeta o escríbele a la IA"
        else:
            texto = "FICHA DEL TEMA  ·  el concepto que necesitas antes de practicar"
        self.create_text(22, 20, text=texto, anchor="w", fill=TENUE, font=self.f_texto_b)

    def _fondo(self, ancho, alto, t):
        for fx, fy, r, fase in self._estrellas:
            brillo = 0.55 + 0.45 * math.sin(t * 0.9 + fase)
            color = mezclar("#3C5A4C", FONDO, 1 - brillo * 0.7)
            x, y = fx * ancho, (fy * alto + t * 2.5 * r) % alto
            self.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")

    def _ramas(self, t):
        o = self.orbe
        for i, c in enumerate(self.tarjetas):
            if c.a < 0.03:
                continue
            mx, my = (o.x + c.x) / 2, (o.y + c.y) / 2
            # La curva se arquea un poco hacia afuera para que parezca una rama.
            dx, dy = c.x - o.x, c.y - o.y
            largo = math.hypot(dx, dy) or 1
            qx, qy = mx - dy / largo * 26, my + dx / largo * 26
            color = mezclar(c.color, FONDO, 0.38 - 0.2 * c.h + (1 - c.a) * 0.6)
            self.create_line(o.x, o.y, qx, qy, c.x, c.y, smooth=True, fill=color, width=2 + c.h * 1.5)
            velocidad = 0.22 + 0.5 * self.pensando.v
            for k in range(2):
                p = (t * velocidad + i * 0.17 + k * 0.5) % 1.0
                bx = (1 - p) ** 2 * o.x + 2 * (1 - p) * p * qx + p * p * c.x
                by = (1 - p) ** 2 * o.y + 2 * (1 - p) * p * qy + p * p * c.y
                self.create_oval(bx - 3, by - 3, bx + 3, by + 3, outline="",
                                 fill=mezclar(c.color, "#FFFFFF", 0.3 + 0.0 * k) if c.a > 0.5 else FONDO)

    def _resplandor(self):
        o = self.orbe
        if o.a < 0.02:
            return
        for k in range(7, 0, -1):          # círculos concéntricos cada vez más tenues
            rr = o.r + k * 7
            self.create_oval(o.x - rr, o.y - rr, o.x + rr, o.y + rr, outline="",
                             fill=mezclar(o.color, FONDO, 0.90 + 0.015 * k + (1 - o.a) * 0.1))

    def _orbe(self, t):
        o = self.orbe
        if o.a < 0.02:
            return
        r = o.r * (1 + 0.025 * math.sin(t * 2.0))
        self.create_oval(o.x - r, o.y - r, o.x + r, o.y + r, fill=mezclar(o.color, PANEL, 0.82),
                         outline=mezclar(o.color, FONDO, 1 - o.a), width=2.5)
        if self.pensando.v > 0.03:
            giro = (t * 260) % 360
            v = self.pensando.v
            self.create_arc(o.x - r - 9, o.y - r - 9, o.x + r + 9, o.y + r + 9, start=giro, extent=80,
                            style="arc", outline=mezclar(o.color, FONDO, 1 - v), width=3)
            self.create_arc(o.x - r - 9, o.y - r - 9, o.x + r + 9, o.y + r + 9, start=giro + 180, extent=50,
                            style="arc", outline=mezclar(o.color, FONDO, 1 - v * 0.7), width=3)
            for k in range(2):
                p = ((t * 0.9) + k * 0.5) % 1.0
                rr = r + 10 + p * 46
                self.create_oval(o.x - rr, o.y - rr, o.x + rr, o.y + rr, outline=mezclar(o.color, FONDO, 1 - v * (1 - p) * 0.8))
        color_texto = mezclar(TEXTO, FONDO, 1 - o.a)
        if self.modo == "opciones":
            ancho = o.r * 1.55
            lineas = self._envolver(o.nodo.valor, self.f_orbe, ancho)
            h = self.f_orbe.metrics("linespace")
            y0 = o.y - (len(lineas) * h) / 2 - 6
            for i, linea in enumerate(lineas):
                self.create_text(o.x, y0 + i * h + h / 2, text=linea, fill=color_texto, font=self.f_orbe)
            self.create_text(o.x, o.y + (len(lineas) * h) / 2 + 2, text="ESTÁS AQUÍ", fill=mezclar(o.color, FONDO, 1 - o.a),
                             font=self.f_texto_b)
        else:
            self.create_text(o.x + o.r + 22, o.y - 12, text=o.nodo.valor, anchor="w", fill=color_texto,
                             font=("Georgia", 22, "bold"))
            ruta = "  ›  ".join(n.valor for n in o.nodo.camino_nodos()[:-1])
            self.create_text(o.x + o.r + 22, o.y + 20, text=ruta, anchor="w", fill=mezclar(TENUE, FONDO, 1 - o.a),
                             font=self.f_texto)
            self.create_text(o.x, o.y, text="✓", fill=mezclar(o.color, FONDO, 1 - o.a), font=("Segoe UI", 22, "bold"))

    def _tarjeta(self, c, chip=False):
        if c.a < 0.03:
            return
        w, h = c.w * c.s * (1 + 0.04 * c.h), c.alto * c.s * (1 + 0.04 * c.h)
        x1, y1, x2, y2 = c.x - w / 2, c.y - h / 2, c.x + w / 2, c.y + h / 2
        vis = c.a
        base = mezclar(c.color, PANEL, 0.88 - 0.1 * c.h)
        if c.h > 0.05:                      # halo al pasar el mouse
            rect_redondo(self, x1 - 5, y1 - 5, x2 + 5, y2 + 5, r=18,
                         fill=mezclar(mezclar(c.color, FONDO, 0.82 - 0.1 * c.h), FONDO, 1 - vis), outline="")
        rect_redondo(self, x1, y1, x2, y2, r=14, fill=mezclar(base, FONDO, 1 - vis),
                     outline=mezclar(mezclar(c.color, FONDO, 0.5 - 0.4 * c.h), FONDO, 1 - vis), width=1.6)
        if c.s < 0.7:
            return
        color_borde = mezclar(c.color, FONDO, 1 - vis)
        self.create_oval(x1 + 8, y1 + 8, x1 + 28, y1 + 28, fill=color_borde, outline="")
        self.create_text(x1 + 18, y1 + 18, text=str(c.indice), fill=FONDO, font=self.f_texto_b)
        nodo = c.nodo
        if chip:
            self.create_text(x1 + 38, c.y, text=nodo.valor, anchor="w", fill=mezclar(TEXTO, FONDO, 1 - vis),
                             font=("Segoe UI", 9, "bold"), width=w - 50)
            return
        subtitulo = f"{len(nodo.hijos)} subtemas" if nodo.hijos else "tema final" + (" · calculadora" if nodo.herramienta else "")
        self.create_text(x1 + 38, c.y - 9, text=nodo.valor, anchor="w", fill=mezclar(TEXTO, FONDO, 1 - vis),
                         font=self.f_nombre, width=w - 48)
        self.create_text(x1 + 38, c.y + 18, text=subtitulo, anchor="w", fill=mezclar(c.color, FONDO, 0.2 + (1 - vis) * 0.8),
                         font=self.f_chico)

    def _panel(self, p):
        if p.a < 0.03:
            return
        y = p.y + p.dy
        vis = p.a
        rect_redondo(self, p.x, y, p.x + p.w, y + p.alto, r=14, fill=mezclar(mezclar(p.color, PANEL, 0.92), FONDO, 1 - vis),
                     outline=mezclar(mezclar(p.color, FONDO, 0.6), FONDO, 1 - vis), width=1.2)
        self.create_text(p.x + 16, y + 18, text=p.titulo, anchor="w", fill=mezclar(p.color, FONDO, 1 - vis),
                         font=self.f_texto_b)
        interlinea = self.f_texto.metrics("linespace") + 3
        for i, linea in enumerate(p.lineas):
            self.create_text(p.x + 16, y + 38 + i * interlinea, text=linea, anchor="nw",
                             fill=mezclar(TEXTO, FONDO, 1 - vis), font=self.f_texto)

    def _leyenda(self, ancho, alto):
        texto = self.leyenda
        if self._hover is not None:
            nodo = self._hover.nodo
            texto = f"{nodo.valor}: {nodo.descripcion}"
        if not texto:
            return
        corto = texto if len(texto) < 170 else texto[:167] + "…"
        self.create_text(ancho / 2, alto - 24, text=corto, fill=TENUE, font=self.f_texto, width=ancho - 80,
                         justify="center")
