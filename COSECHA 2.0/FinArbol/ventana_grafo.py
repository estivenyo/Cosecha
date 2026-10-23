"""MapaRelaciones: el árbol de temas visto como GRAFO DIRIGIDO con ciclos (grafo.py)."""
import math
import tkinter as tk

from componentes import BotonRedondeado
from estilos import BORDE, CORAL, ESMERALDA, F_PEQ, ORO, PANEL, TARJETA, TENUE, TEXTO, color_de_nodo, mezclar


class MapaRelaciones(tk.Toplevel):
    RADIO_NODO = 9

    def __init__(self, master, grafo, arbol, al_ir, obtener_actual):
        super().__init__(master, bg=PANEL)
        self.grafo, self.arbol, self.al_ir, self.obtener_actual = grafo, arbol, al_ir, obtener_actual
        self.title("Mapa de relaciones · Cosecha")
        self.geometry("1180x740")
        self.minsize(1000, 640)
        self.transient(master)
        self.ciclos = grafo.ciclos()
        self.sel_ciclo = None          # ciclo resaltado (lista de nodos)
        self.sel_nodo = None           # tema seleccionado
        self._pos = {}
        # [ÁRBOL] mismos nodos del árbol, en PreOrden, para que los temas de una rama queden juntos en el círculo
        self._orden = [n for n in arbol.preorden() if n.uid in grafo.adyacencia]

        izquierda = tk.Frame(self, bg=PANEL)
        izquierda.pack(side="left", fill="both", expand=True, padx=(22, 8), pady=18)
        tk.Label(izquierda, text="Mapa de relaciones", bg=PANEL, fg=ESMERALDA, font=("Georgia", 20, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(izquierda, bg=PANEL, fg=TENUE, font=("Segoe UI", 10), anchor="w", justify="left", wraplength=740,
                 text=("El árbol dice a qué rama pertenece cada tema. Las flechas dicen qué conviene aprender DESPUÉS, "
                       "aunque esté en otra rama. Como algunas flechas regresan a un tema anterior, forman CICLOS. "
                       "Toca un tema o un ciclo.")).pack(fill="x", pady=(2, 6))
        self.lienzo = tk.Canvas(izquierda, bg=PANEL, highlightthickness=1, highlightbackground=BORDE)
        self.lienzo.pack(fill="both", expand=True)
        self.lienzo.bind("<Configure>", lambda e: self._dibujar())
        self.lienzo.bind("<Button-1>", self._al_clic)

        derecha = tk.Frame(self, bg=PANEL, width=360)
        derecha.pack(side="right", fill="y", padx=(8, 22), pady=18)
        derecha.pack_propagate(False)
        tk.Label(derecha, text=f"CICLOS ENCONTRADOS ({len(self.ciclos)})", bg=PANEL, fg=TENUE, font=F_PEQ,
                 anchor="w").pack(fill="x")
        tk.Label(derecha, text="Búsqueda en profundidad (DFS) sobre las flechas.", bg=PANEL, fg=TENUE,
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", pady=(0, 4))
        lista = tk.Frame(derecha, bg=PANEL)
        lista.pack(fill="x")
        self._botones_ciclo = []
        for i, ciclo in enumerate(self.ciclos):
            nombres = " → ".join(n.valor for n in ciclo)
            fila = tk.Label(lista, text=f"{i + 1}.  {nombres}", bg=TARJETA, fg=TEXTO, font=("Segoe UI", 9), anchor="w",
                            justify="left", wraplength=320, padx=8, pady=4, cursor="hand2",
                            highlightthickness=1, highlightbackground=BORDE)
            fila.pack(fill="x", pady=2)
            fila.bind("<Button-1>", lambda e, c=ciclo: self._elegir_ciclo(c))
            self._botones_ciclo.append((fila, ciclo))
        tk.Label(derecha, text="DETALLE", bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(fill="x", pady=(12, 2))
        self.b_ir = BotonRedondeado(derecha, "Ir a este tema", self._ir, color=ESMERALDA, ancho=340, alto=38, fondo=PANEL)
        self.b_ir.pack(side="bottom", pady=(10, 0))
        self.b_ir.habilitar(False)
        marco = tk.Frame(derecha, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE)
        marco.pack(fill="both", expand=True)
        self.detalle = tk.Text(marco, bg=TARJETA, fg=TEXTO, font=("Segoe UI", 9), wrap="word", relief="flat", bd=0,
                               padx=10, pady=8, highlightthickness=0, height=8, cursor="arrow")
        barra = tk.Scrollbar(marco, command=self.detalle.yview)
        self.detalle.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.detalle.pack(side="left", fill="both", expand=True)
        self.bind("<Escape>", lambda e: self.destroy())
        self._poner_detalle_inicial()
        self.after(60, self._latido)
        self._fase = 0.0

    # ------------------------------------------------------------------
    def _poner(self, texto):
        self.detalle.config(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", texto)
        self.detalle.config(state="disabled")

    def _poner_detalle_inicial(self):
        self._poner(("• Las flechas salen de un tema y apuntan a lo que conviene ver después.\n\n"
                                  "• Un ciclo es un camino que vuelve al tema donde empezó: por ejemplo, el control "
                                  "del dinero se retroalimenta con el ahorro.\n\n"
                                  "• El punto dorado con anillo es tu tema actual."))

    def _dibujar(self):
        c = self.lienzo
        c.delete("all")
        ancho, alto = max(c.winfo_width(), 400), max(c.winfo_height(), 300)
        cx, cy = ancho / 2, alto / 2
        radio = min(ancho, alto) / 2 - 95
        n = len(self._orden)
        self._pos = {}
        for i, nodo in enumerate(self._orden):
            ang = -math.pi / 2 + 2 * math.pi * i / n
            self._pos[nodo.uid] = (cx + radio * math.cos(ang), cy + radio * math.sin(ang), ang, nodo)
        en_ciclo = set()
        if self.sel_ciclo:
            en_ciclo = {(a.uid, b.uid) for a, b in zip(self.sel_ciclo, self.sel_ciclo[1:] + self.sel_ciclo[:1])}
        # aristas (primero las apagadas, al final las resaltadas)
        aristas = self.grafo.aristas()
        aristas.sort(key=lambda a: (a.origen.uid, a.destino.uid) in en_ciclo)
        for a in aristas:
            x1, y1, _, _ = self._pos[a.origen.uid]
            x2, y2, _, _ = self._pos[a.destino.uid]
            dx, dy = x2 - x1, y2 - y1
            dist = math.hypot(dx, dy) or 1
            mx, my = (x1 + x2) / 2 - dy / dist * dist * 0.16, (y1 + y2) / 2 + dx / dist * dist * 0.16
            # el final se acorta para que la flecha termine en el borde del círculo del destino
            ex, ey = mx - x2, my - y2
            d2 = math.hypot(ex, ey) or 1
            fx, fy = x2 + ex / d2 * (self.RADIO_NODO + 4), y2 + ey / d2 * (self.RADIO_NODO + 4)
            sx, sy = mx - x1, my - y1
            d1 = math.hypot(sx, sy) or 1
            ix, iy = x1 + sx / d1 * (self.RADIO_NODO + 2), y1 + sy / d1 * (self.RADIO_NODO + 2)
            activa = (a.origen.uid, a.destino.uid) in en_ciclo
            sel_nodo = self.sel_nodo is not None and (a.origen is self.sel_nodo or a.destino is self.sel_nodo)
            base = color_de_nodo(a.origen)
            if self.sel_ciclo:
                color, ancho_l = (ORO, 3) if activa else (mezclar(base, PANEL, 0.78), 1)
            elif self.sel_nodo is not None:
                color, ancho_l = (base, 2.4) if sel_nodo else (mezclar(base, PANEL, 0.8), 1)
            else:
                color, ancho_l = mezclar(base, PANEL, 0.35), 1.6
            c.create_line(ix, iy, mx, my, fx, fy, smooth=True, fill=color, width=ancho_l, arrow="last",
                          arrowshape=(10, 12, 4))
        actual = self.obtener_actual()
        for uid, (x, y, ang, nodo) in self._pos.items():
            col = color_de_nodo(nodo)
            brillo = (self.sel_ciclo and nodo in self.sel_ciclo) or nodo is self.sel_nodo
            apagado = self.sel_ciclo and nodo not in self.sel_ciclo
            if nodo is actual:
                pulso = 5 + 3 * (0.5 + 0.5 * math.sin(self._fase))
                c.create_oval(x - 11 - pulso, y - 11 - pulso, x + 11 + pulso, y + 11 + pulso, outline=ORO, width=1.5)
            r = self.RADIO_NODO + (2 if brillo else 0)
            c.create_oval(x - r, y - r, x + r, y + r, fill=mezclar(col, PANEL, 0.7) if apagado else col,
                          outline=TEXTO if brillo else "", width=2)
            ca = math.cos(ang)
            anchor = "w" if ca > 0.35 else ("e" if ca < -0.35 else "s" if math.sin(ang) < 0 else "n")
            off = 15
            tx, ty = x + math.cos(ang) * off, y + math.sin(ang) * off
            c.create_text(tx, ty, text=nodo.valor, anchor=anchor, font=("Segoe UI", 9, "bold" if brillo else "normal"),
                          fill=TENUE if apagado else TEXTO)
        c.create_text(cx, cy - 8, text="GRAFO DE TEMAS", fill=TENUE, font=F_PEQ)
        c.create_text(cx, cy + 10, text=f"{len(self.grafo.vertices)} temas · {len(self.grafo.aristas())} flechas · {len(self.ciclos)} ciclos",
                      fill=TENUE, font=("Segoe UI", 9))

    def _latido(self):
        self._fase += 0.3
        if self.winfo_exists():
            self._dibujar()
            self.after(90, self._latido)

    # ------------------------------------------------------------------
    def _al_clic(self, evento):
        mejor, d_mejor = None, 18
        for x, y, _, nodo in self._pos.values():
            d = math.hypot(evento.x - x, evento.y - y)
            if d < d_mejor:
                mejor, d_mejor = nodo, d
        if mejor is not None:
            self._elegir_nodo(mejor)

    def _elegir_ciclo(self, ciclo):
        self.sel_ciclo, self.sel_nodo = ciclo, None
        for fila, c in self._botones_ciclo:
            fila.config(highlightbackground=ORO if c is ciclo else BORDE, bg=mezclar(ORO, TARJETA, 0.88) if c is ciclo else TARJETA)
        pasos = []
        for a, b in zip(ciclo, ciclo[1:] + ciclo[:1]):
            arista = self.grafo.arista(a, b)
            pasos.append(f"• {a.valor} → {b.valor}\n   {arista.motivo}")
        self._poner(f"Ciclo de {len(ciclo)} temas (vuelve al punto de partida):\n\n" + "\n\n".join(pasos))
        self.b_ir.habilitar(False)
        self._dibujar()

    def _elegir_nodo(self, nodo):
        self.sel_nodo, self.sel_ciclo = nodo, None
        for fila, _ in self._botones_ciclo:
            fila.config(highlightbackground=BORDE, bg=TARJETA)
        sal, ent = self.grafo.salientes(nodo), self.grafo.entrantes(nodo)
        texto = f"{nodo.valor}\nRama: {' › '.join(n.valor for n in nodo.camino_nodos()[:-1])}\n"
        if sal:
            texto += "\nDespués conviene ver:\n" + "\n".join(f"  → {a.destino.valor}: {a.motivo}" for a in sal)
        if ent:
            texto += "\n\nLlegan a este tema desde:\n" + "\n".join(f"  ← {a.origen.valor}" for a in ent)
        ciclos = self.grafo.ciclos_de(nodo)
        texto += f"\n\nParticipa en {len(ciclos)} ciclo(s)."
        actual = self.obtener_actual()
        if actual is not nodo:
            ruta = self.grafo.camino_mas_corto(actual, nodo)      # BFS
            texto += ("\n\nDesde tu tema actual: " + (f"{len(ruta) - 1} paso(s): " + " → ".join(n.valor for n in ruta)
                                                      if ruta else "no hay camino por las flechas."))
        self._poner(texto)
        self.b_ir.habilitar(True)
        self._dibujar()

    def _ir(self):
        if self.sel_nodo is not None:
            self.al_ir(self.sel_nodo)
