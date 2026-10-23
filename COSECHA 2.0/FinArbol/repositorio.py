"""RepositorioJSON: lee y guarda el árbol en un archivo JSON.

Mantiene la persistencia separada del árbol y de la interfaz.
"""
import json
from pathlib import Path

from arbol import ArbolGeneral


class RepositorioJSON:
    def __init__(self, ruta):
        self.ruta = Path(ruta)

    def cargar(self):
        """[ÁRBOL] Lee el JSON y lo convierte en un ArbolGeneral con nodos enlazados."""
        with open(self.ruta, encoding="utf-8") as f:
            datos = json.load(f)
        return ArbolGeneral.desde_diccionario(datos)

    def guardar(self, arbol):
        """[ÁRBOL] Convierte el árbol a diccionario anidado y lo escribe como JSON."""
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(arbol.a_diccionario(), f, ensure_ascii=False, indent=2)

