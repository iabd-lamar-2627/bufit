# Prototipo STT

Pieza suelta: recibe audio por HTTP y devuelve el texto. Todavía no sigue el contrato MQTT de `modulos/escucha`.

## Arrancar

```bash
cd prototipos/stt
docker build -t bufit-stt .
docker run --rm -p 8010:8000 -v "$PWD/modelos:/modelos" bufit-stt
```

La primera vez descarga el modelo `base` (~150 MB) en `prototipos/stt/modelos/`. Las siguientes ya no.

## Probar

```bash
# 1. Crear un audio de prueba con la voz del Mac (16 kHz, mono)
say -v Monica -o prueba.wav --data-format=LEI16@16000 "Hola Bufit, ¿jugamos una partida de dominó?"

# 2. Comprobar que el servicio está vivo
curl http://localhost:8010/salud

# 3. Transcribir
curl -F "audio=@prueba.wav" http://localhost:8010/transcribir
```

Respuesta esperada:

```json
{"texto": "Hola Bufit, ¿jugamos una partida de dominó?", "idioma": "es", "duracion_audio": 3.1, "segundos_proceso": 0.8}
```

## Cambiar el modelo

```bash
docker run --rm -p 8010:8000 -e MODELO_WHISPER=small -v "$PWD/modelos:/modelos" bufit-stt
```

`tiny` es el más rápido y el peor. `small` es más preciso y unas 3 veces más lento que `base`.
