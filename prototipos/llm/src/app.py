"""LLM · conversación con Ollama. Guarda un historial por partida.

- POST   /conversar             manda un mensaje y recibe la respuesta completa
- POST   /conversar/stream      igual, pero devuelve la respuesta frase a frase según se genera
- POST   /saludo                Bufit empieza la conversación (saludo según la hora)
- GET    /relleno               una frase de relleno ("espera" o "busqueda") que no se repita
- GET    /historial/{partida}   descarga el historial completo
- DELETE /historial/{partida}   borra el historial (al cerrar la partida)

Base de conocimientos (RAG), tres modos (MODO_BUSQUEDA):
- "mixto" (por defecto): si la frase nombra un tema de la base (un juego, una receta, un
  trámite...), se busca antes de llamar al modelo y el documento va en el mensaje. Si no,
  el modelo tiene la herramienta y decide él si buscar. Así lo que está en la base se usa
  siempre, y lo que las palabras clave no detectan lo puede pedir el modelo.
- "modelo": el modelo decide cuándo buscar. Tiene una herramienta
  buscar_conocimiento y la llama solo si la necesita (reglas, recetas, trámites...).
  En la charla normal no se busca nada y la respuesta sale de una sola pasada.
- "umbral": se busca en cada turno, pero un trozo solo entra si se parece mucho
  (UMBRAL_ALTO) o, si la frase menciona un tema de la base, si supera UMBRAL.

El historial vive en memoria: si el contenedor se reinicia, se pierde.
Descargarlo antes de cerrar la partida es cosa del orquestador.
"""
import json
import os
import random
import re
import time
import unicodedata
from collections import deque

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from ollama import Client, ResponseError
from pydantic import BaseModel

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODELO = os.getenv("MODELO", "llama3.2:3b")
MAX_MENSAJES = int(os.getenv("MAX_MENSAJES", "0"))   # 0 = no recortar
# Modelos con "thinking" (qwen3.5...): "false" lo desactiva. Vacío = no se envía el parámetro
PENSAR = os.getenv("PENSAR", "").lower()
OPCIONES = {"think": PENSAR == "true"} if PENSAR in ("true", "false") else {}

# Servicio de conocimiento (RAG). Vacío = no se usa.
CONOCIMIENTO_URL = os.getenv("CONOCIMIENTO_URL", "")
MODO_BUSQUEDA = os.getenv("MODO_BUSQUEDA", "mixto")   # "mixto", "modelo" o "umbral"
UMBRAL = float(os.getenv("UMBRAL", "0.5"))     # parecido mínimo (0 a 1) para usar un trozo
UMBRAL_ALTO = float(os.getenv("UMBRAL_ALTO", "0.68"))  # modo umbral: sin palabra clave hace falta más parecido
K = int(os.getenv("K", "1"))                   # cuántos trozos pedir como máximo
K_HERRAMIENTA = int(os.getenv("K_HERRAMIENTA", "2"))  # modo modelo: trozos por búsqueda
# Tope de tokens por respuesta, por si el modelo se alarga (0 = sin tope). Si lo alcanza,
# se descarta la última frase a medias para que Bufit no se corte en mitad de una palabra.
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "110"))
MAX_TOKENS_DOC = int(os.getenv("MAX_TOKENS_DOC", "220"))   # tope cuando explica algo de la base

# Frases de relleno (se releen en cada uso: se pueden editar sin reiniciar)
FICHERO_RELLENOS = os.getenv("FICHERO_RELLENOS", "/app/rellenos.json")

