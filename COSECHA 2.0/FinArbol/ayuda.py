"""GuiaRapida: ventana que explica, parte por parte, qué se ve en Cosecha y qué hace la IA en cada mensaje."""
import tkinter as tk

from componentes import BotonRedondeado
from estilos import BORDE, CIELO, CORAL, ESMERALDA, F_PEQ, FONDO, ORO, PANEL, TARJETA, TENUE, TEXTO, VIOLETA, mezclar

PARTES = [
    (ESMERALDA, "1", "Conversación (derecha)",
     "Aquí hablas con la IA (modelo llama3.2:1b de Ollama). Después de cada mensaje suyo aparece una tarjeta amarilla "
     "con una PREGUNTA PUNTUAL y botones numerados: toca la respuesta que más se parezca a ti y avanzas un nivel. "
     "Si prefieres, escribe con tus palabras o pregúntale lo que quieras de finanzas. Las notas en cursiva te cuentan "
     "qué decidió la IA."),
    (CIELO, "2", "Escenario (centro)",
     "El círculo grande es el tema donde estás. Las tarjetas numeradas son las opciones desde ahí: tócalas si prefieres "
     "no escribir. Al llegar a un tema final aparece su ficha (qué es, ejemplo y consejos). La línea de abajo te cuenta "
     "qué está pasando: «leyendo tu mensaje», «escribiendo», «tu turno»."),
    (ORO, "3", "Mapa (izquierda)",
     "Dibuja todos los temas de la guía como un árbol, de lo general (arriba) a lo específico (abajo). El punto brillante "
     "es donde estás, la línea iluminada es tu ruta y la barra cuenta cuántos temas llevas explorados."),
    (VIOLETA, "4", "Botones bajo el escenario",
     "Bajo el escenario: «Volver» sube un tema, «Ver tema» aparece cuando la IA te sugiere uno y «Practicar» abre la "
     "calculadora (se activa cuando ya conoces el concepto). Arriba: «Mi plan» es tu plan de acción personal, que sale de tu "
     "diagnóstico de salud financiera, y «Relaciones» muestra cómo se conectan los temas entre sí (flechas y ciclos)."),
    (CORAL, "5", "Cómo es una conversación",
     "La IA te hace una pregunta → tocas una respuesta → otra pregunta más específica (normalmente 2 o 3 en total) → "
     "llegas al tema final y la IA te explica el concepto completo → te pregunta si quieres practicar → solo si "
     "aceptas se abre la calculadora. Puedes salirte del camino cuando quieras escribiendo una duda."),
]


class GuiaRapida(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master, bg=PANEL)
        self.title("Guía rápida · Cosecha")
        self.geometry("760x800")
        self.transient(master)
        tk.Label(self, text="Cómo usar Cosecha", bg=PANEL, fg=ESMERALDA, font=("Georgia", 20, "bold"),
                 anchor="w").pack(fill="x", padx=26, pady=(22, 2))
        tk.Label(self, text="Todo lo que ves en pantalla, explicado en 5 partes.", bg=PANEL, fg=TENUE,
                 font=("Segoe UI", 10), anchor="w").pack(fill="x", padx=26, pady=(0, 14))
        for color, numero, titulo, texto in PARTES:
            fila = tk.Frame(self, bg=TARJETA, highlightthickness=1, highlightbackground=mezclar(color, PANEL, 0.6))
            fila.pack(fill="x", padx=26, pady=5)
            insignia = tk.Canvas(fila, width=44, height=44, bg=TARJETA, highlightthickness=0)
            insignia.create_oval(6, 6, 38, 38, fill=color, outline="")
            insignia.create_text(22, 22, text=numero, fill=FONDO, font=("Georgia", 15, "bold"))
            insignia.pack(side="left", padx=(14, 8), pady=12, anchor="n")
            cuerpo = tk.Frame(fila, bg=TARJETA)
            cuerpo.pack(side="left", fill="x", expand=True, padx=(0, 14), pady=10)
            tk.Label(cuerpo, text=titulo, bg=TARJETA, fg=color, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(cuerpo, text=texto, bg=TARJETA, fg=TEXTO, font=("Segoe UI", 10), anchor="w", justify="left",
                     wraplength=610).pack(fill="x", pady=(3, 0))
        BotonRedondeado(self, "Entendido", self.destroy, color=ESMERALDA, ancho=160, alto=40, fondo=PANEL).pack(pady=18)
        self.bind("<Escape>", lambda e: self.destroy())
