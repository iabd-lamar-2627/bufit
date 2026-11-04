"""Registro · suscriptor MQTT de ejemplo.

Escucha todo el bus y escribe un JSON por linea. Copia este fichero como
punto de partida para cualquier modulo que solo escuche.
"""
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

import paho.mqtt.client as mqtt

MODULO = "registro"
BROKER = os.environ.get("BROKER", "localhost")
PUERTO = int(os.environ.get("PUERTO", 1883))
DESTINO = Path(os.environ.get("DESTINO", "/trazas"))
VERSION = "0.1.0"

DESTINO.mkdir(parents=True, exist_ok=True)


def fichero_de_hoy() -> Path:
    return DESTINO / f"bufit-{date.today().isoformat()}.jsonl"


def al_conectar(cliente, datos, flags, rc, propiedades=None):
    print(f"[{MODULO}] conectado a {BROKER}:{PUERTO}")
    cliente.subscribe("bufit/#", qos=0)
    # Anuncia que esta vivo. Retenido, para que quien se suscriba despues
    # lo sepa de inmediato.
    cliente.publish(f"bufit/{MODULO}/online",
                    json.dumps({"ts": time.time(), "estado": "online", "version": VERSION}),
                    qos=1, retain=True)


def al_llegar_mensaje(cliente, datos, msg):
    # No registramos nuestros propios anuncios de presencia: ruido.
    if msg.topic == f"bufit/{MODULO}/online":
        return
    try:
        contenido = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        contenido = {"_bruto": repr(msg.payload[:200])}

    linea = {"ts": time.time(), "tema": msg.topic, "datos": contenido}
    try:
        with fichero_de_hoy().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(linea, ensure_ascii=False) + "\n")
    except OSError as e:
        # Nunca detiene el sistema: si no se puede escribir, se avisa y ya.
        print(f"[{MODULO}] no se pudo escribir la traza: {e}")


def main():
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MODULO)
    # Ultimo testamento: si este contenedor muere, el broker lo anuncia solo.
    cliente.will_set(f"bufit/{MODULO}/online",
                     json.dumps({"estado": "offline"}),
                     qos=1, retain=True)
    cliente.on_connect = al_conectar
    cliente.on_message = al_llegar_mensaje

    while True:
        try:
            cliente.connect(BROKER, PUERTO, keepalive=30)
            break
        except OSError:
            print(f"[{MODULO}] el broker no responde, reintento en 2 s")
            time.sleep(2)

    print(f"[{MODULO}] escuchando bufit/# -> {DESTINO}")
    cliente.loop_forever()      # se queda esperando a que lo despierten


if __name__ == "__main__":
    main()
