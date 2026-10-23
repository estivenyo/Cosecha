"""Definición de las herramientas de cálculo asociadas a los nodos del árbol.

Cada herramienta declara sus campos de entrada y una función `calcular` que
recibe los valores y devuelve un `Resultado` (tarjetas, gráfico, tabla y nota).
Las herramientas con interfaz propia (deudas, registro, fraudes, listas de
verificación) se encuentran en ventanas_herramienta.py.
"""
import math
from dataclasses import dataclass, field

import calculos as c
from estilos import (AMARILLO, CATEGORIAS, CIELO, CORAL, ERROR, ESMERALDA, NARANJA, ORO, TENUE,
                     VIOLETA)
from formato import decimal, moneda, porcentaje


@dataclass
class Campo:
    clave: str
    etiqueta: str
    defecto: float
    tipo: str = "numero"        # dinero | porcentaje | entero | numero
    ayuda: str = ""
    minimo: float = None
    maximo: float = None


@dataclass
class Resultado:
    kpis: list                  # [(título, texto, color)]
    grafico: dict = None
    tabla: tuple = None         # (encabezados, filas)
    nota: str = ""
    nivel: str = "info"         # info | ok | aviso | error


@dataclass
class Definicion:
    clave: str
    titulo: str
    subtitulo: str
    campos: list
    calcular: object = field(repr=False)


