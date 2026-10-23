"""GrafoTemas: las relaciones entre temas vistas como un GRAFO DIRIGIDO que puede tener CICLOS.

El árbol dice a qué rama pertenece cada tema (jerarquía: padre → hijos). El grafo dice qué conviene
aprender DESPUÉS de un tema aunque esté en otra rama. Como hay flechas que regresan a temas anteriores,
aparecen ciclos, por ejemplo:

    Regla 50/30/20 → Registro de gastos → Gastos hormiga → Ahorro automático → Fondo de emergencia → Regla 50/30/20

Los vértices son los mismos NodoArbol del árbol; las aristas salen del campo «relacionados» del JSON.
Se guarda como LISTA DE ADYACENCIA: para cada vértice, la lista de aristas que salen de él.
"""
from collections import deque


class Arista:
    """Flecha origen → destino con el motivo por el que conviene seguir ese camino."""
    __slots__ = ("origen", "destino", "motivo")

    def __init__(self, origen, destino, motivo):
        self.origen, self.destino, self.motivo = origen, destino, motivo


class GrafoTemas:
    def __init__(self):
        self.vertices = []          # NodoArbol que participan (en el orden en que se agregaron)
        self.adyacencia = {}        # uid -> [Arista que salen de ese vértice]

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    @classmethod
    def desde_arbol(cls, arbol):
        """[ÁRBOL → GRAFO] Lee el campo «relacionados» de cada nodo y crea las aristas entre nodos del árbol."""
        grafo = cls()
        por_nombre = {n.valor: n for n in arbol.preorden()}
        for nodo in arbol.preorden():
            for rel in nodo.relacionados:
                destino = por_nombre.get(rel.get("tema", ""))
                if destino is None:
                    raise ValueError(f"«{nodo.valor}» se relaciona con un tema que no existe: {rel.get('tema')!r}")
                grafo.agregar_arista(nodo, destino, rel.get("motivo", ""))
        return grafo

    def _vertice(self, nodo):
        if nodo.uid not in self.adyacencia:
            self.adyacencia[nodo.uid] = []
            self.vertices.append(nodo)

    def agregar_arista(self, origen, destino, motivo=""):
        if origen is destino:
            raise ValueError(f"«{origen.valor}» no puede relacionarse consigo mismo.")
        self._vertice(origen)
        self._vertice(destino)
        if any(a.destino is destino for a in self.adyacencia[origen.uid]):
            raise ValueError(f"La relación «{origen.valor}» → «{destino.valor}» está repetida.")
        self.adyacencia[origen.uid].append(Arista(origen, destino, motivo))

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def salientes(self, nodo):
        return list(self.adyacencia.get(nodo.uid, []))

    def entrantes(self, nodo):
        return [a for lista in self.adyacencia.values() for a in lista if a.destino is nodo]

    def aristas(self):
        return [a for v in self.vertices for a in self.adyacencia[v.uid]]

    def sugerencias(self, nodo, visitados, limite=1):
        """Temas a los que conviene ir después de `nodo`: primero los que la persona aún no ha visto."""
        salientes = self.salientes(nodo)
        nuevos = [a for a in salientes if a.destino.uid not in visitados]
        vistos = [a for a in salientes if a.destino.uid in visitados]
        return (nuevos + vistos)[:limite]

    def camino_mas_corto(self, origen, destino):
        """BFS (recorrido por niveles con cola): menor número de pasos de `origen` a `destino`, o None."""
        if origen is destino:
            return [origen]
        previo = {origen.uid: None}
        cola = deque([origen])
        while cola:
            actual = cola.popleft()
            for arista in self.adyacencia.get(actual.uid, []):
                if arista.destino.uid not in previo:
                    previo[arista.destino.uid] = actual
                    if arista.destino is destino:
                        ruta, n = [], destino
                        while n is not None:
                            ruta.append(n)
                            n = previo[n.uid]
                        return ruta[::-1]
                    cola.append(arista.destino)
        return None

    def ciclos(self, max_largo=6):
        """DFS: todos los ciclos simples de hasta `max_largo` temas. Cada ciclo se devuelve una sola vez,
        empezando por su vértice de menor uid. Ordenados por tamaño."""
        encontrados = []
        for inicio in sorted(self.vertices, key=lambda v: v.uid):
            ruta = [inicio]

            def avanzar(actual):
                for arista in self.adyacencia.get(actual.uid, []):
                    d = arista.destino
                    if d is inicio:
                        encontrados.append(list(ruta))
                    elif d.uid > inicio.uid and d not in ruta and len(ruta) < max_largo:
                        ruta.append(d)
                        avanzar(d)
                        ruta.pop()
            avanzar(inicio)
        return sorted(encontrados, key=lambda c: (len(c), [n.uid for n in c]))

    def ciclos_de(self, nodo, max_largo=6):
        return [c for c in self.ciclos(max_largo) if nodo in c]

    def arista(self, origen, destino):
        return next((a for a in self.adyacencia.get(origen.uid, []) if a.destino is destino), None)
