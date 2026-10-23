"""Widgets reutilizables con estilo propio (botones, tarjetas, diálogo, logo)."""
import tkinter as tk

from estilos import (BORDE, ERROR, ESMERALDA, F_KPI, F_NUM, F_PEQ, F_UI, F_UI_B, FONDO,
                     ORO, PANEL, TARJETA, TENUE, TEXTO, mezclar)


def rect_redondo(canvas, x1, y1, x2, y2, r=12, **opciones):
    """Dibuja un rectángulo con esquinas redondeadas en un Canvas."""
    r = max(1, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    puntos = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(puntos, smooth=True, **opciones)


class BotonRedondeado(tk.Canvas):
    """Botón de esquinas redondeadas con efecto al pasar el mouse."""

    def __init__(self, master, texto, comando, color=ESMERALDA, ancho=232, alto=38,
                 fondo=PANEL, fuente=F_UI_B):
        super().__init__(master, width=ancho, height=alto, bg=fondo,
                         highlightthickness=0, cursor="hand2")
        self.texto, self.comando, self.color = texto, comando, color
        self.fondo_padre, self.fuente = fondo, fuente
        self.ancho, self.alto = ancho, alto
        self.activo, self._encima = True, False
        self.bind("<Enter>", lambda e: self._poner_encima(True))
        self.bind("<Leave>", lambda e: self._poner_encima(False))
        self.bind("<ButtonRelease-1>", self._soltar)
        self._dibujar()

    def _poner_encima(self, valor):
        self._encima = valor
        self._dibujar()

    def _soltar(self, evento):
        if self.activo and 0 <= evento.x <= self.ancho and 0 <= evento.y <= self.alto:
            self.comando()

    def poner_texto(self, texto):
        self.texto = texto
        self._dibujar()

    def habilitar(self, valor):
        self.activo = valor
        self.config(cursor="hand2" if valor else "arrow")
        self._dibujar()

    def _dibujar(self):
        self.delete("all")
        color = self.color if self.activo else TENUE
        relleno = mezclar(color, self.fondo_padre, 0.72 if self._encima and self.activo else 0.88)
        borde = color if self._encima and self.activo else mezclar(color, self.fondo_padre, 0.45)
        rect_redondo(self, 2, 2, self.ancho - 2, self.alto - 2, r=14, fill=relleno,
                     outline=borde, width=1.5)
        self.create_text(self.ancho / 2, self.alto / 2, text=self.texto, fill=color,
                         font=self.fuente)


class TarjetaDato(tk.Frame):
    """Tarjeta con un número grande y su título (estadísticas del árbol)."""

    def __init__(self, master, titulo, color, ancho=110):
        super().__init__(master, bg=TARJETA, width=ancho, height=74,
                         highlightthickness=1, highlightbackground=BORDE)
        self.pack_propagate(False)
        tk.Frame(self, bg=color, height=3).pack(fill="x", side="top")
        self.valor = tk.Label(self, text="0", bg=TARJETA, fg=color, font=F_NUM)
        self.valor.pack(pady=(2, 0))
        tk.Label(self, text=titulo.upper(), bg=TARJETA, fg=TENUE, font=F_PEQ).pack()

    def poner(self, valor):
        self.valor.config(text=str(valor))


class DialogoTexto(tk.Toplevel):
    """Diálogo modal con el estilo de la aplicación para pedir un texto."""

    def __init__(self, master, titulo, mensaje, color=ESMERALDA, multilinea=False, inicial=""):
        super().__init__(master, bg=PANEL)
        self.multilinea = multilinea
        self.resultado = None
        self.title(titulo)
        self.resizable(False, False)
        self.transient(master)
        marco = tk.Frame(self, bg=PANEL, padx=26, pady=22, highlightthickness=1,
                         highlightbackground=mezclar(color, PANEL, 0.5))
        marco.pack()
        tk.Label(marco, text=titulo, bg=PANEL, fg=color,
                 font=("Georgia", 15, "bold")).pack(anchor="w")
        tk.Label(marco, text=mensaje, bg=PANEL, fg=TENUE, font=F_UI, wraplength=340,
                 justify="left").pack(anchor="w", pady=(6, 12))
        if multilinea:
            self.entrada = tk.Text(marco, bg=TARJETA, fg=TEXTO, insertbackground=color,
                                   relief="flat", font=("Segoe UI", 11), width=46, height=7,
                                   wrap="word", padx=8, pady=8, highlightthickness=1,
                                   highlightbackground=BORDE, highlightcolor=color)
            self.entrada.insert("1.0", inicial)
            self.entrada.pack(fill="x")
        else:
            self.entrada = tk.Entry(marco, bg=TARJETA, fg=TEXTO, insertbackground=color,
                                    relief="flat", font=("Segoe UI", 12), width=32,
                                    highlightthickness=1, highlightbackground=BORDE,
                                    highlightcolor=color)
            self.entrada.insert(0, inicial)
            self.entrada.pack(ipady=7, fill="x")
        fila = tk.Frame(marco, bg=PANEL)
        fila.pack(pady=(16, 0), anchor="e")
        BotonRedondeado(fila, "Cancelar", self.destroy, color=TENUE, ancho=110, alto=34,
                        fondo=PANEL).pack(side="left", padx=(0, 8))
        BotonRedondeado(fila, "Aceptar", self._aceptar, color=color, ancho=110, alto=34,
                        fondo=PANEL).pack(side="left")
        self.bind("<Return>" if not multilinea else "<Control-Return>", lambda e: self._aceptar())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{x}+{y}")
        self.entrada.focus_set()
        self.grab_set()

    def _aceptar(self):
        texto = self.entrada.get("1.0", "end") if self.multilinea else self.entrada.get()
        self.resultado = texto.strip() or None
        self.destroy()

    def pedir(self):
        self.wait_window()
        return self.resultado


def dibujar_logo(canvas, tam=46):
    """Logo de la app: un pequeño árbol hecho con líneas y círculos."""
    canvas.delete("all")
    rect_redondo(canvas, 1, 1, tam - 1, tam - 1, r=12, fill=mezclar(ESMERALDA, FONDO, 0.82),
                 outline=mezclar(ESMERALDA, FONDO, 0.35))
    c = tam / 2
    ramas = [(c, tam - 11, c, 20), (c, 20, c - 10, 13), (c, 20, c + 10, 13), (c, 28, c + 9, 24)]
    for x1, y1, x2, y2 in ramas:
        canvas.create_line(x1, y1, x2, y2, fill=ESMERALDA, width=2, capstyle="round")
    for x, y, color in [(c, 17, ORO), (c - 10, 12, ESMERALDA), (c + 10, 12, ESMERALDA),
                        (c + 9, 24, ESMERALDA)]:
        canvas.create_oval(x - 3.5, y - 3.5, x + 3.5, y + 3.5, fill=color, outline="")


class TarjetaKpi(tk.Frame):
    """Tarjeta de resultado: título pequeño y un valor destacado."""

    def __init__(self, master, titulo="", valor="", color=ESMERALDA):
        super().__init__(master, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE)
        self.barra = tk.Frame(self, bg=color, height=3)
        self.barra.pack(fill="x")
        self.titulo = tk.Label(self, bg=TARJETA, fg=TENUE, font=F_PEQ, anchor="w")
        self.titulo.pack(fill="x", padx=12, pady=(8, 0))
        self.valor = tk.Label(self, bg=TARJETA, font=F_KPI, anchor="w")
        self.valor.pack(fill="x", padx=12, pady=(0, 10))
        self.poner(titulo, valor, color)

    def poner(self, titulo, valor, color):
        self.barra.config(bg=color)
        self.titulo.config(text=titulo.upper())
        # Los valores largos (por ejemplo "1 año y 4 meses") usan una letra algo menor para no cortarse.
        fuente = F_KPI if len(valor) <= 12 else ("Georgia", 11, "bold")
        self.valor.config(text=valor, fg=color, font=fuente)


class PanelKpis(tk.Frame):
    """Cuadrícula de TarjetaKpi que se reconstruye solo si cambia la cantidad."""

    def __init__(self, master, columnas=3, fondo=FONDO):
        super().__init__(master, bg=fondo)
        self.columnas = columnas
        self.tarjetas = []

    def poner(self, kpis, color_defecto=ESMERALDA):
        if len(kpis) != len(self.tarjetas):
            for t in self.tarjetas:
                t.destroy()
            self.tarjetas = []
            for i in range(len(kpis)):
                t = TarjetaKpi(self)
                t.grid(row=i // self.columnas, column=i % self.columnas, sticky="ew",
                       padx=(0 if i % self.columnas == 0 else 8, 0), pady=(0, 8))
                self.tarjetas.append(t)
            for c in range(self.columnas):
                self.columnconfigure(c, weight=1, uniform="kpi")
        for tarjeta, (titulo, valor, color) in zip(self.tarjetas, kpis):
            tarjeta.poner(titulo, valor, color or color_defecto)


class BarraProgreso(tk.Canvas):
    """Barra de progreso con etiqueta, usada en el encabezado."""

    def __init__(self, master, ancho=210, fondo=FONDO, color=ESMERALDA):
        super().__init__(master, width=ancho, height=44, bg=fondo, highlightthickness=0)
        self.ancho, self.color = ancho, color
        self._actual, self._meta, self._total = 0.0, 0.0, 1
        self._texto = ""
        self._dibujar()

    def poner(self, valor, total):
        self._meta = valor / max(1, total)
        self._total = total
        self._texto = f"{valor} de {total} temas estudiados"
        self._animar()

    def _animar(self):
        if abs(self._meta - self._actual) > 0.004:
            self._actual += (self._meta - self._actual) * 0.2
            self.after(24, self._animar)
        else:
            self._actual = self._meta
        self._dibujar()

    def _dibujar(self):
        self.delete("all")
        self.create_text(0, 8, text="PROGRESO DE ESTUDIO", anchor="w", fill=TENUE, font=F_PEQ)
        rect_redondo(self, 0, 20, self.ancho, 28, r=4, fill=mezclar(self.color, FONDO, 0.85), outline="")
        if self._actual > 0.001:
            rect_redondo(self, 0, 20, max(8, self.ancho * self._actual), 28, r=4, fill=self.color, outline="")
        self.create_text(0, 38, text=self._texto, anchor="w", fill=TEXTO, font=("Segoe UI", 8))
