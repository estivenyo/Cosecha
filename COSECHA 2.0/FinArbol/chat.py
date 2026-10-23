"""PanelChat: la conversación con la IA (burbujas con desplazamiento, escritura en vivo y entrada)."""
import tkinter as tk

from componentes import BotonRedondeado
from estilos import BORDE, ERROR, ESMERALDA, F_PEQ, F_UI, FONDO, ORO, PANEL, TARJETA, TENUE, TEXTO, mezclar

FUENTE_BURBUJA = ("Segoe UI", 10)


class PanelChat(tk.Frame):
    def __init__(self, master, al_enviar, modelo="IA"):
        super().__init__(master, bg=PANEL, highlightthickness=1, highlightbackground=BORDE)
        self.al_enviar = al_enviar
        self.modelo = modelo
        self._burbujas = []          # etiquetas de burbuja, para ajustar su ancho al redimensionar
        self._escribiendo = None
        self._tarjetas = []          # tarjetas de pregunta con botones de respuesta
        self._paso_puntos = 0
        self._habilitado = True

        tk.Label(self, text="CONVERSACIÓN CON LA IA", bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(
            fill="x", padx=16, pady=(14, 0))
        tk.Label(self, text="Pregúntale de finanzas o cuéntale qué quieres resolver.", bg=PANEL, fg=TENUE,
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", padx=16, pady=(0, 6))
        zona = tk.Frame(self, bg=PANEL)
        zona.pack(fill="both", expand=True, padx=(10, 4))
        self.lienzo = tk.Canvas(zona, bg=PANEL, highlightthickness=0)
        self.barra = tk.Scrollbar(zona, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=self.barra.set)
        self.barra.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)
        self.interior = tk.Frame(self.lienzo, bg=PANEL)
        self._ventana = self.lienzo.create_window(0, 0, window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", lambda e: self.lienzo.configure(scrollregion=self.lienzo.bbox("all")))
        self.lienzo.bind("<Configure>", self._al_cambiar_tamano)
        for widget in (self.lienzo, self.interior):
            widget.bind("<MouseWheel>", self._rueda)
            widget.bind("<Button-4>", self._rueda)
            widget.bind("<Button-5>", self._rueda)

        pie = tk.Frame(self, bg=PANEL)
        pie.pack(fill="x", padx=14, pady=(8, 14))
        caja = tk.Frame(pie, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE, highlightcolor=ESMERALDA)
        caja.pack(side="left", fill="x", expand=True)
        self.entrada = tk.Entry(caja, bg=TARJETA, fg=TEXTO, insertbackground=ESMERALDA, relief="flat",
                                font=("Segoe UI", 11), highlightthickness=0, bd=0)
        self.entrada.pack(fill="x", padx=10, ipady=8)
        self.entrada.bind("<Return>", lambda e: self._enviar())
        self.boton = BotonRedondeado(pie, "Enviar", self._enviar, color=ESMERALDA, ancho=82, alto=38, fondo=PANEL)
        self.boton.pack(side="left", padx=(8, 0))
        self._animar_puntos()

    # ------------------------------------------------------------------
    def _rueda(self, evento):
        paso = -1 if (evento.num == 4 or getattr(evento, "delta", 0) > 0) else 1
        self.lienzo.yview_scroll(paso * 2, "units")

    def _al_cambiar_tamano(self, evento):
        self.lienzo.itemconfigure(self._ventana, width=evento.width)
        for etiqueta in self._burbujas:
            etiqueta.config(wraplength=max(160, evento.width - 90))
        for tarjeta in self._tarjetas:
            for etiqueta, margen in tarjeta["etiquetas"]:
                etiqueta.config(wraplength=max(120, evento.width - margen))

    def _al_fondo(self):
        self.update_idletasks()
        self.lienzo.yview_moveto(1.0)

    def _enviar(self):
        texto = self.entrada.get().strip()
        if texto and self._habilitado:
            self.entrada.delete(0, "end")
            self.al_enviar(texto)

    def habilitar(self, valor):
        """Mientras la IA trabaja no se puede enviar otro mensaje."""
        self._habilitado = valor
        self.boton.habilitar(valor)

    def enfocar(self):
        self.entrada.focus_set()

    # ------------------------------------------------------------------
    def agregar(self, quien, texto=""):
        """Agrega una burbuja. quien: 'ia', 'persona' o 'aviso'. Devuelve la etiqueta (para ir completándola)."""
        self.quitar_escribiendo()
        fila = tk.Frame(self.interior, bg=PANEL)
        fila.pack(fill="x", pady=4, padx=(0, 10))
        ancho = max(160, self.lienzo.winfo_width() - 90)
        if quien == "persona":
            etiqueta = tk.Label(fila, text=texto, bg=mezclar(ESMERALDA, PANEL, 0.72), fg=TEXTO, font=FUENTE_BURBUJA,
                                wraplength=ancho, justify="left", padx=12, pady=8)
            etiqueta.pack(side="right")
        elif quien == "ia":
            avatar = tk.Canvas(fila, width=26, height=26, bg=PANEL, highlightthickness=0)
            avatar.create_oval(2, 2, 24, 24, fill=mezclar(ORO, PANEL, 0.7), outline=ORO, width=1.5)
            avatar.create_text(13, 13, text="C", fill=ORO, font=("Georgia", 10, "bold"))
            avatar.pack(side="left", anchor="n", padx=(0, 8))
            columna = tk.Frame(fila, bg=PANEL)
            columna.pack(side="left")
            tk.Label(columna, text=f"● {self.modelo} · Ollama", bg=PANEL, fg=ESMERALDA, font=("Segoe UI", 7, "bold"),
                     anchor="w").pack(fill="x")
            etiqueta = tk.Label(columna, text=texto, bg=TARJETA, fg=TEXTO, font=FUENTE_BURBUJA, wraplength=ancho,
                                justify="left", padx=12, pady=8, anchor="w")
            etiqueta.pack(side="left")
        else:
            etiqueta = tk.Label(fila, text=texto, bg=PANEL,
                                fg=ERROR if quien == "aviso" else mezclar(ESMERALDA, TENUE, 0.5),
                                font=("Segoe UI", 9, "italic"), wraplength=ancho, justify="left")
            etiqueta.pack(anchor="w", padx=34)
        etiqueta._fila = fila
        self._burbujas.append(etiqueta)
        self._al_fondo()
        return etiqueta

    def agregar_texto(self, etiqueta, pedazo):
        etiqueta.config(text=etiqueta.cget("text") + pedazo)
        self._al_fondo()

    def quitar_burbuja(self, etiqueta):
        if etiqueta in self._burbujas:
            self._burbujas.remove(etiqueta)
        etiqueta._fila.destroy()

    def limpiar(self):
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        self._burbujas, self._escribiendo, self._tarjetas = [], None, []

    # --- «La IA está escribiendo…» --------------------------------------
    def mostrar_escribiendo(self):
        if self._escribiendo is None:
            self._escribiendo = self.agregar("ia", "●  ○  ○")
            self._escribiendo.config(fg=ORO)

    def quitar_escribiendo(self):
        if self._escribiendo is not None:
            etiqueta, self._escribiendo = self._escribiendo, None
            self.quitar_burbuja(etiqueta)

    def _animar_puntos(self):
        if self._escribiendo is not None:
            self._paso_puntos = (self._paso_puntos + 1) % 3
            puntos = ["○", "○", "○"]
            puntos[self._paso_puntos] = "●"
            self._escribiendo.config(text="  ".join(puntos))
        self.after(280, self._animar_puntos)

    # --- Pregunta puntual con botones de respuesta ------------------------
    def agregar_pregunta(self, titulo, pregunta, opciones, pie=""):
        """Tarjeta del embudo de preguntas. `opciones` = lista de (número, texto, color, función).
        Al tocar una respuesta se llama a su función y la tarjeta se cierra (queda en el chat como registro)."""
        self.quitar_escribiendo()
        fila = tk.Frame(self.interior, bg=PANEL)
        fila.pack(fill="x", pady=(6, 8), padx=(0, 10))
        marco = tk.Frame(fila, bg=mezclar(ORO, PANEL, 0.9), highlightthickness=1,
                         highlightbackground=mezclar(ORO, PANEL, 0.55))
        marco.pack(fill="x", padx=(34, 0))
        ancho = max(140, self.lienzo.winfo_width() - 110)
        etiquetas = []
        t = tk.Label(marco, text=titulo, bg=marco["bg"], fg=ORO, font=("Segoe UI", 8, "bold"), anchor="w",
                     justify="left", wraplength=ancho)
        t.pack(fill="x", padx=12, pady=(10, 0))
        e = tk.Label(marco, text=pregunta, bg=marco["bg"], fg=TEXTO, font=("Segoe UI", 11, "bold"), anchor="w",
                     justify="left", wraplength=ancho)
        e.pack(fill="x", padx=12, pady=(2, 8))
        etiquetas.append((e, 110))
        etiquetas.append((t, 110))
        botones = []
        for numero, texto, color, funcion in opciones:
            caja = tk.Frame(marco, bg=TARJETA, highlightthickness=1, highlightbackground=mezclar(color, PANEL, 0.6),
                            cursor="hand2")
            caja.pack(fill="x", padx=10, pady=3)
            insignia = tk.Label(caja, text=str(numero), bg=color, fg=FONDO, font=("Segoe UI", 9, "bold"), width=2)
            insignia.pack(side="left", padx=(8, 8), pady=8)
            et = tk.Label(caja, text=texto, bg=TARJETA, fg=TEXTO, font=("Segoe UI", 10), anchor="w", justify="left",
                          wraplength=ancho - 25, cursor="hand2")
            et.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 8))
            etiquetas.append((et, 135))
            boton = {"caja": caja, "texto": et, "insignia": insignia, "color": color, "funcion": funcion}
            botones.append(boton)
            for w in (caja, insignia, et):
                w.bind("<Enter>", lambda ev, b=boton: self._resaltar(b, True))
                w.bind("<Leave>", lambda ev, b=boton: self._resaltar(b, False))
                w.bind("<Button-1>", lambda ev, b=boton: self._tocar(b))
        if pie:
            p = tk.Label(marco, text=pie, bg=marco["bg"], fg=TENUE, font=("Segoe UI", 8, "italic"), anchor="w",
                         justify="left", wraplength=ancho)
            p.pack(fill="x", padx=12, pady=(4, 0))
            etiquetas.append((p, 110))
        tk.Frame(marco, bg=marco["bg"], height=8).pack()
        tarjeta = {"fila": fila, "botones": botones, "etiquetas": etiquetas, "abierta": True}
        self._tarjetas.append(tarjeta)
        for w in (fila, marco):
            w.bind("<MouseWheel>", self._rueda)
        self._al_fondo()

    def _resaltar(self, boton, encima):
        tarjeta = next((t for t in self._tarjetas if boton in t["botones"]), None)
        if tarjeta is None or not tarjeta["abierta"]:
            return
        fondo = mezclar(boton["color"], TARJETA, 0.78) if encima else TARJETA
        for clave in ("caja", "texto"):
            boton[clave].config(bg=fondo)

    def _tocar(self, boton):
        tarjeta = next((t for t in self._tarjetas if boton in t["botones"]), None)
        if tarjeta is None or not tarjeta["abierta"] or not self._habilitado:
            return
        self.cerrar_preguntas(boton)
        boton["funcion"]()

    def cerrar_preguntas(self, elegida=None):
        """Desactiva las tarjetas de pregunta abiertas; la respuesta elegida queda marcada."""
        for tarjeta in self._tarjetas:
            if not tarjeta["abierta"]:
                continue
            tarjeta["abierta"] = False
            for b in tarjeta["botones"]:
                for w in (b["caja"], b["texto"], b["insignia"]):
                    w.config(cursor="")
                if b is elegida:
                    b["caja"].config(bg=mezclar(b["color"], TARJETA, 0.7), highlightbackground=b["color"])
                    b["texto"].config(bg=mezclar(b["color"], TARJETA, 0.7))
                    b["texto"].config(text="✓  " + b["texto"].cget("text"))
                else:
                    b["caja"].config(bg=PANEL, highlightbackground=mezclar(TENUE, PANEL, 0.8))
                    b["texto"].config(bg=PANEL, fg=TENUE)
                    b["insignia"].config(bg=mezclar(TENUE, PANEL, 0.6))
