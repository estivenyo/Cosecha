"""Gráficos propios dibujados sobre un Canvas: líneas, barras y dona (con animación)."""
import tkinter as tk
from tkinter import font as tkfont

from componentes import rect_redondo
from estilos import BORDE, TARJETA, TENUE, TEXTO, mezclar
from formato import compacto, moneda, porcentaje


class Grafico(tk.Canvas):
    """Un solo widget que dibuja distintos tipos de gráfico según `datos["tipo"]`.

    datos para "lineas": {"tipo", "series": [{"nombre","valores","color","relleno"}],
                          "etiquetas_x": [(indice, texto)], "formato": funcion}
    datos para "barras": {"tipo", "items": [(texto, valor, color)], "formato": funcion}
    datos para "dona":   {"tipo", "items": [(texto, valor, color)], "centro": (grande, pequeño)}
    """

    def __init__(self, master, **opciones):
        super().__init__(master, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE,
                         **opciones)
        self.datos = None
        self._progreso = 1.0
        self._tarea = None
        self.f_eje = tkfont.Font(family="Segoe UI", size=8)
        self.f_texto = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self.f_centro = tkfont.Font(family="Georgia", size=20, weight="bold")
        self.bind("<Configure>", lambda e: self._dibujar())
        self.bind("<Destroy>", self._al_destruir)

    def mostrar(self, datos):
        """Muestra un gráfico. Solo se anima cuando cambia el tipo de gráfico."""
        animar = self.datos is None or self.datos.get("tipo") != datos.get("tipo")
        self.datos = datos
        self._cancelar()
        self._progreso = 0.0 if animar else 1.0
        self._paso()

    def _al_destruir(self, _evento):
        self._cancelar()

    def _cancelar(self):
        if self._tarea:
            try:
                self.after_cancel(self._tarea)
            except tk.TclError:
                pass
            self._tarea = None

    def _paso(self):
        self._progreso = min(1.0, self._progreso + 0.06)
        self._dibujar()
        if self._progreso < 1.0:
            self._tarea = self.after(16, self._paso)
        else:
            self._tarea = None

    def _dibujar(self):
        self.delete("all")
        if not self.datos or self.winfo_width() < 80 or self.winfo_height() < 80:
            return
        suave = 1 - (1 - self._progreso) ** 3
        tipo = self.datos["tipo"]
        {"lineas": self._lineas, "barras": self._barras, "dona": self._dona}[tipo](suave)

    # ------------------------------------------------------------------
    def _lineas(self, e):
        d = self.datos
        w, h = self.winfo_width(), self.winfo_height()
        series = d["series"]
        formato = d.get("formato", compacto)
        n = max(len(s["valores"]) for s in series)
        x0, x1, y0, y1 = 66, w - 20, 40, h - 32
        vmax = max(max(s["valores"]) for s in series) * 1.08 or 1.0
        vmin = min(0.0, min(min(s["valores"]) for s in series))

        for k in range(5):                                     # rejilla y eje Y
            y = y1 - (y1 - y0) * k / 4
            self.create_line(x0, y, x1, y, fill=mezclar(BORDE, TARJETA, 0.2), dash=(2, 4))
            self.create_text(x0 - 8, y, text=formato(vmin + (vmax - vmin) * k / 4), anchor="e",
                             fill=TENUE, font=self.f_eje)
        for i, texto in d.get("etiquetas_x", []):               # eje X
            x = x0 + (x1 - x0) * i / max(1, n - 1)
            self.create_text(x, y1 + 8, text=texto, anchor="n", fill=TENUE, font=self.f_eje)

        lx = x0
        for s in series:                                       # leyenda
            self.create_rectangle(lx, 14, lx + 10, 24, fill=s["color"], outline="")
            self.create_text(lx + 15, 19, text=s["nombre"], anchor="w", fill=TEXTO, font=self.f_eje)
            lx += 30 + self.f_eje.measure(s["nombre"])

        trazos = []
        for s in series:
            pts = [(x0 + (x1 - x0) * i / max(1, n - 1),
                    y1 - (y1 - y0) * (v - vmin) / (vmax - vmin)) for i, v in enumerate(s["valores"])]
            limite = e * (len(pts) - 1)
            k = int(limite)
            visibles = pts[:k + 1]
            if k < len(pts) - 1:
                (ax, ay), (bx, by) = pts[k], pts[k + 1]
                f = limite - k
                visibles.append((ax + (bx - ax) * f, ay + (by - ay) * f))
            if len(visibles) >= 2:
                trazos.append((s, visibles))
        for s, visibles in trazos:                             # primero los rellenos...
            if s.get("relleno"):
                self.create_polygon(visibles + [(visibles[-1][0], y1), (visibles[0][0], y1)],
                                    fill=mezclar(s["color"], TARJETA, 0.84), outline="")
        for s, visibles in trazos:                             # ...y encima todas las líneas
            plano = [c for p in visibles for c in p]
            self.create_line(*plano, fill=s["color"], width=2.5, capstyle="round", joinstyle="round")
            ex, ey = visibles[-1]
            self.create_oval(ex - 4, ey - 4, ex + 4, ey + 4, fill=s["color"], outline=TARJETA, width=2)

    def _barras(self, e):
        d = self.datos
        w, h = self.winfo_width(), self.winfo_height()
        items = d["items"]
        formato = d.get("formato", moneda)
        vmax = max(v for _, v, _ in items) or 1.0
        ancho_texto = min(170, max(self.f_texto.measure(t) for t, _, _ in items))
        x_barra = 18 + ancho_texto + 12
        x_max = w - 110
        alto_fila = min(40, (h - 24) / len(items))
        y = (h - alto_fila * len(items)) / 2
        for texto, valor, color in items:
            cy = y + alto_fila / 2
            self.create_text(18, cy, text=texto, anchor="w", fill=TEXTO, font=self.f_texto, width=ancho_texto + 4)
            largo = 0.0 if valor <= 0 else max(4.0, (valor / vmax) * (x_max - x_barra) * e)
            if largo:
                rect_redondo(self, x_barra, cy - alto_fila * 0.3, x_barra + largo, cy + alto_fila * 0.3,
                             r=8, fill=mezclar(color, TARJETA, 0.12), outline="")
            self.create_text(x_barra + largo + 8, cy, text=formato(valor), anchor="w", fill=color,
                             font=self.f_texto)
            y += alto_fila

    def _dona(self, e):
        d = self.datos
        w, h = self.winfo_width(), self.winfo_height()
        items = [(t, v, c) for t, v, c in d["items"] if v > 0]
        total = sum(v for _, v, _ in items) or 1.0
        ancho_leyenda = 230 if w > 520 else 0
        cx = (w - ancho_leyenda) / 2
        cy = h / 2
        r_ext = min(h * 0.42, cx * 0.9)
        grosor = r_ext * 0.34
        r = r_ext - grosor / 2
        angulo = 90.0
        for _, valor, color in items:
            extension = -min(359.99, 360.0 * valor / total * e)
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=angulo, extent=extension,
                            style="arc", width=grosor, outline=color)
            angulo += extension
        grande, pequeno = d.get("centro", ("", ""))
        self.create_text(cx, cy - 8, text=grande, fill=TEXTO, font=self.f_centro)
        self.create_text(cx, cy + 18, text=pequeno, fill=TENUE, font=self.f_eje)
        if ancho_leyenda:
            ly = cy - len(items) * 24 / 2
            for texto, valor, color in items:
                self.create_oval(w - ancho_leyenda + 8, ly + 4, w - ancho_leyenda + 18, ly + 14,
                                 fill=color, outline="")
                self.create_text(w - ancho_leyenda + 26, ly + 9, anchor="w", fill=TEXTO,
                                 font=self.f_texto, text=f"{texto}  ·  {porcentaje(valor / total * 100, 0)}")
                ly += 24
