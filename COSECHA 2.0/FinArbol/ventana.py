"""Ventana principal de Cosecha: une el árbol, la IA de Ollama, el escenario y las herramientas.

Flujo de una conversación:
  1. La IA saluda y el programa muestra la PRIMERA PREGUNTA puntual (la «pregunta» de la raíz) con un
     botón de respuesta por cada hijo del nodo actual.
  2. La persona toca una respuesta (o escribe con sus palabras y la IA decide). La guía baja un nivel del
     árbol y aparece la pregunta del siguiente nivel: así se va filtrando hasta un tema final (hoja).
  3. En el tema final la IA explica el concepto y pregunta si quiere practicar con su calculadora.
Los hilos de trabajo hablan con Ollama; la interfaz recibe sus resultados por una cola.
"""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from asistente import AsistenteFinanciero
from ayuda import GuiaRapida
from chat import PanelChat
from componentes import BotonRedondeado, dibujar_logo
from conocimiento import BaseConocimiento
from escenario import Escenario
from estilos import (BORDE, CORAL, ERROR, ESMERALDA, F_PEQ, F_TITULO, F_UI, FONDO, ORO, PANEL, TARJETA, TENUE, TEXTO,
                     CIELO, VIOLETA, color_de_nodo, mezclar)
from grafo import GrafoTemas
from guia import GuiaArbol
from ia_ollama import ClienteOllama, ErrorOllama
from minimapa import MiniMapa
from plan import NOMBRES_PRIORIDAD, PlanPrioridades
from repositorio import RepositorioJSON
from ventana_grafo import MapaRelaciones
from ventana_plan import VentanaPlan
from ventanas_herramienta import TITULOS, abrir_herramienta


