"""Fórmulas financieras puras (sin interfaz). Las usan las herramientas del árbol."""
import math

from lista_doble import ListaDoble


def ea_a_mensual(ea):
    """Tasa efectiva anual (fracción, 0.24 = 24%) -> tasa efectiva mensual."""
    return (1.0 + ea) ** (1.0 / 12.0) - 1.0


def saldos_con_aportes(inicial, aporte, tasa_m, meses):
    """Saldo mes a mes con aporte al final de cada mes. Devuelve [mes0, mes1, ...]."""
    saldos, s = [inicial], inicial
    for _ in range(meses):
        s = s * (1 + tasa_m) + aporte
        saldos.append(s)
    return saldos


def aporte_para_meta(meta, inicial, tasa_m, meses):
    """Aporte mensual necesario para llegar a `meta` en `meses`."""
    crecimiento = (1 + tasa_m) ** meses
    faltante = meta - inicial * crecimiento
    if faltante <= 0:
        return 0.0
    if abs(tasa_m) < 1e-12:
        return faltante / meses
    return faltante * tasa_m / (crecimiento - 1)


def cuota_prestamo(monto, tasa_m, n):
    if abs(tasa_m) < 1e-12:
        return monto / n
    return monto * tasa_m / (1 - (1 + tasa_m) ** -n)


def saldos_prestamo(monto, tasa_m, n, cuota):
    saldos, s = [monto], monto
    for _ in range(n):
        s = max(0.0, s * (1 + tasa_m) - cuota)
        saldos.append(s)
    return saldos


def rendimiento_bono(nominal, cupon, anios, precio):
    """Rendimiento al vencimiento (TIR anual) de un bono con cupón anual. cupon en fracción."""
    pago = nominal * cupon

    def valor(y):
        return sum(pago / (1 + y) ** t for t in range(1, anios + 1)) + nominal / (1 + y) ** anios

    lo, hi = -0.95, 10.0
    for _ in range(200):
        medio = (lo + hi) / 2
        if valor(medio) > precio:
            lo = medio
        else:
            hi = medio
    return (lo + hi) / 2


def rendimiento_periodo(capital, ea, dias):
    """Rendimiento bruto de un capital a tasa EA durante `dias` días (base 365)."""
    return capital * ((1 + ea) ** (dias / 365.0) - 1)


def asignacion_por_edad(edad, riesgo):
    """Regla clásica '100 menos tu edad' ajustada por tolerancia al riesgo (1 a 5).

    Devuelve (% renta variable, % renta fija).
    """
    renta_variable = 100 - edad + (riesgo - 3) * 10
    renta_variable = max(10, min(90, renta_variable))
    return renta_variable, 100 - renta_variable


def simular_deudas(deudas, extra, metodo, max_meses=600):
    """Simula el pago de varias deudas.

    deudas: lista de dicts {nombre, saldo, tasa_ea (fracción), minimo}
    metodo: "avalancha" (mayor tasa primero) o "bola_nieve" (menor saldo primero)
    El presupuesto mensual es fijo: suma de mínimos + extra. Al liquidar una deuda,
    su cuota se reutiliza en la siguiente (efecto bola de nieve).
    """
    estado = [dict(d, tm=ea_a_mensual(d["tasa_ea"]), pagada=None) for d in deudas]
    presupuesto = sum(d["minimo"] for d in estado) + extra
    saldos = [sum(d["saldo"] for d in estado)]
    intereses, mes = 0.0, 0

    while any(d["saldo"] > 0.5 for d in estado) and mes < max_meses:
        mes += 1
        activas = [d for d in estado if d["saldo"] > 0.5]
        for d in activas:                              # 1) se cargan los intereses
            i = d["saldo"] * d["tm"]
            d["saldo"] += i
            intereses += i
        disponible = presupuesto
        for d in activas:                              # 2) se pagan los mínimos
            pago = min(d["minimo"], d["saldo"])
            d["saldo"] -= pago
            disponible -= pago
        # 3) el resto va a la deuda prioritaria. La cola de prioridades es una LISTA DOBLEMENTE ENLAZADA:
        #    cada deuda se inserta en su lugar y se recorre desde la cabeza (la más prioritaria).
        if metodo == "avalancha":
            clave = lambda d: (-d["tasa_ea"], d["saldo"])
        else:
            clave = lambda d: (d["saldo"], -d["tasa_ea"])
        prioridades = ListaDoble.desde_iterable((d for d in activas if d["saldo"] > 0.5), clave)
        for d in prioridades:
            if disponible <= 0:
                break
            pago = min(disponible, d["saldo"])
            d["saldo"] -= pago
            disponible -= pago
        for d in activas:
            if d["saldo"] <= 0.5 and d["pagada"] is None:
                d["saldo"], d["pagada"] = 0.0, mes
        saldos.append(sum(d["saldo"] for d in estado))

    viable = all(d["saldo"] <= 0.5 for d in estado)
    orden_pago = sorted((d for d in estado if d["pagada"]), key=lambda d: d["pagada"])
    return {"meses": mes, "intereses": intereses, "saldos": saldos, "viable": viable,
            "orden": [(d["nombre"], d["pagada"]) for d in orden_pago]}


def meses_a_texto(meses):
    anios, resto = divmod(int(meses), 12)
    if anios and resto:
        return f"{anios} año{'s' if anios > 1 else ''} y {resto} mes{'es' if resto > 1 else ''}"
    if anios:
        return f"{anios} año{'s' if anios > 1 else ''}"
    return f"{resto} mes{'es' if resto != 1 else ''}"
