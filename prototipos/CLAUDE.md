# Bufit · prototipo de voz y ojos — contexto para Claude

> Léelo al empezar. Resume cómo está el prototipo para no tener que leer el código cada vez.
> Si cambias algo importante (servicios, parámetros, decisiones), **actualiza este fichero**.

## Qué es

Bufit es un robot compañero de juegos de mesa para personas mayores (proyecto troncal del curso de IA y Big Data, IES La Mar, Xàbia). Repo: `iabd-lamar-2627/bufit`. Este directorio, `prototipos/`, es un prototipo independiente de los módulos de `modulos/`: conversa por voz, sabe de juegos, recetas y trámites (RAG) y tiene unos ojos animados en una pantalla.

- Profesor y usuario: Manol. Todo en **español de España**. Explicaciones claras y concisas; cambios pequeños y de uno en uno.
- Objetivo de hardware: **el mínimo posible**, CPU sin GPU (equipos económicos). Habrá más contenedores (visión con dos cámaras), así que cada pieza debe ser ligera. Si al final hace falta una GPU modesta, se acepta.
- Desarrollo en un MacBook (Apple Silicon) con Docker Desktop: **5 CPU y unos 14 GB de RAM** asignados. Destino final: un PC Linux.

## Arquitectura

```
micrófono → conversar.py ──HTTP──▶ stt (Whisper) ──▶ texto
                 │──HTTP stream──▶ llm ──▶ ollama (qwen3:8b)
                 │                   └──herramienta──▶ conocimiento (RAG, bge-m3 en ollama)
                 │──HTTP──▶ tts (Piper) ──▶ altavoz
                 └──MQTT──▶ mqtt (Mosquitto) ──WebSocket──▶ ojos/index.html (navegador)
```

Un contenedor por pieza (`docker-compose.yml`). `conversar.py` y la página de los ojos van **fuera de Docker**: Docker en Mac no tiene acceso a micrófono, altavoz ni cámara.

| Servicio | Puerto | Qué hace | Parámetros (en `docker-compose.yml`) |
|---|---|---|---|
| `stt` | 8010 | Audio → texto con faster-whisper (CPU, int8, VAD, filtro de alucinaciones) | `MODELO_WHISPER: small` (base confundía "parchís"); `HAZ: "2"` (beam size: 1 rápido, 5 preciso); `HILOS: "0"` (todos los núcleos); `VAD_UMBRAL: "0.35"` (detector de voz; 0.5 descartaba voz flojita); `PROMPT_WHISPER` (vocabulario raro, lista corta) |
| `ollama` | interno 11434 | Servidor de modelos. Modelos en `./ollama/modelos` | `OLLAMA_KEEP_ALIVE: "-1"` (nunca descarga el modelo de memoria); `OLLAMA_NOPRUNE: "1"` (no borra ficheros al arrancar) |
| `llm` | 8011 | Conversación: historial por partida en memoria, prompt, herramienta de búsqueda, respuesta frase a frase | `MODELO: qwen3:8b`; `PENSAR: "false"` (sin razonamiento, más rápido); `MODO_BUSQUEDA: mixto`; `K_HERRAMIENTA: "2"`; `UMBRAL: "0.58"`; `UMBRAL_ALTO: "0.68"`; `MAX_TOKENS: "110"` (charla); `MAX_TOKENS_DOC: "220"` (explicando algo de la base); `MAX_MENSAJES: "0"` (sin recorte); `MODELO_REACCION: ""` (desactivado); `K: "2"` (trozos en la búsqueda automática de los modos mixto y umbral; 2 da explicaciones más completas a cambio de ~4 s) |
| `conocimiento` | 8013 | RAG: indexa los `.md` de `conocimiento/documentos/` con Chroma y embeddings bge-m3 (vía ollama). Al arrancar reutiliza el índice de `conocimiento/vectores` y solo recalcula los documentos nuevos o cambiados (huella SHA-1 del texto y de `TAM_TROZO`); si cambia el modelo de embeddings, lo rehace entero. **Búsqueda híbrida**: semántica (embeddings) + por palabras (BM25 escrito a mano, sin librerías), mezcladas con Reciprocal Rank Fusion. `puntuacion` sigue siendo el parecido semántico (el llm la compara con `UMBRAL`), +`BONUS_ACUERDO` si el trozo está también entre los 3 primeros por palabras. `/buscar` admite `"modo"` y devuelve `semantica`, `bm25` y los puestos (para comparar) | `MODELO_EMBEDDINGS: bge-m3`; `TAM_TROZO: "400"`; `MODO_BUSQUEDA: hibrida` (o `semantica`, `palabras`); `BONUS_ACUERDO: "0.1"` (arregló «se canta las cuarenta» → tute 0,49 → 0,59, y «clave pin» → Cl@ve) |
| `tts` | 8012 | Texto → audio con Piper. Limpia mmm/hmm, jaja, emojis, asteriscos | `VOZ: es_ES-davefx-medium` |
| `mqtt` | 1883 (MQTT) y 9001 (WebSocket) | Broker Mosquitto (`mqtt/mosquitto.conf`, sin contraseña, solo red local) | — |

