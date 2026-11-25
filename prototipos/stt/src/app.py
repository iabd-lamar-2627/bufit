"""STT · recibe un fichero de audio y devuelve el texto."""
import os
import tempfile
import time

from fastapi import FastAPI, File, UploadFile
from faster_whisper import WhisperModel

MODELO = os.getenv("MODELO_WHISPER", "base")   # tiny, base, small...
IDIOMA = os.getenv("IDIOMA", "es")

# Vocabulario del dominio: ayuda a Whisper con nombres propios y jerga del juego
PROMPT = os.getenv(
    "PROMPT_WHISPER",
    "Bufit, dominó, ficha, fichas, doble, pasar, robar, partida, jugamos, tablero.",
)

# Frases que Whisper "se inventa" con silencio o ruido: aprendió de subtítulos de vídeos de internet
ALUCINACIONES = (
    "suscribete", "suscribanse", "subtitulos", "amara.org", "gracias por ver",
    "no olvides suscribirte", "dale like", "musica",
)


def es_alucinacion(texto: str) -> bool:
    import unicodedata
    limpio = unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()
    limpio = "".join(c for c in limpio if c.isalnum() or c in " .")
    return any(frase in limpio for frase in ALUCINACIONES) and len(limpio.split()) <= 8


app = FastAPI(title="Bufit STT")

# Se carga una sola vez al arrancar. En CPU, int8 es lo más rápido.
# HILOS: núcleos que usa Whisper (0 = todos los del contenedor). STT y LLM no trabajan a la vez,
# así que mientras transcribe puede usar todos.
HILOS = int(os.getenv("HILOS", "0")) or os.cpu_count() or 4
# HAZ (beam size): cuántas transcripciones posibles compara. 1 = la más rápida (unas dos veces
# más que 5, el valor por defecto de Whisper), a cambio de fallar algo más en palabras raras.
HAZ = int(os.getenv("HAZ", "1"))
# VAD_UMBRAL: seguridad (0 a 1) que pide el detector de voz para quedarse un trozo de audio.
# El de Whisper es 0.5; más bajo deja pasar la voz flojita o lejana, a cambio de colar algo más de ruido.
VAD_UMBRAL = float(os.getenv("VAD_UMBRAL", "0.35"))
modelo = WhisperModel(MODELO, device="cpu", compute_type="int8", cpu_threads=HILOS)


@app.get("/salud")
def salud():
    return {"ok": True, "modelo": MODELO, "hilos": HILOS, "haz": HAZ, "vad_umbral": VAD_UMBRAL}


@app.post("/transcribir")
async def transcribir(audio: UploadFile = File(...)):
    # Guardamos el audio en un fichero temporal para que Whisper lo lea
    sufijo = os.path.splitext(audio.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=sufijo) as tmp:
        tmp.write(await audio.read())
        tmp.flush()

        inicio = time.time()
        segmentos, info = modelo.transcribe(
            tmp.name,
            language=IDIOMA,
            initial_prompt=PROMPT,
            beam_size=HAZ,
            without_timestamps=True,            # no necesitamos marcas de tiempo: ahorra trabajo
            vad_filter=True,                    # descarta los trozos sin voz antes de transcribir
            vad_parameters={"onset": VAD_UMBRAL, "offset": max(VAD_UMBRAL - 0.15, 0.01)},  # en faster-whisper 1.1 "threshold" pasó a llamarse "onset"
            condition_on_previous_text=False,   # evita que una alucinación arrastre a la siguiente
        )
        # Descarta los segmentos que el propio Whisper considera probablemente sin voz
        segmentos = list(segmentos)
        validos = [s for s in segmentos if not (s.no_speech_prob > 0.6 and s.avg_logprob < -1.0)]
        # Cuando no sale nada, dejar dicho por qué (para ajustar VAD_UMBRAL o el filtro)
        if not segmentos:
            print(f"Sin texto: el detector de voz no encontró voz en {info.duration:.1f} s de audio", flush=True)
        elif not validos:
            print("Sin texto: Whisper cree que no es voz → "
                  + "; ".join(f"{s.text.strip()!r} (sin voz {s.no_speech_prob:.2f}, confianza {s.avg_logprob:.2f})"
                              for s in segmentos), flush=True)
        texto = " ".join(s.text.strip() for s in validos)
        if es_alucinacion(texto):
            print(f"Descartada alucinación: {texto!r}", flush=True)
            texto = ""
        segundos = round(time.time() - inicio, 2)

    return {
        "texto": texto,
        "idioma": info.language,
        "duracion_audio": round(info.duration, 2),
        "segundos_proceso": segundos,
    }
