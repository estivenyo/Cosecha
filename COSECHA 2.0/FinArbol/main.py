"""Punto de entrada. Ejecuta:  python main.py

Requisitos: Python 3.10+ (con Tkinter) y Ollama abierto con el modelo llama3.2:1b
(una sola vez:  ollama pull llama3.2:1b). No hay que instalar ninguna librería de Python.
"""
from pathlib import Path

from ventana import AplicacionCosecha


def main():
    # En Windows evita que la interfaz se vea borrosa en pantallas de alta resolución.
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    carpeta = Path(__file__).parent
    AplicacionCosecha(carpeta / "FinanzasPersonales.json", carpeta).mainloop()


if __name__ == "__main__":
    main()
