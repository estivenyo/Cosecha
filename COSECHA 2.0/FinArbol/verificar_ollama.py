"""Comprueba, paso a paso, que Cosecha está hablando de verdad con Ollama.  Uso:  python verificar_ollama.py"""
import time
from pathlib import Path

from asistente import AsistenteFinanciero
from conocimiento import BaseConocimiento
from guia import GuiaArbol
from ia_ollama import ClienteOllama, ErrorOllama
from repositorio import RepositorioJSON

carpeta = Path(__file__).parent
cliente = ClienteOllama()


def paso(titulo, funcion):
    print(f"\n▸ {titulo}")
    inicio = time.perf_counter()
    try:
        resultado = funcion()
    except (ErrorOllama, OSError, ValueError) as error:
        print(f"  ✗ FALLÓ: {error}")
        raise SystemExit(1)
    print(f"  ✓ OK ({time.perf_counter() - inicio:.1f} s)")
    return resultado


print(f"Servidor: {cliente.url}   Modelo: {cliente.modelo}")
paso("1. Ollama está encendido y tiene el modelo instalado", cliente.disponible)

respuesta = paso("2. El modelo genera texto (esto lo escribe llama, no el programa)",
                 lambda: cliente.texto_en_vivo([{"role": "user", "content": "Di «hola» en una frase corta."}],
                                               lambda p: None, max_tokens=30))
if not respuesta.strip():
    print("  ✗ FALLÓ: el modelo respondió vacío.")
    raise SystemExit(1)
print(f"  Respuesta real del modelo: {respuesta!r}")

arbol = RepositorioJSON(carpeta / "FinanzasPersonales.json").cargar()
base = BaseConocimiento(carpeta / "ConocimientoIA.txt", carpeta / "FinanzasPersonales.json")
guia = GuiaArbol(arbol)
asistente = AsistenteFinanciero(cliente, base)
guia.ir_a(arbol.buscar("Ahorro")[0])

decision = paso("3. La IA decide en JSON (estando en «Ahorro», el usuario dice que quiere juntar para una moto)",
                lambda: asistente.decidir(guia, "quiero juntar plata para comprarme una moto"))
elegida = guia.opciones()[decision.opcion - 1].valor if decision.accion == "elegir" else "-"
print(f"  Decisión: {decision.accion} · opción {decision.opcion} ({elegida}) · razón: {decision.razon}")
print("  Esperado: elegir «Metas de ahorro»" + ("  → ✓ acertó" if elegida == "Metas de ahorro" else "  → ✗ no coincide (puede variar; repite o mejora ConocimientoIA.txt)"))

decision2 = paso("4. Pregunta de conocimiento (estando en «Ahorro»): «¿qué es un CDT?» -> debe responder, no mover",
                 lambda: asistente.decidir(guia, "¿qué es un CDT?"))
destino = decision2.nodo.valor if decision2.nodo else "-"
print(f"  Decisión: {decision2.accion} · tema relacionado: {destino}")
print("  Esperado: responder, sugiriendo «Certificados de depósito»"
      + ("  → ✓ acertó" if decision2.accion == "responder" and destino == "Certificados de depósito"
         else "  → ✗ no coincide (puede variar; mejora los ejemplos del .txt)"))

decision3 = paso("5. Problema concreto desde otra rama: «quiero pagar mis deudas, tengo tres tarjetas»",
                 lambda: asistente.decidir(guia, "quiero pagar mis deudas, tengo tres tarjetas"))
destino = decision3.nodo.valor if decision3.nodo else "-"
print(f"  Decisión: {decision3.accion} · tema: {destino}")
print("  Esperado: ir_a «Deuda» (o «Método avalancha» / «Método bola de nieve»)"
      + ("  → ✓ acertó" if decision3.accion == "ir_a" and destino in ("Deuda", "Método avalancha", "Método bola de nieve")
         else "  → ✗ no coincide (puede variar)"))

print("\nTodo conectado: la aplicación usa este mismo camino para cada mensaje.")
