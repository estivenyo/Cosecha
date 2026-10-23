"""PlanPrioridades: «Mi plan de acción», generado a partir del DIAGNÓSTICO de salud financiera de la persona.

Usa una LISTA DOBLEMENTE ENLAZADA (lista_doble.py):
  - cada eslabón es una Tarea (tema + prioridad + motivo) que calcula diagnostico.generar_plan();
  - al generar el plan, cada tarea se inserta en su lugar según la prioridad (1 alta, 2 media, 3 baja)
    recorriendo desde la cola con los enlaces «anterior»;
  - la persona puede subir o bajar una tarea (solo se intercambian enlaces vecinos), marcarla como hecha (se
    desenlaza) y recorrer el plan hacia adelante o hacia atrás.
Todo se guarda en plan.json (marcas del diagnóstico, orden actual y tareas hechas) para que sobreviva al cerrar.
"""
import json
from pathlib import Path

from diagnostico import N_ITEMS, generar_plan, nivel_de
from lista_doble import ListaDoble

NOMBRES_PRIORIDAD = {1: "Alta", 2: "Media", 3: "Baja"}


class Tarea:
    """Un paso del plan: qué tema estudiar, qué tan urgente es y por qué le toca a esta persona."""
    __slots__ = ("nodo", "prioridad", "motivo")

    def __init__(self, nodo, prioridad, motivo):
        self.nodo, self.prioridad, self.motivo = nodo, prioridad, motivo


class PlanPrioridades:
    def __init__(self, arbol, ruta=None):
        self.arbol = arbol
        self.ruta = Path(ruta) if ruta else None
        self.lista = ListaDoble()           # datos = Tarea
        self._eslabon = {}                  # uid del tema -> eslabón de la lista (búsqueda directa)
        self.marcas = None                  # respuestas del último diagnóstico (None = aún no se hace)
        self.completados = []               # nombres de los temas que la persona ya marcó como hechos
        self.cargar()

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def __len__(self):
        return len(self.lista)

    @property
    def hay_diagnostico(self):
        return self.marcas is not None

    @property
    def nivel(self):
        """(nombre del nivel, mensaje) del último diagnóstico, o None."""
        return nivel_de(self.marcas) if self.hay_diagnostico else None

    def contiene(self, nodo):
        return nodo.uid in self._eslabon

    def tarea(self, nodo):
        e = self._eslabon.get(nodo.uid)
        return e.dato if e else None

    def posicion(self, nodo):
        eslabon = self._eslabon.get(nodo.uid)
        return self.lista.posicion(eslabon) if eslabon else 0

    def tareas(self):
        """Tareas de la más urgente a la menos (recorrido hacia adelante con «sig»)."""
        return list(self.lista)

    def tareas_reversa(self):
        """Recorrido hacia atrás con «ant»."""
        return [e.dato for e in self.lista.eslabones_reversa()]

    def vecinos(self, nodo):
        """(tarea anterior, tarea siguiente) dentro del plan, usando los enlaces de la lista."""
        e = self._eslabon[nodo.uid]
        return (e.ant.dato if e.ant else None), (e.sig.dato if e.sig else None)

    def siguiente_paso(self, nodo=None):
        """Tarea que sigue después de `nodo` si está en el plan; si no, la cabeza (el primer paso)."""
        if nodo is not None and self.contiene(nodo):
            return self.vecinos(nodo)[1]
        return self.lista.cabeza.dato if self.lista.cabeza else None

    # ------------------------------------------------------------------
    # Generar y modificar
    # ------------------------------------------------------------------
    def generar(self, marcas):
        """Reemplaza el plan por el que sale de este diagnóstico. Devuelve cuántos pasos tiene."""
        por_nombre = {n.valor: n for n in self.arbol.preorden()}
        self.lista, self._eslabon, self.completados = ListaDoble(), {}, []
        self.marcas = [bool(x) for x in marcas]
        for nombre, prioridad, motivo in generar_plan(self.marcas):
            nodo = por_nombre[nombre]
            self._eslabon[nodo.uid] = self.lista.insertar_ordenado(Tarea(nodo, prioridad, motivo), lambda t: t.prioridad)
        self.guardar()
        return len(self.lista)

    def quitar(self, nodo):
        e = self._eslabon.pop(nodo.uid, None)
        if e is not None:
            self.lista.quitar(e)
            self.guardar()

    def completar(self, nodo):
        """La persona ya hizo este paso: se desenlaza de la lista y se anota como hecho."""
        if self.contiene(nodo):
            self.quitar(nodo)
            self.completados.append(nodo.valor)
            self.guardar()

    def subir(self, nodo):
        ok = self.lista.subir(self._eslabon[nodo.uid])
        if ok:
            self.guardar()
        return ok

    def bajar(self, nodo):
        ok = self.lista.bajar(self._eslabon[nodo.uid])
        if ok:
            self.guardar()
        return ok

    def vaciar(self):
        """Borra todo: plan y diagnóstico."""
        self.lista, self._eslabon, self.marcas, self.completados = ListaDoble(), {}, None, []
        self.guardar()

    # ------------------------------------------------------------------
    # Texto para la IA
    # ------------------------------------------------------------------
    def resumen(self, actual=None):
        """Descripción del plan para el contexto de la IA (vacío si la persona aún no hizo el diagnóstico)."""
        if not self.hay_diagnostico:
            return ""
        nombre, _ = self.nivel
        lineas = [f"Diagnóstico de salud financiera de la persona: {sum(self.marcas)} de {len(self.marcas)} ({nombre})."]
        if len(self.lista):
            lineas.append("Su plan de acción, del paso más urgente al menos urgente:")
            for i, t in enumerate(self.tareas(), 1):
                lineas.append(f"  {i}. {t.nodo.valor} (prioridad {NOMBRES_PRIORIDAD[t.prioridad].lower()})")
        else:
            lineas.append("Su plan está vacío: ya hizo todos los pasos.")
        if self.completados:
            lineas.append("Pasos ya hechos: " + ", ".join(self.completados) + ".")
        t = self.tarea(actual) if actual is not None else None
        if t is not None:
            lineas.append(f"El tema actual es el paso {self.posicion(actual)} de su plan porque: {t.motivo}")
        return "\n".join(lineas)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def guardar(self):
        if self.ruta is None:
            return
        datos = {"marcas": self.marcas, "completados": self.completados,
                 "plan": [{"tema": t.nodo.valor, "prioridad": t.prioridad, "motivo": t.motivo} for t in self.lista]}
        try:
            self.ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass

    def cargar(self):
        if self.ruta is None or not self.ruta.exists():
            return
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(datos, dict):                  # formato de la versión anterior: se ignora
            return
        marcas = datos.get("marcas")
        if isinstance(marcas, list) and len(marcas) == N_ITEMS:
            self.marcas = [bool(x) for x in marcas]
        hechos = datos.get("completados")
        self.completados = [h for h in hechos if isinstance(h, str)] if isinstance(hechos, list) else []
        por_nombre = {n.valor: n for n in self.arbol.preorden()}
        for fila in datos.get("plan", []) if isinstance(datos.get("plan"), list) else []:
            nodo = por_nombre.get(fila.get("tema")) if isinstance(fila, dict) else None
            if nodo is not None and not self.contiene(nodo):          # se respeta el orden guardado
                prioridad = fila.get("prioridad") if fila.get("prioridad") in (1, 2, 3) else 2
                self._eslabon[nodo.uid] = self.lista.agregar_final(Tarea(nodo, prioridad, str(fila.get("motivo", ""))))

