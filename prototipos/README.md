# Prototipos de voz

# curl -X POST http://localhost:8013/reindexar

Piezas sueltas para probar la conversación por voz antes de adaptarlas a los contratos de `modulos/`.

| Carpeta | Qué hace | Puerto |
|---|---|---|
| `stt/` | Audio → texto (Whisper) | 8010 |
| `llm/` | Conversación con historial por partida (Ollama, en su propio contenedor) | 8011 |
| `conocimiento/` | RAG: busca en los `.md` de `conocimiento/documentos/` los trozos parecidos a la pregunta | 8013 |
| `tts/` | Texto → audio (Piper) | 8012 |
| `conversar.py` | Cliente que lo une todo: micrófono → STT → LLM → TTS → altavoz | — |

## Arrancar los servicios

```bash
cd prototipos
docker compose up --build -d
docker compose logs -f llm        # espera a "Modelo ... listo" y pulsa Ctrl+C
```

Para pararlos: `docker compose down`

## Conversar

El cliente corre fuera de Docker, porque es quien usa el micrófono y el altavoz.

```bash
cd prototipos
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-cliente.txt
python conversar.py
```

La primera vez, macOS pedirá permiso para que el Terminal use el micrófono.

Al terminar (di "adiós" o pulsa Ctrl+C) el historial se guarda en `datos/partidas/`, que no se sube al repositorio.

## Base de conocimiento (RAG)

Deja ficheros `.md` en `conocimiento/documentos/` (se pueden organizar en subcarpetas). La primera línea `# Título` es el nombre con el que Bufit cita la fuente.

Después de añadir o editar documentos:

```bash
curl -X POST http://localhost:8013/reindexar
```

Para ver qué encuentra para una pregunta:

```bash
curl -X POST http://localhost:8013/buscar -H "Content-Type: application/json" \
  -d '{"texto": "¿cómo se hace la paella?"}'
```

`UMBRAL` en `docker-compose.yml` decide a partir de qué puntuación se usa un trozo. Ajústalo con pruebas.