### llm (`llm/src/app.py`)

- Endpoints: `POST /conversar`, `POST /conversar/stream` (NDJSON: `{"relleno"}`, `{"frase"}`, `{"fin", tokens_seg, fuentes, medidas}`), `POST /saludo` (según la hora local que manda el cliente; se guarda en el historial), `GET /relleno?tipo=`, `GET/DELETE /historial/{partida}`, `GET /salud`.
- **Prompt**: `PROMPT_BASE` (compañero de charla de cualquier tema, especialista en juegos de mesa, primera persona, 1-2 frases, sin coletillas, no inventa datos de la persona/tiempo/fecha, no ofrece buscar ni internet; para el tiempo o noticias sugiere radio, tele o móvil; nunca menciona su base ni que ha buscado; si la búsqueda no trae nada, responde con lo que sabe salvo en trámites, ayudas, salud y dinero) + `PROMPT_HERRAMIENTA` (modos mixto y modelo) o `PROMPT_CORCHETES` (modo umbral).
- **`MODO_BUSQUEDA: mixto`** (actual): si la frase contiene una palabra clave de la base (`PALABRAS_CLAVE`: juegos, receta, trámite, Imserso…), se busca antes de llamar al modelo y el documento va entre corchetes en el mensaje, que se guarda así en el historial (continuidad y caché). Si no, actúa como el modo `modelo`. Se añadió porque el modelo a veces no buscaba cuando debía (dijo que las fichas de dominó son cuadradas). Palabras demasiado comunes («ayuda», «dicho», «partida», «plato», «contacto», «Xàbia»/«Jávea», porque vive allí) se quitaron de la lista porque disparaban búsquedas falsas.
- **`MODO_BUSQUEDA: modelo`**: el modelo tiene la herramienta `buscar_conocimiento(consulta)` y decide cuándo usarla. Charla normal = 1 pasada; con búsqueda = 2 pasadas. La llamada y el resultado se guardan en el historial (así "sí, sigue" conserva el documento). Al buscar manda un relleno de tipo `busqueda`.
- **`MODO_BUSQUEDA: umbral`** (reserva): busca en cada turno; un trozo entra si su parecido ≥ `UMBRAL_ALTO`, o ≥ `UMBRAL` si la frase contiene una palabra clave de la base (`PALABRAS_CLAVE`).
- **Caché del prompt (crítico en CPU)**: el principio del prompt no debe cambiar entre llamadas. Por eso: el contexto RAG va dentro del último mensaje de usuario (no como `system`), y **las herramientas se mandan en todas las pasadas** (si una pasada va sin ellas, Ollama relee todo el prompt: de 2 s a 20-30 s).
- `MAX_TOKENS`: si la respuesta llega al tope, la última frase a medias no se dice ni se guarda.
- Frases de relleno en `llm/rellenos.json` (se releen en cada uso, sin reconstruir): `espera`, `espera_larga`, `busqueda`, `saludo_manana/tarde/noche`. Nada de "mmm": Piper lo deletrea.

