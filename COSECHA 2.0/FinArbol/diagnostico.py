"""Del DIAGNÓSTICO de salud financiera al PLAN de acción personal.

La persona marca en el diagnóstico (la lista de 8 afirmaciones de la raíz) lo que ya hace. Cada afirmación SIN
marcar activa una o más reglas: «si no haces X, te conviene estudiar el tema Y». Cada regla calcula la prioridad
(1 alta, 2 media, 3 baja) y el motivo según el RESTO de las respuestas. Ejemplo: el fondo de emergencia es
prioridad media mientras haya «fugas» abiertas (gastas más de lo que ganas, pagas tarde o usas mal la tarjeta),
porque primero hay que cerrarlas; cuando no hay fugas, pasa a prioridad alta.

Resultado: una lista de (tema, prioridad, motivo) distinta para cada persona. plan.py la guarda en una lista
doblemente enlazada ordenada por prioridad.
"""
from herramientas import LISTAS

N_ITEMS = len(LISTAS["diagnostico"]["items"])      # 8 afirmaciones


def _hay_fugas(m):
    """Fugas = gastar más de lo que se gana, pagar deudas tarde o usar la tarjeta sin pagarla completa."""
    return not (m[1] and m[2] and m[4])


def _fondo(m):
    if _hay_fugas(m):
        return 2, ("Aún no tienes 3 meses de gastos guardados. Es importante, pero primero conviene cerrar las "
                   "fugas de más arriba: sin eso el fondo no crece.")
    return 1, ("Tus gastos y deudas están bajo control, y un imprevisto todavía te obligaría a endeudarte: "
               "este es hoy tu mayor riesgo.")


def _inversion(m):
    if all(m):
        return 1, "Ya cumples todo el diagnóstico: el siguiente nivel es hacer crecer tu dinero."
    return 3, ("Ya tienes la base (gastas menos de lo que ganas, sin deudas atrasadas y con fondo de emergencia). "
               "Cuando termines lo anterior, el siguiente nivel es invertir.")


# (n.º de afirmación sin marcar, tema, prioridad, motivo). La prioridad y el motivo pueden ser una función de las marcas.
# Si dos reglas apuntan al mismo tema se conserva la prioridad más alta y se unen los motivos.
REGLAS = [
    (0, "Registro de gastos", 1, "No llevas el control de tus gastos: no se puede mejorar lo que no se mide. Es el primer paso."),
    (1, "Regla 50/30/20", 1, "Gastas igual o más de lo que ganas: repartir tu ingreso es lo más urgente."),
    (1, "Gastos hormiga", 2, "Cuando el dinero no alcanza, los pequeños gastos diarios suelen ser la fuga."),
    (2, "Método avalancha", 1, "Pagas tarde alguna deuda: genera intereses y recargos. Ordénalas y paga primero la más cara."),
    (2, "Tasa de interés", 2, "Entender cuánto te cuesta cada deuda te dice cuál atacar primero."),
    (3, "Fondo de emergencia", _fondo, None),
    (4, "Tasa de interés", 1, "Usas la tarjeta sin pagarla completa: es la deuda más cara, conviene saber cuánto te cuesta."),
    (4, "Método bola de nieve", 2, "Si tienes varias deudas pequeñas, pagarlas de menor a mayor te da impulso."),
    (5, "Ahorro automático", 2, "No ahorras un porcentaje fijo: automatizarlo hace que ahorres sin depender de la fuerza de voluntad."),
    (6, "Metas de ahorro", 2, "Sin una meta con monto y fecha es difícil mantener el ahorro: ponle número y fecha."),
    (7, "Autenticación en dos pasos", 2, "Tus cuentas no tienen verificación en dos pasos: toma minutos y evita muchos robos."),
    (7, "Fraudes en línea", 3, "Para completar la protección de tus cuentas, aprende a reconocer los fraudes más comunes."),
]
# Regla de crecimiento: solo si la persona ya tiene la base sólida (afirmaciones 2, 3, 4 y 5 marcadas).
REGLA_BASE_SOLIDA = ("Inversión", _inversion)


def _evaluar(valor, marcas):
    return valor(marcas) if callable(valor) else valor


def generar_plan(marcas):
    """Devuelve [(nombre_del_tema, prioridad, motivo)] para las marcas del diagnóstico.
    El orden de salida es el de las reglas; la lista doble lo reordena por prioridad."""
    if len(marcas) != N_ITEMS:
        raise ValueError(f"El diagnóstico tiene {N_ITEMS} afirmaciones, llegaron {len(marcas)}.")
    marcas = [bool(x) for x in marcas]
    por_tema = {}
    for item, tema, prio, motivo in REGLAS:
        if marcas[item]:
            continue
        if callable(prio):
            prio, motivo = prio(marcas)
        if tema in por_tema:
            p0, m0 = por_tema[tema]
            por_tema[tema] = (min(p0, prio), f"{m0} {motivo}" if p0 <= prio else f"{motivo} {m0}")
        else:
            por_tema[tema] = (prio, motivo)
    if marcas[1] and marcas[2] and marcas[3] and marcas[4]:
        tema, f = REGLA_BASE_SOLIDA
        por_tema[tema] = f(marcas)
    return [(tema, p, m) for tema, (p, m) in por_tema.items()]


def nivel_de(marcas):
    """(nombre del nivel, mensaje) según cuántas afirmaciones cumple la persona."""
    fraccion = sum(bool(x) for x in marcas) / len(marcas)
    for umbral, nombre, mensaje, _ in LISTAS["diagnostico"]["niveles"]:
        if fraccion < umbral:
            return nombre, mensaje
    return LISTAS["diagnostico"]["niveles"][-1][1:3]
