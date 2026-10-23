"""Prueba del filtro de relevancia: un mensaje al azar o incoherente no debe avanzar por el árbol.

Uso:  python pruebas_filtro.py   (no necesita Ollama ni interfaz)
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from pathlib import Path
from repositorio import RepositorioJSON
from guia import GuiaArbol
from conocimiento import BaseConocimiento
from asistente import AsistenteFinanciero
ruta=Path(__file__).parent/"FinanzasPersonales.json"
arbol=RepositorioJSON(ruta).cargar() if hasattr(RepositorioJSON(ruta),"cargar") else None
base=BaseConocimiento(Path(__file__).parent/"ConocimientoIA.txt",ruta)
a=AsistenteFinanciero(None,base)
def g(nombre=None):
    gu=GuiaArbol(arbol)
    if nombre: gu.ir_a(next(n for n in arbol.preorden() if n.valor==nombre))
    return gu
casos=[ # (nodo, mensaje, bruto IA, esperado)
 (None,"asdfgh jjj",{"accion":"elegir","opcion":3},"fuera_de_tema"),
 (None,"me gusta la pizza con piña",{"accion":"elegir","opcion":2},"fuera_de_tema"),
 (None,"quién ganó el partido de ayer",{"accion":"ir_a","tema":"Acciones"},"fuera_de_tema"),
 (None,"cuéntame un chiste",{"accion":"responder","tema":"Ahorro"},"fuera_de_tema"),
 (None,"hola",{"accion":"elegir","opcion":1},"aclarar"),
 (None,"quiero salir de mis deudas",{"accion":"elegir","opcion":3},"elegir"),
 (None,"tengo deudas con la tarjeta",{"accion":"elegir","opcion":3},"elegir"),
 (None,"quiero ahorrar para una moto",{"accion":"elegir","opcion":2},"elegir"),
 (None,"quiero ahorrar para una moto",{"accion":"elegir","opcion":4},"responder"),  # IA se equivocó de opción -> no entra
 (None,"¿qué es la inflación?",{"accion":"responder","tema":"Inversión"},"responder"),
 (None,"¿qué es un CDT?",{"accion":"responder","tema":"Certificados de depósito"},"responder"),
 (None,"me llegó un mensaje del banco pidiéndome la clave",{"accion":"responder","tema":"Fraudes en línea"},"responder"),
 (None,"¿cómo funciona esto?",{"accion":"ayuda"},"ayuda"),
 (None,"la 3",{"accion":"elegir","opcion":3},"elegir"),
 (None,"no sé, lo que sea",{"accion":"aclarar"},"aclarar"),
 ("Deuda","mejor las pequeñas, así me motivo",{"accion":"elegir","opcion":2},"elegir"),
 ("Deuda","jajaja qué risa",{"accion":"elegir","opcion":1},"fuera_de_tema"),
 ("Deuda","quiero invertir en acciones",{"accion":"ir_a","tema":"Acciones"},"ir_a"),
 ("Deuda","me duele la cabeza",{"accion":"ir_a","tema":"Acciones"},"fuera_de_tema"),
 (None,"pen",{"accion":"elegir","opcion":2},"fuera_de_tema"),
 (None,"pen",{"accion":"aclarar"},"fuera_de_tema"),
 (None,"ayyyhostia",{"accion":"responder","tema":"Inversión"},"fuera_de_tema"),
 (None,"ayyyhostia",{"accion":"practicar"},"fuera_de_tema"),
 ("Acciones","ayyyhostia",{"accion":"practicar"},"fuera_de_tema"),
 ("Acciones","pen",{"accion":"ayuda"},"fuera_de_tema"),
 ("Acciones","xd",{"accion":"volver"},"fuera_de_tema"),
 (None,"jajaja",{"accion":"ir_a","tema":"Acciones"},"fuera_de_tema"),
 ("Acciones","quiero volver",{"accion":"volver"},"volver"),
 (None,"cómo funciona esta pantalla",{"accion":"ayuda"},"ayuda"),
 (None,"no sé",{"accion":"aclarar"},"aclarar"),
 ("Acciones","quiero practicar",{"accion":"practicar"},"concepto"),   # primero se explica el concepto
]
mal=0
for nodo,msg,bruto,esp in casos:
    gu=g(nodo)
    b={"razon":"x","opcion":0,"tema":"",**bruto}
    d=a.validar(b,gu,msg,None)
    ok = d.accion==esp
    mal += not ok
    print("OK " if ok else "MAL", f"{(nodo or 'raíz'):8}| {msg[:45]:45}| IA:{bruto['accion']:9} -> {d.accion:14} (esperado {esp}) {d.razon if d.accion!=bruto['accion'] else ''}")
# aceptar tema propuesto
gu=g(); sug=next(n for n in arbol.preorden() if n.valor=="Certificados de depósito")
d=a.validar({"accion":"ir_a","tema":"Certificados de depósito","opcion":0,"razon":""},gu,"sí, quiero ver ese tema",sug); print("OK " if d.accion=="ir_a" else "MAL","acepta propuesta ->",d.accion); mal+= d.accion!="ir_a"
print("fallos:",mal)
assert mal==0, "el filtro de relevancia dejó pasar o bloqueó mensajes"
print("Todo correcto.")