### conversar.py (cliente, en el Mac)

- Micrófono con cola de bloques de 30 ms; umbral de inicio/fin adaptativo al ruido; `SILENCIO_FIN = 1.0` s (**no bajarlo**: corta a la persona); máx. 15 s por frase.
- Reproduce cada frase en cuanto llega (hilo reproductor). Rellenos: a los 5 s sin respuesta (`espera`), luego cada 7 s (`espera_larga`), máx. 3 por turno (`ESPERA_RELLENO`, `ESPERA_SIGUIENTE`, `MAX_RELLENOS`).
- Al arrancar espera a que el `llm` responda en `/salud` (el modelo puede tardar en cargar) antes de saludar.
- Si el servicio falla en un turno, avisa, pone los ojos en `dudoso` y sigue escuchando.
- Publica en MQTT (`bufit/pantalla/set`) el estado de los ojos con `retain` y deja una **última voluntad** `{"ojos":"dormido"}`. Mientras hablas publica `{"voz": 0-1}` ~8 veces/s.
  - espera (esperando voz) · escuchando (hablas) · pensando (STT + modelo) · contento (Bufit habla) · repiteme (Whisper no entendió) · dudoso (fallo del servicio) · dormido (60 s sin voz, `DORMIR_TRAS`, o al salir).
- Historial de cada conversación en `datos/partidas/` (no se sube a git).
- Entorno: `prototipos/.venv` con `requirements-cliente.txt` (sounddevice, numpy, requests, paho-mqtt).

### ojos (`ojos/index.html`)

- Página autónoma (doble clic). Librería `mqtt.min.js` local (mqtt.js 5.10.1) para funcionar sin internet. Otro broker: `index.html?mqtt=ws://IP:9001`.
- Estados: espera, atento, pensando, sorprendido, contento, dudoso, dormido, escuchando, concentrado, tu_turno, repiteme, busca_carta, escaneando, borracho. Teclas 1-9, T/R/B/S/D; M = mirada con el ratón; V = simular voz; H = ocultar botones; F = pantalla completa; espacio = parpadear. Botón de sonido (hipo del borracho, barrido al escanear).
- Mensajes MQTT (JSON, combinables): `{"ojos": "..."}`, `{"mirar": {"x": -1..1, "y": -1..1}}`, `{"parpadear": true}`, `{"voz": 0..1}`. Al conectarse al broker se duerme hasta recibir un estado.
- Diseño: cejas SVG asimétricas desplazadas hacia fuera; globo con pupila y reflejo; párpados como máscara CSS. Cada estado solo cambia variables CSS (`--cy --cx --cr --cs` cejas, `--px --py` pupila, `--ps --pr` párpado, `--sonrisa`, `--mx --my` mirada, `--voz`). Gestos de ceja con `gestoCeja()` (Web Animations). La voz no es un ecualizador: solo indica si alguien habla; los gestos de escucha van a su ritmo.
- **La página la ha retocado Manol a mano**: edítala con cambios quirúrgicos (añadir, no reescribir).

### Contrato MQTT

Documentado en `../contratos/mqtt-temas.md` y `../contratos/esquemas/pantalla-set.schema.json` (incluye los 13 estados, `mirar`, `parpadear` y `voz`; `borracho` aún no está en el contrato).

## Arrancar

```bash
cd prototipos
docker compose up -d            # --build si has cambiado código o el compose
docker compose logs -f llm      # espera a "Modelo qwen3:8b listo" (10-20 s; 2 min si hay poca memoria)
# abrir ojos/index.html → "MQTT: conectado"
source .venv/bin/activate
python conversar.py             # "adiós" o Ctrl+C para terminar
```

Primera vez en un equipo nuevo: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-cliente.txt`, y descargar modelos:

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:8b
docker compose exec ollama ollama pull bge-m3
```