def _marcas_meses(n):
    paso = max(1, n // 4)
    marcas = [(i, f"Mes {i}") for i in range(0, n, paso)]
    marcas.append((n, f"Mes {n}"))
    return marcas


def _marcas_anios(meses):
    marcas = []
    for a in range(0, meses // 12 + 1, max(1, (meses // 12) // 5)):
        marcas.append((a * 12, f"Año {a}"))
    return marcas


# ----------------------------------------------------------------------
# Presupuesto
# ----------------------------------------------------------------------
def _presupuesto(v):
    ingreso = v["ingreso"]
    categorias = [("Vivienda", v["vivienda"]), ("Alimentación", v["alimentacion"]),
                  ("Transporte", v["transporte"]), ("Servicios", v["servicios"]),
                  ("Ocio", v["ocio"]), ("Otros", v["otros"]), ("Ahorro", v["ahorro"])]
    gastos = sum(x for _, x in categorias[:-1])
    ahorro = v["ahorro"]
    saldo = ingreso - gastos - ahorro
    necesidades = v["vivienda"] + v["alimentacion"] + v["transporte"] + v["servicios"]
    pct_ahorro = ahorro / ingreso * 100
    pct_nec = necesidades / ingreso * 100
    if saldo < 0:
        nota = (f"Te pasas {moneda(-saldo)} del ingreso. Revisa primero ocio y otros, "
                "que son los gastos más fáciles de ajustar.")
        nivel = "error"
    elif pct_ahorro < 10:
        nota = (f"Cierras el mes en positivo, pero ahorras solo {porcentaje(pct_ahorro, 0)}. "
                "Intenta llegar al 10% y luego al 20%.")
        nivel = "aviso"
    else:
        nota = (f"Buen plan: ahorras {porcentaje(pct_ahorro, 0)} y te sobran {moneda(saldo)}. "
                f"Tus necesidades pesan {porcentaje(pct_nec, 0)} del ingreso (referencia: 50%).")
        nivel = "ok"
    return Resultado(
        kpis=[("Gastos del mes", moneda(gastos), CORAL),
              ("Ahorro planeado", f"{moneda(ahorro)} · {porcentaje(pct_ahorro, 0)}", ESMERALDA),
              ("Saldo libre", moneda(saldo), ESMERALDA if saldo >= 0 else ERROR)],
        grafico={"tipo": "barras", "items": [(t, x, CATEGORIAS[i]) for i, (t, x) in enumerate(categorias)]},
        nota=nota, nivel=nivel)


# ----------------------------------------------------------------------
# Regla 50/30/20
# ----------------------------------------------------------------------
def _regla(v):
    ingreso = v["ingreso"]
    partes = [("Necesidades", ingreso * .5, CIELO), ("Deseos", ingreso * .3, ORO),
              ("Ahorro y deudas", ingreso * .2, ESMERALDA)]
    return Resultado(
        kpis=[(f"{t} {p}%", moneda(x), col) for (t, x, col), p in zip(partes, (50, 30, 20))],
        grafico={"tipo": "dona", "items": partes, "centro": (moneda(ingreso), "ingreso mensual")},
        nota="Si tus necesidades reales superan el 50%, ajusta: por ejemplo 60/20/20. "
             "Lo importante es que el ahorro no sea lo que sobra, sino lo primero que separas.",
        nivel="info")


# ----------------------------------------------------------------------
# Gastos hormiga
# ----------------------------------------------------------------------
def _hormiga(v):
    mensual = v["gasto"] * v["veces"] * 52 / 12
    anual = mensual * 12
    tm = c.ea_a_mensual(v["rendimiento"] / 100)
    meses = int(v["anios"] * 12)
    invertido = c.saldos_con_aportes(0, mensual, tm, meses)
    guardado = [mensual * i for i in range(meses + 1)]
    return Resultado(
        kpis=[("Al mes", moneda(mensual), CORAL), ("Al año", moneda(anual), NARANJA),
              (f"Ahorrado en {int(v['anios'])} años", moneda(guardado[-1]), CIELO),
              (f"Invertido al {decimal(v['rendimiento'], 1)}% EA", moneda(invertido[-1]), ESMERALDA)],
        grafico={"tipo": "lineas",
                 "series": [{"nombre": "Si lo guardas", "valores": guardado, "color": CIELO},
                            {"nombre": "Si lo inviertes", "valores": invertido, "color": ESMERALDA,
                             "relleno": True}],
                 "etiquetas_x": _marcas_anios(meses)},
        nota=f"Ese hábito te cuesta {moneda(anual)} al año. No hace falta eliminarlo del todo: "
             "recortar la mitad ya libera una cantidad importante.",
        nivel="aviso")


# ----------------------------------------------------------------------
# Fondo de emergencia
# ----------------------------------------------------------------------
def _fondo(v):
    meta = v["gastos"] * v["meses"]
    falta = max(0.0, meta - v["actual"])
    if falta <= 0:
        return Resultado(
            kpis=[("Meta del fondo", moneda(meta), ESMERALDA), ("Ya tienes", moneda(v["actual"]), CIELO),
                  ("Falta", moneda(0), ESMERALDA)],
            grafico={"tipo": "barras", "items": [("Meta", meta, ESMERALDA), ("Tienes", v["actual"], CIELO)]},
            nota="Ya alcanzaste tu meta. Mantén el fondo en una cuenta segura y úsalo solo en emergencias.",
            nivel="ok")
    if v["ahorro"] <= 0:
        raise ValueError("Escribe cuánto puedes ahorrar al mes para estimar el tiempo.")
    meses = math.ceil(falta / v["ahorro"])
    tope = min(meses, 120)
    saldos = [min(meta, v["actual"] + v["ahorro"] * i) for i in range(tope + 1)]
    nivel = "ok" if meses <= 24 else "aviso"
    nota = (f"Llegarías en {c.meses_a_texto(meses)}. " +
            ("Es un plazo razonable." if meses <= 24 else
             "Es largo: considera una meta intermedia de 1 a 3 meses o aumentar el aporte."))
    return Resultado(
        kpis=[("Meta del fondo", moneda(meta), ESMERALDA), ("Falta por ahorrar", moneda(falta), CORAL),
              ("Tiempo estimado", c.meses_a_texto(meses), ORO)],
        grafico={"tipo": "lineas",
                 "series": [{"nombre": "Meta", "valores": [meta] * (tope + 1), "color": TENUE},
                            {"nombre": "Tu fondo", "valores": saldos, "color": ESMERALDA, "relleno": True}],
                 "etiquetas_x": _marcas_meses(tope)},
        nota=nota, nivel=nivel)


# ----------------------------------------------------------------------
# Meta de ahorro
# ----------------------------------------------------------------------
def _meta(v):
    n = int(v["plazo"])
    tm = c.ea_a_mensual(v["rendimiento"] / 100)
    cuota = c.aporte_para_meta(v["meta"], v["actual"], tm, n)
    saldos = c.saldos_con_aportes(v["actual"], cuota, tm, n)
    aportado = v["actual"] + cuota * n
    rendimientos = saldos[-1] - aportado
    nota = ("Con lo que ya tienes y los rendimientos, tu meta se cumple sin aportes adicionales."
            if cuota == 0 else
            f"Debes separar {moneda(cuota)} cada mes durante {c.meses_a_texto(n)}. "
            "Si es demasiado, alarga el plazo o reduce la meta.")
    return Resultado(
        kpis=[("Aporte mensual", moneda(cuota), ESMERALDA), ("Total aportado", moneda(aportado), CIELO),
              ("Rendimientos", moneda(max(0, rendimientos)), ORO)],
        grafico={"tipo": "lineas",
                 "series": [{"nombre": "Meta", "valores": [v["meta"]] * (n + 1), "color": TENUE},
                            {"nombre": "Tu ahorro", "valores": saldos, "color": ESMERALDA, "relleno": True}],
                 "etiquetas_x": _marcas_meses(n)},
        nota=nota, nivel="ok" if cuota == 0 else "info")


# ----------------------------------------------------------------------
# Ahorro automático
# ----------------------------------------------------------------------
def _ahorro_auto(v):
    aporte = v["ingreso"] * v["porcentaje"] / 100
    meses = int(v["anios"] * 12)
    tm = c.ea_a_mensual(v["rendimiento"] / 100)
    saldos = c.saldos_con_aportes(0, aporte, tm, meses)
    aportado = [aporte * i for i in range(meses + 1)]
    return Resultado(
        kpis=[("Aporte mensual", moneda(aporte), ESMERALDA), ("Total aportado", moneda(aportado[-1]), CIELO),
              ("Rendimientos", moneda(saldos[-1] - aportado[-1]), ORO),
              (f"Valor en {int(v['anios'])} años", moneda(saldos[-1]), VIOLETA)],
        grafico={"tipo": "lineas",
                 "series": [{"nombre": "Lo que aportas", "valores": aportado, "color": CIELO},
                            {"nombre": "Con rendimientos", "valores": saldos, "color": ESMERALDA,
                             "relleno": True}],
                 "etiquetas_x": _marcas_anios(meses)},
        nota="La diferencia entre las dos líneas es el trabajo del interés compuesto: "
             "crece más cuanto más tiempo dejes el dinero.",
        nivel="info")


# ----------------------------------------------------------------------
# Préstamo / tasa de interés
# ----------------------------------------------------------------------
def _prestamo(v):
    n = int(v["plazo"])
    tm = c.ea_a_mensual(v["tasa"] / 100)
    cuota = c.cuota_prestamo(v["monto"], tm, n)
    total = cuota * n
    saldos = c.saldos_prestamo(v["monto"], tm, n, cuota)
    pct = (total - v["monto"]) / v["monto"] * 100
    return Resultado(
        kpis=[("Cuota mensual", moneda(cuota), ESMERALDA), ("Intereses totales", moneda(total - v["monto"]), CORAL),
              ("Total a pagar", moneda(total), ORO),
              ("Tasa mensual efectiva", porcentaje(tm * 100, 2), CIELO),
              ("Tasa nominal anual", porcentaje(tm * 1200, 2), VIOLETA)],
        grafico={"tipo": "lineas",
                 "series": [{"nombre": "Saldo de la deuda", "valores": saldos, "color": CORAL, "relleno": True}],
                 "etiquetas_x": _marcas_meses(n)},
        nota=f"Pagas {porcentaje(pct, 0)} adicional sobre lo prestado. Compara créditos por la tasa EA "
             "y por el total a pagar, no solo por la cuota.",
        nivel="aviso" if pct > 30 else "info")


# ----------------------------------------------------------------------
# Bonos
# ----------------------------------------------------------------------
def _bonos(v):
    anios = int(v["anios"])
    nominal = v["nominal"]
    precio = nominal * v["precio"] / 100
    cupon = nominal * v["cupon"] / 100
    ganancia = cupon * anios + nominal - precio
    tir = c.rendimiento_bono(nominal, v["cupon"] / 100, anios, precio) * 100
    items = [(f"Año {a}", cupon + (nominal if a == anios else 0), CIELO if a < anios else ESMERALDA)
             for a in range(1, anios + 1)]
    if v["precio"] < 100:
        relacion = "con descuento: pagas menos que el nominal, por eso tu rendimiento supera al cupón"
    elif v["precio"] > 100:
        relacion = "con prima: pagas más que el nominal, por eso tu rendimiento queda por debajo del cupón"
    else:
        relacion = "a la par: tu rendimiento coincide con el cupón"
    return Resultado(
        kpis=[("Cupón anual", moneda(cupon), CIELO), ("Ganancia total", moneda(ganancia), ESMERALDA),
              ("Rendimiento al vencimiento", porcentaje(tir, 2), ORO)],
        grafico={"tipo": "barras", "items": items},
        nota=f"Compras {relacion}. El último año recibes además el valor nominal.",
        nivel="info")


# ----------------------------------------------------------------------
# Certificados de depósito
# ----------------------------------------------------------------------
def _cdt(v):
    bruto = c.rendimiento_periodo(v["capital"], v["tasa"] / 100, v["dias"])
    retencion = bruto * v["retencion"] / 100
    neto = bruto - retencion
    return Resultado(
        kpis=[("Rendimiento bruto", moneda(bruto), CIELO), ("Retención", moneda(retencion), CORAL),
              ("Rendimiento neto", moneda(neto), ESMERALDA), ("Total a recibir", moneda(v["capital"] + neto), ORO),
              ("Rentabilidad del plazo", porcentaje(neto / v["capital"] * 100, 2), VIOLETA)],
        grafico={"tipo": "barras",
                 "items": [("Rendimiento bruto", bruto, CIELO), ("Retención", retencion, CORAL),
                           ("Rendimiento neto", neto, ESMERALDA)]},
        nota="La tasa EA es anual: para plazos menores a un año el rendimiento se calcula proporcionalmente "
             "(base 365 días). Confirma con tu entidad cómo aplica la retención.",
        nivel="info")


# ----------------------------------------------------------------------
# Acciones
# ----------------------------------------------------------------------
def _acciones(v):
    cant = v["cantidad"]
    com = v["comision"] / 100

    def neto(precio_venta):
        compra = v["compra"] * cant
        venta = precio_venta * cant
        comisiones = (compra + venta) * com
        divid = v["dividendo"] * cant
        ganancia = venta - compra - comisiones + divid
        return ganancia, ganancia / (compra * (1 + com)) * 100

    ganancia, rent = neto(v["venta"])
    compra = v["compra"] * cant
    venta = v["venta"] * cant
    comisiones = (compra + venta) * com
    filas = []
    for cambio in (-30, -15, 0, 15, 30):
        g, r = neto(v["compra"] * (1 + cambio / 100))
        filas.append((f"{'+' if cambio > 0 else ''}{cambio}%", moneda(v["compra"] * (1 + cambio / 100)),
                      moneda(g), porcentaje(r, 1)))
    return Resultado(
        kpis=[("Inversión inicial", moneda(compra), CIELO), ("Ganancia neta", moneda(ganancia),
              ESMERALDA if ganancia >= 0 else ERROR),
              ("Rentabilidad", porcentaje(rent, 1), ESMERALDA if rent >= 0 else ERROR),
              ("Comisiones pagadas", moneda(comisiones), CORAL)],
        grafico={"tipo": "barras", "items": [("Inversión inicial", compra, CIELO), ("Valor de venta", venta, ORO),
                                             ("Dividendos", v["dividendo"] * cant, ESMERALDA),
                                             ("Comisiones", comisiones, CORAL)]},
        tabla=(["Precio vs. compra", "Precio de venta", "Ganancia neta", "Rentabilidad"], filas),
        nota="La tabla muestra qué pasaría si el precio cambiara. Una caída del 30% exige una subida de "
             "más del 40% para recuperarte: por eso conviene diversificar.",
        nivel="info" if ganancia >= 0 else "aviso")


# ----------------------------------------------------------------------
# Fondos indexados
# ----------------------------------------------------------------------
def _fondos(v):
    meses = int(v["anios"] * 12)
    neto_pct = v["retorno"] - v["comision"]
    tm = c.ea_a_mensual(neto_pct / 100)
    tm_sin = c.ea_a_mensual(v["retorno"] / 100)
    saldos = c.saldos_con_aportes(v["inicial"], v["aporte"], tm, meses)
    sin_comision = c.saldos_con_aportes(v["inicial"], v["aporte"], tm_sin, meses)
    aportado = [v["inicial"] + v["aporte"] * i for i in range(meses + 1)]
    costo = sin_comision[-1] - saldos[-1]
    return Resultado(
        kpis=[("Valor final", moneda(saldos[-1]), ESMERALDA), ("Total aportado", moneda(aportado[-1]), CIELO),
              ("Ganancia", moneda(saldos[-1] - aportado[-1]), ORO),
              ("Costo de la comisión", moneda(costo), CORAL)],
        grafico={"tipo": "lineas",
                 "series": [{"nombre": "Lo que aportas", "valores": aportado, "color": CIELO},
                            {"nombre": f"Fondo (rend. neto {decimal(neto_pct, 1)}%)", "valores": saldos,
                             "color": ESMERALDA, "relleno": True}],
                 "etiquetas_x": _marcas_anios(meses)},
        nota=f"Una comisión de {decimal(v['comision'], 1)}% anual te cuesta {moneda(costo)} en este plazo. "
             "Los rendimientos son hipotéticos: el mercado real sube y baja, y el pasado no garantiza el futuro.",
        nivel="info")


# ----------------------------------------------------------------------
# Diversificación
# ----------------------------------------------------------------------
def _diversificacion(v):
    rv, rf = c.asignacion_por_edad(v["edad"], v["riesgo"])
    partes = [("Fondos indexados", rv * .6, ESMERALDA), ("Acciones", rv * .4, CIELO),
              ("Bonos", rf * .5, ORO), ("Certificados de depósito", rf * .5, VIOLETA)]
    perfil = {1: "muy conservador", 2: "conservador", 3: "moderado", 4: "arriesgado", 5: "muy arriesgado"}[int(v["riesgo"])]
    return Resultado(
        kpis=[("Renta variable", porcentaje(rv, 0), ESMERALDA), ("Renta fija", porcentaje(rf, 0), ORO),
              ("Perfil", perfil, CIELO)],
        grafico={"tipo": "dona", "items": partes, "centro": (f"{rv:.0f}/{rf:.0f}", "variable / fija")},
        nota="Es una guía orientativa basada en la regla «100 menos tu edad», ajustada ±10 puntos por cada "
             "nivel de riesgo. No es una recomendación personalizada: revisa tu plazo y tus metas.",
        nivel="info")


# ----------------------------------------------------------------------
# Catálogo de herramientas de cálculo
# ----------------------------------------------------------------------
DEFINICIONES = {d.clave: d for d in [
    Definicion("presupuesto", "Presupuesto del mes",
               "Anota tu ingreso, tus gastos y cuánto planeas ahorrar. Ves el saldo y el peso de cada categoría.",
               [Campo("ingreso", "Ingreso mensual", 2500000, "dinero", minimo=1),
                Campo("vivienda", "Vivienda", 800000, "dinero", minimo=0),
                Campo("alimentacion", "Alimentación", 500000, "dinero", minimo=0),
                Campo("transporte", "Transporte", 200000, "dinero", minimo=0),
                Campo("servicios", "Servicios", 200000, "dinero", minimo=0),
                Campo("ocio", "Ocio y salidas", 250000, "dinero", minimo=0),
                Campo("otros", "Otros gastos", 150000, "dinero", minimo=0),
                Campo("ahorro", "Ahorro planeado", 300000, "dinero", minimo=0)], _presupuesto),
    Definicion("regla_50_30_20", "Regla 50/30/20",
               "Reparte tu ingreso neto en necesidades, deseos y ahorro.",
               [Campo("ingreso", "Ingreso mensual neto", 2500000, "dinero", minimo=1)], _regla),
    Definicion("hormiga", "Calculadora de gastos hormiga",
               "Descubre cuánto cuesta un pequeño gasto repetido y qué pasaría si lo invirtieras.",
               [Campo("gasto", "Gasto cada vez", 4500, "dinero", minimo=1),
                Campo("veces", "Veces por semana", 5, "numero", minimo=0.1, maximo=50),
                Campo("anios", "Años a proyectar", 5, "entero", minimo=1, maximo=30),
                Campo("rendimiento", "Rendimiento anual (EA)", 8, "porcentaje", minimo=0, maximo=50)], _hormiga),
    Definicion("fondo_emergencia", "Fondo de emergencia",
               "Calcula la meta de tu colchón y en cuánto tiempo lo alcanzas.",
               [Campo("gastos", "Gastos esenciales al mes", 1800000, "dinero", minimo=1),
                Campo("meses", "Meses que quieres cubrir", 6, "entero", minimo=1, maximo=24),
                Campo("actual", "Ya tienes ahorrado", 500000, "dinero", minimo=0),
                Campo("ahorro", "Puedes ahorrar al mes", 250000, "dinero", minimo=0)], _fondo),
    Definicion("meta_ahorro", "Meta de ahorro",
               "Dime tu meta y tu plazo: calculo cuánto separar cada mes.",
               [Campo("meta", "Meta a reunir", 12000000, "dinero", minimo=1),
                Campo("actual", "Ya tienes", 1000000, "dinero", minimo=0),
                Campo("plazo", "Plazo en meses", 18, "entero", minimo=1, maximo=600),
                Campo("rendimiento", "Rendimiento anual (EA)", 5, "porcentaje", minimo=0, maximo=50,
                      ayuda="Usa 0 si lo guardas sin rendimiento")], _meta),
    Definicion("ahorro_automatico", "Ahorro automático",
               "Proyecta cuánto acumularías si ahorras un porcentaje fijo de tu ingreso.",
               [Campo("ingreso", "Ingreso mensual", 2500000, "dinero", minimo=1),
                Campo("porcentaje", "Porcentaje que ahorras", 10, "porcentaje", minimo=0.1, maximo=100),
                Campo("anios", "Años", 5, "entero", minimo=1, maximo=40),
                Campo("rendimiento", "Rendimiento anual (EA)", 6, "porcentaje", minimo=0, maximo=50)], _ahorro_auto),
    Definicion("prestamo", "Costo de un préstamo",
               "Convierte una tasa en la cuota real y en el total que terminarás pagando.",
               [Campo("monto", "Monto prestado", 5000000, "dinero", minimo=1),
                Campo("tasa", "Tasa efectiva anual (EA)", 24, "porcentaje", minimo=0, maximo=200),
                Campo("plazo", "Plazo en meses", 24, "entero", minimo=1, maximo=600)], _prestamo),
    Definicion("bonos", "Calculadora de bonos",
               "Cupones, ganancia total y rendimiento al vencimiento según el precio que pagas.",
               [Campo("nominal", "Valor nominal", 1000000, "dinero", minimo=1),
                Campo("cupon", "Cupón anual", 9, "porcentaje", minimo=0, maximo=100),
                Campo("anios", "Años al vencimiento", 5, "entero", minimo=1, maximo=15),
                Campo("precio", "Precio de compra (% del nominal)", 100, "porcentaje", minimo=50, maximo=150,
                      ayuda="100 = lo compras a la par")], _bonos),
    Definicion("cdt", "Certificado de depósito",
               "Rendimiento de un certificado a plazo fijo, bruto y neto de retención.",
               [Campo("capital", "Capital", 5000000, "dinero", minimo=1),
                Campo("tasa", "Tasa efectiva anual (EA)", 10, "porcentaje", minimo=0, maximo=100),
                Campo("dias", "Plazo en días", 180, "entero", minimo=1, maximo=3650),
                Campo("retencion", "Retención sobre rendimientos", 4, "porcentaje", minimo=0, maximo=50)], _cdt),
    Definicion("acciones", "Simulador de una operación en acciones",
               "Ganancia neta de comprar y vender, con comisiones y dividendos, más una tabla de escenarios.",
               [Campo("compra", "Precio de compra", 10000, "dinero", minimo=1),
                Campo("venta", "Precio de venta", 11500, "dinero", minimo=0),
                Campo("cantidad", "Cantidad de acciones", 50, "entero", minimo=1),
                Campo("comision", "Comisión por operación", 0.5, "porcentaje", minimo=0, maximo=10),
                Campo("dividendo", "Dividendo por acción", 200, "dinero", minimo=0)], _acciones),
    Definicion("fondos_indexados", "Fondo indexado a largo plazo",
               "Proyecta tus aportes y mira cuánto pesa la comisión del fondo.",
               [Campo("aporte", "Aporte mensual", 300000, "dinero", minimo=0),
                Campo("inicial", "Aporte inicial", 0, "dinero", minimo=0),
                Campo("retorno", "Rendimiento anual (antes de comisión)", 8.5, "porcentaje", minimo=0, maximo=30),
                Campo("comision", "Comisión anual del fondo", 0.5, "porcentaje", minimo=0, maximo=5),
                Campo("anios", "Años", 20, "entero", minimo=1, maximo=50)], _fondos),
    Definicion("diversificacion", "Distribución de tu portafolio",
               "Una guía de cómo repartir entre renta variable y renta fija según tu edad y tu riesgo.",
               [Campo("edad", "Tu edad", 22, "entero", minimo=16, maximo=90),
                Campo("riesgo", "Tolerancia al riesgo (1 a 5)", 3, "entero", minimo=1, maximo=5,
                      ayuda="1 = muy conservador · 5 = muy arriesgado")], _diversificacion),
]}

# ----------------------------------------------------------------------
# Listas de verificación (diagnóstico y seguridad)
# ----------------------------------------------------------------------
LISTAS = {
    "diagnostico": {
        "titulo": "Diagnóstico de salud financiera",
        "subtitulo": "Marca lo que ya haces. Con tus respuestas Cosecha arma tu plan de acción personal: lo que no marques se convierte en pasos ordenados por urgencia.",
        "genera_plan": True,
        "items": [
            ("Reviso o anoto mis gastos cada mes", "Anota tus gastos durante una semana y apóyate en el Registro de gastos."),
            ("Gasto menos de lo que gano", "Recorta primero gastos hormiga y deseos hasta que el saldo del mes sea positivo."),
            ("Pago todas mis deudas a tiempo", "Programa recordatorios o débitos automáticos para evitar la mora."),
            ("Tengo un fondo de emergencia de al menos 3 meses de gastos", "Empieza con un mini fondo de un mes y automatiza el aporte."),
            ("No uso la tarjeta de crédito si no puedo pagarla completa", "Usa la tarjeta solo para compras que podrías pagar en efectivo ese mes."),
            ("Ahorro un porcentaje fijo de mi ingreso cada mes", "Programa una transferencia automática el día de pago, aunque sea del 5%."),
            ("Tengo una meta financiera con monto y fecha", "Define una meta y calcula cuánto separar cada mes."),
            ("Protejo mis cuentas con verificación en dos pasos", "Actívala hoy en tu correo y en las apps de tu banco."),
        ],
        "niveles": [
            (0.34, "Punto de partida", "Estás empezando, y eso ya es un paso. Enfócate en un solo hábito a la vez.", ERROR),
            (0.67, "En construcción", "Ya tienes bases. Cierra los huecos de abajo en orden y subirás rápido de nivel.", ORO),
            (1.0, "Sólida", "Tu salud financiera es buena. Te faltan pocos detalles para blindarla.", CIELO),
            (1.01, "Excelente", "Cumples todos los puntos. Mantén el hábito y revisa tu plan cada mes.", ESMERALDA),
        ],
        "completo": "¡Lo cumples todo! Sigue revisando tu plan una vez al mes.",
    },
    "dos_pasos": {
        "titulo": "Chequeo de seguridad de tus cuentas",
        "subtitulo": "Marca las medidas que ya aplicas. Empieza por las primeras: protegen lo más importante.",
        "items": [
            ("Activé la verificación en dos pasos en mi correo principal", "Tu correo permite restablecer casi todas tus contraseñas: protégelo primero."),
            ("La activé también en mis apps y cuentas bancarias", "Entra a la configuración de seguridad de tu app bancaria y actívala hoy."),
            ("Uso una contraseña distinta en cada cuenta importante", "Una contraseña repetida convierte una filtración en efecto dominó."),
            ("Uso un administrador de contraseñas o frases largas", "Una frase de 4 o más palabras es más segura y más fácil de recordar."),
            ("Nunca comparto los códigos que me llegan por SMS o app", "Ningún banco ni tienda legítima te pedirá ese código."),
            ("Tengo activadas las alertas de transacciones", "Activa notificaciones de cada compra o transferencia para detectar abusos rápido."),
            ("Descargo apps solo de las tiendas oficiales", "Evita archivos instaladores enviados por mensaje o enlaces desconocidos."),
            ("Evito operar con mi banco en redes wifi públicas", "Usa tus datos móviles para operaciones bancarias fuera de casa."),
        ],
        "niveles": [
            (0.34, "Riesgo alto", "Tus cuentas están bastante expuestas. Empieza hoy por el primer punto sin marcar.", ERROR),
            (0.67, "Riesgo medio", "Tienes protecciones básicas, pero aún hay puertas abiertas.", ORO),
            (1.0, "Riesgo bajo", "Vas muy bien. Un par de ajustes más y quedas blindado.", CIELO),
            (1.01, "Muy protegido", "Cumples todas las medidas. Revisa tus alertas con regularidad.", ESMERALDA),
        ],
        "completo": "¡Excelente! Revisa tus alertas y tus accesos con regularidad.",
    },
}

# ----------------------------------------------------------------------
# Casos para entrenar la detección de fraudes
# ----------------------------------------------------------------------
CASOS_FRAUDE = [
    dict(canal="SMS", remitente="+57 300 000 0000 (número desconocido)",
         texto="Tu cuenta fue bloqueada por seguridad. Ingresa a bit.ly/banco-seguro y confirma tu clave en los próximos 10 minutos o perderás el acceso.",
         fraude=True,
         explicacion="Es phishing. Combina urgencia, un enlace acortado y la petición de tu clave. Los bancos no bloquean cuentas por SMS con enlaces para pedir contraseñas.",
         senales=["Urgencia de 10 minutos", "Enlace acortado", "Te pide la clave"]),
    dict(canal="Notificación", remitente="App oficial de tu banco",
         texto="Compra aprobada por $45.000 en una tienda. Si no la reconoces, ábrela desde la app o llama al número impreso en tu tarjeta.",
         fraude=False,
         explicacion="Es legítimo: informa un movimiento, no te pide datos ni claves y te dirige a canales oficiales que tú ya conoces.",
         senales=["No pide datos", "No trae enlaces", "Remite al número de tu tarjeta"]),
    dict(canal="WhatsApp", remitente="Número nuevo: «Hola mamá, soy yo»",
         texto="Hola mamá, cambié de número y se me dañó la app del banco. ¿Me transfieres $300.000 ya? Es urgente, te explico luego.",
         fraude=True,
         explicacion="Es suplantación de un familiar. Pide dinero con urgencia desde un número nuevo y evita dar explicaciones. Llama al número de siempre de esa persona antes de transferir.",
         senales=["Número nuevo", "Pide dinero urgente", "Evita hablar por voz"]),
    dict(canal="Llamada", remitente="«Asesor de seguridad del banco»",
         texto="Detectamos una compra sospechosa. Para cancelarla, dígame el código de 6 dígitos que le acaba de llegar por mensaje.",
         fraude=True,
         explicacion="Es fraude. Ese código autoriza operaciones a tu nombre. Ningún banco te lo pide jamás: si lo das, ellos completan la compra o ingresan a tu cuenta.",
         senales=["Pide un código de verificación", "Llamada que tú no pediste"]),
    dict(canal="Redes sociales", remitente="Anuncio: «Inversiones Garantizadas»",
         texto="Invierte $500.000 hoy y recibe $1.500.000 en 15 días. Ganancia garantizada, cupos limitados.",
         fraude=True,
         explicacion="Es una estafa tipo pirámide. Ninguna inversión legítima garantiza triplicar tu dinero en 15 días: a mayor rendimiento prometido, mayor riesgo.",
         senales=["Ganancia garantizada", "Rendimiento irreal", "Cupos limitados"]),
    dict(canal="Notificación", remitente="Correo oficial de tu proveedor de correo",
         texto="Detectamos un nuevo inicio de sesión desde tu teléfono. Si fuiste tú, no tienes que hacer nada.",
         fraude=False,
         explicacion="Es un aviso informativo. No pide datos, no incluye enlaces de verificación y no exige ninguna acción si fuiste tú. Si no fuiste tú, cambia la contraseña desde el sitio oficial.",
         senales=["No pide datos", "No presiona", "Informa y ya"]),
]