class AplicacionCosecha(tk.Tk):
    def __init__(self, ruta_json, carpeta_datos=None):
        super().__init__()
        self.title("Cosecha · Guía de finanzas personales")
        ancho = min(1440, self.winfo_screenwidth() - 40)
        alto = min(840, self.winfo_screenheight() - 80)
        self.geometry(f"{ancho}x{alto}")
        self.minsize(1280, 700)
        self.configure(bg=FONDO)

        self.carpeta = Path(carpeta_datos or Path(ruta_json).parent)
        try:
            # [ÁRBOL] El JSON se convierte en un árbol de nodos enlazados.
            self.arbol = RepositorioJSON(ruta_json).cargar()
            # [GRAFO] Las relaciones entre temas del JSON forman un grafo dirigido con ciclos.
            self.grafo = GrafoTemas.desde_arbol(self.arbol)
            self.base = BaseConocimiento(self.carpeta / "ConocimientoIA.txt", ruta_json)
        except (OSError, ValueError) as error:
            messagebox.showerror("Cosecha", f"No se pudo cargar la información:\n{error}")
            self.destroy()
            raise SystemExit(1)
        self.cliente = ClienteOllama()
        self.asistente = AsistenteFinanciero(self.cliente, self.base)
        self.guia = GuiaArbol(self.arbol)
        # [LISTA DOBLE] «Mi plan de acción»: lo genera el diagnóstico de salud financiera; los pasos quedan ordenados
        # por prioridad en una lista doblemente enlazada.
        self.plan = PlanPrioridades(self.arbol, self.carpeta / "plan.json")
        self._v_plan = None
        self.asistente.contexto_plan = lambda: self.plan.resumen(self.guia.actual)   # la IA conoce el diagnóstico
        self._v_grafo = None

        self._cola = queue.Queue()      # resultados que llegan desde los hilos que hablan con Ollama
        self._generacion = 0            # sube cada vez que la persona cambia de rumbo (descarta respuestas viejas)
        self._burbuja = None            # burbuja de la IA que se está escribiendo
        self._conectado = False
        self._sugerido = None           # tema relacionado que la IA le propuso a la persona
        self._situacion = ""           # qué está explicando la IA ahora mismo
        self._ventanas = {}
        self._pulso = 0.0

        self._construir()
        self.minimapa.usar(self.guia)
        self.after(30, self._revisar_cola)
        self.after(60, self._arrancar)
        self._latido_boton()

    # ==================================================================
    # Construcción de la interfaz
    # ==================================================================
    def _construir(self):
        barra = tk.Frame(self, bg=FONDO)
        barra.pack(fill="x", padx=20, pady=(16, 12))
        logo = tk.Canvas(barra, width=46, height=46, bg=FONDO, highlightthickness=0)
        logo.pack(side="left")
        dibujar_logo(logo, 46)
        titulos = tk.Frame(barra, bg=FONDO)
        titulos.pack(side="left", padx=12)
        fila = tk.Frame(titulos, bg=FONDO)
        fila.pack(anchor="w")
        tk.Label(fila, text="Cose", bg=FONDO, fg=TEXTO, font=F_TITULO, padx=0, bd=0).pack(side="left")
        tk.Label(fila, text="cha", bg=FONDO, fg=ESMERALDA, font=F_TITULO, padx=0, bd=0).pack(side="left")
        tk.Label(titulos, text="Tu guía de finanzas personales con inteligencia artificial", bg=FONDO, fg=TENUE,
                 font=F_UI).pack(anchor="w")

        derecha = tk.Frame(barra, bg=FONDO)
        derecha.pack(side="right")
        BotonRedondeado(derecha, "↺  Reiniciar", self._reiniciar, color=ORO, ancho=104, alto=36,
                        fondo=FONDO).pack(side="right", padx=(8, 0))
        BotonRedondeado(derecha, "Guía rápida", self._abrir_guia, color=CIELO, ancho=108, alto=36,
                        fondo=FONDO).pack(side="right", padx=(8, 0))
        BotonRedondeado(derecha, "Lo que sabe la IA", self._ver_conocimiento, color=ESMERALDA, ancho=142, alto=36,
                        fondo=FONDO).pack(side="right", padx=(8, 0))
        BotonRedondeado(derecha, "Relaciones", self._abrir_grafo, color=VIOLETA, ancho=104, alto=36,
                        fondo=FONDO).pack(side="right", padx=(8, 0))
        self.b_plan = BotonRedondeado(derecha, "", self._abrir_plan, color=CORAL, ancho=104, alto=36, fondo=FONDO)
        self.b_plan.pack(side="right", padx=(8, 0))
        self._actualizar_plan()
        self.estado = tk.Label(derecha, text="● Conectando con Ollama…", bg=FONDO, fg=TENUE, font=("Segoe UI", 10, "bold"),
                               cursor="hand2", padx=12)
        self.estado.pack(side="right")
        self.estado.bind("<Button-1>", lambda e: self._conectar())

        cuerpo = tk.Frame(self, bg=FONDO)
        cuerpo.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.rowconfigure(0, weight=1)

        self.minimapa = MiniMapa(cuerpo, self.arbol)
        self.minimapa.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.minimapa.config(width=270)
        self.minimapa.pack_propagate(False)

        centro = tk.Frame(cuerpo, bg=FONDO)
        centro.grid(row=0, column=1, sticky="nsew")
        self.escenario = Escenario(centro, self._al_tocar_tarjeta, self._al_pasar_tarjeta)
        self.escenario.pack(fill="both", expand=True)
        acciones = tk.Frame(centro, bg=FONDO)
        acciones.pack(fill="x", pady=(10, 0))
        self.b_volver = BotonRedondeado(acciones, "↶  Volver", self._volver, color=TENUE, ancho=110, alto=40, fondo=FONDO)
        self.b_volver.pack(side="left")
        self.b_sugerido = BotonRedondeado(acciones, "", self._aceptar_sugerido, color=ORO, ancho=250, alto=40, fondo=FONDO)
        self.b_practicar = BotonRedondeado(acciones, "", self._practicar, color=ESMERALDA, ancho=330, alto=40, fondo=FONDO)
        self.b_practicar.pack(side="right")

        self.chat = PanelChat(cuerpo, self._al_escribir, self.cliente.modelo)
        self.chat.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        self.chat.config(width=400)
        self.chat.pack_propagate(False)

    # ==================================================================
    # Conexión con Ollama
    # ==================================================================
    def _arrancar(self):
        self.escenario.mostrar(self.guia.actual, self.guia.opciones())
        self._refrescar()
        self._conectar(primera_vez=True)
        marca = self.carpeta / ".guia_vista"
        if not marca.exists():                       # la primera vez se abre sola la guía rápida
            try:
                marca.write_text("ok", encoding="utf-8")
            except OSError:
                pass
            self.after(600, self._abrir_guia)

    def _conectar(self, primera_vez=False):
        self.estado.config(text="● Conectando con Ollama…", fg=TENUE)

        def trabajo():
            try:
                self.cliente.disponible()
                self._cola.put(("conexion", True, ""))
            except ErrorOllama as error:
                self._cola.put(("conexion", False, str(error)))
        threading.Thread(target=trabajo, daemon=True).start()

    def _al_conexion(self, ok, mensaje):
        habia = self._conectado
        self._conectado = ok
        if ok:
            self.estado.config(text=f"● IA conectada · {self.cliente.modelo}", fg=ESMERALDA)
            if not habia and not self.asistente.historial:
                self._narrar("inicio")
        else:
            self.estado.config(text="● IA sin conexión · clic para reintentar", fg=ERROR)
            self.chat.agregar("aviso", mensaje)

    # ==================================================================
    # Conversación: hilos que hablan con la IA
    # ==================================================================
    def _nueva_generacion(self):
        """Invalida lo que la IA estuviera haciendo y limpia la burbuja a medio escribir."""
        self._generacion += 1
        self.chat.cerrar_preguntas()
        if self._burbuja is not None and not self._burbuja.cget("text"):
            self.chat.quitar_burbuja(self._burbuja)
        self._burbuja = None
        self.chat.quitar_escribiendo()

    def _ocupar(self, ocupado, fase="escribiendo"):
        """Muestra qué está haciendo la IA en cada momento (animación del orbe + línea de estado del escenario)."""
        self.chat.habilitar(not ocupado)
        self.escenario.pensar(ocupado)
        if ocupado:
            if fase == "decidiendo":
                self.escenario.poner_leyenda("①  La IA está leyendo tu mensaje para decidir qué hacer: responderte, llevarte a un tema o abrir una calculadora…")
            else:
                self.escenario.poner_leyenda("②  La IA está escribiendo su respuesta en el chat.")
            self.chat.mostrar_escribiendo()
        else:
            if self.guia.es_tema_final:
                self.escenario.poner_leyenda("③  Tu turno: responde en el chat si quieres practicar con la calculadora, o pregunta lo que quieras de este tema.")
            else:
                self.escenario.poner_leyenda("③  Tu turno: toca una respuesta de la pregunta del chat (o una tarjeta numerada), o escribe con tus palabras.")
            self.chat.quitar_escribiendo()

    def _narrar(self, situacion, mensaje="", sugerido=None):
        """La IA escribe (en vivo) la pregunta o explicación que corresponde a la situación."""
        if not self._conectado:
            return
        gen = self._generacion
        self._situacion = situacion
        mensajes = self.asistente.mensajes_redaccion(situacion, self.guia, mensaje, sugerido)
        self._ocupar(True)

        def trabajo():
            try:
                texto = self.asistente.redactar(mensajes, lambda p: self._cola.put(("pedazo", gen, p)),
                                                cancelado=lambda: gen != self._generacion)
                self._cola.put(("fin", gen, texto))
            except ErrorOllama as error:
                self._cola.put(("error", gen, str(error)))
            except (OSError, ValueError) as error:
                self._cola.put(("error", gen, f"Falló la conexión con la IA: {error}"))
        threading.Thread(target=trabajo, daemon=True).start()

    def _decidir(self, texto):
        """La IA lee el mensaje de la persona y decide qué hacer en el árbol."""
        gen = self._generacion
        mensajes = self.asistente.mensajes_decision(self.guia, texto, self._sugerido)
        self._ocupar(True, "decidiendo")

        def trabajo():
            try:
                self._cola.put(("decision", gen, (self.asistente.pedir_decision(mensajes), texto)))
            except ErrorOllama as error:
                self._cola.put(("error", gen, str(error)))
            except (OSError, ValueError) as error:
                self._cola.put(("error", gen, f"Falló la conexión con la IA: {error}"))
        threading.Thread(target=trabajo, daemon=True).start()

    def _revisar_cola(self):
        try:
            while True:
                tipo, *datos = self._cola.get_nowait()
                if tipo == "conexion":
                    self._al_conexion(*datos)
                    continue
                gen, carga = datos
                if gen != self._generacion:
                    continue                         # respuesta de algo que la persona ya dejó atrás
                if tipo == "pedazo":
                    if self._burbuja is None:
                        self.chat.quitar_escribiendo()
                        self._burbuja = self.chat.agregar("ia", "")
                    self.chat.agregar_texto(self._burbuja, carga)
                elif tipo == "fin":
                    if carga:
                        self.asistente.registrar("ia", carga)
                    self._burbuja = None
                    self._concepto_explicado()
                    self._ocupar(False)
                    self._mostrar_pregunta()
                    self.chat.enfocar()
                elif tipo == "decision":
                    self._aplicar_decision(*carga)
                elif tipo == "error":
                    self._burbuja = None
                    self._concepto_explicado()       # la ficha ya está en pantalla aunque la IA haya fallado
                    self._ocupar(False)
                    self.chat.agregar("aviso", carga)
                    if "conectarme" in carga or "modelo" in carga:
                        self._conectado = False
                        self.estado.config(text="● IA sin conexión · clic para reintentar", fg=ERROR)
                    else:
                        self._mostrar_pregunta()
        except queue.Empty:
            pass
        self.after(30, self._revisar_cola)

    def _concepto_explicado(self):
        """Si lo que acaba de decir la IA era la explicación del tema, ya se puede practicar."""
        if self._situacion in ("tema", "concepto"):
            self.guia.marcar_concepto()
            self._refrescar()

    # ==================================================================
    # Lo que la persona hace
    # ==================================================================
    def _al_escribir(self, texto):
        if not self._conectado:
            self.chat.agregar("aviso", "La IA no está conectada. Abre Ollama y toca «IA sin conexión» para reintentar.")
            return
        self._nueva_generacion()
        self.chat.agregar("persona", texto)
        self.asistente.registrar("persona", texto)
        self._decidir(texto)

    def _al_tocar_tarjeta(self, nodo):
        """Clic directo en una tarjeta del escenario: equivale a tocar su respuesta en la pregunta del chat."""
        self._elegir_respuesta(nodo)

    def _elegir_respuesta(self, nodo):
        """La persona contestó la pregunta puntual eligiendo este nodo: la guía baja y la IA narra el nuevo punto."""
        self._nueva_generacion()
        frase = nodo.respuesta
        self.chat.agregar("persona", frase)
        self.asistente.registrar("persona", frase)
        self.guia.ir_a(nodo)
        self._ir(nodo, elegido=nodo, mensaje=frase)

    def _al_inicio(self):
        """Respuesta «volver al inicio»: salta a la raíz para empezar otro filtrado."""
        if self.guia.actual.padre is None:
            return
        self._nueva_generacion()
        self.chat.agregar("persona", "Quiero explorar otra área desde el inicio")
        self.asistente.registrar("persona", "Quiero explorar otra área desde el inicio")
        anterior = self.guia.actual
        self.guia.ir_a(self.arbol.raiz)
        self._sugerido = None
        self.escenario.mostrar(self.arbol.raiz, self.guia.opciones(), elegido=anterior, hacia_arriba=True)
        self._refrescar()
        self._narrar("volver")

    def _mostrar_pregunta(self, repetir=False):
        """[ÁRBOL] El embudo: en una categoría se pregunta la «pregunta» de ese nodo y cada hijo es una respuesta;
        en un tema final se pregunta si quiere practicar. Se muestra después de que la IA termina de escribir.
        [LISTA DOBLE] Si ya hay diagnóstico, se ofrece el siguiente paso del plan personal."""
        if not self._conectado:
            return
        guia, actual, plan = self.guia, self.guia.actual, self.plan
        padre = actual.padre
        if self._situacion == "plan":              # acaba de crearse el plan: se ofrece empezar por el primer paso
            self._pregunta_plan()
            return
        if actual.hijos:
            titulo = f"PREGUNTA {guia.paso} · toca la respuesta que más se parezca a ti"
            pregunta = guia.pregunta
            opciones = [(i, h.respuesta, color_de_nodo(h), lambda h=h: self._elegir_respuesta(h))
                        for i, h in enumerate(guia.opciones(), 1)]
            if padre is None:                       # en la raíz: el atajo hacia el diagnóstico y el plan personal
                texto = ("Quiero rehacer mi diagnóstico de salud financiera" if plan.hay_diagnostico
                         else "Prefiero empezar con un diagnóstico de mi salud financiera")
                opciones.append((len(opciones) + 1, texto, VIOLETA, self._pedir_diagnostico))
                paso = plan.siguiente_paso()
                if paso is not None:
                    opciones.append((len(opciones) + 1, f"Ir al primer paso de mi plan: «{paso.nodo.valor}»", CORAL,
                                     lambda t=paso: self._ir_plan(t)))
            pie = "¿Ninguna encaja? Escríbele a la IA con tus palabras."
        else:
            titulo = "SIGUIENTE PASO · tú decides"
            if plan.contiene(actual):
                titulo = f"SIGUIENTE PASO · este es el paso {plan.posicion(actual)} de tu plan"
            opciones = []
            if self._situacion == "practicar":
                pregunta = "¿Qué quieres hacer ahora?"
            elif guia.puede_practicar:
                clave = actual.herramienta
                pregunta = f"¿Quieres ponerlo en práctica con la calculadora «{TITULOS.get(clave, clave)}»?"
                opciones.append((len(opciones) + 1, "Sí, abrir la calculadora", color_de_nodo(actual), self._practicar))
            else:
                pregunta = "¿Qué quieres hacer ahora?"
            if plan.contiene(actual):               # [LISTA DOBLE] el paso del plan se marca como hecho (se desenlaza)
                opciones.append((len(opciones) + 1, "Ya lo hice: marcarlo como hecho en mi plan", ESMERALDA,
                                 lambda a=actual: self._completar_plan(a)))
            paso = plan.siguiente_paso(actual)
            if paso is not None and paso.nodo is not actual:
                opciones.append((len(opciones) + 1, f"Ir al siguiente paso de mi plan: «{paso.nodo.valor}»", CORAL,
                                 lambda t=paso: self._ir_plan(t)))
            for arista in self.grafo.sugerencias(actual, guia.visitados, 1):     # [GRAFO] temas relacionados
                opciones.append((len(opciones) + 1, f"Seguir con «{arista.destino.valor}»: {arista.motivo}",
                                 color_de_nodo(arista.destino), lambda a=arista: self._ir_relacionado(a)))
            if padre is not None:
                opciones.append((len(opciones) + 1, f"Quiero ver otro tema de «{padre.valor}»", CIELO, self._volver))
            if padre is not None and padre.padre is not None:
                opciones.append((len(opciones) + 1, "Quiero explorar otra área desde el inicio", ORO, self._al_inicio))
            pie = "También puedes escribir tu duda sobre este tema."
        if not opciones:
            return
        self.chat.agregar_pregunta(titulo, pregunta, opciones, pie)
        if not repetir:
            self.asistente.registrar_pregunta(pregunta)

    def _pregunta_plan(self):
        """Tarjeta que aparece cuando la IA terminó de contar el resultado del diagnóstico."""
        plan = self.plan
        paso = plan.siguiente_paso()
        opciones = []
        if paso is not None:
            opciones.append((1, f"Empezar con el paso 1: «{paso.nodo.valor}»", CORAL, lambda t=paso: self._ir_plan(t)))
        opciones.append((len(opciones) + 1, "Ver mi plan completo", VIOLETA, self._abrir_plan))
        if self.guia.actual.padre is None:
            opciones.append((len(opciones) + 1, "Seguir con las preguntas para explorar un área", CIELO, self._seguir_embudo))
        pregunta = "¿Por dónde quieres empezar?" if paso is not None else "¿Qué quieres hacer ahora?"
        self.chat.agregar_pregunta("TU PLAN ESTÁ LISTO", pregunta, opciones, "También puedes escribirle a la IA lo que quieras.")
        self.asistente.registrar_pregunta(pregunta)

    def _seguir_embudo(self):
        """Después del plan, vuelve a mostrar la pregunta de las áreas de la guía."""
        self.chat.cerrar_preguntas()
        self._situacion = ""
        self._mostrar_pregunta(repetir=True)

    def _al_pasar_tarjeta(self, nodo):
        pass

    def _volver(self):
        if self.guia.actual.padre is None:
            return
        self._nueva_generacion()
        self.chat.agregar("persona", "Quiero volver")
        self.asistente.registrar("persona", "Quiero volver")
        self._subir()

    def _reiniciar(self):
        self._nueva_generacion()
        self._sugerido = None
        self.guia.reiniciar()
        self.asistente.reiniciar()
        self.chat.limpiar()
        self.escenario.mostrar(self.guia.actual, self.guia.opciones())
        self._refrescar()
        if self._conectado:
            self._narrar("inicio")
        else:
            self._conectar()

    def _practicar(self, narrar=True):
        if not self.guia.puede_practicar:
            return
        clave = self.guia.actual.herramienta
        existente = self._ventanas.get(clave)
        if existente is not None and existente.winfo_exists():
            existente.lift()
            existente.focus_force()
            return
        try:
            self._ventanas[clave] = abrir_herramienta(self, clave, color_de_nodo(self.guia.actual), self.carpeta,
                                                      self._al_diagnostico, self.plan.marcas)
        except KeyError:
            messagebox.showinfo("Cosecha", f"La herramienta «{clave}» no existe.", parent=self)
            return
        if narrar:                    # el texto que ve la persona lo escribe siempre la IA
            self._nueva_generacion()
            self.chat.agregar("persona", "Quiero practicar")
            self.asistente.registrar("persona", "Quiero practicar")
            self._narrar("practicar")

    # ==================================================================
    # Aplicar lo que decidió la IA
    # ==================================================================
    def _nota_decision(self, d):
        """Una línea que cuenta a la persona qué decidió la IA (para que entienda qué está pasando)."""
        destino = d.nodo.valor if d.nodo else (self.guia.opciones()[d.opcion - 1].valor if d.accion == "elegir" else "")
        textos = {"elegir": f"llevarte al tema «{destino}»",
                  "ir_a": f"llevarte al tema «{destino}»",
                  "responder": "responder tu duda (el escenario no cambia de tema)"
                               + (f"; hay un tema relacionado: «{d.nodo.valor}»" if d.nodo else ""),
                  "ayuda": "explicarte cómo funciona la aplicación",
                  "aclarar": "hacerte una pregunta para entender mejor qué buscas",
                  "volver": "regresar al tema anterior",
                  "practicar": "abrir la calculadora del tema",
                  "concepto": "explicarte primero el concepto antes de abrir la calculadora",
                  "sin_calculadora": "avisarte que este tema no tiene calculadora propia",
                  "fuera_de_tema": "recordarte que aquí hablamos de finanzas personales"}
        razon = f" — {d.razon}" if d.razon else ""
        return f"▸ Decisión de la IA: {textos.get(d.accion, d.accion)}{razon}."

    def _aplicar_decision(self, bruto, texto):
        decision = self.asistente.validar(bruto, self.guia, texto, self._sugerido)   # [ÁRBOL] se valida antes de mover la guía
        self.chat.agregar("nota", self._nota_decision(decision))
        if decision.accion == "elegir":
            nodo = self.guia.elegir(decision.opcion)
            self._ir(nodo, elegido=nodo, mensaje=texto)
        elif decision.accion == "ir_a":                        # salto directo a cualquier tema del árbol
            self.guia.ir_a(decision.nodo)
            self._ir(decision.nodo, elegido=decision.nodo, mensaje=texto)
        elif decision.accion == "volver":
            self._subir()
        elif decision.accion in ("practicar", "concepto") and self.guia.actual.padre is None:
            self._abrir_diagnostico()                          # en la raíz, «practicar» es hacer el diagnóstico
            self._narrar("diagnostico", texto)
        elif decision.accion == "practicar":                   # el concepto ya se explicó: se abre la calculadora
            self._ocupar(False)
            self._practicar(narrar=False)
            self._narrar("practicar", texto)
        elif decision.accion == "responder":                   # responde como una IA normal; el tema es solo una sugerencia
            self._sugerido = decision.nodo
            self._refrescar()
            self._narrar("responder", texto, decision.nodo)
        else:        # ayuda, concepto (primero explicar), sin_calculadora, aclarar o fuera_de_tema
            self._narrar(decision.accion, texto)

    def _aceptar_sugerido(self):
        """Botón «Ver tema»: la persona acepta el tema relacionado que la IA le sugirió."""
        nodo = self._sugerido
        if nodo is None:
            return
        self._nueva_generacion()
        self.chat.agregar("persona", f"Quiero ver el tema «{nodo.valor}»")
        self.asistente.registrar("persona", f"Quiero ver el tema «{nodo.valor}»")
        self.guia.ir_a(nodo)
        self._ir(nodo, elegido=nodo, mensaje=f"Quiero ver el tema «{nodo.valor}»")

    def _abrir_guia(self):
        GuiaRapida(self)

    # ==================================================================
    # Plan de acción (lista doblemente enlazada) y mapa de relaciones (grafo)
    # ==================================================================
    def _actualizar_plan(self):
        self.b_plan.poner_texto(f"Mi plan ({len(self.plan)})")
        if self._v_plan is not None and self._v_plan.winfo_exists():
            self._v_plan.refrescar()

    def _abrir_plan(self):
        if self._v_plan is not None and self._v_plan.winfo_exists():
            self._v_plan.lift()
            self._v_plan.refrescar()
            return
        self._v_plan = VentanaPlan(self, self.plan, self._ir_desde_ventana, self._actualizar_plan,
                                   self._pedir_diagnostico)

    def _abrir_grafo(self):
        if self._v_grafo is not None and self._v_grafo.winfo_exists():
            self._v_grafo.lift()
            return
        self._v_grafo = MapaRelaciones(self, self.grafo, self.arbol, self._ir_desde_ventana, lambda: self.guia.actual)

    def _ir_desde_ventana(self, nodo):
        """Desde «Mi plan» o «Relaciones»: salta a un tema (la IA lo explica como cualquier otro)."""
        self._nueva_generacion()
        frase = f"Quiero ir al tema «{nodo.valor}»"
        self.chat.agregar("persona", frase)
        self.asistente.registrar("persona", frase)
        self.guia.ir_a(nodo)
        self._ir(nodo, elegido=nodo, mensaje=frase)
        self.lift()

    def _abrir_diagnostico(self):
        """Abre (o trae al frente) la ventana del diagnóstico de salud financiera, que vive en la raíz."""
        existente = self._ventanas.get("diagnostico")
        if existente is not None and existente.winfo_exists():
            existente.lift()
            existente.focus_force()
            return
        self._ventanas["diagnostico"] = abrir_herramienta(self, "diagnostico", color_de_nodo(self.arbol.raiz), self.carpeta,
                                                          self._al_diagnostico, self.plan.marcas)

    def _pedir_diagnostico(self):
        """La persona quiere hacer (o rehacer) su diagnóstico: se va a la raíz, se abre y la IA lo explica."""
        self._nueva_generacion()
        frase = "Prefiero empezar con un diagnóstico de mi salud financiera"
        self.chat.cerrar_preguntas()
        self.chat.agregar("persona", frase)
        self.asistente.registrar("persona", frase)
        raiz = self.arbol.raiz
        if self.guia.actual is not raiz:
            anterior = self.guia.actual
            self.guia.ir_a(raiz)
            self._sugerido = None
            self.escenario.mostrar(raiz, self.guia.opciones(), elegido=anterior, hacia_arriba=True)
            self._refrescar()
        self._abrir_diagnostico()
        self._narrar("diagnostico", frase)
        self.lift()

    def _al_diagnostico(self, marcas):
        """La persona terminó el diagnóstico: se genera su plan (lista doble) y la IA cuenta el resultado."""
        self._nueva_generacion()
        n = self.plan.generar(marcas)
        self._actualizar_plan()
        nivel, _ = self.plan.nivel
        self.chat.cerrar_preguntas()
        self.chat.agregar("persona", f"Terminé mi diagnóstico: {sum(marcas)} de {len(marcas)}")
        self.asistente.registrar("persona", f"Terminé mi diagnóstico de salud financiera: cumplo {sum(marcas)} de {len(marcas)}.")
        self.chat.agregar("nota", f"▸ Tu diagnóstico: {sum(marcas)} de {len(marcas)} · {nivel}. "
                                  + (f"Armé tu plan de acción con {n} paso(s); lo ves en «Mi plan»." if n
                                     else "No te queda ningún paso pendiente."))
        self._narrar("plan", "Terminé mi diagnóstico")

    def _ir_plan(self, tarea):
        """Va al tema de un paso del plan; la IA lo explica diciendo por qué le toca a la persona."""
        self._nueva_generacion()
        frase = f"Quiero empezar con el paso «{tarea.nodo.valor}» de mi plan"
        self.chat.cerrar_preguntas()
        self.chat.agregar("persona", frase)
        self.chat.agregar("nota", f"▸ Paso {self.plan.posicion(tarea.nodo)} de tu plan (prioridad "
                                  f"{NOMBRES_PRIORIDAD[tarea.prioridad].lower()}): {tarea.motivo}")
        self.asistente.registrar("persona", frase)
        self.guia.ir_a(tarea.nodo)
        self._ir(tarea.nodo, elegido=tarea.nodo, mensaje=frase)

    def _completar_plan(self, nodo):
        """«Ya lo hice»: el paso se desenlaza de la lista y la tarjeta se vuelve a mostrar con el siguiente paso."""
        self.chat.cerrar_preguntas()
        siguiente = self.plan.siguiente_paso(nodo)
        self.plan.completar(nodo)
        self.chat.agregar("nota", f"▸ ¡Bien! «{nodo.valor}» quedó como hecho. Te quedan {len(self.plan)} paso(s) en tu plan."
                                  + (f" El que sigue es «{siguiente.nodo.valor}»." if siguiente else ""))
        self._actualizar_plan()
        self._mostrar_pregunta(repetir=True)

    def _ir_relacionado(self, arista):
        """Sigue una flecha del grafo: va a un tema que conviene ver después, aunque esté en otra rama."""
        self._nueva_generacion()
        frase = f"Quiero seguir con «{arista.destino.valor}»"
        self.chat.agregar("persona", frase)
        self.chat.agregar("nota", f"▸ Relación del grafo: «{arista.origen.valor}» → «{arista.destino.valor}». {arista.motivo}.")
        self.asistente.registrar("persona", frase)
        self.guia.ir_a(arista.destino)
        self._ir(arista.destino, elegido=arista.destino, mensaje=frase)

    def _ir(self, nodo, elegido=None, mensaje=""):
        """La guía ya está en `nodo`: se anima el escenario y la IA explica (tema final) o pregunta (categoría)."""
        self._sugerido = None
        self.escenario.mostrar(nodo, self.guia.opciones(), elegido=elegido)
        self._refrescar()
        self._narrar("tema" if self.guia.es_tema_final else "bajar", mensaje)

    def _subir(self):
        anterior = self.guia.actual
        nodo = self.guia.subir()
        self._sugerido = None
        self.escenario.mostrar(nodo, self.guia.opciones(), elegido=anterior, hacia_arriba=True)
        self._refrescar()
        self._narrar("volver")

    def _refrescar(self):
        """Actualiza el minimapa y los botones de acción según el nodo actual."""
        self.minimapa.actualizar()
        self.b_volver.habilitar(self.guia.actual.padre is not None)
        if self._sugerido is not None:                 # botón «Ver tema» (solo cuando la IA sugiere un tema)
            self.b_sugerido.color = color_de_nodo(self._sugerido)
            self.b_sugerido.poner_texto(f"▸  Ver tema: {self._sugerido.valor}")
            self.b_sugerido.habilitar(True)
            if not self.b_sugerido.winfo_ismapped():
                self.b_sugerido.pack(side="left", padx=(10, 0), after=self.b_volver)
        elif self.b_sugerido.winfo_ismapped():
            self.b_sugerido.pack_forget()
        if self.guia.puede_practicar:
            clave = self.guia.actual.herramienta
            self.b_practicar.color = color_de_nodo(self.guia.actual)
            self.b_practicar.poner_texto(f"▸  Practicar: {TITULOS.get(clave, clave)}")
            self.b_practicar.habilitar(True)
        elif self.guia.tiene_herramienta:
            self.b_practicar.color = TENUE
            self.b_practicar.poner_texto("Practicar (tras conocer el tema)")
            self.b_practicar.habilitar(False)
        else:
            self.b_practicar.color = TENUE
            self.b_practicar.poner_texto("Elige un tema para practicar")
            self.b_practicar.habilitar(False)

    def _latido_boton(self):
        """El botón de practicar «respira» cuando hay una calculadora disponible."""
        if self.guia.puede_practicar:
            self._pulso += 0.2
            self.b_practicar.fondo_padre = FONDO
            self.b_practicar._encima = (int(self._pulso) % 4) < 2
            self.b_practicar._dibujar()
        self.after(350, self._latido_boton)

    # ==================================================================
    # Ventana con el conocimiento de la IA
    # ==================================================================
    def _ver_conocimiento(self):
        ventana = tk.Toplevel(self, bg=PANEL)
        ventana.title("Lo que sabe la IA · Cosecha")
        ventana.geometry("900x640")
        tk.Label(ventana, text="Esto es todo lo que se le entrega a la IA (archivo ConocimientoIA.txt)", bg=PANEL,
                 fg=ESMERALDA, font=("Georgia", 13, "bold"), anchor="w").pack(fill="x", padx=18, pady=(16, 8))
        marco = tk.Frame(ventana, bg=PANEL)
        marco.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        texto = tk.Text(marco, bg=TARJETA, fg=TEXTO, font=("Consolas", 10), wrap="word", relief="flat", padx=14, pady=12,
                        highlightthickness=1, highlightbackground=BORDE)
        barra = tk.Scrollbar(marco, command=texto.yview)
        texto.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        texto.pack(side="left", fill="both", expand=True)
        texto.insert("1.0", self.base.texto)
        texto.config(state="disabled")
