"""LLM · conversación con Ollama. Guarda un historial por partida.

- POST   /conversar             manda un mensaje y recibe la respuesta completa
- POST   /conversar/stream      igual, pero devuelve la respuesta frase a frase según se genera
- POST   /saludo                Bufit empieza la conversación (saludo según la hora)
- GET    /relleno               una frase de relleno ("espera" o "busqueda") que no se repita
- GET    /historial/{partida}   descarga el historial completo
- DELETE /historial/{partida}   borra el historial (al cerrar la partida)

En cada turno pregunta al servicio de conocimiento (RAG). Si encuentra trozos de
documentos parecidos a la pregunta, los añade al prompt para que el modelo responda
con esa información en lugar de inventársela.

El historial vive en memoria: si el contenedor se reinicia, se pierde.
Descargarlo antes de cerrar la partida es cosa del orquestador.
"""
import json
import os
import random
import re
import time
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
UMBRAL = float(os.getenv("UMBRAL", "0.5"))     # parecido mínimo (0 a 1) para usar un trozo
K = int(os.getenv("K", "1"))                   # cuántos trozos pedir como máximo

# Frases de relleno (se releen en cada uso: se pueden editar sin reiniciar)
FICHERO_RELLENOS = os.getenv("FICHERO_RELLENOS", "/app/rellenos.json")

SISTEMA = os.getenv(
    "SISTEMA",
    """Te llamas Bufit. Si te preguntan tu nombre, di que te llamas Bufit.

Eres un compañero de conversación para personas mayores. Te gusta charlar de cualquier tema cotidiano: la familia, el tiempo, la comida, los recuerdos, las aficiones o lo que pasa en el pueblo.

También sabes jugar al dominó, pero solo hablas del dominó si la persona saca el tema o pide jugar. No lo propongas en cada respuesta.

Cómo hablas:
- Responde siempre en español de España, nunca en otro idioma.
- Habla como un vecino amable: frases cortas, claras y cálidas.
- Tienes un poco de sentido del humor: muy de vez en cuando haces una broma suave o un comentario simpático. La mayoría de tus respuestas no llevan ninguna broma. No escribas risas como jaja o haha. Nunca te burlas de la persona, y si está triste o habla de algo serio como la salud o una pérdida, no bromeas.
- Contesta en una o dos frases y, si encaja, haz una pregunta para seguir la conversación.
- No inventes datos sobre la persona ni sobre su familia: usa solo lo que te haya contado.
- No sabes qué tiempo hace, qué día es ni qué pasa fuera de esta conversación. No lo inventes: si hace falta, pregúntalo.
- No sabes nada de la vida de la persona salvo lo que te cuente en esta conversación: ni sus planes, ni sus visitas, ni su familia. Si te pregunta algo así, di que no lo sabes y pregúntale.
- No tienes una vida propia fuera de esta conversación: no cuentes cosas que hayas hecho, comido o visto.
- Si no sabes algo, dilo con sencillez. No te lo inventes.
- Si te preguntan por un trámite, una ayuda, la salud o el dinero y no tienes información sobre ello, dilo y recomienda preguntar en el ayuntamiento, en el centro de salud o en la web oficial.
- Tus respuestas se leen en voz alta: no uses listas, emojis, asteriscos ni símbolos, ni onomatopeyas como mmm o hmm.
- Solo puedes hablar: no puedes enseñar fotos, poner música, llamar a nadie ni hacer nada fuera de esta conversación. No lo ofrezcas.

A veces el mensaje de la persona llega con información de tu base de conocimientos entre corchetes. Cuando pase:
- Si la pregunta trata de eso, responde con esa información y no añadas datos que no estén ahí.
- Copia exactamente las fechas, plazos, cantidades y teléfonos.
- Si lo que te preguntan no está en esa información, di que no lo sabes.
- Si es un trámite, di de dónde sale la información, por ejemplo: "según la información que tengo del Imserso".
- Si es una receta o unas reglas, explícalas poco a poco, un paso cada vez, y pregunta si quiere que sigas.
- Empieza con una frase muy corta y natural que reaccione a lo que te han dicho, y después da la información. Varía esa frase: no repitas la misma reacción de un turno a otro.
- Si no entiendes bien lo que te dicen, o la frase no tiene sentido, pregunta qué ha querido decir en lugar de suponerlo.""",
)

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

def buscar(consulta: str) -> list[dict]:
    """Pregunta al servicio de conocimiento y devuelve los trozos que superan el UMBRAL."""
    try:
        r = httpx.post(f"{CONOCIMIENTO_URL}/buscar", json={"texto": consulta, "k": K}, timeout=10)
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

    trozos = buscar(del_jugador[-1])
    if trozos or len(del_jugador[-1].split()) > 8:
        return trozos
    return buscar(" ".join(de_bufit[-1:] + del_jugador[-2:]))


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


# ------------------------------------------------------------ arranque

def calentar():
    """Primera llamada de prueba: carga el modelo en memoria y deja el prompt de sistema en caché."""
    inicio = time.time()
    cliente.chat(
        model=MODELO,
        messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": "Hola"}],
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
        "umbral": UMBRAL,
        "partidas_abiertas": list(historiales),
    }


@app.post("/conversar")
def conversar(peticion: Peticion):
    historial, recientes, mensajes, fuentes, trozos = preparar(peticion.partida, peticion.texto)

    respuesta = cliente.chat(model=MODELO, messages=mensajes, **OPCIONES)
    texto = respuesta["message"]["content"]
    historial.append({"role": "assistant", "content": texto})

    segundos = respuesta["eval_duration"] / 1_000_000_000
    return {
        "respuesta": texto,
        "fuentes": fuentes,
        "mensajes_guardados": len(historial),
        "mensajes_enviados": len(recientes),
        "tokens_seg": round(respuesta["eval_count"] / segundos, 1) if segundos else None,
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

        completo, pendiente, tokens_seg, medidas = "", "", None, {}
        try:
            for trozo in cliente.chat(model=MODELO, messages=mensajes, stream=True, **OPCIONES):
                contenido = trozo.message.content or ""
                completo += contenido
                pendiente += contenido
                # Enviar cada frase en cuanto está completa
                while (m := FIN_FRASE.match(pendiente)):
                    yield linea({"frase": m.group(1).strip()})
                    pendiente = pendiente[m.end():]
                if trozo.done and trozo.eval_duration:
                    tokens_seg = round(trozo.eval_count / (trozo.eval_duration / 1_000_000_000), 1)
                    # Dónde se va el tiempo: cargar el modelo, leer el prompt o escribir la respuesta
                    medidas = {
                        "carga_s": round((trozo.load_duration or 0) / 1e9, 1),
                        "lectura_tokens": trozo.prompt_eval_count or 0,
                        "lectura_s": round((trozo.prompt_eval_duration or 0) / 1e9, 1),
                        "escritura_tokens": trozo.eval_count,
                        "escritura_s": round(trozo.eval_duration / 1e9, 1),
                    }
                    print(f"[respuesta] {medidas}", flush=True)
            if pendiente.strip():
                yield linea({"frase": pendiente.strip()})
        finally:
            # La respuesta completa se guarda aunque el cliente corte a mitad
            historial.append({"role": "assistant", "content": completo.strip()})
        yield linea({"fin": True, "tokens_seg": tokens_seg, "fuentes": fuentes, "medidas": medidas})

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
