"""Cliente de conversación por voz con Bufit.

micrófono → STT → LLM → TTS → altavoz, en bucle.

Corre en el ordenador (fuera de Docker), porque es quien tiene el micrófono y el altavoz.
Necesita los servicios arrancados: docker compose up -d

Además publica el estado de los ojos en MQTT (bufit/pantalla/set) para que
la página ojos/index.html se mueva con la conversación. Si el broker no está,
la conversación funciona igual, sin ojos.

Para terminar, di "adiós" o pulsa Ctrl+C (dos veces para forzar).
El historial se guarda en datos/partidas/.
"""
import io
import json
import os
import queue
import signal
import threading
import sys
import time
import traceback
import wave
from collections import deque
from datetime import datetime

import numpy as np
import requests
import sounddevice as sd

STT = "http://localhost:8010"
LLM = "http://localhost:8011"
TTS = "http://localhost:8012"

FRECUENCIA = 16000       # Whisper trabaja a 16 kHz
BLOQUE = 0.03            # el micrófono entrega trozos de 30 ms
PREVIO = 0.3             # segundos que se guardan de antes de empezar a hablar
SILENCIO_FIN = 1.0       # segundos de silencio que cierran la frase
MIN_VOZ = 0.5            # por debajo de esto se descarta (ruidos, golpes)
MAX_GRABACION = 15       # segundos como máximo por frase
UMBRAL_MIN = 150         # umbral mínimo de inicio, aunque el ruido sea muy bajo
PALABRAS_SALIR = ("adiós", "adios", "hasta luego", "salir")
ESPERA_RELLENO = 5.0     # segundos sin respuesta antes de decir una frase de relleno
ESPERA_SIGUIENTE = 7.0   # si sigue sin llegar nada, otra frase de espera cada tantos segundos
MAX_RELLENOS = 3         # como mucho, frases de espera por turno
BROKER = "localhost"     # broker MQTT (servicio mqtt del compose)
TEMA_PANTALLA = "bufit/pantalla/set"
DORMIR_TRAS = 60         # segundos sin que nadie hable para que Bufit se duerma

# ------------------------------------------------------------ ojos (MQTT)

try:
    import paho.mqtt.client as paho
    cliente_mqtt = paho.Client(paho.CallbackAPIVersion.VERSION2)
    # Última voluntad: si este programa se cierra o se cuelga, el broker pone los ojos a dormir
    cliente_mqtt.will_set(TEMA_PANTALLA, json.dumps({"ojos": "dormido"}), retain=True)
    cliente_mqtt.connect_async(BROKER, 1883)
    cliente_mqtt.loop_start()             # se conecta (y reconecta) en segundo plano
except ImportError:
    cliente_mqtt = None
    print("[sin ojos: falta paho-mqtt → pip install -r requirements-cliente.txt]")

estado_ojos = None
ultima_voz = 0.0


def voz_ojos(volumen, inicio, fin):
    """Manda a los ojos el nivel de tu voz (0 a 1), como mucho unas 8 veces por segundo."""
    global ultima_voz
    if cliente_mqtt is None or time.time() - ultima_voz < 0.12:
        return
    ultima_voz = time.time()
    nivel = min(1.0, max(0.0, (volumen - fin) / (inicio * 4)))
    cliente_mqtt.publish(TEMA_PANTALLA, json.dumps({"voz": round(nivel, 2)}))


def ojos(estado):
    """Cambia la expresión de los ojos. Si no hay broker, no pasa nada."""
    global estado_ojos
    if estado == estado_ojos or cliente_mqtt is None:
        return
    estado_ojos = estado
    # retain: el broker guarda el último estado y se lo da a la página aunque se abra más tarde
    cliente_mqtt.publish(TEMA_PANTALLA, json.dumps({"ojos": estado}), retain=True)

# ------------------------------------------------------------ Ctrl+C

salir = False


class Interrumpido(Exception):
    pass


def al_pulsar_ctrl_c(senal, marco):
    """Primera vez: salir limpiamente. Segunda: salir a la fuerza."""
    global salir
    if salir:
        print("\nSalida forzada", flush=True)
        os._exit(1)
    salir = True
    print("\n[saliendo... pulsa Ctrl+C otra vez para forzar]", flush=True)


# ------------------------------------------------------------ micrófono
#
# El micrófono se abre una sola vez. La librería de audio va dejando los
# trozos en una cola y el programa los recoge cuando le hacen falta.
# Así nunca se queda bloqueado esperando al micrófono.

cola = queue.Queue()


def al_recibir_audio(datos, muestras, tiempo, estado):
    cola.put(datos.copy())


