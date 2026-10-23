"""BaseConocimiento: lee ConocimientoIA.txt y entrega a la IA solo las partes que necesita.

El .txt es la única fuente de lo que la IA sabe: rol, reglas, acciones, fichas y ejemplos.
"""
import re
from pathlib import Path


class BaseConocimiento:
    def __init__(self, ruta_txt, ruta_json=None):
        self.ruta = Path(ruta_txt)
        if not self.ruta.exists() and ruta_json is not None:
            # Si falta el archivo se vuelve a generar desde el árbol.
            from generar_conocimiento import generar
            generar(ruta_json, self.ruta)
        self.texto = self.ruta.read_text(encoding="utf-8")
        self.secciones = self._partir_secciones(self.texto)
        if 9 not in self.secciones and ruta_json is not None:
            # El archivo es de una versión anterior (menos secciones): se regenera con el formato actual.
            from generar_conocimiento import generar
            generar(ruta_json, self.ruta)
            self.texto = self.ruta.read_text(encoding="utf-8")
            self.secciones = self._partir_secciones(self.texto)
        self.fichas = self._partir_fichas(self.secciones.get(7, ""))
        self.calculadoras = self._partir_fichas(self.secciones.get(8, ""))

    @staticmethod
    def _partir_secciones(texto):
        """Devuelve {numero: contenido} usando los encabezados «=== N. TÍTULO ===»."""
        partes = re.split(r"^=== (\d+)\. .*? ===\n", texto, flags=re.M)
        return {int(partes[i]): partes[i + 1].strip() for i in range(1, len(partes) - 1, 2)}

    @staticmethod
    def _partir_fichas(texto):
        fichas = {}
        for bloque in re.split(r"^### ", texto, flags=re.M)[1:]:
            nombre, _, cuerpo = bloque.partition("\n")
            fichas[nombre.strip()] = cuerpo.strip()
        return fichas

    # --- Partes que se envían a la IA --------------------------------------
    @property
    def rol(self):
        return self.secciones.get(1, "")

    @property
    def programa(self):
        return self.secciones.get(2, "")

    @property
    def reglas(self):
        return self.secciones.get(3, "")

    @property
    def acciones(self):
        return self.secciones.get(4, "")

    @property
    def mapa(self):
        return self.secciones.get(5, "")

    @property
    def rutas(self):
        return self.secciones.get(6, "")

    @property
    def ejemplos(self):
        return self.secciones.get(9, "")

    def calculadora(self, titulo):
        """Texto de la sección «Calculadoras» para una herramienta (qué hace y qué datos pide)."""
        return self.calculadoras.get(titulo, "")

    def ficha(self, nombre):
        """Ficha completa de un tema (ruta, palabras clave, qué es, ejemplo, consejos...)."""
        return self.fichas.get(nombre, "")

    def campo(self, nombre, campo):
        """Un campo de una ficha, por ejemplo campo('Bonos', 'Palabras clave')."""
        coincidencia = re.search(rf"^{re.escape(campo)}: (.*)$", self.ficha(nombre), flags=re.M)
        return coincidencia.group(1).strip() if coincidencia else ""

    def contexto_base(self):
        """Mensaje de sistema común: rol, cómo funciona el programa, reglas, mapa de temas y guía de enrutamiento."""
        return (f"{self.rol}\n\nCÓMO FUNCIONA EL PROGRAMA:\n{self.programa}\n\nREGLAS:\n{self.reglas}\n\n"
                f"TEMAS QUE CONOCES (de lo general a lo específico):\n{self.mapa}\n\n"
                f"GUÍA DE ENRUTAMIENTO:\n{self.rutas}")

    def contexto_decision(self):
        """Mensaje de sistema para decidir: rol + reglas + acciones + ejemplos."""
        return (f"{self.contexto_base()}\n\nFORMA DE DECIDIR:\n{self.acciones}\n\n"
                f"EJEMPLOS:\n{self.ejemplos}")
