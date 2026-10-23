"""AsistenteFinanciero: la IA (Ollama) que conversa, responde dudas y decide por dónde llevar a la persona.

Cada mensaje de la persona pasa por DOS llamadas al modelo:
  1. decidir()  -> respuesta JSON estructurada {razon, accion, opcion, tema}. Un modelo pequeño
                   (llama3.2:1b) es mucho más preciso clasificando que redactando.
  2. redactar() -> texto libre en streaming: la respuesta que ve la persona. Se envía la conversación
                   real (turno por turno) para que responda como una IA normal y no repita mensajes.
El programa valida la decisión (que la opción o el tema existan) antes de mover el árbol.
La IA responde con su conocimiento general; ConocimientoIA.txt la guía, no la limita.
"""
import unicodedata
from dataclasses import dataclass

import lexico

ACCIONES = ["responder", "elegir", "ir_a", "ayuda", "aclarar", "volver", "practicar", "fuera_de_tema"]

ESQUEMA_DECISION = {
    "type": "object",
    "properties": {"razon": {"type": "string"},
                   "accion": {"type": "string", "enum": ACCIONES},
                   "opcion": {"type": "integer"},
                   "tema": {"type": "string"}},
    "required": ["razon", "accion", "opcion", "tema"],
}


@dataclass
class Decision:
    accion: str
    opcion: int = 0
    razon: str = ""
    nodo: object = None     # tema destino («ir_a») o tema relacionado que se sugiere («responder»)


