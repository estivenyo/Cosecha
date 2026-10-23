"""Paleta, tipografías y utilidades de color de la interfaz.

Tema: «bosque nocturno financiero». Fondo verde casi negro, cada rama del árbol
tiene su propio color y el oro marca la raíz.
"""

# --- Colores base -----------------------------------------------------
FONDO = "#0A1210"
PANEL = "#0F1B17"
TARJETA = "#14261F"
BORDE = "#1F3A30"
TEXTO = "#E9F3EE"
TENUE = "#82998E"
ORO = "#F2C14E"
ESMERALDA = "#2EE59D"
ERROR = "#FF7A6B"

# Un color por cada rama principal del árbol (los descendientes lo heredan).
RAMAS = ["#2EE59D", "#5CC8FF", "#FF7A6B", "#B28CFF", "#FF9F43", "#F4D35E"]

# --- Tipografías ------------------------------------------------------
F_TITULO = ("Georgia", 21, "bold")
F_SUBTITULO = ("Georgia", 15, "bold")
F_UI = ("Segoe UI", 10)
F_UI_B = ("Segoe UI", 10, "bold")
F_TEXTO = ("Segoe UI", 11)
F_NODO = ("Segoe UI", 10, "bold")
F_MONO = ("Consolas", 9)
F_PEQ = ("Segoe UI", 8, "bold")
F_NUM = ("Georgia", 24, "bold")


def mezclar(color_a, color_b, t):
    """Mezcla dos colores hex. t=0 devuelve a, t=1 devuelve b."""
    t = max(0.0, min(1.0, t))
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    c = [round(a[i] + (b[i] - a[i]) * t) for i in range(3)]
    return "#%02x%02x%02x" % tuple(c)

# Nombres para los colores de las ramas (se usan en gráficos y tarjetas).
CIELO, CORAL, VIOLETA, NARANJA, AMARILLO = RAMAS[1], RAMAS[2], RAMAS[3], RAMAS[4], RAMAS[5]
CATEGORIAS = ["#2EE59D", "#5CC8FF", "#FF7A6B", "#B28CFF", "#FF9F43", "#F4D35E", "#7BE0D6", "#E58CC9"]
F_KPI = ("Georgia", 14, "bold")
F_TEXTO_PANEL = ("Segoe UI", 10)


def color_de_nodo(nodo):
    """[ÁRBOL] Color de un tema: el de su rama principal (hijo de la raíz); la raíz es dorada."""
    camino = nodo.camino_nodos()
    if len(camino) == 1:
        return ORO
    return RAMAS[camino[0].hijos.index(camino[1]) % len(RAMAS)]
