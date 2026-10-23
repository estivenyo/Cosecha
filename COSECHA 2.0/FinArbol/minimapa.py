"""MiniMapa: el árbol completo en pequeño; se ilumina el camino que va recorriendo la persona."""
import math
import tkinter as tk

from disenio import calcular_filas
from estilos import BORDE, ESMERALDA, F_PEQ, FONDO, ORO, PANEL, TENUE, TEXTO, color_de_nodo, mezclar


class MiniMapa(tk.Frame):
    def __init__(self, master, arbol):
        super().__init__(master, bg=PANEL, highlightthickness=1, highlightbackground=BORDE)
        self.arbol, self.guia = arbol, None
        tk.Label(self, text="MAPA DE TU RECORRIDO", bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(
            fill="x", padx=16, pady=(14, 0))
        tk.Label(self, text="Todos los temas de la guía. El punto brillante es donde estás.", bg=PANEL, fg=TENUE,
                 font=("Segoe UI", 8), anchor="w", wraplength=240, justify="left").pack(fill="x", padx=16, pady=(0, 4))
        self.lienzo = tk.Canvas(self, bg=PANEL, height=300, highlightthickness=0)
        self.lienzo.pack(fill="x", padx=10)
        self.lienzo.bind("<Configure>", lambda e: self._calcular())
        self.lienzo.bind("<Motion>", self._al_mover)
        self.lienzo.bind("<Leave>", lambda e: self._poner_nombre(None))
        self.nombre = tk.Label(self, text="", bg=PANEL, fg=TEXTO, font=("Segoe UI", 9, "bold"), anchor="w")
        self.nombre.pack(fill="x", padx=16)

        tk.Label(self, text="TU RUTA", bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(
            fill="x", padx=16, pady=(14, 4))
        self.ruta = tk.Frame(self, bg=PANEL)
        self.ruta.pack(fill="x", padx=16)

        tk.Label(self, text="TEMAS EXPLORADOS", bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(
            fill="x", padx=16, pady=(16, 4))
        self.barra = tk.Canvas(self, bg=PANEL, height=26, highlightthickness=0)
        self.barra.pack(fill="x", padx=16, pady=(0, 14))
        self.barra.bind("<Configure>", lambda e: self._dibujar_barra())

        tk.Label(self, text="CÓMO FUNCIONA", bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(fill="x", padx=16, pady=(4, 4))
        tk.Label(self, text="1. La IA te hace una pregunta puntual en el chat.\n2. Tocas la respuesta que más se parece a ti "
                 "(o la escribes) y bajas un nivel del árbol.\n3. Con 2 o 3 preguntas llegas a tu tema: lo conoces y "
                 "lo practicas con su calculadora.",
                 bg=PANEL, fg=TENUE, font=("Segoe UI", 9), justify="left", wraplength=230, anchor="w").pack(fill="x", padx=16)

        self._posiciones = {}
        self._fase = 0.0
        self._nombre_hover = None
        self._latido()

    def usar(self, guia):
        self.guia = guia
        self.actualizar()

    def actualizar(self):
        if self.guia is None:
            return
        self._dibujar()
        self._dibujar_ruta()
        self._dibujar_barra()

    # ------------------------------------------------------------------
    def _calcular(self):
        # [ÁRBOL] El mismo cálculo PostOrden que ubica a cada nodo, con todas las ramas abiertas.
        abiertos = {n.uid for n in self.arbol.preorden() if n.hijos}
        filas, total = calcular_filas(self.arbol.raiz, abiertos)
        ancho = max(self.lienzo.winfo_width(), 200)
        alto = int(self.lienzo.cget("height"))
        niveles = self.arbol.altura() + 1
        self._posiciones = {}
        for nodo in self.arbol.preorden():
            nivel, fila = filas[nodo.uid]
            x = 14 + (fila + 0.5) * (ancho - 28) / total
            y = 22 + nivel * (alto - 44) / max(1, niveles - 1)
            self._posiciones[nodo.uid] = (x, y, nodo)
        self._dibujar()

    def _dibujar(self):
        c = self.lienzo
        c.delete("all")
        if not self._posiciones or self.guia is None:
            return
        camino = {n.uid for n in self.guia.ruta}
        actual = self.guia.actual
        for uid, (x, y, nodo) in self._posiciones.items():     # ramas
            if nodo.padre is None:
                continue
            px, py, _ = self._posiciones[nodo.padre.uid]
            if uid in camino:
                color, ancho = color_de_nodo(nodo), 2.4
            elif uid in self.guia.visitados:
                color, ancho = mezclar(color_de_nodo(nodo), PANEL, 0.55), 1.4
            else:
                color, ancho = mezclar(TENUE, PANEL, 0.7), 1
            c.create_line(px, py, px, (py + y) / 2, x, (py + y) / 2, x, y, fill=color, width=ancho)
        for uid, (x, y, nodo) in self._posiciones.items():     # nodos
            color = color_de_nodo(nodo)
            if nodo is actual:
                pulso = 4 + 2.5 * (0.5 + 0.5 * math.sin(self._fase))
                c.create_oval(x - 7 - pulso, y - 7 - pulso, x + 7 + pulso, y + 7 + pulso, outline=mezclar(color, PANEL, 0.4), width=1.5)
                c.create_oval(x - 7, y - 7, x + 7, y + 7, fill=color, outline=TEXTO, width=1.5)
            elif uid in camino:
                c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline="")
            elif uid in self.guia.visitados:
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill=mezclar(color, PANEL, 0.4), outline="")
            else:
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=mezclar(TENUE, PANEL, 0.55), outline="")

    def _latido(self):
        self._fase += 0.25
        if self.guia is not None:
            self._dibujar()
        self.after(70, self._latido)

    def _al_mover(self, evento):
        cercano, mejor = None, 12
        for x, y, nodo in self._posiciones.values():
            d = math.hypot(evento.x - x, evento.y - y)
            if d < mejor:
                cercano, mejor = nodo, d
        self._poner_nombre(cercano)

    def _poner_nombre(self, nodo):
        self.nombre.config(text=nodo.valor if nodo else "")

    def _dibujar_ruta(self):
        for hijo in self.ruta.winfo_children():
            hijo.destroy()
        for i, nodo in enumerate(self.guia.ruta):
            fila = tk.Frame(self.ruta, bg=PANEL)
            fila.pack(fill="x", anchor="w")
            tk.Label(fila, text="    " * i + ("↳ " if i else "● "), bg=PANEL, fg=color_de_nodo(nodo),
                     font=("Segoe UI", 9)).pack(side="left")
            ultimo = i == len(self.guia.ruta) - 1
            tk.Label(fila, text=nodo.valor, bg=PANEL, fg=TEXTO if ultimo else TENUE,
                     font=("Segoe UI", 10, "bold" if ultimo else "normal")).pack(side="left")

    def _dibujar_barra(self):
        b = self.barra
        b.delete("all")
        if self.guia is None:
            return
        ancho = max(b.winfo_width(), 100)
        total = self.arbol.contar_nodos()
        vistos = len(self.guia.visitados)
        b.create_rectangle(0, 4, ancho, 10, fill=mezclar(ESMERALDA, PANEL, 0.85), outline="")
        b.create_rectangle(0, 4, ancho * vistos / total, 10, fill=ESMERALDA, outline="")
        b.create_text(0, 20, anchor="w", text=f"{vistos} de {total} temas", fill=TEXTO, font=("Segoe UI", 8))