PROMPT_BASE = """Te llamas Bufit. Si te preguntan tu nombre, di que te llamas Bufit.

Eres un compañero de charla para personas mayores. Hablas de cualquier tema como lo haría un vecino culto y simpático: la familia, los recuerdos, el pueblo, la comida, la música, el cine, los deportes, la historia o lo que la persona quiera.

Tu especialidad son los juegos de mesa y de cartas: te encanta hablar de ellos, explicar sus reglas y jugar. Pero no los propones en cada respuesta: solo si la persona saca el tema o la conversación se queda parada.

Lo que sabes y lo que no:
- De temas generales puedes hablar con lo que sabes. Si no estás seguro de un dato concreto, como una fecha, una cifra o un nombre, dilo con naturalidad en vez de inventarlo.
- No sabes qué tiempo hace ni hará, qué día es ni las noticias de hoy. Si te preguntan algo así, responde algo como: "Eso no lo sé, mejor míralo en la radio o en el móvil." No te ofrezcas a mirarlo tú.
- No tienes internet ni puedes usar el móvil de nadie. Nunca te ofrezcas a buscar nada, ni a hacerlo tú, ni preguntes si quieren que lo busques.
- De la vida de la persona solo sabes lo que te cuente en esta conversación. No inventes nada sobre ella ni sobre su familia.
- No tienes una vida propia: no cuentes cosas que hayas hecho, comido o visto.
- Solo puedes hablar: no puedes enseñar fotos, poner música, llamar a nadie, dar comida o bebida ni hacer nada fuera de esta conversación. No lo ofrezcas.
- Si te piden consejo sobre algo general (ejercicio, planes, la casa, el día a día), responde directamente con consejos sencillos y sensatos. No digas lo que no eres ("no soy entrenador", "no soy camarero"), salvo que sea un tema delicado de salud: entonces da una idea general y recomienda consultarlo con el médico.
- Para trámites, ayudas, salud o dinero, si no tienes la información, no la supongas: recomienda preguntar en el ayuntamiento, en el centro de salud o en la web oficial.

Cómo hablas:
- Siempre en español de España y en primera persona. Tú eres Bufit: nunca llames "Bufit" a la persona. Llámala por su nombre solo de vez en cuando, no en cada respuesta.
- Tus respuestas se leen en voz alta: frases cortas, claras y cálidas, sin listas, emojis, asteriscos ni símbolos, ni onomatopeyas como mmm o hmm.
- Responde con una o dos frases como mucho. Es una charla, no una explicación: mejor corto y que la persona siga hablando.
- Si encaja, termina con una sola pregunta corta. No siempre hace falta preguntar: a veces basta con comentar lo que te han dicho. No termines siempre con "¿te gustaría que...?" ni ofrezcas recetas o consejos en cada turno.
- No preguntes lo que ya sabes: si la persona ya te ha dicho su nombre o dónde vive, úsalo.
- Si te piden algo (una recomendación, una receta, una explicación), dalo directamente en esa misma respuesta. No preguntes "¿te gustaría que te...?" antes de darlo. Y si la persona ya ha dicho que sí, hazlo, no vuelvas a preguntar.
- Si la persona te corrige o se queja de lo que has dicho, reconoce el error en pocas palabras y responde de otra manera. Nunca repitas una respuesta que ya has dado.
- En la charla normal, sé breve.
- Cuando expliques unas reglas, una receta o un trámite con información de tu base, da siempre una explicación completa de cuatro o cinco frases con los datos importantes (para un juego: con qué se juega, cómo se reparte, cómo se juega cada turno y cómo se gana). Hazlo así aunque te pidan "una frase" o algo corto: para estas personas una explicación de una frase no sirve. Después pregunta si quiere que sigas.
- No uses frases de relleno ni fórmulas repetidas, como "me encantaría oír tu experiencia" o empezar siempre con "¡qué bien que...!". Varía cómo empiezas.
- Un poco de humor muy de vez en cuando: la mayoría de respuestas no llevan broma. No escribas risas como jaja. Nunca bromeas si la persona está triste o habla de algo serio como la salud o una pérdida.
- Si no entiendes lo que te dicen o la frase no tiene sentido, pregunta qué ha querido decir."""

