# Prototipo TTS

Pieza suelta: recibe texto por HTTP y devuelve el audio en WAV. Todavía no sigue el contrato MQTT de `modulos/voz`.

## Arrancar

```bash
cd prototipos/tts
docker build -t bufit-tts .
docker run --rm -p 8012:8000 -v "$PWD/modelos:/modelos" bufit-tts
```

La primera vez descarga la voz `es_ES-davefx-medium` (~60 MB) en `prototipos/tts/modelos/`.

## Probar

```bash
curl -X POST http://localhost:8012/sintetizar \
  -H "Content-Type: application/json" \
  -d '{"texto": "Hola, soy Bufit. ¿Jugamos una partida de dominó?"}' \
  -o respuesta.wav

afplay respuesta.wav
```

## Cambiar la voz

Voces en español: `es_ES-davefx-medium`, `es_ES-sharvard-medium`, `es_ES-carlfm-x_low`, `es_MX-claude-high`.

```bash
docker run --rm -p 8012:8000 -e VOZ=es_ES-sharvard-medium -v "$PWD/modelos:/modelos" bufit-tts
```
