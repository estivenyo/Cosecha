"""Clase NodoArbol: la unidad básica del árbol.

[ÁRBOL] Cada nodo guarda su valor, una referencia a su padre y una lista
ordenada de hijos. Esa lista de hijos es lo que lo hace un árbol GENERAL
(n-ario): un nodo puede tener cualquier cantidad de hijos, no solo dos.

Además de su valor, cada nodo lleva su propio contenido educativo (descripción,
ejemplo, consejos) y, si corresponde, la clave de una herramienta de cálculo.
"""
import itertools


class NodoArbol:
    # Contador compartido para darle a cada nodo un identificador único (uid).
    _contador = itertools.count(1)

    def __init__(self, valor, padre=None, datos=None):
        self.uid = next(NodoArbol._contador)
        self.valor = valor
        self.padre = padre      # [ÁRBOL] enlace hacia arriba (None en la raíz)
        self.hijos = []         # [ÁRBOL] enlaces hacia abajo (lista ordenada)
        self.datos = dict(datos or {})   # contenido del nodo (descripcion, ejemplo, ...)

    # ------------------------------------------------------------------
    # Contenido del nodo
    # ------------------------------------------------------------------
    @property
    def descripcion(self):
        return self.datos.get("descripcion", "")

    @property
    def ejemplo(self):
        return self.datos.get("ejemplo", "")

    @property
    def consejos(self):
        return self.datos.get("consejos", [])

    @property
    def herramienta(self):
        return self.datos.get("herramienta", "")

    @property
    def relacionados(self):
        """Relaciones del tema con otros temas (aristas del grafo): [{"tema": nombre, "motivo": texto}]."""
        return self.datos.get("relacionados", [])

    @property
    def pregunta(self):
        """Pregunta puntual que se le hace a la persona en una categoría para filtrar entre sus hijos."""
        return self.datos.get("pregunta", "")

    @property
    def respuesta(self):
        """Frase en primera persona con la que la persona «elige» este nodo al contestar la pregunta de su padre."""
        return self.datos.get("respuesta", "") or f"Me interesa {self.valor}"

    # ------------------------------------------------------------------
    # Propiedades estructurales
    # ------------------------------------------------------------------
    @property
    def es_hoja(self):
        """[ÁRBOL] Una hoja es un nodo sin hijos."""
        return not self.hijos

    @property
    def es_raiz(self):
        """[ÁRBOL] La raíz es el único nodo sin padre."""
        return self.padre is None

    @property
    def nivel(self):
        """[ÁRBOL] Nivel = cantidad de aristas entre la raíz y este nodo."""
        nivel = 0
        actual = self.padre
        while actual is not None:
            nivel += 1
            actual = actual.padre
        return nivel

    @property
    def grado(self):
        """[ÁRBOL] Grado de un nodo = cantidad de hijos directos."""
        return len(self.hijos)

    # ------------------------------------------------------------------
    # Operaciones sobre los hijos
    # ------------------------------------------------------------------
    def agregar_hijo(self, valor, datos=None):
        """[ÁRBOL] Inserta un nuevo hijo al final de la lista (orden de llegada)."""
        hijo = NodoArbol(valor, padre=self, datos=datos)
        self.hijos.append(hijo)
        return hijo

    def quitar_hijo(self, hijo):
        """[ÁRBOL] Elimina un hijo y, con él, todo su subárbol."""
        self.hijos.remove(hijo)
        hijo.padre = None

    def camino_nodos(self):
        """[ÁRBOL] Lista de nodos desde la raíz hasta este nodo (subiendo por 'padre')."""
        camino = []
        actual = self
        while actual is not None:
            camino.append(actual)
            actual = actual.padre
        camino.reverse()
        return camino

    def camino(self):
        """Lista de textos desde la raíz hasta este nodo."""
        return [n.valor for n in self.camino_nodos()]

    def ruta(self):
        """Ruta como texto, por ejemplo 'Finanzas Personales > Deuda > Tasa de interés'."""
        return " > ".join(self.camino())

    def __repr__(self):
        return f"NodoArbol({self.valor!r}, hijos={len(self.hijos)})"
