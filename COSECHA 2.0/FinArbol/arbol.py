"""Clase ArbolGeneral: administra el árbol completo.

TIPO DE ÁRBOL:  árbol general (n-ario), enraizado y ordenado.
  - General / n-ario : cada nodo puede tener cualquier número de hijos
                       (no es binario y no es un árbol de búsqueda).
  - Enraizado        : existe una única raíz de la que descienden todos.
  - Ordenado         : el orden de los hermanos importa y se conserva.
ORDEN DEL ÁRBOL:    grado máximo de sus nodos (se calcula en `orden`).
"""
from collections import deque

from nodo import NodoArbol


class ArbolGeneral:
    def __init__(self, raiz):
        self.raiz = raiz

    # ------------------------------------------------------------------
    # Construcción desde / hacia diccionarios (formato JSON del profesor)
    # ------------------------------------------------------------------
    @classmethod
    def desde_diccionario(cls, datos):
        """[ÁRBOL] Construye el árbol recursivamente a partir de {"valor", "hijos", ...}.

        Cualquier otra clave del nodo (descripcion, ejemplo, consejos, herramienta)
        se guarda como contenido del nodo.
        """
        def construir(d, padre):
            if not isinstance(d, dict) or not isinstance(d.get("valor"), str):
                raise ValueError("Cada nodo debe ser un objeto con la clave 'valor' (texto).")
            hijos = d.get("hijos", [])
            if not isinstance(hijos, list):
                raise ValueError(f"'hijos' de «{d['valor']}» debe ser una lista.")
            consejos = d.get("consejos", [])
            if not isinstance(consejos, list) or not all(isinstance(c, str) for c in consejos):
                raise ValueError(f"'consejos' de «{d['valor']}» debe ser una lista de textos.")
            extra = {k: v for k, v in d.items() if k not in ("valor", "hijos")}
            nodo = NodoArbol(d["valor"], padre, extra)
            # [ÁRBOL] Recursión: cada hijo es la raíz de un subárbol.
            nodo.hijos = [construir(h, nodo) for h in hijos]
            return nodo

        return cls(construir(datos, None))

    def a_diccionario(self):
        """[ÁRBOL] Convierte el árbol a diccionario anidado (las hojas no llevan 'hijos')."""
        def convertir(nodo):
            d = {"valor": nodo.valor, **nodo.datos}
            if nodo.hijos:
                d["hijos"] = [convertir(h) for h in nodo.hijos]
            return d

        return convertir(self.raiz)

    # ------------------------------------------------------------------
    # Recorridos
    # ------------------------------------------------------------------
    def preorden(self, nodo=None):
        """[ÁRBOL] Recorrido PreOrden (DFS): primero la raíz, luego cada subárbol."""
        nodo = nodo or self.raiz
        yield nodo
        for hijo in nodo.hijos:
            yield from self.preorden(hijo)

    def postorden(self, nodo=None):
        """[ÁRBOL] Recorrido PostOrden (DFS): primero los subárboles, al final la raíz."""
        nodo = nodo or self.raiz
        for hijo in nodo.hijos:
            yield from self.postorden(hijo)
        yield nodo

    def por_niveles(self):
        """[ÁRBOL] Recorrido por niveles (BFS): nivel 0, luego nivel 1, etc. Usa una cola."""
        cola = deque([self.raiz])
        while cola:
            nodo = cola.popleft()
            yield nodo
            cola.extend(nodo.hijos)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def buscar(self, texto):
        """[ÁRBOL] Busca en el árbol completo (PreOrden).

        Primero van los nodos cuyo nombre contiene el texto y después los que
        solo lo mencionan en su descripción.
        """
        texto = texto.strip().lower()
        if not texto:
            return []
        por_nombre, por_contenido = [], []
        for nodo in self.preorden():
            if texto in nodo.valor.lower():
                por_nombre.append(nodo)
            elif texto in nodo.descripcion.lower():
                por_contenido.append(nodo)
        return por_nombre + por_contenido

    def contar_nodos(self):
        return sum(1 for _ in self.preorden())

    def contar_hojas(self):
        """[ÁRBOL] Hojas = nodos sin hijos."""
        return sum(1 for n in self.preorden() if n.es_hoja)

    def altura(self):
        """[ÁRBOL] Altura = nivel del nodo más profundo (la raíz sola tiene altura 0)."""
        return max(n.nivel for n in self.preorden())

    def orden(self):
        """[ÁRBOL] Orden del árbol = mayor grado (cantidad de hijos) entre todos los nodos."""
        return max(n.grado for n in self.preorden())

    def descripcion_tipo(self):
        return f"Árbol general (n-ario) · enraizado · ordenado · orden {self.orden()}"
