"""Pruebas de las estructuras nuevas: lista doblemente enlazada, plan de prioridades y grafo con ciclos.

Uso:  python pruebas_estructuras.py     (no necesita Ollama ni interfaz)
"""
import random
import tempfile
from pathlib import Path

from diagnostico import generar_plan
from grafo import GrafoTemas
from lista_doble import ListaDoble
from plan import PlanPrioridades
from repositorio import RepositorioJSON

AQUI = Path(__file__).parent


def revisar_enlaces(lista):
    """Los dos recorridos deben coincidir y todos los enlaces ser consistentes."""
    adelante = [e.dato for e in lista.eslabones()]
    atras = [e.dato for e in lista.eslabones_reversa()][::-1]
    assert adelante == atras, (adelante, atras)
    assert len(adelante) == len(lista)
    for e in lista.eslabones():
        assert e.ant is None or e.ant.sig is e
        assert e.sig is None or e.sig.ant is e
    assert (lista.cabeza is None) == (lista.cola is None) == (len(lista) == 0)
    assert lista.cabeza is None or lista.cabeza.ant is None
    assert lista.cola is None or lista.cola.sig is None


def prueba_lista_doble():
    random.seed(3)
    for _ in range(300):                      # comparada contra una lista normal como modelo
        lista, modelo, eslabones = ListaDoble(), [], {}
        for paso in range(random.randint(1, 40)):
            op = random.choice(["ins", "ins", "ins", "quitar", "subir", "bajar"])
            if op == "ins" or not modelo:
                x = (random.randint(1, 3), paso)
                eslabones[x] = lista.insertar_ordenado(x, lambda t: t[0])
                i = len(modelo)
                while i > 0 and modelo[i - 1][0] > x[0]:
                    i -= 1
                modelo.insert(i, x)
            else:
                x = random.choice(modelo)
                i = modelo.index(x)
                if op == "quitar":
                    lista.quitar(eslabones.pop(x)); modelo.pop(i)
                elif op == "subir" and i > 0:
                    assert lista.subir(eslabones[x]); modelo[i - 1], modelo[i] = modelo[i], modelo[i - 1]
                elif op == "subir":
                    assert not lista.subir(eslabones[x])
                elif op == "bajar" and i < len(modelo) - 1:
                    assert lista.bajar(eslabones[x]); modelo[i + 1], modelo[i] = modelo[i], modelo[i + 1]
                elif op == "bajar":
                    assert not lista.bajar(eslabones[x])
            assert list(lista) == modelo
            revisar_enlaces(lista)
    print("  lista doble: OK (300 secuencias aleatorias contra una lista normal)")


