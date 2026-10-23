"""GuiaArbol: el «dónde estoy» de la conversación. Mueve a la persona por el árbol de temas.

No usa Tkinter ni la IA: solo sabe en qué nodo está la persona, qué opciones tiene y por
dónde ha pasado. La IA decide A DÓNDE ir; esta clase valida y ejecuta el movimiento.
"""


class GuiaArbol:
    def __init__(self, arbol):
        self.arbol = arbol                  # [ÁRBOL] ArbolGeneral con todos los temas
        self.reiniciar()

    def reiniciar(self):
        self.actual = self.arbol.raiz       # [ÁRBOL] se empieza siempre por la raíz
        self.visitados = {self.actual.uid}
        self.recorrido = [self.actual]      # orden en que la persona fue pasando por los nodos
        self.conceptos = set()              # temas cuyo concepto ya se le explicó a la persona

    # ------------------------------------------------------------------
    # Qué se puede elegir desde aquí
    # ------------------------------------------------------------------
    def opciones(self):
        """[ÁRBOL] En una categoría: sus hijos. En un tema final (hoja): sus hermanos."""
        if self.actual.hijos:
            return list(self.actual.hijos)
        if self.actual.padre is not None:
            return [h for h in self.actual.padre.hijos if h is not self.actual]
        return []

    @property
    def pregunta(self):
        """[ÁRBOL] La pregunta que filtra entre los hijos del nodo actual (vacía en un tema final)."""
        if not self.actual.hijos:
            return ""
        return self.actual.pregunta or "¿Cuál de estas opciones se parece más a lo que buscas?"

    @property
    def paso(self):
        """Número de la pregunta en el embudo: nivel del nodo actual + 1 (raíz = pregunta 1)."""
        return self.actual.nivel + 1

    @property
    def es_tema_final(self):
        """[ÁRBOL] Una hoja es un tema sin más subtemas: aquí se explica y se practica."""
        return self.actual.es_hoja

    @property
    def tiene_herramienta(self):
        return bool(self.actual.herramienta)

    @property
    def concepto_visto(self):
        return self.actual.uid in self.conceptos

    def marcar_concepto(self):
        self.conceptos.add(self.actual.uid)

    @property
    def puede_practicar(self):
        """Primero el concepto, después la práctica: la calculadora solo se habilita tras explicar el tema."""
        return self.tiene_herramienta and self.concepto_visto

    @property
    def ruta(self):
        """[ÁRBOL] Camino de la raíz al nodo actual (sube por el enlace «padre»)."""
        return self.actual.camino_nodos()

    # ------------------------------------------------------------------
    # Movimientos
    # ------------------------------------------------------------------
    def ir_a(self, nodo):
        self.actual = nodo
        self.visitados.add(nodo.uid)
        self.recorrido.append(nodo)
        return nodo

    def elegir(self, numero):
        """Elige la opción n.º `numero` (empieza en 1). Devuelve el nodo o None si no existe."""
        opciones = self.opciones()
        if isinstance(numero, int) and 1 <= numero <= len(opciones):
            return self.ir_a(opciones[numero - 1])
        return None

    def subir(self):
        """Regresa al padre. Devuelve el nodo o None si ya está en la raíz."""
        if self.actual.padre is None:
            return None
        return self.ir_a(self.actual.padre)
