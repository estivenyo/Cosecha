"""VentanaPlan: «Mi plan de acción», generado desde el diagnóstico de salud financiera.
Muestra la lista doblemente enlazada de pasos ordenados por prioridad, cada uno con el motivo que lo puso ahí."""
import tkinter as tk

from componentes import BotonRedondeado
from estilos import (BORDE, CIELO, CORAL, ESMERALDA, F_PEQ, ORO, PANEL, TARJETA, TENUE, TEXTO, VIOLETA,
                     color_de_nodo, mezclar)
from plan import NOMBRES_PRIORIDAD

COLOR_PRIORIDAD = {1: CORAL, 2: ORO, 3: CIELO}


class VentanaPlan(tk.Toplevel):
    def __init__(self, master, plan, al_ir, al_cambiar, al_diagnostico):
        super().__init__(master, bg=PANEL)
        self.plan, self.al_ir, self.al_cambiar, self.al_diagnostico = plan, al_ir, al_cambiar, al_diagnostico
        self._reversa = False
        self.title("Mi plan de acción · Cosecha")
        self.geometry("900x760")
        self.minsize(720, 580)
        self.transient(master)

        tk.Label(self, text="Mi plan de acción", bg=PANEL, fg=ESMERALDA, font=("Georgia", 20, "bold"),
                 anchor="w").pack(fill="x", padx=26, pady=(20, 2))
        tk.Label(self, text=("Se arma con tu diagnóstico de salud financiera: lo que no cumples se convierte en un paso, "
                             "ordenado por urgencia (alta, media, baja). Es una lista doblemente enlazada: cada paso "
                             "apunta al anterior y al siguiente, así que subirlo, bajarlo o marcarlo como hecho solo "
                             "cambia esos enlaces."),
                 bg=PANEL, fg=TENUE, font=("Segoe UI", 10), anchor="w", justify="left", wraplength=840).pack(
            fill="x", padx=26, pady=(0, 8))

        self.resumen = tk.Frame(self, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE)
        self.resumen.pack(fill="x", padx=26, pady=(0, 8))
        self.b_diagnostico = BotonRedondeado(self.resumen, "", self._diagnostico, color=VIOLETA, ancho=190, alto=34,
                                             fondo=TARJETA)
        self.b_diagnostico.pack(side="right", padx=12, pady=10)
        self.texto_resumen = tk.Label(self.resumen, text="", bg=TARJETA, fg=TEXTO, font=("Segoe UI", 11, "bold"),
                                      anchor="w", justify="left", wraplength=560)
        self.texto_resumen.pack(side="left", fill="x", expand=True, padx=14, pady=10)

        self.cadena = tk.Canvas(self, bg=PANEL, height=64, highlightthickness=0)
        self.cadena.pack(fill="x", padx=26)
        self.cadena.bind("<Configure>", lambda e: self._dibujar_cadena())

        barra = tk.Frame(self, bg=PANEL)
        barra.pack(fill="x", padx=26, pady=(6, 6))
        self.b_sentido = BotonRedondeado(barra, "", self._cambiar_sentido, color=CIELO, ancho=250, alto=34, fondo=PANEL)
        self.b_sentido.pack(side="left")
        self.b_vaciar = BotonRedondeado(barra, "Borrar plan y diagnóstico", self._vaciar, color=CORAL, ancho=210, alto=34,
                                        fondo=PANEL)
        self.b_vaciar.pack(side="right")

        zona = tk.Frame(self, bg=PANEL)
        zona.pack(fill="both", expand=True, padx=(26, 12), pady=(0, 16))
        self.lienzo = tk.Canvas(zona, bg=PANEL, highlightthickness=0)
        barra_v = tk.Scrollbar(zona, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=barra_v.set)
        barra_v.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.interior = tk.Frame(self.lienzo, bg=PANEL)
        self._id = self.lienzo.create_window(0, 0, window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self.lienzo.bind("<Configure>", lambda e: self.lienzo.itemconfigure(self._id, width=e.width))
        for w in (self.lienzo, self.interior):
            w.bind("<MouseWheel>", lambda e: self.lienzo.yview_scroll(-1 if e.delta > 0 else 1, "units"))
            w.bind("<Button-4>", lambda e: self.lienzo.yview_scroll(-1, "units"))
            w.bind("<Button-5>", lambda e: self.lienzo.yview_scroll(1, "units"))
        self.bind("<Escape>", lambda e: self.destroy())
        self.refrescar()

    # ------------------------------------------------------------------
    def _cambiar_sentido(self):
        self._reversa = not self._reversa
        self.refrescar()

    def _diagnostico(self):
        self.al_diagnostico()

    def _vaciar(self):
        if self.plan.hay_diagnostico or len(self.plan):
            self.plan.vaciar()
            self._cambio()

    def _cambio(self):
        self.refrescar()
        self.al_cambiar()

    def _mover(self, nodo, arriba):
        (self.plan.subir if arriba else self.plan.bajar)(nodo)
        self._cambio()

    def _hecho(self, nodo):
        self.plan.completar(nodo)
        self._cambio()

    def _ir(self, nodo):
        self.al_ir(nodo)

    # ------------------------------------------------------------------
    def refrescar(self):
        plan = self.plan
        self.b_sentido.poner_texto("Recorrer: de más a menos urgente ▸" if not self._reversa
                                   else "◂ Recorrer: al revés (por los enlaces «anterior»)")
        self.b_vaciar.habilitar(plan.hay_diagnostico or len(plan) > 0)
        self.b_sentido.habilitar(len(plan) > 0)
        self.b_diagnostico.poner_texto("Rehacer mi diagnóstico" if plan.hay_diagnostico else "Hacer mi diagnóstico")
        if plan.hay_diagnostico:
            nivel, _ = plan.nivel
            hechos = f" · {len(plan.completados)} paso(s) hecho(s)" if plan.completados else ""
            self.texto_resumen.config(text=f"Tu salud financiera: {sum(plan.marcas)} de {len(plan.marcas)} · {nivel}{hechos}")
        else:
            self.texto_resumen.config(text="Aún no has hecho tu diagnóstico de salud financiera")
        self._dibujar_cadena()
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        tareas = plan.tareas_reversa() if self._reversa else plan.tareas()
        if not tareas:
            if plan.hay_diagnostico:
                texto = ("¡No te queda ningún paso pendiente! Cumples todo lo que revisa el diagnóstico. "
                         "Rehazlo dentro de unos meses para comprobar que sigues así.")
            else:
                texto = ("Tu plan aparece aquí cuando hagas el diagnóstico: son 8 afirmaciones que marcas según lo que "
                         "ya haces hoy. Cosecha convierte lo que te falta en pasos ordenados por urgencia, distinto "
                         "para cada persona.\n\nTambién puedes pedirlo desde el chat: «Prefiero empezar con un "
                         "diagnóstico de mi salud financiera».")
            tk.Label(self.interior, bg=PANEL, fg=TENUE, font=("Segoe UI", 11), justify="left", wraplength=700,
                     text=texto).pack(anchor="w", pady=26)
            return
        for tarea in tareas:
            self._fila(tarea)

    def _fila(self, tarea):
        nodo = tarea.nodo
        c = color_de_nodo(nodo)
        col_p = COLOR_PRIORIDAD[tarea.prioridad]
        pos = self.plan.posicion(nodo)
        ant, sig = self.plan.vecinos(nodo)
        fila = tk.Frame(self.interior, bg=TARJETA, highlightthickness=1, highlightbackground=mezclar(c, PANEL, 0.6))
        fila.pack(fill="x", pady=4, padx=(0, 6))
        tk.Label(fila, text=str(pos), bg=col_p, fg=PANEL, font=("Georgia", 14, "bold"), width=3).pack(
            side="left", fill="y")
        botones = tk.Frame(fila, bg=TARJETA)
        botones.pack(side="right", padx=10)
        centro = tk.Frame(fila, bg=TARJETA)
        centro.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        cab = tk.Frame(centro, bg=TARJETA)
        cab.pack(fill="x")
        tk.Label(cab, text=nodo.valor, bg=TARJETA, fg=TEXTO, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(cab, text=f" Prioridad {NOMBRES_PRIORIDAD[tarea.prioridad]} ", bg=mezclar(col_p, TARJETA, 0.75),
                 fg=col_p, font=("Segoe UI", 8, "bold")).pack(side="left", padx=10)
        tk.Label(centro, text=tarea.motivo, bg=TARJETA, fg=TEXTO, font=("Segoe UI", 10), anchor="w", justify="left",
                 wraplength=470).pack(fill="x", pady=(3, 0))
        tk.Label(centro, bg=TARJETA, fg=mezclar(TENUE, TEXTO, 0.3), font=("Consolas", 9), anchor="w",
                 text=f"◂ anterior: {ant.nodo.valor if ant else '— (es la cabeza)'}    siguiente: {sig.nodo.valor if sig else '— (es la cola)'} ▸").pack(
            fill="x", pady=(4, 0))
        BotonRedondeado(botones, "Ir al tema", lambda n=nodo: self._ir(n), color=c, ancho=100, alto=30, fondo=TARJETA).pack(
            side="left", padx=2)
        if not self._reversa:
            arriba = BotonRedondeado(botones, "▲", lambda n=nodo: self._mover(n, True), color=TENUE, ancho=34, alto=30, fondo=TARJETA)
            arriba.pack(side="left", padx=2)
            arriba.habilitar(ant is not None)
            abajo = BotonRedondeado(botones, "▼", lambda n=nodo: self._mover(n, False), color=TENUE, ancho=34, alto=30, fondo=TARJETA)
            abajo.pack(side="left", padx=2)
            abajo.habilitar(sig is not None)
        BotonRedondeado(botones, "✓ Hecho", lambda n=nodo: self._hecho(n), color=ESMERALDA, ancho=80, alto=30, fondo=TARJETA).pack(
            side="left", padx=2)
        for w in (fila, centro):
            w.bind("<MouseWheel>", lambda e: self.lienzo.yview_scroll(-1 if e.delta > 0 else 1, "units"))

    def _dibujar_cadena(self):
        """Dibuja la lista como cadena: cabeza ⇄ paso ⇄ paso ⇄ … ⇄ cola."""
        c = self.cadena
        c.delete("all")
        ancho = max(c.winfo_width(), 300)
        tareas = self.plan.tareas_reversa() if self._reversa else self.plan.tareas()
        y = 32
        c.create_text(4, y, text="cola" if self._reversa else "cabeza", fill=TENUE, font=F_PEQ, anchor="w")
        if not tareas:
            c.create_text(70, y, text="(lista vacía)", fill=TENUE, font=("Segoe UI", 9), anchor="w")
            return
        maximo = max(1, (ancho - 130) // 118)
        mostrados = tareas[:maximo] if len(tareas) <= maximo else tareas[:maximo - 1]
        x = 54
        for t in mostrados:
            col = COLOR_PRIORIDAD[t.prioridad]
            nodo = t.nodo
            c.create_rectangle(x, y - 18, x + 98, y + 18, fill=mezclar(col, PANEL, 0.75), outline=col, width=1.5)
            nombre = nodo.valor if len(nodo.valor) <= 14 else nodo.valor[:13] + "…"
            c.create_text(x + 49, y - 5, text=nombre, fill=TEXTO, font=("Segoe UI", 8, "bold"))
            c.create_text(x + 49, y + 8, text=f"prioridad {NOMBRES_PRIORIDAD[t.prioridad].lower()}", fill=col, font=("Segoe UI", 7))
            c.create_text(x + 108, y, text="⇄", fill=TENUE, font=("Segoe UI", 12))
            x += 118
        if len(tareas) > len(mostrados):
            c.create_text(x + 6, y, text=f"… +{len(tareas) - len(mostrados)}", fill=TENUE, font=("Segoe UI", 9), anchor="w")
            x += 60
        c.create_text(x, y, text="cabeza" if self._reversa else "cola", fill=TENUE, font=F_PEQ, anchor="w")
