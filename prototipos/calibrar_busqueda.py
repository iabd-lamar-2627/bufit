"""Calibra el UMBRAL del RAG con preguntas de prueba.

Lanza al servicio de conocimiento preguntas que SÍ tienen documento y otras que NO,
y muestra la mejor puntuación de cada una. El umbral bueno es el que deja por encima
las que tienen documento y por debajo las que no.

    python calibrar_busqueda.py
"""
import requests

CONOCIMIENTO = "http://localhost:8013"

# (pregunta, palabra que debe aparecer en el título del documento correcto)
CON_DOCUMENTO = [
    ("¿cómo se hace la paella?", "paella"),
    ("arroz con conejo los domingos", "paella"),
    ("explícame cómo se hace la fideuà", "fideuà"),
    ("¿cómo se juega a la brisca?", "brisca"),
    ("¿cuántas fichas tiene el dominó?", "dominó"),
    ("¿cuánto cuesta un viaje del Imserso?", "Imserso"),
    ("¿cómo pido la teleasistencia?", "eleasistencia"),
    ("¿cuándo son las fiestas de Moros y Cristianos en Xàbia?", "Moros"),
    ("dime un refrán del tiempo", "efranes"),
    ("¿cómo mando una foto por WhatsApp?", "foto"),
    ("me han llamado del banco pidiéndome el pin", "estafas"),
    ("¿qué son los riuraus?", "riuraus"),
]
SIN_DOCUMENTO = [
    "esta mañana he desayunado tostadas con caballa",
    "hola, ¿qué tal estás?",
    "mi nieto se llama Pablo y estudia en Valencia",
    "¿tengo a alguien para comer mañana en casa?",
    "hoy hace muy buen día",
    "me duele un poco la espalda",
    "ayer vi una película muy bonita en la tele",
    "¿qué hora es?",
]


def mejor(pregunta):
    r = requests.post(f"{CONOCIMIENTO}/buscar", json={"texto": pregunta, "k": 1}, timeout=60)
    r.raise_for_status()
    t = r.json()["resultados"][0]
    return t["puntuacion"], t["titulo"]


print("\nCON documento (deberían puntuar ALTO):")
altos = []
for pregunta, esperado in CON_DOCUMENTO:
    p, titulo = mejor(pregunta)
    ok = "✓" if esperado.lower() in titulo.lower() else "✗ documento equivocado"
    altos.append(p)
    print(f"  {p:.2f}  {ok:24}  {pregunta}  →  {titulo}")

print("\nSIN documento (deberían puntuar BAJO):")
bajos = []
for pregunta in SIN_DOCUMENTO:
    p, titulo = mejor(pregunta)
    bajos.append(p)
    print(f"  {p:.2f}  {pregunta}  →  {titulo}")

print(f"\nLa más baja CON documento: {min(altos):.2f}")
print(f"La más alta SIN documento: {max(bajos):.2f}")
if min(altos) > max(bajos):
    print(f"Umbral recomendado: {(min(altos) + max(bajos)) / 2:.2f}")
else:
    print("Se solapan: no hay un umbral que separe todo. Mira qué preguntas fallan.")
