"""Cálculo de posiciones del árbol para dibujarlo (lógica pura, sin Tkinter)."""


def calcular_filas(raiz, expandidos):
    """[ÁRBOL] Asigna a cada nodo visible su (nivel, fila).

    Es un recorrido PostOrden: primero se ubican los hijos y después el padre,
    que queda centrado verticalmente entre su primer y su último hijo.
    Las hojas visibles ocupan filas consecutivas.

    Devuelve ({uid: (nivel, fila)}, total_de_filas).
    """
    resultado = {}
    contador = [0]

    def visitar(nodo, nivel):
        visibles = nodo.hijos if nodo.uid in expandidos else []
        if not visibles:                       # hoja (o rama contraída)
            fila = contador[0]
            contador[0] += 1
        else:                                  # [ÁRBOL] recursión sobre los hijos
            filas = [visitar(h, nivel + 1) for h in visibles]
            fila = (filas[0] + filas[-1]) / 2  # el padre se centra entre sus hijos
        resultado[nodo.uid] = (nivel, fila)
        return fila

    visitar(raiz, 0)
    return resultado, contador[0]