def siguiente_bloque():
    """Devuelve el siguiente trozo de audio, comprobando Ctrl+C cada 0,1 s."""
    while True:
        if salir:
            raise Interrumpido
        try:
            return cola.get(timeout=0.1)
        except queue.Empty:
            pass


def vaciar_cola():
    """Descarta lo que se ha oído mientras Bufit hablaba o pensaba."""
    while not cola.empty():
        cola.get_nowait()


def nivel(bloque):
    """Volumen medio (RMS) de un trozo de audio."""
    return float(np.sqrt(np.mean(bloque.astype(np.float32) ** 2)))


def umbrales(ruido):
    """Umbral para empezar a grabar y umbral para dar la frase por terminada."""
    inicio = max(ruido * 2.5, UMBRAL_MIN)
    fin = max(ruido * 1.6, UMBRAL_MIN * 0.6)
    return inicio, fin


def calibrar():
    """Primera medida del ruido de fondo. Luego se va actualizando sola."""
    print("Calibrando el ruido de fondo: 1 segundo en silencio...")
    vaciar_cola()
    niveles = [nivel(siguiente_bloque()) for _ in range(int(1 / BLOQUE))]
    ruido = float(np.mean(niveles))
    print(f"Ruido inicial {ruido:.0f}")
    return ruido


def grabar(ruido):
    """Espera a que empieces a hablar y graba hasta que te callas.

    Mientras espera, sigue midiendo el ruido de fondo: si los ventiladores
    se aceleran (por ejemplo, mientras el modelo piensa), los umbrales suben solos.
    Devuelve el audio y la última medida del ruido.
    """
    vaciar_cola()
    previos = deque(maxlen=int(PREVIO / BLOQUE))   # para no cortar la primera sílaba
    bloques = []
    silencio = 0.0
    inicio, fin = umbrales(ruido)
    ojos("espera")
    esperando_desde = time.time()

    while True:
        bloque = siguiente_bloque()
        volumen = nivel(bloque)

        if not bloques:                           # todavía no has empezado a hablar
            if volumen < inicio:                  # es ruido de fondo: actualizar la medida
                ruido = 0.95 * ruido + 0.05 * volumen
                inicio, fin = umbrales(ruido)
            print(f"\r  nivel {volumen:6.0f}  ·  ruido {ruido:5.0f}  ·  inicio {inicio:5.0f}  ·  fin {fin:5.0f}  ",
                  end="", flush=True)
            previos.append(bloque)
            if volumen > inicio:
                bloques = list(previos)
                print("\n[te oigo]")
                ojos("escuchando")
            elif time.time() - esperando_desde > DORMIR_TRAS:
                ojos("dormido")
            continue

        print(f"\r  nivel {volumen:6.0f}  ·  ruido {ruido:5.0f}  ·  inicio {inicio:5.0f}  ·  fin {fin:5.0f}  ",
              end="", flush=True)
        bloques.append(bloque)
        voz_ojos(volumen, inicio, fin)
        silencio = silencio + BLOQUE if volumen < fin else 0.0
        duracion = len(bloques) * BLOQUE

        if silencio >= SILENCIO_FIN or duracion >= MAX_GRABACION:
            voz = duracion - silencio
            if voz < MIN_VOZ:
                print(f"\n[descartado: solo {voz:.1f} s de sonido]")
                bloques, silencio = [], 0.0
                previos.clear()
                ojos("espera")
                esperando_desde = time.time()
                continue
            motivo = "silencio" if silencio >= SILENCIO_FIN else "máximo de 15 s"
            print(f"\n[grabado {duracion:.1f} s · cortado por {motivo}]")
            return np.concatenate(bloques), ruido


# ------------------------------------------------------------ audio

