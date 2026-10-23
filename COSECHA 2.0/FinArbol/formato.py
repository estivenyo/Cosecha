"""Lectura y formato de números (estilo latinoamericano: 1.250.000,50)."""


def leer_numero(texto):
    """Convierte texto a número. Acepta 2500000, 2.500.000, 2,5 y 1.234,56."""
    t = texto.strip().replace("$", "").replace("%", "").replace(" ", "")
    if not t:
        raise ValueError("Escribe un número.")
    if "," in t and "." in t:
        # El último separador que aparece es el decimal.
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", "") if t.count(",") > 1 else t.replace(",", ".")
    elif "." in t:
        partes = t.split(".")
        if len(partes) > 2:
            t = "".join(partes)                      # 2.500.000
        elif len(partes[1]) == 3 and partes[0] not in ("", "0", "-0") and len(partes[0].lstrip("-")) <= 3:
            t = "".join(partes)                      # 2.500 -> 2500
    try:
        return float(t)
    except ValueError:
        raise ValueError("Escribe un número válido.") from None


def _miles(texto):
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


def moneda(x):
    signo = "-" if round(x) < 0 else ""
    return signo + "$" + f"{abs(round(x)):,}".replace(",", ".")


def decimal(x, n=1):
    return _miles(f"{x:,.{n}f}")


def porcentaje(x, n=1):
    return decimal(x, n) + "%"


def numero_campo(x, tipo):
    """Cómo se muestra un valor dentro de un campo de entrada."""
    if tipo in ("dinero", "entero"):
        return f"{round(x):,}".replace(",", ".")
    texto = f"{x:.4f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def compacto(x):
    """Etiqueta corta para ejes de gráficos: 850 mil, 17,4 M."""
    a = abs(x)
    if a >= 1e9:
        return decimal(x / 1e9, 1) + " mil M"
    if a >= 1e6:
        return decimal(x / 1e6, 1) + " M"
    if a >= 1e3:
        return f"{round(x / 1e3)} mil"
    return f"{round(x)}"