Whisper y Piper descargan sus modelos solos la primera vez (`stt/modelos`, `tts/modelos`). Documentos nuevos del RAG: dejarlos en `conocimiento/documentos/<categoría>/` (primera línea `# Título`) y `curl -X POST http://localhost:8013/reindexar` (solo los nuevos o cambiados; `?completo=true` lo rehace todo), o reiniciar el servicio.

## Rendimiento de referencia (Mac, 5 CPU, sin CVAT)

STT ~1,4 s · empieza a hablar 2,5-5 s tras callarte (incluye 1 s de silencio de fin) · respuesta completa 3,5-8 s · lectura del prompt con caché 2-3 s · escritura ~10 tokens/s.

## Problemas conocidos y soluciones

- **Todo va lentísimo / el modelo tarda 2 min en cargar**: suele estar arrancado CVAT (curso de etiquetado) y se come CPU y ~5 GB de RAM. Pararlo: `docker stop $(docker ps -q --filter "name=cvat") $(docker ps -q --filter "name=nuclio") traefik` y `docker compose restart ollama llm`.
- **`model "qwen3:8b" not found`**: faltan los pesos en `ollama/modelos/models/blobs` (una limpieza del Mac los borró una vez). Volver a hacer `pull`. Pendiente: mover los modelos de Ollama a un volumen de Docker para que las limpiezas no los toquen.
- **`RemoteDisconnected` al empezar**: el `llm` aún está cargando el modelo ("Waiting for application startup"). Esperar a "listo". `conversar.py` ya espera solo.
- Leer documentos cuesta: en CPU el modelo lee ~30 tokens/s, y cada trozo de 400 caracteres son unos 110 tokens (~4 s). Con `K: "2"` un turno con documento tarda unos 8-10 s; Manol prefiere explicaciones completas. Turnos de búsqueda con lectura de 20-30 s: algo ha cambiado el principio del prompt (ver "caché del prompt").
- «Whisper no ha entendido nada» repetido: `docker compose logs stt` dice el motivo (el detector de voz no encontró voz → bajar `VAD_UMBRAL` o hablar más cerca; Whisper cree que no es voz → filtro `no_speech_prob`).
- Whisper: alucinaciones tipo "¡Suscríbete!" se filtran; si falla en palabras raras, añadirlas a `PROMPT_WHISPER` o subir `HAZ`.

## Decisiones tomadas (y por qué)

- Ollama en su propio contenedor (el `llm` no lleva modelos): se cambia de modelo sin reconstruir.
- qwen3:8b: la calidad compensa; los modelos de 3-4B (llama3.2:3b, qwen3.5:4b) respondían peor. Los alumnos, en cambio, compiten con modelos ≤ 4B.
- Búsqueda decidida por el modelo (herramienta) en vez de buscar siempre: antes se colaban documentos irrelevantes ("tengo sueño" → "dormir bien").
- Sin modelo de reacción (llama3.2:3b decía frases sin sentido que el 8B copiaba); se usan rellenos fijos.
- Parakeet u otras alternativas a Whisper e interrumpir a Bufit mientras habla (barge-in): aparcados por ahora.

## Pendiente

1. Visión: cámara que detecta personas (YOLO pequeño) → `mirar` para seguir a la persona, despertar y saludar.
2. Orquestador que decida los estados en lugar de `conversar.py` (según el contrato del repo).
3. Volumen de Docker para los modelos de Ollama.
4. Medir en el hardware objetivo (o simularlo con `cpus:` por contenedor) con las dos cámaras.
5. Añadir `borracho` al contrato o dejarlo como estado de demostración.

## Normas para trabajar aquí

- Antes de cambiar un fichero, copia la versión anterior a `_to_delete/` (está en `.gitignore`).
- No hacer commit ni push sin que Manol lo pida. Rama de trabajo: `prototipo-voz-ojos`. Autor de los commits: el de Manol.
- No subir modelos, vectores, audios ni `datos/` (ya están en `.gitignore`).
- Al acabar un cambio, decir exactamente qué comando hay que ejecutar para probarlo (`docker compose up -d --build <servicio>`, etc.).