def a_wav(audio):
    """Convierte las muestras grabadas en un fichero WAV en memoria."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)                       # 16 bits
        wav.setframerate(FRECUENCIA)
        wav.writeframes(audio.tobytes())
    return buffer.getvalue()


def reproducir(wav_bytes):
    """Reproduce el audio. Se corta en cuanto se pulsa Ctrl+C."""
    with wave.open(io.BytesIO(wav_bytes)) as wav:
        datos = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
        frecuencia = wav.getframerate()
    sd.play(datos, frecuencia)
    fin = time.time() + len(datos) / frecuencia
    while time.time() < fin:
        if salir:
            sd.stop()
            raise Interrumpido
        time.sleep(0.1)


# Las frases ya sintetizadas esperan en esta cola y un hilo las reproduce en orden.
# Así, mientras suena una frase, ya se está preparando la siguiente.
cola_voz = queue.Queue()


def reproductor():
    while True:
        wav = cola_voz.get()
        try:
            if not salir:
                reproducir(wav)
        except Interrumpido:
            pass
        except Exception as e:
            # Si un audio falla, se avisa y se sigue: si este hilo muriera,
            # el programa se quedaría esperando para siempre a que Bufit termine de hablar
            print(f"\n[error al reproducir: {e}]", flush=True)
        finally:
            cola_voz.task_done()


def esperar_a_que_termine_de_hablar():
    while cola_voz.unfinished_tasks:
        if salir:
            raise Interrumpido
        time.sleep(0.1)


# ------------------------------------------------------------ rellenos

class Turno:
    """Lo que dice Bufit en un turno, en el orden correcto.

    Si en ESPERA_RELLENO segundos no ha llegado nada del servicio, dice una frase de espera
    ("A ver..."). Si sigue sin llegar nada, cada ESPERA_SIGUIENTE segundos dice otra más larga
    ("Ya casi lo tengo..."), hasta MAX_RELLENOS en total contando la que manda el servicio al
    buscar. El cerrojo garantiza que un relleno nunca suene después de la respuesta de verdad.
    """

    def __init__(self, partida):
        self.partida = partida
        self.cerrojo = threading.Lock()
        self.respondido = False          # ya ha llegado una frase de verdad
        self.rellenos = 0
        self.temporizador = None
        self._programar(ESPERA_RELLENO)

    def _programar(self, segundos):
        if self.temporizador:
            self.temporizador.cancel()
        self.temporizador = threading.Timer(segundos, self._relleno_de_espera)
        self.temporizador.daemon = True
        self.temporizador.start()

    def _relleno_de_espera(self):
        with self.cerrojo:
            if self.respondido or salir or self.rellenos >= MAX_RELLENOS:
                return
            tipo = "espera" if self.rellenos == 0 else "espera_larga"
            try:
                r = requests.get(f"{LLM}/relleno",
                                 params={"partida": self.partida, "tipo": tipo}, timeout=5)
                frase = r.json().get("relleno")
                if frase:
                    cola_voz.put(sintetizar(frase))
                    self.rellenos += 1
                    print(f"({frase}) ", end="", flush=True)
            except requests.RequestException:
                pass
            self._programar(ESPERA_SIGUIENTE)

    def decir(self, frase, relleno=False):
        with self.cerrojo:
            if relleno:
                if self.respondido or self.rellenos >= MAX_RELLENOS:
                    return
                cola_voz.put(sintetizar(frase))
                self.rellenos += 1
                self._programar(ESPERA_SIGUIENTE)
            else:
                self.temporizador.cancel()
                cola_voz.put(sintetizar(frase))
                self.respondido = True
        print(f"({frase}) " if relleno else f"{frase} ", end="", flush=True)

    def terminar(self):
        self.temporizador.cancel()


# ------------------------------------------------------------ servicios

def transcribir(audio):
    r = requests.post(
        f"{STT}/transcribir",
        files={"audio": ("voz.wav", a_wav(audio), "audio/wav")},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["texto"].strip()


def conversar_por_frases(partida, texto, fuentes):
    """Pide la respuesta en streaming y va devolviendo ("relleno" o "frase", texto) según llegan.

    Al terminar, deja en la lista `fuentes` los documentos que ha usado el RAG.
    """
    r = requests.post(
        f"{LLM}/conversar/stream",
        json={"partida": partida, "texto": texto},
        stream=True,
        timeout=120,
    )
    r.raise_for_status()
    for linea in r.iter_lines():
        if not linea:
            continue
        dato = json.loads(linea)
        if "relleno" in dato:
            yield "relleno", dato["relleno"]
        elif "frase" in dato:
            yield "frase", dato["frase"]
        elif dato.get("fin"):
            fuentes.extend(dato.get("fuentes") or [])
            m = dato.get("medidas") or {}
            if m:
                print(f"\n       [modelo: carga {m['carga_s']} s · lee {m['lectura_tokens']} tokens en "
                      f"{m['lectura_s']} s · escribe {m['escritura_tokens']} tokens en {m['escritura_s']} s]",
                      end="", flush=True)


def sintetizar(texto):
    r = requests.post(f"{TTS}/sintetizar", json={"texto": texto}, timeout=60)
    r.raise_for_status()
    return r.content


def esperar_servicios():
    """Espera a que el servicio de diálogo haya cargado el modelo (tras arrancar puede tardar)."""
    avisado = False
    while not salir:
        try:
            if requests.get(f"{LLM}/salud", timeout=3).ok:
                if avisado:
                    print(" listo.")
                return
        except requests.RequestException:
            pass
        if not avisado:
            print("Esperando a que Bufit cargue el modelo...", end="", flush=True)
            avisado = True
        else:
            print(".", end="", flush=True)
        time.sleep(3)
    raise Interrumpido


def saludar(partida):
    """Bufit empieza la conversación. Se le manda la hora local para que elija el saludo."""
    try:
        r = requests.post(f"{LLM}/saludo", json={"partida": partida, "hora": datetime.now().hour}, timeout=10)
        r.raise_for_status()
        frase = r.json()["saludo"]
    except requests.RequestException as e:
        print(f"[no se ha podido saludar: {e}]")
        return
    print(f"Bufit: {frase}\n")
    ojos("contento")
    cola_voz.put(sintetizar(frase))
    esperar_a_que_termine_de_hablar()


def guardar_y_cerrar(partida):
    """Descarga el historial de la partida, lo guarda en disco y lo borra del servicio."""
    try:
        r = requests.get(f"{LLM}/historial/{partida}", timeout=10)
        if r.status_code != 200:
            return
        os.makedirs("datos/partidas", exist_ok=True)
        ruta = f"datos/partidas/{partida}.json"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(r.json(), f, ensure_ascii=False, indent=2)
        requests.delete(f"{LLM}/historial/{partida}", timeout=10)
        print(f"Historial guardado en {ruta}")
    except requests.RequestException as e:
        print(f"No se ha podido guardar el historial: {e}")


# ------------------------------------------------------------ bucle principal

def main():
    signal.signal(signal.SIGINT, al_pulsar_ctrl_c)

    micro = sd.InputStream(
        samplerate=FRECUENCIA,
        channels=1,
        dtype="int16",
        blocksize=int(FRECUENCIA * BLOQUE),
        callback=al_recibir_audio,
    )
    micro.start()
    threading.Thread(target=reproductor, daemon=True).start()

    partida = datetime.now().strftime("partida-%Y%m%d-%H%M%S")
    try:
        ruido = calibrar()
        print(f"\n{partida} · Di 'adiós' para terminar.\n")
        esperar_servicios()
        saludar(partida)

        while not salir:
            print("[escuchando]")
            audio, ruido = grabar(ruido)
            ojos("pensando")

            t0 = time.time()
            texto = transcribir(audio)
            t1 = time.time()
            if not texto:
                print("[Whisper no ha entendido nada]\n")
                ojos("repiteme")
                time.sleep(1.5)
                continue
            print(f"Tú:    {texto}")

            # Cada frase se sintetiza y se pone a sonar en cuanto llega,
            # sin esperar a que el modelo termine la respuesta entera
            print("Bufit: ", end="", flush=True)
            primera = None
            fuentes = []
            turno = Turno(partida)
            try:
                for tipo, frase in conversar_por_frases(partida, texto, fuentes):
                    if salir:
                        raise Interrumpido
                    turno.decir(frase, relleno=(tipo == "relleno"))
                    ojos("contento")
                    if primera is None:
                        primera = time.time() - t1
            except requests.RequestException as e:
                # Un fallo del servicio (modelo que no carga, contenedor reiniciándose...) no cierra
                # la conversación: se avisa, Bufit pone cara de duda y se sigue escuchando
                print(f"\n[el servicio de diálogo ha fallado: {e}]")
                if isinstance(e, requests.HTTPError) or e.response is not None:
                    print(f"[respuesta: {e.response.text[:300]}]")
                print("[mira: docker compose logs --tail 40 llm]\n")
                ojos("dudoso")
                time.sleep(1.5)
                continue
            finally:
                turno.terminar()
            t2 = time.time()
            print(f"\n       (STT {t1 - t0:.1f} s · empieza a hablar en {primera or 0:.1f} s"
                  f" · respuesta completa en {t2 - t1:.1f} s)")
            if fuentes:
                usadas = ", ".join(f"{f['titulo']} ({f['puntuacion']:.2f})" for f in fuentes)
                print(f"       [conocimiento: {usadas}]")
            print()

            esperar_a_que_termine_de_hablar()

            if any(p in texto.lower() for p in PALABRAS_SALIR):
                break
    except Interrumpido:
        pass
    except Exception:
        # Mostrar el error antes de salir: os._exit() no lo enseñaría
        traceback.print_exc()
        if isinstance(sys.exc_info()[1], requests.HTTPError):
            print(f"Respuesta del servicio: {sys.exc_info()[1].response.text}")
    finally:
        ojos("dormido")
        time.sleep(0.3)                   # dar tiempo a que salga el mensaje antes de cerrar
        guardar_y_cerrar(partida)
        # Salimos sin cerrar el micrófono: en macOS, cerrarlo puede dejar el programa colgado
        os._exit(0)


if __name__ == "__main__":
    main()
