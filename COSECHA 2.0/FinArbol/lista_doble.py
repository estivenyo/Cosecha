"""Lista doblemente enlazada: cada elemento conoce al anterior y al siguiente.

Se usa para manejar PRIORIDADES (el plan de acción de la persona y el orden de pago de las deudas).
Ventaja frente a una lista normal: para subir o bajar un elemento de prioridad, o quitarlo, solo se
reconectan los enlaces vecinos (O(1)); no hay que mover los demás elementos. Además se puede recorrer
en los dos sentidos (de la prioridad más alta a la más baja, y al revés).

    cabeza ⇄ [prioridad alta] ⇄ [ ... ] ⇄ [prioridad baja] ⇄ cola
"""


class NodoLista:
    """Un eslabón de la lista: guarda un dato y los enlaces `ant` (anterior) y `sig` (siguiente)."""
    __slots__ = ("dato", "ant", "sig")

    def __init__(self, dato):
        self.dato = dato
        self.ant = None
        self.sig = None


class ListaDoble:
    def __init__(self):
        self.cabeza = None      # primer elemento (la mayor prioridad)
        self.cola = None        # último elemento (la menor prioridad)
        self._n = 0

    # ------------------------------------------------------------------
    # Consulta y recorrido
    # ------------------------------------------------------------------
    def __len__(self):
        return self._n

    def __iter__(self):
        """Recorre de la cabeza a la cola devolviendo los datos."""
        for eslabon in self.eslabones():
            yield eslabon.dato

    def eslabones(self):
        """Recorrido hacia adelante (sig): de mayor a menor prioridad."""
        actual = self.cabeza
        while actual is not None:
            yield actual
            actual = actual.sig

    def eslabones_reversa(self):
        """Recorrido hacia atrás (ant): de menor a mayor prioridad."""
        actual = self.cola
        while actual is not None:
            yield actual
            actual = actual.ant

    def buscar(self, condicion):
        return next((e for e in self.eslabones() if condicion(e.dato)), None)

    def posicion(self, eslabon):
        """Posición del eslabón (1 = cabeza)."""
        return next((i for i, e in enumerate(self.eslabones(), 1) if e is eslabon), 0)

    # ------------------------------------------------------------------
    # Inserción
    # ------------------------------------------------------------------
    def agregar_inicio(self, dato):
        nuevo = NodoLista(dato)
        nuevo.sig = self.cabeza
        if self.cabeza is not None:
            self.cabeza.ant = nuevo
        else:
            self.cola = nuevo
        self.cabeza = nuevo
        self._n += 1
        return nuevo

    def agregar_final(self, dato):
        nuevo = NodoLista(dato)
        nuevo.ant = self.cola
        if self.cola is not None:
            self.cola.sig = nuevo
        else:
            self.cabeza = nuevo
        self.cola = nuevo
        self._n += 1
        return nuevo

    def insertar_despues(self, eslabon, dato):
        """Inserta un dato justo después de `eslabon` reconectando sus cuatro enlaces."""
        nuevo = NodoLista(dato)
        nuevo.ant, nuevo.sig = eslabon, eslabon.sig
        if eslabon.sig is not None:
            eslabon.sig.ant = nuevo
        else:
            self.cola = nuevo
        eslabon.sig = nuevo
        self._n += 1
        return nuevo

    def insertar_ordenado(self, dato, clave):
        """Inserta según prioridad (clave menor = más prioritario). Es estable: a igual clave, queda
        después de los que ya estaban. Se busca desde la cola usando los enlaces `ant`."""
        mia = clave(dato)
        actual = self.cola
        while actual is not None and clave(actual.dato) > mia:
            actual = actual.ant
        if actual is None:
            return self.agregar_inicio(dato)
        return self.insertar_despues(actual, dato)

    @classmethod
    def desde_iterable(cls, datos, clave):
        lista = cls()
        for dato in datos:
            lista.insertar_ordenado(dato, clave)
        return lista

    # ------------------------------------------------------------------
    # Cambios de prioridad
    # ------------------------------------------------------------------
    def quitar(self, eslabon):
        """Desenlaza el eslabón: su anterior y su siguiente pasan a apuntarse entre sí."""
        if eslabon.ant is not None:
            eslabon.ant.sig = eslabon.sig
        else:
            self.cabeza = eslabon.sig
        if eslabon.sig is not None:
            eslabon.sig.ant = eslabon.ant
        else:
            self.cola = eslabon.ant
        eslabon.ant = eslabon.sig = None
        self._n -= 1

    def subir(self, eslabon):
        """Sube una posición (más prioridad) intercambiando enlaces con su anterior. False si ya es la cabeza."""
        previo = eslabon.ant
        if previo is None:
            return False
        antes, despues = previo.ant, eslabon.sig
        # el anterior pasa a quedar después del eslabón
        eslabon.ant, eslabon.sig = antes, previo
        previo.ant, previo.sig = eslabon, despues
        if antes is not None:
            antes.sig = eslabon
        else:
            self.cabeza = eslabon
        if despues is not None:
            despues.ant = previo
        else:
            self.cola = previo
        return True

    def bajar(self, eslabon):
        """Baja una posición (menos prioridad). False si ya es la cola."""
        return eslabon.sig is not None and self.subir(eslabon.sig)