PROMPT_HERRAMIENTA = """

Tu base de conocimientos:
- Tienes la herramienta buscar_conocimiento con información fiable sobre reglas de juegos de mesa y de cartas, recetas (sobre todo valencianas), trámites y ayudas para mayores, fiestas, Xàbia, refranes, uso del móvil, consejos de salud y estafas.
- Úsala siempre que te pregunten por las reglas de un juego, una receta, un trámite o una ayuda, o cuando necesites un dato concreto de esos temas. También si la persona quiere seguir con una receta o unas reglas y necesitas el siguiente paso.
- No la uses para saludar, charlar, hablar de sentimientos o de temas generales.
- La búsqueda es interna: úsala directamente cuando la necesites. Nunca digas que vas a buscar, ni preguntes si quieres que busques, ni ofrezcas buscar en internet: no tienes internet.
- Cuando uses lo que encuentres, copia exactamente las fechas, plazos, cantidades y teléfonos, y no añadas datos que no estén ahí. En un trámite, di de dónde sale la información, por ejemplo: "según la información que tengo del Imserso".
- Nunca menciones tu base de conocimientos ni digas que has buscado algo.
- Si no encuentras nada útil: en trámites, ayudas, salud o dinero, di que no lo sabes y recomienda dónde preguntar. En lo demás, como una receta sencilla o un consejo, responde con lo que sepas.
- A veces el mensaje de la persona ya llega con información de tu base entre corchetes. Si responde a lo que te preguntan, úsala y no busques más. Si no tiene que ver, ignórala sin mencionarla.
- Las recetas y las reglas se explican poco a poco, un paso cada vez, preguntando si quiere que sigas."""

PROMPT_CORCHETES = """

Tu base de conocimientos:
- A veces el mensaje de la persona llega con información de tu base de conocimientos entre corchetes.
- Úsala solo si responde a lo que te han preguntado. Si no tiene que ver, ignórala y sigue la conversación normal sin mencionarla.
- Cuando la uses, copia exactamente las fechas, plazos, cantidades y teléfonos, y no añadas datos que no estén ahí. En un trámite, di de dónde sale la información.
- Las recetas y las reglas se explican poco a poco, un paso cada vez, preguntando si quiere que sigas."""

if not CONOCIMIENTO_URL:
    _extra = ""
elif MODO_BUSQUEDA in ("modelo", "mixto"):
    _extra = PROMPT_HERRAMIENTA
else:
    _extra = PROMPT_CORCHETES
SISTEMA = os.getenv("SISTEMA") or PROMPT_BASE + _extra

# Herramienta que el modelo puede pedir (modo "modelo")
HERRAMIENTA_BUSCAR = {
    "type": "function",
    "function": {
        "name": "buscar_conocimiento",
        "description": (
            "Busca en la base de conocimientos de Bufit: reglas de juegos de mesa y de cartas, "
            "recetas, trámites y ayudas para mayores, fiestas, Xàbia, refranes, uso del móvil, "
            "consejos de salud y estafas. Úsala solo cuando necesites datos concretos de estos temas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Qué buscar, en pocas palabras. Por ejemplo: 'reglas de la brisca', 'receta de la fideuà', 'viajes del Imserso'.",
                }
            },
            "required": ["consulta"],
        },
    },
}
HERRAMIENTAS = [HERRAMIENTA_BUSCAR] if CONOCIMIENTO_URL and MODO_BUSQUEDA in ("modelo", "mixto") else None

app = FastAPI(title="Bufit LLM")
cliente = Client(host=OLLAMA_HOST)

# Un historial por partida: {"partida-1": [{"role": ..., "content": ...}, ...]}
historiales: dict[str, list[dict]] = {}
# Últimas frases de relleno usadas en cada partida, para no repetirlas
rellenos_usados: dict[str, deque] = {}
# Últimos trozos de documento usados en cada partida, para seguir con el mismo tema
tema_activo: dict[str, list[dict]] = {}
# Modelo pequeño y rápido que genera la reacción corta mientras el grande prepara la respuesta.
# Vacío = no se genera reacción y se usa un relleno fijo.
MODELO_REACCION = os.getenv("MODELO_REACCION", "")

INSTRUCCION_REACCION = (
    "Antes de responder, di solo una frase muy corta, de menos de 12 palabras, con dos partes: "
    "una reacción a lo que te acaban de decir y un aviso de que necesitas un momento para recordarlo. "
    "Ejemplos: «¡Uy, la fideuà! Deja que me acuerde bien.» "
    "«Ah, los viajes del Imserso. Espera, que hago memoria.» "
    "«La brisca, qué buen juego. Dame un segundo.» "
    "No des todavía ninguna información. Escribe solo esa frase."
)