def prueba_plan(arbol):
    nodo = {n.valor: n for n in arbol.preorden()}
    nombres = lambda tareas: [t.nodo.valor for t in tareas]
    # --- reglas: cada respuesta del diagnóstico produce un plan distinto
    todo_no = generar_plan([False] * 8)
    assert {t for t, _, _ in todo_no} <= set(nodo), "todos los temas del plan existen en el árbol"
    prio = {t: p for t, p, _ in todo_no}
    assert prio["Fondo de emergencia"] == 2 and prio["Método avalancha"] == 1       # hay fugas: el fondo espera
    con_fugas_cerradas = [True, True, True, False, True, True, True, True]
    assert {t: p for t, p, _ in generar_plan(con_fugas_cerradas)} == {"Fondo de emergencia": 1}   # sin fugas: alta
    base_solida = [True, True, True, True, True, False, False, False]
    assert {t: p for t, p, _ in generar_plan(base_solida)}["Inversión"] == 3          # la base está: toca crecer
    assert generar_plan([True] * 8) == [("Inversión", 1, generar_plan([True] * 8)[0][2])]
    tasa = [m for t, p, m in todo_no if t == "Tasa de interés"][0]
    assert prio["Tasa de interés"] == 1 and "tarjeta" in tasa and "cuesta" in tasa    # dos reglas, un tema, motivos unidos
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "plan.json"
        plan = PlanPrioridades(arbol, ruta)
        assert not plan.hay_diagnostico and len(plan) == 0 and plan.siguiente_paso() is None
        n = plan.generar([False] * 8)
        assert n == len(todo_no) == len(plan)
        prios = [t.prioridad for t in plan.tareas()]
        assert prios == sorted(prios), "la lista queda ordenada por prioridad"
        assert nombres(plan.tareas())[:2] == ["Registro de gastos", "Regla 50/30/20"]   # misma prioridad: orden de las reglas
        assert nombres(plan.tareas_reversa()) == nombres(plan.tareas())[::-1]
        revisar_enlaces(plan.lista)
        primero = plan.siguiente_paso()
        assert primero.nodo is nodo["Registro de gastos"] and plan.siguiente_paso(nodo["Registro de gastos"]).nodo is nodo["Regla 50/30/20"]
        ant, sig = plan.vecinos(nodo["Regla 50/30/20"])
        assert ant.nodo is nodo["Registro de gastos"] and sig is plan.tareas()[2]
        assert plan.subir(nodo["Regla 50/30/20"]) and plan.posicion(nodo["Regla 50/30/20"]) == 1
        assert not plan.subir(nodo["Regla 50/30/20"])
        orden = nombres(plan.tareas())
        plan.completar(nodo["Método avalancha"])
        assert plan.completados == ["Método avalancha"] and not plan.contiene(nodo["Método avalancha"])
        assert nombres(plan.tareas()) == [x for x in orden if x != "Método avalancha"]
        revisar_enlaces(plan.lista)
        otro = PlanPrioridades(arbol, ruta)                            # se recupera todo lo guardado
        assert nombres(otro.tareas()) == nombres(plan.tareas()) and otro.marcas == [False] * 8
        assert otro.completados == ["Método avalancha"] and otro.nivel[0] == "Punto de partida"
        assert "Registro de gastos" in otro.resumen(nodo["Registro de gastos"]) and "porque" in otro.resumen(nodo["Registro de gastos"])
        otro.generar([True] * 8)                                       # rehacer el diagnóstico reemplaza el plan
        assert nombres(otro.tareas()) == ["Inversión"] and otro.completados == [] and otro.nivel[0] == "Excelente"
        otro.vaciar()
        assert not otro.hay_diagnostico and len(otro) == 0 and "Diagnóstico" not in otro.resumen()
        ruta.write_text('["Acciones"]', encoding="utf-8")              # archivo del formato viejo: se ignora sin fallar
        assert len(PlanPrioridades(arbol, ruta)) == 0
        revisar_enlaces(otro.lista)
    print("  plan personal (diagnóstico -> lista doble): OK")


def prueba_grafo(arbol):
    grafo = GrafoTemas.desde_arbol(arbol)
    ciclos = grafo.ciclos()
    assert ciclos, "el grafo debe tener ciclos"
    for ciclo in ciclos:                                               # cada ciclo es realmente cerrado
        for a, b in zip(ciclo, ciclo[1:] + ciclo[:1]):
            assert grafo.arista(a, b) is not None, (a.valor, b.valor)
    assert len({tuple(n.uid for n in c) for c in ciclos}) == len(ciclos)   # sin repetidos
    nodo = {n.valor: n for n in arbol.preorden()}
    ruta = grafo.camino_mas_corto(nodo["Gastos hormiga"], nodo["Método avalancha"])
    assert [n.valor for n in ruta] == ["Gastos hormiga", "Ahorro automático", "Fondo de emergencia", "Tasa de interés", "Método avalancha"]
    assert grafo.camino_mas_corto(nodo["Bonos"], nodo["Regla 50/30/20"]) is None      # no hay camino de vuelta
    print(f"  grafo: OK ({len(grafo.vertices)} vértices, {len(grafo.aristas())} aristas, {len(ciclos)} ciclos)")
    for c in ciclos:
        print("     ·", " → ".join(n.valor for n in c), "→ (vuelve)")


if __name__ == "__main__":
    arbol = RepositorioJSON(AQUI / "FinanzasPersonales.json").cargar()
    print("Pruebas de estructuras")
    prueba_lista_doble()
    prueba_plan(arbol)
    prueba_grafo(arbol)
    print("Todo correcto.")
