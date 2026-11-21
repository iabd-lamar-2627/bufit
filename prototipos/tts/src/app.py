"""TTS · recibe un texto y devuelve el audio en WAV."""
import io
import os
import re
import time
import urllib.request
import wave

from fastapi import FastAPI
from fastapi.responses import Response
from piper import PiperVoice
from pydantic import BaseModel

VOZ = os.getenv("VOZ", "es_ES-davefx-medium")
DIR_VOCES = os.getenv("DIR_VOCES", "/modelos")
URL_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def descargar_voz(voz: str) -> str:
    """Descarga el .onnx y su .json si no están ya en DIR_VOCES."""
    idioma, nombre, calidad = voz.split("-")          # es_ES, davefx, medium
    carpeta = f"{idioma.split('_')[0]}/{idioma}/{nombre}/{calidad}"
    os.makedirs(DIR_VOCES, exist_ok=True)
    for ext in (".onnx", ".onnx.json"):
        destino = os.path.join(DIR_VOCES, voz + ext)
        if not os.path.exists(destino):
            print(f"Descargando {voz}{ext}...", flush=True)
            urllib.request.urlretrieve(f"{URL_BASE}/{carpeta}/{voz}{ext}", destino)
    return os.path.join(DIR_VOCES, voz + ".onnx")


app = FastAPI(title="Bufit TTS")

# Se carga una sola vez al arrancar
voz = PiperVoice.load(descargar_voz(VOZ))


class Peticion(BaseModel):
    texto: str


@app.get("/salud")
def salud():
    return {"ok": True, "voz": VOZ}


def limpiar(texto: str) -> str:
    """Quita lo que la voz leería mal: onomatopeyas que deletrea (mmm, hmm), risas escritas,
    asteriscos y emojis."""
    texto = re.sub(r"\b[mMhH]m+\b[.,…]*", "", texto)          # mmm, hmm → se deletrean "eme eme"
    texto = re.sub(r"\b(?:[jJ]a){2,}\b|\b(?:[hH]a){2,}\b", "", texto)   # jaja, haha
    texto = re.sub(r"[*_#~`]", "", texto)
    texto = "".join(c for c in texto if ord(c) < 0x2600)      # emojis y símbolos
    texto = re.sub(r"[¡¿]\s*[!?]", "", texto)                 # "¡!" que queda al quitar una risa
    return re.sub(r"\s{2,}", " ", texto).strip()


@app.post("/sintetizar")
def sintetizar(peticion: Peticion):
    inicio = time.time()
    texto = limpiar(peticion.texto) or "..."
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        voz.synthesize_wav(texto, wav)
    segundos = round(time.time() - inicio, 2)

    return Response(
        content=buffer.getvalue(),
        media_type="audio/wav",
        headers={"X-Segundos-Proceso": str(segundos)},
    )
