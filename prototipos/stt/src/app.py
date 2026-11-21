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
modelo = WhisperModel(MODELO, device="cpu", compute_type="int8")


@app.get("/salud")
def salud():
    return {"ok": True, "modelo": MODELO}


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
            vad_filter=True,                    # descarta los trozos sin voz antes de transcribir
            condition_on_previous_text=False,   # evita que una alucinación arrastre a la siguiente
        )
        # Descarta los segmentos que el propio Whisper considera probablemente sin voz
        validos = [s for s in segmentos if not (s.no_speech_prob > 0.6 and s.avg_logprob < -1.0)]
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
