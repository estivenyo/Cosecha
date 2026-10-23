"""Filtro de relevancia: decide si un mensaje tiene relación REAL con las finanzas personales o con un tema de la guía.

La IA (llama3.2:1b) a veces lleva a la persona a un tema aunque el mensaje no tenga nada que ver. Este módulo es la
segunda barrera, hecha por el programa: para entrar a un tema o sugerirlo, el mensaje debe compartir al menos una
palabra (por su raíz) con ese tema, su respuesta o sus palabras clave. Para responder como asesor, debe hablar de
algo del mundo del dinero.
"""
import re
import unicodedata

# Raíces (primeras 5 letras) de palabras de finanzas en general. No sirven para entrar a un tema concreto.
FINANZAS = set("""
dinero plata sueld salar ingre gasto gasta gasto ahorr deuda debo debe credi presta banco banca tarje
inver bolsa accio bonos bono cdt fondo presu infla impue renta pensi jubil segur estaf fraud phish clave
moned dolar pesos cuota mora finan econo cobro cobra factu nomin patri riesg rendi divid porta diver meta
emerg hipot arrie merca cript bitco negoc emprend cajer retir pagar pago pagos depos comis tasa ganar
ganan vende leasi ventas precio costo cuesta barat caro lucro ingreso fiado crece creci aprop invers
""".split())
FINANZAS = {r[:5] for r in FINANZAS}          # todas las raíces miden 5 letras como máximo

# Palabras que solo cuentan completas (su raíz también aparece en palabras que no son de dinero: «cuéntame», «interesante»).
FINANZAS_EXACTAS = set("""
cuenta cuentas interes intereses transferencia transferir compra compras comprar comprando contrasena contrasenas uvr gmf afp dian iva tes etf pib 4x1000 cesantias
""".split())

# Palabras demasiado comunes: no cuentan como evidencia de que el mensaje habla de un tema concreto.
GENERICAS = set("""
dinero plata finan quier tengo puedo hacer saber necesi ayuda cuand donde porqu sobre cosa esto esta estoy algo todo
mucho quisi favor tema temas como para pero quien cual cuales mejor bueno buena gracias hola buenas ahora siempre
mi mis tu tus persona gente manera forma tiempo vez dias mes año meses años pasa pasar hace hacia entre desde hasta
""".split())

SOCIALES = set("hola buenas buenos gracias gracia saludos chao adios ok vale listo perfecto genial".split())
AFIRMATIVOS = set("si sí dale claro ok vale listo vamos bueno perfecto adelante".split())


def _limpio(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def raices(texto):
    """Raíces de las palabras con significado de un texto (sin tildes, 5 letras)."""
    palabras = re.findall(r"[a-z0-9ñ]{3,}", _limpio(texto))
    return {p[:5] for p in palabras if len(p) >= 4 or p == "cdt"}


def habla_de_finanzas(mensaje):
    palabras = set(re.findall(r"[a-z0-9ñ]{3,}", _limpio(mensaje)))
    return bool(raices(mensaje) & FINANZAS) or bool(palabras & FINANZAS_EXACTAS)


def evidencia(mensaje, texto_tema):
    """True si el mensaje comparte alguna raíz significativa con el texto del tema."""
    comunes = (raices(mensaje) & raices(texto_tema)) - GENERICAS
    return bool(comunes)


def es_saludo(mensaje):
    r = {p for p in re.findall(r"[a-z]+", _limpio(mensaje))}
    return bool(r) and r <= SOCIALES | {"muy", "dias", "tardes", "noches", "bien", "que", "tal", "como", "estas", "estas"}


def es_afirmacion(mensaje):
    r = re.findall(r"[a-z]+", _limpio(mensaje))
    return bool(r) and len(r) <= 6 and r[0] in {_limpio(a) for a in AFIRMATIVOS}


def apunta_a_numero(mensaje):
    """«la 2», «opción 3», «el primero»: elige por número una opción que se ve en pantalla."""
    m = _limpio(mensaje).strip()
    return bool(re.fullmatch(r"(la |el |opcion |numero |la opcion |el numero )?\d", m)
                or re.search(r"\b(primer[oa]|segund[oa]|tercer[oa]|cuart[oa]|quint[oa])\b", m)
                and len(m.split()) <= 5)


# Mensajes vagos pero legítimos: la persona participa y solo falta que precise («no sé», «lo que sea»).
VAGAS = ["no se", "nose", "lo que sea", "cualquiera", "ni idea", "no entiendo", "no comprendo", "no se por donde empezar"]
# Palabras de quien pregunta por la aplicación o quiere regresar.
APP = set("ayuda ayudame funciona funcionan significa boton botones tarjeta tarjetas pantalla aplicacion app mapa chat guia "
          "cosecha como que para sirve usar uso".split())
REGRESAR = set("volver vuelve vuelvo regresar regreso atras anterior otra otro ninguna ninguno cambiar inicio".split())
PRACTICA = set("practicar practica calcular calcula calculadora simular simulador abrir abre probar prueba".split())


def _palabras(mensaje):
    return set(re.findall(r"[a-z0-9ñ]+", _limpio(mensaje)))


def es_vago(mensaje):
    m = " ".join(re.findall(r"[a-z]+", _limpio(mensaje)))
    return any(m == v or m.startswith(v + " ") for v in VAGAS)


def sentido(mensaje, accion):
    """¿El mensaje justifica esta acción? Para algo que no es de dinero ni una orden clara de la aplicación,
    ninguna acción vale salvo «fuera_de_tema»."""
    p = _palabras(mensaje)
    if habla_de_finanzas(mensaje) or es_saludo(mensaje) or es_afirmacion(mensaje) or apunta_a_numero(mensaje):
        return True
    if accion == "aclarar":
        return es_vago(mensaje)
    if accion == "ayuda":
        return len(p & APP) >= 2 or "ayuda" in p
    if accion == "volver":
        return bool(p & REGRESAR)
    if accion in ("practicar", "concepto", "sin_calculadora"):
        return bool(p & PRACTICA)
    return False