class AsistenteFinanciero:
    def __init__(self, cliente, base):
        self.cliente = cliente      # ClienteOllama
        self.base = base            # BaseConocimiento (lee ConocimientoIA.txt)
        self.historial = []         # [(quien, texto)] de la conversación
        self.contexto_plan = lambda: ""     # texto con el diagnóstico y el plan de la persona (lo pone la ventana)

    def reiniciar(self):
        self.historial = []

    def registrar(self, quien, texto):
        self.historial.append((quien, texto))

    def registrar_pregunta(self, texto):
        """La pregunta puntual con botones también cuenta como parte de lo último que dijo la IA."""
        if self.historial and self.historial[-1][0] == "ia":
            self.historial[-1] = ("ia", f"{self.historial[-1][1]}\n{texto}")
        else:
            self.historial.append(("ia", texto))

    # ------------------------------------------------------------------
    # Piezas de texto que se arman con el contenido del .txt
    # ------------------------------------------------------------------
    def _turnos(self, ultimos=8):
        """La conversación como turnos reales de chat (la IA responde mejor así y no repite)."""
        turnos = [{"role": "user" if q == "persona" else "assistant", "content": t}
                  for q, t in self.historial[-ultimos:]]
        while turnos and turnos[0]["role"] == "assistant":
            turnos.pop(0)
        if not turnos:
            turnos = [{"role": "user", "content": "Hola"}]
        elif turnos[-1]["role"] == "assistant":
            turnos.append({"role": "user", "content": "Continúa."})
        return turnos

    def _opciones_texto(self, nodos, con_claves=True):
        lineas = []
        for i, nodo in enumerate(nodos, 1):
            claves = ", ".join(self.base.campo(nodo.valor, "Palabras clave").split(", ")[:4])
            quien = f" — responde «{nodo.respuesta}»" if nodo.datos.get("respuesta") else ""
            lineas.append(f"{i}. {nodo.valor}{quien}" + (f" (palabras clave: {claves})" if con_claves and claves else ""))
        return "\n".join(lineas) or "(ninguna)"

    def _situacion(self, guia, sugerido=None):
        actual = guia.actual
        if actual.hijos:
            texto = (f"Estás en la categoría «{actual.valor}». La pregunta que se le muestra a la persona con botones es: "
                     f"«{guia.pregunta}»\nOPCIONES:\n"
                     f"{self._opciones_texto(guia.opciones())}")
        else:
            texto = (f"Estás en el tema final «{actual.valor}» (ya se le explicó a la persona).\n"
                     f"TEMAS CERCANOS:\n{self._opciones_texto(guia.opciones())}")
        if sugerido is not None:
            texto += f"\nTEMA QUE LE PROPUSISTE: {sugerido.valor}"
        return texto

    # ------------------------------------------------------------------
    # 1) Decidir qué quiere la persona
    # ------------------------------------------------------------------
    def mensajes_decision(self, guia, mensaje, sugerido=None):
        """Arma (en el hilo principal) los mensajes que se le envían al modelo para decidir."""
        pregunta_previa = next((t for q, t in reversed(self.historial) if q == "ia"), "(ninguna)")
        usuario = (f"{self._situacion(guia, sugerido)}\n\n"
                   f"Lo último que le dijiste a la persona: {pregunta_previa}\n\n"
                   f"MENSAJE DE LA PERSONA: \"{mensaje}\"\n\n"
                   "Recuerda: usa «elegir» o «ir_a» SOLO si la persona dice con claridad que quiere resolver lo que describe esa "
                   "opción o ese tema; si el mensaje es incoherente, al azar o no trata de dinero, usa «fuera_de_tema»; "
                   "si es una duda de finanzas, usa «responder».\n"
                   "Responde SOLO con el JSON {\"razon\":...,\"accion\":...,\"opcion\":...,\"tema\":...}.")
        return [{"role": "system", "content": self.base.contexto_decision()},
                {"role": "user", "content": usuario}]

    def pedir_decision(self, mensajes):
        """Llamada al modelo (se ejecuta en un hilo): devuelve el JSON tal como lo escribió la IA."""
        return self.cliente.json(mensajes, ESQUEMA_DECISION)

    def decidir(self, guia, mensaje, sugerido=None):
        return self.validar(self.pedir_decision(self.mensajes_decision(guia, mensaje, sugerido)), guia, mensaje, sugerido)

    @staticmethod
    def _buscar_tema(arbol, nombre):
        """[ÁRBOL] Encuentra el nodo cuyo nombre escribió la IA (sin importar tildes ni mayúsculas)."""
        def limpio(texto):
            texto = unicodedata.normalize("NFD", str(texto).lower())
            return "".join(c for c in texto if unicodedata.category(c) != "Mn").strip(" «»\"'.")
        buscado = limpio(nombre)
        if not buscado:
            return None
        nodos = list(arbol.preorden())
        for nodo in nodos:
            if limpio(nodo.valor) == buscado:
                return nodo
        parecidos = [n for n in nodos if buscado in limpio(n.valor) or limpio(n.valor) in buscado]
        return parecidos[0] if len(parecidos) == 1 else None

    @staticmethod
    def _validar_basico(bruto, guia):
        """Si la IA devuelve algo imposible (opción inexistente, tema que no existe, calculadora que no hay o
        que aún no se ha explicado), el programa lo corrige antes de mover nada."""
        accion = str(bruto.get("accion", "")).strip().lower()
        if accion == "preguntar":
            accion = "responder"
        try:
            opcion = int(bruto.get("opcion", 0))
        except (TypeError, ValueError):
            opcion = 0
        razon = str(bruto.get("razon", ""))[:120]
        if accion not in ACCIONES:
            accion = "aclarar"
        tema = AsistenteFinanciero._buscar_tema(guia.arbol, bruto.get("tema", ""))
        if accion == "elegir" and not 1 <= opcion <= len(guia.opciones()):
            accion, opcion = "aclarar", 0
        if accion == "ir_a":
            if tema is None:
                return Decision("aclarar", 0, razon)
            if tema is guia.actual:
                return Decision("responder", 0, razon)
            return Decision("ir_a", 0, razon, tema)
        if accion == "responder":                     # el tema relacionado es solo una sugerencia
            return Decision("responder", 0, razon, tema if tema is not guia.actual else None)
        if accion == "volver" and guia.actual.padre is None:
            accion = "aclarar"
        if accion == "practicar":
            if not guia.tiene_herramienta:
                accion = "sin_calculadora"
            elif not guia.concepto_visto:
                accion = "concepto"          # primero se explica el concepto; la práctica viene después
        return Decision(accion, opcion if accion == "elegir" else 0, razon)

    # ------------------------------------------------------------------
    # Segunda barrera: solo se entra a un tema si el mensaje REALMENTE se relaciona con él
    # ------------------------------------------------------------------
    def _texto_tema(self, arbol, nodo):
        """Todo lo que identifica a un tema (y a sus subtemas): nombre, respuesta y palabras clave de la ficha."""
        piezas = []
        for n in arbol.preorden(nodo):
            piezas += [n.valor, n.datos.get("respuesta", ""), self.base.campo(n.valor, "Palabras clave")]
        return " ".join(piezas)

    def validar(self, bruto, guia, mensaje="", sugerido=None):
        """Primero se corrige lo imposible (opción o tema inexistente). Después se revisa la relación con el mensaje:
          - elegir / ir_a solo valen si el mensaje habla de ESE tema (o es un número, o acepta el tema propuesto);
          - un tema sugerido en «responder» solo se conserva si el mensaje se relaciona con él;
          - si el mensaje no habla de dinero, la acción pasa a «fuera_de_tema» y no se mueve nada.
        Así un mensaje al azar o incoherente nunca avanza por el árbol."""
        d = self._validar_basico(bruto, guia)
        if not mensaje:
            return d
        finanzas = lexico.habla_de_finanzas(mensaje)
        if d.accion not in ("fuera_de_tema", "elegir", "ir_a") and not lexico.sentido(mensaje, d.accion):
            # «pen», «ayyyhostia»…: no habla de dinero ni da una orden clara. No se mueve nada ni se abre nada.
            return Decision("fuera_de_tema", 0, "el mensaje no tiene relación con las finanzas")
        if d.accion in ("elegir", "ir_a"):
            destino = guia.opciones()[d.opcion - 1] if d.accion == "elegir" else d.nodo
            acepta = d.accion == "ir_a" and sugerido is not None and d.nodo is sugerido and lexico.es_afirmacion(mensaje)
            por_numero = d.accion == "elegir" and lexico.apunta_a_numero(mensaje)
            if not (acepta or por_numero or lexico.evidencia(mensaje, self._texto_tema(guia.arbol, destino))):
                if finanzas:
                    return Decision("responder", 0, "no habla claramente de un tema de la guía")
                if lexico.es_saludo(mensaje):
                    return Decision("aclarar", 0, "solo saluda, aún no dice qué quiere resolver")
                return Decision("fuera_de_tema", 0, "el mensaje no tiene relación con las finanzas")
        elif d.accion == "responder":
            if d.nodo is not None and not lexico.evidencia(mensaje, self._texto_tema(guia.arbol, d.nodo)):
                d = Decision("responder", 0, d.razon, None)           # no se sugiere un tema sin relación
            if not finanzas and not lexico.es_saludo(mensaje) and not lexico.es_afirmacion(mensaje):
                return Decision("fuera_de_tema", 0, "el mensaje no tiene relación con las finanzas")
        elif d.accion == "aclarar":
            if not finanzas and not lexico.es_saludo(mensaje) and not lexico.es_afirmacion(mensaje) \
                    and not lexico.apunta_a_numero(mensaje) and len(lexico.raices(mensaje)) >= 1:
                return Decision("fuera_de_tema", 0, "el mensaje no tiene relación con las finanzas")
        return d

    # ------------------------------------------------------------------
    # 2) Redactar la respuesta que ve la persona
    # ------------------------------------------------------------------
    def _tarea(self, situacion, guia, mensaje, sugerido=None):
        actual, opciones = guia.actual, guia.opciones()
        lista = self._opciones_texto(opciones)
        herramienta = self.base.campo(actual.valor, "Herramienta")
        ficha = self.base.ficha(actual.valor)
        calculadora = self.base.calculadora(herramienta)
        if situacion == "inicio":
            return ("Es el primer mensaje. Saluda en una frase, di que eres Cosecha, un guía de finanzas personales con "
                    "IA, y explica en una o dos frases cómo funciona la pantalla: aquí en el chat puede escribirte "
                    "cualquier duda de finanzas, y en el centro verá los temas de la guía como tarjetas que también "
                    "puede tocar (a la izquierda está el mapa de dónde va). Dile que a continuación le harás unas preguntas "
                    "puntuales con botones para encontrar justo lo que necesita, y que también puede escribirte lo que "
                    f"quiera. NO hagas preguntas tú: el programa muestra la primera. Áreas de la guía:\n{lista}")
        if situacion == "responder":
            extra = ""
            if sugerido is not None:
                extra = (f"\nEn la guía hay un tema relacionado: «{sugerido.valor}». Dile en una frase que puede abrirlo "
                         "con el botón «Ver tema» (junto a «Volver») cuando quiera ver el concepto completo y practicar.\n"
                         f"Información de ese tema (úsala como apoyo):\n{self.base.ficha(sugerido.valor)}")
            cierre = ("NO hagas preguntas: el programa le mostrará enseguida una pregunta con botones para ir "
                      "encontrando lo que necesita." if actual.hijos else
                      "Termina diciendo que, si quiere, puede practicar con la calculadora o tocar un tema cercano.")
            return ("Responde la última pregunta de la persona como lo haría un asesor financiero experto: completo, claro "
                    "y fácil de entender (hasta unas 120 palabras, con un ejemplo sencillo si ayuda). Usa tu conocimiento "
                    f"general. NO repitas mensajes anteriores. {cierre} No abras calculadoras todavía."
                    f"{extra}\n\nTema donde está la persona ahora: «{actual.valor}».\n{ficha if actual.hijos == [] else ''}")
        if situacion == "ayuda":
            return ("La persona pregunta cómo funciona la aplicación o qué significa algo de la pantalla. Explícaselo con "
                    "sencillez en 4 a 6 frases, usando esta descripción (sin copiarla):\n"
                    f"{self.base.programa}\n\nPantalla actual: el tema «{actual.valor}» y estas opciones:\n{lista}")
        if situacion == "bajar":
            return (f"La persona eligió seguir por «{actual.valor}». Confírmalo en una frase y explica en una o dos frases "
                    "qué abarca este tema (sin copiar la ficha). NO hagas preguntas: el programa le muestra enseguida la "
                    "pregunta puntual con botones, con estas opciones (que también ve como tarjetas numeradas en el "
                    f"centro):\n{lista}\n\nInformación del tema:\n{ficha}")
        if situacion == "tema":
            return (f"La persona llegó al tema final «{actual.valor}» (en pantalla ya ve su ficha: qué es, ejemplo y "
                    "consejos). Dile en una frase que ahí lo tiene, explica el concepto completo con calma en 4 a 6 "
                    "frases (qué es, para qué sirve, cómo se aplica; usa el ejemplo con tus palabras, sin copiarlo). "
                    f"Termina diciendo que abajo puede elegir si quiere ponerlo en práctica con la calculadora «{herramienta}», "
                    "seguir con el siguiente paso de su plan de acción o con un tema relacionado. Si este tema es un paso de su "
                    "plan (mira el apartado del plan al final), dile en una frase por qué le toca según su diagnóstico. "
                    "NO hagas preguntas: el programa muestra la pregunta con botones.\n\n"
                    f"FICHA:\n{ficha}\n\nCALCULADORA:\n{calculadora}")
        if situacion == "concepto":
            return (f"La persona pidió practicar con «{herramienta}», pero todavía NO le has explicado «{actual.valor}». "
                    "No abras nada: primero explica el concepto completo en 4 a 6 frases (qué es, para qué sirve y "
                    "cómo se aplica) y termina diciendo que abajo puede elegir si quiere ponerlo en práctica con la calculadora. "
                    "NO hagas preguntas: el programa muestra la pregunta con botones."
                    f"\n\nFICHA:\n{ficha}\n\nCALCULADORA:\n{calculadora}")
        if situacion == "aclarar":
            return ("El mensaje de la persona fue vago o no queda claro qué quiere resolver. Dile algo amable en una frase "
                    "y pídele que escoja la respuesta que más se parezca a su caso en los botones de abajo, o que lo "
                    "cuente con otras palabras. NO hagas preguntas tú; las opciones son:\n" + lista)
        if situacion == "volver":
            return (f"La persona regresó a «{actual.valor}». Dile en una frase que no hay problema y que puede escoger "
                    f"otra respuesta en los botones de abajo. NO hagas preguntas. Opciones:\n{lista}")
        if situacion == "fuera_de_tema":
            return ("La persona escribió algo que NO tiene relación con finanzas personales (puede ser una palabra suelta, "
                    "un sonido, una exclamación o un tema ajeno). NO interpretes ni comentes ni respondas lo que escribió, "
                    "y no hables de ningún otro tema. Responde en máximo 2 frases, así: «Eso no tiene nada que ver con las "
                    "finanzas personales, que es de lo que me encargo en Cosecha, así que no avanzo en la guía.» y luego "
                    "invítala a contarte una duda o una meta de dinero, o a tocar una de las opciones de abajo. "
                    "NO hagas preguntas, NO abras calculadoras y NO menciones temas de la guía.")
        if situacion == "practicar":
            return (f"La persona aceptó practicar. Dile en una frase que abres la calculadora «{herramienta}» "
                    "(se abre en una ventana aparte) y qué datos conviene tener a la mano (usa esta descripción, sin "
                    f"inventar cifras):\n{calculadora}")
        if situacion == "diagnostico":
            return ("La persona quiere empezar con un diagnóstico de su salud financiera. Dile en 2 o 3 frases que abres el "
                    "diagnóstico en una ventana aparte: son 8 afirmaciones y marca solo las que ya cumple hoy, con "
                    "honestidad (no hay respuestas malas). Cuando termine, el botón «Crear mi plan de acción» arma un plan "
                    "personal con lo que le falta, ordenado por urgencia. NO hagas preguntas.")
        if situacion == "plan":
            return ("La persona acaba de terminar su diagnóstico de salud financiera y Cosecha armó su plan de acción "
                    "(lo ves en el apartado del plan, al final). En 3 a 5 frases: dile su resultado y nivel con tono "
                    "alentador, nombra su primer paso y explica con sus palabras por qué va primero (según su "
                    "diagnóstico); si el plan está vacío, felicítala. No inventes pasos que no estén en el plan. "
                    "NO hagas preguntas: el programa muestra los botones.")
        if situacion == "sin_calculadora":
            return (f"«{actual.valor}» es una categoría y no tiene calculadora propia. Dile eso en una frase y "
                    f"dile que elija en los botones de abajo con cuál de estas opciones quiere practicar. NO hagas preguntas:\n{lista}")
        raise ValueError(situacion)

    def mensajes_redaccion(self, situacion, guia, mensaje="", sugerido=None):
        """Arma (en el hilo principal) los mensajes para que el modelo redacte la respuesta:
        sistema = rol + programa + reglas + tarea de este momento; después, la conversación real."""
        if situacion == "fuera_de_tema":
            # Contexto mínimo y SIN historial: así el modelo pequeño no se pone a conversar del tema ajeno.
            sistema = (f"{self.base.rol}\n\n=== TAREA DE ESTE MOMENTO ===\n"
                       f"{self._tarea(situacion, guia, mensaje, sugerido)}")
            return [{"role": "system", "content": sistema},
                    {"role": "user", "content": f"Mensaje que no tiene que ver con finanzas: «{mensaje}»"}]
        sistema = (f"{self.base.contexto_base()}\n\n=== TAREA DE ESTE MOMENTO ===\n"
                   f"{self._tarea(situacion, guia, mensaje, sugerido)}")
        plan = self.contexto_plan()
        if plan:
            sistema += (f"\n\n=== DIAGNÓSTICO Y PLAN DE ACCIÓN DE LA PERSONA (úsalo si ayuda a responder; no lo repitas entero) "
                        f"===\n{plan}")
        return [{"role": "system", "content": sistema}] + self._turnos()

    def redactar(self, mensajes, al_recibir, cancelado=lambda: False):
        """Llamada al modelo (en un hilo): escribe en vivo y devuelve el texto completo."""
        return self.cliente.texto_en_vivo(mensajes, al_recibir, cancelado=cancelado).strip()