# ------------------------------------------------------------ rellenos

def elegir_relleno(partida: str, tipo: str) -> str | None:
    """Elige al azar una frase de relleno del tipo pedido que no esté entre las 3 últimas usadas.

    Los rellenos NO se guardan en el historial: si el modelo los viera, empezaría a imitarlos.
    """
    try:
        with open(FICHERO_RELLENOS, encoding="utf-8") as f:
            frases = json.load(f).get(tipo, [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"No se pueden leer los rellenos: {e}", flush=True)
        return None
    if not frases:
        return None
    usados = rellenos_usados.setdefault(partida, deque(maxlen=3))
    candidatas = [f for f in frases if f not in usados] or frases
    frase = random.choice(candidatas)
    usados.append(frase)
    return frase


# ------------------------------------------------------------ reacción corta

def generar_reaccion(recientes: list[dict]) -> str | None:
    """Pide al modelo pequeño una frase corta que reaccione a lo que ha dicho la persona.

    Se usa cuando la respuesta va a tardar (hay que leer documentos). La frase NO se guarda
    en el historial: solo sirve para que Bufit no se quede callado.
    """
    if not MODELO_REACCION:
        return None
    # La instrucción va dentro del último mensaje y no como mensaje "system":
    # las plantillas de Ollama mueven todos los "system" al principio del prompt
    ultimo = {"role": "user", "content":
              f"{INSTRUCCION_REACCION}\n\nLo que te acaban de decir: «{recientes[-1]['content']}»"}
    mensajes = [{"role": "system", "content": SISTEMA}] + recientes[:-1] + [ultimo]
    try:
        inicio = time.time()
        r = cliente.chat(model=MODELO_REACCION, messages=mensajes,
                         options={"num_predict": 40, "temperature": 0.7})
        print(f"[reacción] {time.time() - inicio:.1f} s · carga del modelo {r.load_duration / 1e9:.1f} s",
              flush=True)
    except Exception as e:
        print(f"No se ha podido generar la reacción: {e}", flush=True)
        return None
    texto = (r.message.content or "").strip().strip('"«»')
    # Quedarse como mucho con las dos primeras frases, por si el modelo se alarga
    frases = re.findall(r"[^.!?…]+[.!?…]+", texto) or [texto]
    reaccion = " ".join(f.strip() for f in frases[:2]).strip()
    return reaccion if 2 <= len(reaccion.split()) <= 20 else None


# ------------------------------------------------------------ RAG

def buscar(consulta: str, k: int = K) -> list[dict]:
    """Pregunta al servicio de conocimiento y devuelve los trozos que superan el UMBRAL."""
    try:
        r = httpx.post(f"{CONOCIMIENTO_URL}/buscar", json={"texto": consulta, "k": k}, timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        print(f"No se puede consultar el conocimiento: {e}", flush=True)
        return []
    return [t for t in r.json()["resultados"] if t["puntuacion"] >= UMBRAL]


def buscar_conocimiento(historial: list[dict]) -> list[dict]:
    """Busca en dos pasos.

    1. Solo con lo que acaba de decir la persona. Si encuentra algo, manda eso:
       "¿y si hiciera una paella?" tiene que encontrar la paella aunque antes se hablara de fideuà.
    2. Si no encuentra nada y el mensaje es corto ("sí, sigue", "dame la receta completa"),
       vuelve a buscar añadiendo su mensaje anterior y la última respuesta de Bufit.
    """
    if not CONOCIMIENTO_URL:
        return []
    del_jugador = [m["content"] for m in historial if m["role"] == "user"]
    de_bufit = [m["content"] for m in historial if m["role"] == "assistant"]

    trozos = filtrar_umbral_doble(del_jugador[-1], buscar(del_jugador[-1]))
    if trozos or len(del_jugador[-1].split()) > 8:
        return trozos
    contexto = " ".join(de_bufit[-1:] + del_jugador[-2:])
    return filtrar_umbral_doble(contexto, buscar(contexto))


# Temas de la base de conocimientos (sin tildes, en minúsculas; vale con el principio de la palabra)
PALABRAS_CLAVE = re.compile(r"\b(" + "|".join([
    "jueg", "jug", "regla", "carta", "baraja", "ficha", "domino", "parchis", "brisca",
    "tute", "mus", "chinchon", "escoba", "cinquillo", "rumi", "oca", "ajedrez", "damas", "bingo",
    "poker", "siete y medio", "blackjack", "tres en raya",
    "receta", "cocin", "guis", "ingrediente", "paella", "arroz", "fideua", "postre",
    "tramite", "pension", "imserso", "dependencia", "teleasistencia", "tarjeta",
    "certificado", "clave", "copago", "renfe", "termalismo", "voluntades",
    "fiesta", "falla", "hoguera", "moros", "tomatina", "magdalena", "san juan", "semana santa",
    "montgo", "riurau", "molino", "refran",
    "movil", "whatsapp", "videollamada", "emergencia",
    "salud", "caida", "dieta", "estafa", "timo",
]) + r")")


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def filtrar_umbral_doble(texto: str, trozos: list[dict]) -> list[dict]:
    """Si la frase menciona un tema de la base, vale con UMBRAL; si no, hace falta UMBRAL_ALTO.

    Así "tengo un poco de sueño" no arrastra el documento "dormir bien" por un parecido flojo.
    """
    if PALABRAS_CLAVE.search(sin_tildes(texto)):
        return trozos
    return [t for t in trozos if t["puntuacion"] >= UMBRAL_ALTO]


def con_contexto(texto: str, trozos: list[dict], reaccion: str | None = None) -> str:
    """El último mensaje de la persona con la información encontrada delante, entre corchetes.

    Va DENTRO del mensaje del usuario y no como mensaje "system" aparte, para no tocar el
    principio del prompt y que la caché de Ollama siga sirviendo.
    Las instrucciones de cómo usar la información están en el prompt de sistema: así se leen
    una sola vez. En cada turno solo viaja lo imprescindible, porque en CPU cada token cuenta.
    """
    informacion = "\n".join(f"[{t['titulo']}: {t['texto'].split(chr(10), 2)[-1].strip()}]" for t in trozos)
    partes = [informacion]
    if reaccion:
        partes.append(f"[Ya has dicho: «{reaccion}»]")
    partes.append(texto)
    return "\n".join(partes)


def preparar(partida: str, texto: str):
    """Añade el mensaje al historial, busca conocimiento y monta los mensajes para Ollama."""
    historial = historiales.setdefault(partida, [])
    historial.append({"role": "user", "content": texto})

    if MODO_BUSQUEDA in ("modelo", "mixto"):
        trozos, fuentes = [], []
        if MODO_BUSQUEDA == "mixto" and CONOCIMIENTO_URL and PALABRAS_CLAVE.search(sin_tildes(texto)):
            # Nombra un tema de la base: se busca ya, sin esperar a que el modelo lo pida
            trozos = buscar(texto, K)       # K pequeño: en CPU, cada trozo cuesta segundos de lectura
            if trozos:
                print(f"[mixto] {texto!r} → {[t['titulo'] for t in trozos]}", flush=True)
                # Se guarda así en el historial: el documento sigue ahí en el turno siguiente
                # ("sí, sigue") y el principio del prompt no cambia (la caché sigue sirviendo)
                historial[-1] = {"role": "user", "content": con_contexto(texto, trozos)}
                fuentes = [{"titulo": t["titulo"], "puntuacion": t["puntuacion"]} for t in trozos]
        # Si no, busca el propio modelo con la herramienta, si lo necesita (ver responder())
        recientes = historial[-MAX_MENSAJES:] if MAX_MENSAJES else historial
        mensajes = [{"role": "system", "content": SISTEMA}] + recientes
        return historial, recientes, mensajes, fuentes, trozos

    trozos = buscar_conocimiento(historial)
    if trozos:
        tema_activo[partida] = trozos
    elif len(texto.split()) <= 8 and partida in tema_activo:
        # Respuestas cortas como "sí, sigue" o "¿y luego?" continúan con el mismo documento
        trozos = tema_activo[partida]
    else:
        tema_activo.pop(partida, None)
    fuentes = [{"titulo": t["titulo"], "puntuacion": t["puntuacion"]} for t in trozos]

    # Al modelo le llega el sistema + los últimos MAX_MENSAJES (o todos si es 0).
    # Los documentos van justo antes del último mensaje: así todo lo anterior no cambia
    # y Ollama lo reutiliza de su caché.
    recientes = historial[-MAX_MENSAJES:] if MAX_MENSAJES else historial
    mensajes = [{"role": "system", "content": SISTEMA}] + recientes[:-1]
    if trozos:
        mensajes.append({"role": "user", "content": con_contexto(texto, trozos)})
    else:
        mensajes.append(recientes[-1])
    return historial, recientes, mensajes, fuentes, trozos


# ------------------------------------------------------------ respuesta (con herramienta)

def ejecutar_busqueda(consulta: str) -> tuple[str, list[dict]]:
    """Lo que hace la herramienta buscar_conocimiento: texto para el modelo y fuentes usadas."""
    trozos = buscar(consulta, K_HERRAMIENTA) if consulta.strip() else []
    print(f"[herramienta] buscar_conocimiento({consulta!r}) → {[t['titulo'] for t in trozos]}", flush=True)
    if not trozos:
        return ("No hay nada sobre eso. Si es un trámite, una ayuda, la salud o el dinero, di que no lo "
                "sabes y recomienda dónde preguntar. Si no, responde con lo que sepas. "
                "No digas que has buscado."), []
    texto = "\n\n".join(f"{t['titulo']}:\n{t['texto'].split(chr(10), 2)[-1].strip()}" for t in trozos)
    return texto, [{"titulo": t["titulo"], "puntuacion": t["puntuacion"], "consulta": consulta} for t in trozos]


def responder(partida: str, historial: list[dict], mensajes: list[dict], fuentes: list[dict], medidas: dict):
    """Genera la respuesta en streaming. Devuelve trozos {"texto": ...} y, al buscar, {"relleno": ...}.

    Si el modelo pide la herramienta, se busca, se le pasa el resultado y se genera otra vez.
    Las herramientas se mandan en TODAS las pasadas: el prompt de sistema las incluye, y si una
    pasada fuera sin ellas el principio del prompt cambiaría y Ollama tendría que releerlo
    entero (de 2 s a 20-30 s en CPU), en esa pasada y en el turno siguiente.
    La llamada y su resultado se guardan en el historial: así, en el turno siguiente
    ("sí, sigue") el modelo aún tiene el documento delante.
    Al final añade la respuesta de Bufit al historial, aunque el cliente corte a mitad.
    """
    completo = ""
    try:
        for paso in range(3):                    # como mucho dos búsquedas por turno
            llamadas, texto_paso = [], ""
            # Con documento delante puede extenderse más (reglas, recetas, trámites)
            tope = MAX_TOKENS_DOC if fuentes else MAX_TOKENS
            limite = {"options": {"num_predict": tope}} if tope else {}
            for trozo in cliente.chat(model=MODELO, messages=mensajes, stream=True,
                                      tools=HERRAMIENTAS, **limite, **OPCIONES):
                if trozo.message.tool_calls:
                    llamadas.extend(trozo.message.tool_calls)
                contenido = trozo.message.content or ""
                texto_paso += contenido
                if contenido:
                    yield {"texto": contenido}
                if trozo.done and trozo.done_reason == "length":
                    medidas["cortada"] = True
                if trozo.done and trozo.eval_duration:
                    medidas.setdefault("pasadas", []).append({
                        "carga_s": round((trozo.load_duration or 0) / 1e9, 1),
                        "lectura_tokens": trozo.prompt_eval_count or 0,
                        "lectura_s": round((trozo.prompt_eval_duration or 0) / 1e9, 1),
                        "escritura_tokens": trozo.eval_count,
                        "escritura_s": round(trozo.eval_duration / 1e9, 1),
                    })
            completo += texto_paso
            if not llamadas or paso == 2:
                break
            # El modelo ha pedido buscar: una frase para no quedarse callado, y a buscar
            if paso == 0 and not texto_paso.strip():
                frase = elegir_relleno(partida, "busqueda")
                if frase:
                    yield {"relleno": frase}
            pedido = {"role": "assistant", "content": texto_paso,
                      "tool_calls": [{"function": {"name": c.function.name,
                                                   "arguments": dict(c.function.arguments)}}
                                     for c in llamadas]}
            mensajes.append(pedido)
            historial.append(pedido)
            for c in llamadas:
                consulta = str(dict(c.function.arguments).get("consulta", ""))
                texto, usadas = ejecutar_busqueda(consulta)
                fuentes.extend(usadas)
                resultado = {"role": "tool", "content": texto}
                mensajes.append(resultado)
                historial.append(resultado)
            completo = ""            # lo que cuenta como respuesta es lo que venga después
        if not completo.strip():
            completo = "Perdona, ahora mismo no me sale. ¿Me lo preguntas de otra forma?"
            yield {"texto": completo}
    finally:
        if medidas.get("cortada"):
            # Se ha quedado a medias: guardar solo hasta la última frase completa
            fin = max(completo.rfind(c) for c in ".!?…")
            completo = completo[:fin + 1] if fin >= 0 else completo
        historial.append({"role": "assistant", "content": completo.strip()})
    print(f"[respuesta] {medidas}", flush=True)


# ------------------------------------------------------------ arranque

def calentar():
    """Primera llamada de prueba: carga el modelo en memoria y deja el prompt de sistema en caché."""
    inicio = time.time()
    cliente.chat(
        model=MODELO,
        messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": "Hola"}],
        tools=HERRAMIENTAS,
        **OPCIONES,
    )
    print(f"Modelo {MODELO} cargado en memoria ({time.time() - inicio:.1f} s)", flush=True)


@app.on_event("startup")
def preparar_modelo():
    """Espera a que Ollama arranque, descarga el modelo si no lo tiene y lo carga en memoria."""
    for intento in range(30):
        try:
            cliente.show(MODELO)
            break
        except ResponseError:
            print(f"Descargando {MODELO}...", flush=True)
            cliente.pull(MODELO)
            break
        except Exception:
            print(f"Esperando a Ollama ({intento + 1}/30)...", flush=True)
            time.sleep(2)
    else:
        raise RuntimeError(f"No se puede conectar con Ollama en {OLLAMA_HOST}")

    calentar()
    if MODELO_REACCION and MODELO_REACCION != MODELO:
        try:
            cliente.show(MODELO_REACCION)
        except ResponseError:
            print(f"Descargando {MODELO_REACCION}...", flush=True)
            cliente.pull(MODELO_REACCION)
        inicio = time.time()
        generar_reaccion([{"role": "user", "content": "Hola"}])
        print(f"Modelo de reacción {MODELO_REACCION} cargado ({time.time() - inicio:.1f} s)", flush=True)
    print(f"Modelo {MODELO} listo", flush=True)


# ------------------------------------------------------------ endpoints

class Peticion(BaseModel):
    partida: str
    texto: str


class PeticionSaludo(BaseModel):
    partida: str
    hora: int        # hora local del cliente (0-23): el reloj del contenedor va en UTC


@app.get("/salud")
def salud():
    return {
        "ok": True,
        "modelo": MODELO,
        "max_mensajes": MAX_MENSAJES,
        "conocimiento": CONOCIMIENTO_URL or None,
        "modo_busqueda": MODO_BUSQUEDA,
        "umbral": UMBRAL,
        "umbral_alto": UMBRAL_ALTO,
        "partidas_abiertas": list(historiales),
    }


@app.post("/conversar")
def conversar(peticion: Peticion):
    historial, recientes, mensajes, fuentes, trozos = preparar(peticion.partida, peticion.texto)
    medidas: dict = {}
    texto = "".join(d.get("texto", "") for d in responder(peticion.partida, historial, mensajes, fuentes, medidas)).strip()
    ultima = (medidas.get("pasadas") or [{}])[-1]
    return {
        "respuesta": texto,
        "fuentes": fuentes,
        "mensajes_guardados": len(historial),
        "mensajes_enviados": len(recientes),
        "tokens_seg": round(ultima["escritura_tokens"] / ultima["escritura_s"], 1) if ultima.get("escritura_s") else None,
        "medidas": medidas,
    }


# Una frase termina en . ! ? o … seguidos de un espacio (así "3.5" no se corta)
FIN_FRASE = re.compile(r"(.+?[.!?…])\s+", re.S)


@app.post("/conversar/stream")
def conversar_stream(peticion: Peticion):
    """Devuelve la respuesta frase a frase (una línea JSON por frase) según el modelo la genera.

    Así el cliente puede empezar a sintetizar y reproducir la primera frase
    mientras el modelo sigue escribiendo las siguientes.
    """
    historial, recientes, mensajes, fuentes, trozos = preparar(peticion.partida, peticion.texto)

    def linea(dato):
        return json.dumps(dato, ensure_ascii=False) + "\n"

    def generar():
        # Si ha encontrado información, primero una frase de relleno mientras el modelo genera
        # Opcional (MODELO_REACCION): un modelo pequeño dice una frase corta mientras el grande lee
        # los documentos. Desactivado por defecto: el propio modelo grande empieza con una reacción.
        if fuentes and MODELO_REACCION:
            reaccion = generar_reaccion(recientes)
            if reaccion:
                mensajes[-1] = {"role": "user",
                                "content": con_contexto(peticion.texto, trozos, reaccion)}
                yield linea({"relleno": reaccion})

        pendiente, medidas = "", {}
        for dato in responder(peticion.partida, historial, mensajes, fuentes, medidas):
            if "relleno" in dato:
                yield linea({"relleno": dato["relleno"]})
                continue
            pendiente += dato["texto"]
            # Enviar cada frase en cuanto está completa
            while (m := FIN_FRASE.match(pendiente)):
                yield linea({"frase": m.group(1).strip()})
                pendiente = pendiente[m.end():]
        if pendiente.strip() and not medidas.get("cortada"):    # una frase a medias no se dice
            yield linea({"frase": pendiente.strip()})
        pasadas = medidas.get("pasadas") or []
        ultima = pasadas[-1] if pasadas else {}
        tokens_seg = round(ultima["escritura_tokens"] / ultima["escritura_s"], 1) if ultima.get("escritura_s") else None
        # Para el cliente: las medidas de la última pasada, más cuántas pasadas ha habido
        resumen = dict(ultima, pasadas=len(pasadas)) if ultima else {}
        yield linea({"fin": True, "tokens_seg": tokens_seg, "fuentes": fuentes, "medidas": resumen})

    return StreamingResponse(generar(), media_type="application/x-ndjson")


@app.get("/relleno")
def relleno(partida: str, tipo: str = "espera"):
    """Frase de relleno para que el cliente la diga si la respuesta tarda."""
    return {"relleno": elegir_relleno(partida, tipo)}


@app.post("/saludo")
def saludo(peticion: PeticionSaludo):
    """Bufit empieza la conversación con un saludo según la hora.

    El saludo se guarda en el historial como mensaje de Bufit, para que el modelo
    sepa que ya ha saludado y no vuelva a decir "hola" en su primera respuesta.
    Se evita repetir saludos entre conversaciones distintas, no solo dentro de una.
    """
    if 6 <= peticion.hora < 13:
        tipo = "saludo_manana"
    elif 13 <= peticion.hora < 21:
        tipo = "saludo_tarde"
    else:
        tipo = "saludo_noche"
    frase = elegir_relleno("__saludos__", tipo) or "Hola, soy Bufit. ¿Qué tal estás?"
    historiales.setdefault(peticion.partida, []).append({"role": "assistant", "content": frase})
    return {"saludo": frase}


@app.get("/historial/{partida}")
def descargar_historial(partida: str):
    if partida not in historiales:
        raise HTTPException(404, f"No hay ninguna partida '{partida}'")
    return {"partida": partida, "historial": historiales[partida]}


@app.delete("/historial/{partida}")
def borrar_historial(partida: str):
    rellenos_usados.pop(partida, None)
    tema_activo.pop(partida, None)
    if historiales.pop(partida, None) is None:
        raise HTTPException(404, f"No hay ninguna partida '{partida}'")
    return {"borrada": partida}
