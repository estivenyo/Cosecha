"""Ventanas de las herramientas que se abren desde los nodos del árbol."""
import json
import tkinter as tk
from pathlib import Path

import calculos as c
from componentes import BotonRedondeado, PanelKpis, rect_redondo
from estilos import (BORDE, CATEGORIAS, CIELO, CORAL, ERROR, ESMERALDA, F_PEQ, F_TEXTO, F_UI, F_UI_B,
                     FONDO, ORO, PANEL, TARJETA, TENUE, TEXTO, mezclar)
from formato import leer_numero, moneda, numero_campo
from graficos import Grafico
from herramientas import CASOS_FRAUDE, DEFINICIONES, LISTAS

CATEGORIAS_GASTO = ["Vivienda", "Alimentación", "Transporte", "Servicios", "Ocio", "Salud",
                    "Educación", "Otros"]


def crear_entrada(master, variable, color, ancho=14, alineacion="right"):
    return tk.Entry(master, textvariable=variable, bg=TARJETA, fg=TEXTO, insertbackground=color,
                    relief="flat", font=("Segoe UI", 11), width=ancho, justify=alineacion,
                    highlightthickness=1, highlightbackground=BORDE, highlightcolor=color)


class VentanaBase(tk.Toplevel):
    """Marco común: franja de color, encabezado, cuerpo y aviso al pie."""

    def __init__(self, master, titulo, subtitulo, color, ancho=1020, alto=700):
        super().__init__(master, bg=FONDO)
        self.color = color
        self.title(f"{titulo} · Cosecha")
        ancho = min(ancho, self.winfo_screenwidth() - 50)
        alto = min(alto, self.winfo_screenheight() - 90)
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - ancho) // 2
        y = master.winfo_rooty() + (master.winfo_height() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{max(0, x)}+{max(0, y)}")
        self.minsize(min(860, ancho), min(560, alto))
        tk.Frame(self, bg=color, height=4).pack(fill="x")
        cabecera = tk.Frame(self, bg=PANEL, padx=24, pady=14)
        cabecera.pack(fill="x")
        tk.Label(cabecera, text=titulo, bg=PANEL, fg=TEXTO, font=("Georgia", 20, "bold")).pack(anchor="w")
        tk.Label(cabecera, text=subtitulo, bg=PANEL, fg=TENUE, font=F_UI, wraplength=ancho - 70,
                 justify="left").pack(anchor="w", pady=(2, 0))
        tk.Label(self, text="Herramienta educativa · los resultados son estimaciones y no constituyen asesoría financiera.",
                 bg=PANEL, fg=TENUE, font=F_PEQ, pady=6).pack(side="bottom", fill="x")
        self.cuerpo = tk.Frame(self, bg=FONDO)
        self.cuerpo.pack(fill="both", expand=True, padx=16, pady=12)
        self.bind("<Escape>", lambda e: self.destroy())

    def crear_nota(self, padre):
        """Caja de mensaje con barra de color a la izquierda."""
        caja = tk.Frame(padre, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE)
        self._barra_nota = tk.Frame(caja, bg=TENUE, width=5)
        self._barra_nota.pack(side="left", fill="y")
        self._texto_nota = tk.Label(caja, text="", bg=TARJETA, fg=TEXTO, font=F_UI, justify="left",
                                    anchor="w", wraplength=560, padx=14, pady=10)
        self._texto_nota.pack(side="left", fill="x", expand=True)
        caja.bind("<Configure>", lambda e: self._texto_nota.config(wraplength=max(200, e.width - 60)))
        return caja

    def poner_nota(self, texto, nivel="info"):
        color = {"ok": ESMERALDA, "aviso": ORO, "error": ERROR}.get(nivel, self.color)
        self._barra_nota.config(bg=color)
        self._texto_nota.config(text=texto)


# ======================================================================
# Calculadora genérica (se construye a partir de una Definicion)
# ======================================================================
class VentanaCalculadora(VentanaBase):
    def __init__(self, master, definicion, color):
        super().__init__(master, definicion.titulo, definicion.subtitulo, color)
        self.definicion = definicion
        self.variables, self.entradas = {}, {}
        self._pendiente = None
        self.cuerpo.columnconfigure(1, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)

        formulario = tk.Frame(self.cuerpo, bg=PANEL, width=340, padx=18, pady=14,
                              highlightthickness=1, highlightbackground=BORDE)
        formulario.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        formulario.pack_propagate(False)
        tk.Label(formulario, text="TUS DATOS", bg=PANEL, fg=TENUE, font=F_PEQ).pack(anchor="w", pady=(0, 8))
        for campo in definicion.campos:
            fila = tk.Frame(formulario, bg=PANEL)
            fila.pack(fill="x", pady=4)
            tk.Label(fila, text=campo.etiqueta + (" ($)" if campo.tipo == "dinero" else
                     " (%)" if campo.tipo == "porcentaje" else ""), bg=PANEL, fg=TEXTO, font=F_UI,
                     wraplength=170, justify="left", anchor="w").pack(side="left")
            variable = tk.StringVar(value=numero_campo(campo.defecto, campo.tipo))
            entrada = crear_entrada(fila, variable, color, ancho=13)
            entrada.pack(side="right", ipady=5)
            entrada.bind("<KeyRelease>", lambda e: self._programar())
            entrada.bind("<FocusOut>", lambda e, cm=campo: self._normalizar(cm))
            self.variables[campo.clave], self.entradas[campo.clave] = variable, entrada
            if campo.ayuda:
                tk.Label(formulario, text=campo.ayuda, bg=PANEL, fg=TENUE, font=F_PEQ, anchor="w").pack(fill="x")
        tk.Label(formulario, text="Puedes escribir 2500000 o 2.500.000.\nLos resultados se actualizan al escribir.",
                 bg=PANEL, fg=TENUE, font=F_PEQ, justify="left").pack(side="bottom", anchor="w")

        derecha = tk.Frame(self.cuerpo, bg=FONDO)
        derecha.grid(row=0, column=1, sticky="nsew")
        derecha.columnconfigure(0, weight=1)
        derecha.rowconfigure(1, weight=1)
        self.kpis = PanelKpis(derecha, columnas=3)
        self.kpis.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        self.grafico = Grafico(derecha)
        self.grafico.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.marco_tabla = tk.Frame(derecha, bg=FONDO)
        self.marco_tabla.grid(row=2, column=0, sticky="ew")
        self.crear_nota(derecha).grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.after(80, self._calcular)

    def _programar(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(220, self._calcular)

    def _normalizar(self, campo):
        try:
            self.variables[campo.clave].set(numero_campo(leer_numero(self.variables[campo.clave].get()), campo.tipo))
        except ValueError:
            pass

    def _calcular(self):
        self._pendiente = None
        valores = {}
        for campo in self.definicion.campos:
            entrada = self.entradas[campo.clave]
            try:
                x = leer_numero(self.variables[campo.clave].get())
                if campo.minimo is not None and x < campo.minimo:
                    raise ValueError(f"«{campo.etiqueta}» debe ser al menos {numero_campo(campo.minimo, campo.tipo)}.")
                if campo.maximo is not None and x > campo.maximo:
                    raise ValueError(f"«{campo.etiqueta}» no puede superar {numero_campo(campo.maximo, campo.tipo)}.")
            except ValueError as error:
                entrada.config(highlightbackground=ERROR, highlightcolor=ERROR)
                self.poner_nota(str(error) if str(error).startswith("«") else f"«{campo.etiqueta}»: {error}", "error")
                return
            entrada.config(highlightbackground=BORDE, highlightcolor=self.color)
            valores[campo.clave] = int(round(x)) if campo.tipo == "entero" else x
        try:
            resultado = self.definicion.calcular(valores)
        except ValueError as error:
            self.poner_nota(str(error), "error")
            return
        self.kpis.poner(resultado.kpis, self.color)
        if resultado.grafico:
            self.grafico.mostrar(resultado.grafico)
        self._pintar_tabla(resultado.tabla)
        self.poner_nota(resultado.nota, resultado.nivel)

    def _pintar_tabla(self, tabla):
        for w in self.marco_tabla.winfo_children():
            w.destroy()
        if not tabla:
            return
        encabezados, filas = tabla
        for j, t in enumerate(encabezados):
            tk.Label(self.marco_tabla, text=t.upper(), bg=FONDO, fg=TENUE, font=F_PEQ).grid(row=0, column=j, sticky="w", padx=(0, 24))
        for i, fila in enumerate(filas, 1):
            for j, t in enumerate(fila):
                tk.Label(self.marco_tabla, text=t, bg=FONDO, fg=TEXTO if j == 0 else self.color,
                         font=F_UI_B).grid(row=i, column=j, sticky="w", padx=(0, 24))


# ======================================================================
# Deudas: compara avalancha y bola de nieve con las deudas del usuario
# ======================================================================
class VentanaDeudas(VentanaBase):
    EJEMPLO = [("Tarjeta", 3000000, 28, 150000), ("Moto", 6000000, 18, 300000), ("Celular", 1200000, 12, 100000)]

    def __init__(self, master, color, metodo):
        nombre = "avalancha" if metodo == "avalancha" else "bola de nieve"
        super().__init__(master, f"Método {nombre}",
                         "Escribe tus deudas y compara cuánto tardas y cuántos intereses pagas con cada método.",
                         color, ancho=1200, alto=720)
        self.metodo = metodo
        self._pendiente = None
        self.filas = []
        self.cuerpo.columnconfigure(1, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)

        formulario = tk.Frame(self.cuerpo, bg=PANEL, width=490, padx=16, pady=14,
                              highlightthickness=1, highlightbackground=BORDE)
        formulario.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        formulario.pack_propagate(False)
        tk.Label(formulario, text="TUS DEUDAS", bg=PANEL, fg=TENUE, font=F_PEQ).pack(anchor="w", pady=(0, 6))
        tabla = tk.Frame(formulario, bg=PANEL)
        tabla.pack(fill="x")
        for j, t in enumerate(["Nombre", "Saldo ($)", "Tasa EA %", "Mínimo ($)"]):
            tk.Label(tabla, text=t.upper(), bg=PANEL, fg=TENUE, font=F_PEQ).grid(row=0, column=j, sticky="w", padx=3)
        for i in range(5):
            datos = self.EJEMPLO[i] if i < len(self.EJEMPLO) else ("", "", "", "")
            vars_fila = []
            for j, (valor, ancho, alin) in enumerate(zip(datos, (8, 10, 6, 9), ("left", "right", "right", "right"))):
                texto = "" if valor == "" else (str(valor) if j == 0 else numero_campo(valor, "dinero" if j != 2 else "numero"))
                v = tk.StringVar(value=texto)
                e = crear_entrada(tabla, v, color, ancho=ancho, alineacion=alin)
                e.grid(row=i + 1, column=j, padx=3, pady=3, ipady=4)
                e.bind("<KeyRelease>", lambda ev: self._programar())
                vars_fila.append(v)
            self.filas.append(vars_fila)
        fila = tk.Frame(formulario, bg=PANEL)
        fila.pack(fill="x", pady=(14, 0))
        tk.Label(fila, text="Dinero extra al mes ($)", bg=PANEL, fg=TEXTO, font=F_UI_B).pack(side="left")
        self.extra = tk.StringVar(value="200.000")
        e = crear_entrada(fila, self.extra, color, ancho=12)
        e.pack(side="right", ipady=4)
        e.bind("<KeyRelease>", lambda ev: self._programar())
        tk.Label(formulario, text=("Cómo funciona\n\n• Pagas el mínimo de todas las deudas.\n"
                 "• El dinero extra va a la deuda prioritaria:\n   avalancha → la de mayor tasa;\n"
                 "   bola de nieve → la de menor saldo.\n• Al liquidar una deuda, su cuota pasa a la siguiente.\n\n"
                 "Deja filas vacías si tienes menos de 5 deudas."),
                 bg=PANEL, fg=TENUE, font=F_PEQ, justify="left").pack(side="bottom", anchor="w")

        derecha = tk.Frame(self.cuerpo, bg=FONDO)
        derecha.grid(row=0, column=1, sticky="nsew")
        derecha.columnconfigure(0, weight=1)
        derecha.rowconfigure(1, weight=1)
        self.kpis = PanelKpis(derecha, columnas=3)
        self.kpis.grid(row=0, column=0, sticky="ew")
        self.grafico = Grafico(derecha)
        self.grafico.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.crear_nota(derecha).grid(row=2, column=0, sticky="ew")
        self.after(80, self._calcular)

    def _programar(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(250, self._calcular)

    def _leer(self):
        deudas = []
        for i, (vn, vs, vt, vm) in enumerate(self.filas, 1):
            if not vs.get().strip() and not vn.get().strip() and not vt.get().strip() and not vm.get().strip():
                continue
            try:
                saldo, tasa, minimo = leer_numero(vs.get()), leer_numero(vt.get()), leer_numero(vm.get())
            except ValueError:
                raise ValueError(f"Fila {i}: completa saldo, tasa y mínimo con números.") from None
            if saldo <= 0 or minimo <= 0 or tasa < 0:
                raise ValueError(f"Fila {i}: el saldo y el mínimo deben ser mayores que 0 y la tasa no puede ser negativa.")
            deudas.append(dict(nombre=vn.get().strip() or f"Deuda {i}", saldo=saldo, tasa_ea=tasa / 100, minimo=minimo))
        if not deudas:
            raise ValueError("Agrega al menos una deuda.")
        try:
            extra = leer_numero(self.extra.get())
        except ValueError:
            raise ValueError("Escribe el dinero extra (puede ser 0).") from None
        if extra < 0:
            raise ValueError("El dinero extra no puede ser negativo.")
        return deudas, extra

    def _calcular(self):
        self._pendiente = None
        try:
            deudas, extra = self._leer()
        except ValueError as error:
            self.poner_nota(str(error), "error")
            return
        a = c.simular_deudas(deudas, extra, "avalancha")
        b = c.simular_deudas(deudas, extra, "bola_nieve")
        if not (a["viable"] and b["viable"]):
            self.poner_nota("Con estos pagos las deudas nunca se terminan: el mínimo no alcanza a cubrir los intereses. "
                            "Sube el mínimo o el dinero extra.", "error")
            return
        sel_a, sel_b = self.metodo == "avalancha", self.metodo == "bola_nieve"
        diferencia = b["intereses"] - a["intereses"]
        self.kpis.poner([
            (("★ " if sel_a else "") + "Avalancha: tiempo", c.meses_a_texto(a["meses"]), ESMERALDA),
            (("★ " if sel_a else "") + "Avalancha: intereses", moneda(a["intereses"]), ESMERALDA),
            ("Pago mensual total", moneda(sum(d["minimo"] for d in deudas) + extra), ORO),
            (("★ " if sel_b else "") + "Bola de nieve: tiempo", c.meses_a_texto(b["meses"]), CIELO),
            (("★ " if sel_b else "") + "Bola de nieve: intereses", moneda(b["intereses"]), CIELO),
            ("Diferencia", moneda(abs(diferencia)), CORAL if diferencia > 0 else ESMERALDA),
        ], self.color)
        n = max(len(a["saldos"]), len(b["saldos"]))
        relleno = lambda s: s + [0.0] * (n - len(s))
        paso = max(1, (n - 1) // 4)
        marcas = [(i, f"Mes {i}") for i in range(0, n, paso)]
        self.grafico.mostrar({"tipo": "lineas", "etiquetas_x": marcas, "series": [
            {"nombre": "Avalancha", "valores": relleno(a["saldos"]), "color": ESMERALDA, "relleno": sel_a},
            {"nombre": "Bola de nieve", "valores": relleno(b["saldos"]), "color": CIELO, "relleno": sel_b}]})
        orden = lambda r: "  →  ".join(f"{nombre} (mes {mes})" for nombre, mes in r["orden"])
        if diferencia > 1:
            conclusion = f"La avalancha te ahorra {moneda(diferencia)} en intereses frente a la bola de nieve."
        elif diferencia < -1:
            conclusion = f"En este caso la bola de nieve cuesta {moneda(-diferencia)} menos en intereses."
        else:
            conclusion = "Ambos métodos cuestan lo mismo en este caso."
        plazo = ("" if a["meses"] == b["meses"] else
                 f" Terminas {'antes' if a['meses'] < b['meses'] else 'después'} con la avalancha.")
        self.poner_nota(f"{conclusion}{plazo}\nAvalancha: {orden(a)}\nBola de nieve: {orden(b)}",
                        "ok" if (diferencia > 0) == sel_a else "info")


# ======================================================================
# Listas de verificación (diagnóstico y seguridad)
# ======================================================================
class VentanaChecklist(VentanaBase):
    def __init__(self, master, clave, color, al_resultado=None, marcas=None):
        self.datos = LISTAS[clave]
        super().__init__(master, self.datos["titulo"], self.datos["subtitulo"], color, ancho=1000, alto=680)
        self.items = self.datos["items"]
        self.al_resultado = al_resultado if self.datos.get("genera_plan") else None
        self.marcas = list(marcas) if marcas and len(marcas) == len(self.items) else [False] * len(self.items)
        self.cuerpo.columnconfigure(0, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)

        izquierda = tk.Frame(self.cuerpo, bg=FONDO)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.cajas = []
        for i, (texto, _) in enumerate(self.items):
            fila = tk.Frame(izquierda, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE, cursor="hand2")
            fila.pack(fill="x", pady=4, ipady=6)
            caja = tk.Canvas(fila, width=30, height=30, bg=TARJETA, highlightthickness=0, cursor="hand2")
            caja.pack(side="left", padx=(12, 10))
            etiqueta = tk.Label(fila, text=texto, bg=TARJETA, fg=TEXTO, font=F_TEXTO, anchor="w",
                                justify="left", wraplength=480, cursor="hand2")
            etiqueta.pack(side="left", fill="x", expand=True)
            for w in (fila, caja, etiqueta):
                w.bind("<Button-1>", lambda e, k=i: self._alternar(k))
            self.cajas.append(caja)

        derecha = tk.Frame(self.cuerpo, bg=PANEL, width=360, padx=18, pady=14,
                           highlightthickness=1, highlightbackground=BORDE)
        derecha.grid(row=0, column=1, sticky="ns")
        derecha.pack_propagate(False)
        self.grafico = Grafico(derecha, height=230)
        self.grafico.pack(fill="x")
        self.nivel = tk.Label(derecha, text="", bg=PANEL, font=("Georgia", 18, "bold"))
        self.nivel.pack(anchor="w", pady=(14, 2))
        self.mensaje = tk.Label(derecha, text="", bg=PANEL, fg=TEXTO, font=F_UI, wraplength=320, justify="left")
        self.mensaje.pack(anchor="w")
        tk.Label(derecha, text="SIGUIENTE PASO", bg=PANEL, fg=TENUE, font=F_PEQ).pack(anchor="w", pady=(16, 4))
        self.paso = tk.Label(derecha, text="", bg=PANEL, fg=color, font=F_UI_B, wraplength=320, justify="left")
        self.paso.pack(anchor="w")
        if self.al_resultado is not None:       # el diagnóstico genera el plan de acción de la persona
            self.boton_plan = BotonRedondeado(derecha, "Crear mi plan de acción", self._crear_plan, color=color,
                                              ancho=320, alto=44, fondo=PANEL)
            self.boton_plan.pack(side="bottom", pady=(8, 0))
            tk.Label(derecha, text="Lo que no marques se vuelve un paso de tu plan, ordenado por urgencia.",
                     bg=PANEL, fg=TENUE, font=F_PEQ, wraplength=320, justify="left").pack(side="bottom", anchor="w")
        self._actualizar()

    def _crear_plan(self):
        self.al_resultado(list(self.marcas))
        self.destroy()

    def _alternar(self, i):
        self.marcas[i] = not self.marcas[i]
        self._actualizar()

    def _actualizar(self):
        for caja, marcada in zip(self.cajas, self.marcas):
            caja.delete("all")
            rect_redondo(caja, 3, 3, 27, 27, r=8, fill=self.color if marcada else TARJETA,
                         outline=self.color if marcada else TENUE, width=2)
            if marcada:
                caja.create_text(15, 15, text="✓", fill=FONDO, font=("Segoe UI", 13, "bold"))
        n, total = sum(self.marcas), len(self.marcas)
        fraccion = n / total
        nombre, mensaje, color_nivel = next((nom, msg, col) for umbral, nom, msg, col in self.datos["niveles"]
                                            if fraccion < umbral)
        items = [("Cumples", n, color_nivel)] if n else []
        if total - n:
            items.append(("Pendiente", total - n, mezclar(BORDE, TARJETA, 0.2)))
        self.grafico.mostrar({"tipo": "dona", "items": items, "centro": (f"{n}/{total}", "cumplidos")})
        self.nivel.config(text=nombre, fg=color_nivel)
        self.mensaje.config(text=mensaje)
        pendiente = next((consejo for (_, consejo), m in zip(self.items, self.marcas) if not m), None)
        self.paso.config(text=pendiente or self.datos["completo"])


# ======================================================================
# Detector de fraudes (quiz)
# ======================================================================
class VentanaFraudes(VentanaBase):
    def __init__(self, master, color):
        super().__init__(master, "Detector de fraudes",
                         "Lee cada mensaje y decide si es un fraude o si es legítimo. Entrena el ojo antes de que lo necesites.",
                         color, ancho=900, alto=700)
        self.casos = CASOS_FRAUDE
        self._reiniciar()

    def _reiniciar(self):
        self.indice, self.resultados = 0, []
        self._mostrar_caso()

    def _limpiar(self):
        for w in self.cuerpo.winfo_children():
            w.destroy()

    def _puntos(self, padre):
        lienzo = tk.Canvas(padre, width=26 * len(self.casos), height=18, bg=FONDO, highlightthickness=0)
        for i in range(len(self.casos)):
            x = 10 + i * 26
            if i < len(self.resultados):
                col, relleno = (ESMERALDA if self.resultados[i] else CORAL), True
            else:
                col, relleno = (self.color if i == self.indice else TENUE), False
            lienzo.create_oval(x - 6, 3, x + 6, 15, outline=col, width=2, fill=col if relleno else "")
        return lienzo

    def _mostrar_caso(self):
        self._limpiar()
        caso = self.casos[self.indice]
        contenedor = tk.Frame(self.cuerpo, bg=FONDO)
        contenedor.pack(fill="both", expand=True, padx=40)
        cab = tk.Frame(contenedor, bg=FONDO)
        cab.pack(fill="x", pady=(6, 12))
        tk.Label(cab, text=f"CASO {self.indice + 1} DE {len(self.casos)}", bg=FONDO, fg=TENUE, font=F_PEQ).pack(side="left")
        self._puntos(cab).pack(side="right")

        tarjeta = tk.Frame(contenedor, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE, padx=26, pady=22)
        tarjeta.pack(fill="x")
        fila = tk.Frame(tarjeta, bg=TARJETA)
        fila.pack(fill="x")
        tk.Label(fila, text=caso["canal"].upper(), bg=mezclar(self.color, TARJETA, 0.75), fg=self.color,
                 font=F_PEQ, padx=10, pady=3).pack(side="left")
        tk.Label(fila, text=caso["remitente"], bg=TARJETA, fg=TENUE, font=F_UI).pack(side="left", padx=12)
        tk.Label(tarjeta, text=caso["texto"], bg=TARJETA, fg=TEXTO, font=("Georgia", 14), wraplength=720,
                 justify="left").pack(anchor="w", pady=(16, 0))

        self.botones = tk.Frame(contenedor, bg=FONDO)
        self.botones.pack(pady=18)
        BotonRedondeado(self.botones, "⚑  Es un fraude", lambda: self._responder(True), color=CORAL,
                        ancho=250, alto=46, fondo=FONDO).pack(side="left", padx=8)
        BotonRedondeado(self.botones, "✓  Es legítimo", lambda: self._responder(False), color=ESMERALDA,
                        ancho=250, alto=46, fondo=FONDO).pack(side="left", padx=8)
        self.resultado = tk.Frame(contenedor, bg=FONDO)
        self.resultado.pack(fill="x")

    def _responder(self, dice_fraude):
        caso = self.casos[self.indice]
        acierto = dice_fraude == caso["fraude"]
        self.resultados.append(acierto)
        for w in self.botones.winfo_children():
            w.habilitar(False)
        color = ESMERALDA if acierto else CORAL
        caja = tk.Frame(self.resultado, bg=mezclar(color, FONDO, 0.88), highlightthickness=1,
                        highlightbackground=mezclar(color, FONDO, 0.45), padx=22, pady=16)
        caja.pack(fill="x")
        verdad = "Era un fraude" if caso["fraude"] else "Era legítimo"
        tk.Label(caja, text=("✓  ¡Correcto! " if acierto else "✕  No exactamente. ") + verdad + ".",
                 bg=caja["bg"], fg=color, font=("Georgia", 14, "bold")).pack(anchor="w")
        tk.Label(caja, text=caso["explicacion"], bg=caja["bg"], fg=TEXTO, font=F_UI, wraplength=700,
                 justify="left").pack(anchor="w", pady=(6, 8))
        fila = tk.Frame(caja, bg=caja["bg"])
        fila.pack(anchor="w")
        for senal in caso["senales"]:
            tk.Label(fila, text=senal, bg=mezclar(color, FONDO, 0.7), fg=TEXTO, font=F_PEQ, padx=8,
                     pady=3).pack(side="left", padx=(0, 6))
        ultimo = self.indice == len(self.casos) - 1
        BotonRedondeado(self.resultado, "Ver resultado  ▸" if ultimo else "Siguiente caso  ▸", self._siguiente,
                        color=self.color, ancho=220, alto=40, fondo=FONDO).pack(anchor="e", pady=12)

    def _siguiente(self):
        if self.indice == len(self.casos) - 1:
            self._final()
        else:
            self.indice += 1
            self._mostrar_caso()

    def _final(self):
        self._limpiar()
        aciertos = sum(self.resultados)
        total = len(self.casos)
        if aciertos == total:
            nombre, color = "¡Ojo de halcón!", ESMERALDA
            mensaje = "Identificaste todos los casos. Sigue desconfiando de la urgencia y de las promesas irreales."
        elif aciertos >= total - 2:
            nombre, color = "Buen criterio", CIELO
            mensaje = "Detectas la mayoría. Repasa los casos que fallaste: casi siempre se repite la misma señal."
        else:
            nombre, color = "A entrenar más", ORO
            mensaje = "Los estafadores cuentan con eso. Recuerda: urgencia, enlaces y códigos son las alarmas."
        cont = tk.Frame(self.cuerpo, bg=FONDO)
        cont.pack(expand=True)
        tk.Label(cont, text=f"{aciertos} / {total}", bg=FONDO, fg=color, font=("Georgia", 54, "bold")).pack()
        tk.Label(cont, text=nombre, bg=FONDO, fg=TEXTO, font=("Georgia", 20, "bold")).pack()
        tk.Label(cont, text=mensaje, bg=FONDO, fg=TENUE, font=F_TEXTO, wraplength=520, justify="center").pack(pady=(8, 16))
        for caso, ok in zip(self.casos, self.resultados):
            tk.Label(cont, text=f"{'✓' if ok else '✕'}  {caso['canal']}: {'fraude' if caso['fraude'] else 'legítimo'}",
                     bg=FONDO, fg=ESMERALDA if ok else CORAL, font=F_UI).pack(anchor="w")
        BotonRedondeado(cont, "↻  Intentar de nuevo", self._reiniciar, color=self.color, ancho=240, alto=42,
                        fondo=FONDO).pack(pady=18)


# ======================================================================
# Registro de gastos (se guarda en un archivo junto a la aplicación)
# ======================================================================
class VentanaRegistro(VentanaBase):
    def __init__(self, master, color, ruta):
        super().__init__(master, "Registro de gastos",
                         "Anota cada gasto en el momento. Verás cuánto llevas y en qué categoría se concentra.",
                         color, ancho=1040, alto=700)
        self.ruta = Path(ruta)
        self.registros = self._cargar()
        self.cuerpo.columnconfigure(1, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)

        izquierda = tk.Frame(self.cuerpo, bg=PANEL, width=360, padx=18, pady=14,
                             highlightthickness=1, highlightbackground=BORDE)
        izquierda.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        izquierda.pack_propagate(False)
        tk.Label(izquierda, text="NUEVO GASTO", bg=PANEL, fg=TENUE, font=F_PEQ).pack(anchor="w")
        self.concepto, self.monto = tk.StringVar(), tk.StringVar()
        self.categoria = tk.StringVar(value=CATEGORIAS_GASTO[0])
        tk.Label(izquierda, text="Concepto", bg=PANEL, fg=TEXTO, font=F_UI).pack(anchor="w", pady=(8, 2))
        e1 = crear_entrada(izquierda, self.concepto, color, ancho=30, alineacion="left")
        e1.pack(fill="x", ipady=5)
        tk.Label(izquierda, text="Categoría", bg=PANEL, fg=TEXTO, font=F_UI).pack(anchor="w", pady=(8, 2))
        menu = tk.OptionMenu(izquierda, self.categoria, *CATEGORIAS_GASTO)
        menu.config(bg=TARJETA, fg=TEXTO, activebackground=TARJETA, activeforeground=color, relief="flat",
                    highlightthickness=1, highlightbackground=BORDE, font=F_UI, anchor="w")
        menu["menu"].config(bg=PANEL, fg=TEXTO, font=F_UI, activebackground=color, activeforeground=FONDO, bd=0)
        menu.pack(fill="x")
        tk.Label(izquierda, text="Monto ($)", bg=PANEL, fg=TEXTO, font=F_UI).pack(anchor="w", pady=(8, 2))
        e2 = crear_entrada(izquierda, self.monto, color, ancho=30)
        e2.pack(fill="x", ipady=5)
        e2.bind("<Return>", lambda e: self._agregar())
        e1.bind("<Return>", lambda e: e2.focus_set())
        self.aviso = tk.Label(izquierda, text="", bg=PANEL, fg=ERROR, font=F_PEQ, wraplength=320, justify="left")
        BotonRedondeado(izquierda, "＋  Agregar gasto", self._agregar, color=color, ancho=324, alto=38).pack(pady=(12, 2))
        self.aviso.pack(anchor="w")
        BotonRedondeado(izquierda, "✕  Quitar el seleccionado", self._quitar, color=ERROR, ancho=324,
                        alto=34).pack(side="bottom", pady=(10, 0))
        tk.Label(izquierda, text="GASTOS REGISTRADOS", bg=PANEL, fg=TENUE, font=F_PEQ).pack(anchor="w", pady=(10, 4))
        marco = tk.Frame(izquierda, bg=BORDE)
        marco.pack(fill="both", expand=True)
        self.lista = tk.Listbox(marco, bg=TARJETA, fg=TEXTO, relief="flat", font=F_UI, highlightthickness=0,
                                activestyle="none", selectbackground=mezclar(color, TARJETA, 0.6),
                                selectforeground=TEXTO, borderwidth=0)
        barra = tk.Scrollbar(marco, command=self.lista.yview)
        self.lista.config(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lista.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        derecha = tk.Frame(self.cuerpo, bg=FONDO)
        derecha.grid(row=0, column=1, sticky="nsew")
        derecha.columnconfigure(0, weight=1)
        derecha.rowconfigure(1, weight=1)
        self.kpis = PanelKpis(derecha, columnas=3)
        self.kpis.grid(row=0, column=0, sticky="ew")
        self.grafico = Grafico(derecha)
        self.grafico.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.crear_nota(derecha).grid(row=2, column=0, sticky="ew")
        self._actualizar()

    def _cargar(self):
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            return [r for r in datos if {"concepto", "categoria", "monto"} <= set(r)]
        except (OSError, ValueError, TypeError):
            return []

    def _guardar(self):
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump(self.registros, f, ensure_ascii=False, indent=2)
        except OSError:
            self.aviso.config(text="No se pudo guardar el archivo (solo quedará en esta sesión).")

    def _agregar(self):
        try:
            monto = leer_numero(self.monto.get())
            if monto <= 0:
                raise ValueError
        except ValueError:
            self.aviso.config(text="Escribe un monto mayor que 0.")
            return
        concepto = self.concepto.get().strip() or "Sin concepto"
        self.registros.append({"concepto": concepto, "categoria": self.categoria.get(), "monto": monto})
        self.concepto.set("")
        self.monto.set("")
        self.aviso.config(text="")
        self._guardar()
        self._actualizar()

    def _quitar(self):
        seleccion = self.lista.curselection()
        if not seleccion:
            return
        del self.registros[len(self.registros) - 1 - seleccion[0]]     # la lista muestra lo más reciente primero
        self._guardar()
        self._actualizar()

    def _actualizar(self):
        self.lista.delete(0, "end")
        for r in reversed(self.registros):
            self.lista.insert("end", f"  {r['concepto']}  ·  {r['categoria']}  ·  {moneda(r['monto'])}")
        totales = {cat: 0.0 for cat in CATEGORIAS_GASTO}
        for r in self.registros:
            totales[r["categoria"]] = totales.get(r["categoria"], 0.0) + r["monto"]
        total = sum(totales.values())
        mayor = max(totales, key=totales.get)
        self.kpis.poner([("Total gastado", moneda(total), CORAL),
                         ("Gastos anotados", str(len(self.registros)), CIELO),
                         ("Categoría mayor", mayor if total else "—", ORO)], self.color)
        self.grafico.mostrar({"tipo": "barras",
                              "items": [(cat, totales[cat], CATEGORIAS[i % len(CATEGORIAS)])
                                        for i, cat in enumerate(CATEGORIAS_GASTO)]})
        if not self.registros:
            self.poner_nota("Aún no hay gastos. Anota el primero: el hábito de registrar vale más que el monto.", "info")
        else:
            peso = totales[mayor] / total * 100
            self.poner_nota(f"«{mayor}» concentra el {peso:.0f}% de lo que has anotado. "
                            "Revisa si coincide con lo que creías gastar ahí.", "aviso" if peso > 50 else "info")


# ======================================================================
# Puerta de entrada desde el árbol
# ======================================================================
TITULOS = {**{k: d.titulo for k, d in DEFINICIONES.items()},
           **{k: v["titulo"] for k, v in LISTAS.items()},
           "fraudes": "Detector de fraudes", "registro_gastos": "Registro de gastos",
           "deudas_avalancha": "Simulador de deudas", "deudas_bola_nieve": "Simulador de deudas"}


def abrir_herramienta(master, clave, color, carpeta_datos, al_resultado=None, marcas=None):
    """Abre la ventana de la herramienta asociada a un nodo. `al_resultado` y `marcas` solo los usa el
    diagnóstico de salud financiera (recibe las respuestas y genera el plan; `marcas` precarga el anterior)."""
    if clave in DEFINICIONES:
        return VentanaCalculadora(master, DEFINICIONES[clave], color)
    if clave in LISTAS:
        return VentanaChecklist(master, clave, color, al_resultado, marcas)
    if clave == "fraudes":
        return VentanaFraudes(master, color)
    if clave in ("deudas_avalancha", "deudas_bola_nieve"):
        return VentanaDeudas(master, color, "avalancha" if clave.endswith("avalancha") else "bola_nieve")
    if clave == "registro_gastos":
        return VentanaRegistro(master, color, Path(carpeta_datos) / "registro_gastos.json")
    raise KeyError(clave)
