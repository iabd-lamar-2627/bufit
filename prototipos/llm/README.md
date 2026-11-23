# Prototipo LLM

Servicio de conversación. No tiene modelos dentro: le pide las respuestas al contenedor `ollama`.

- Guarda un historial por partida, en memoria.
- Usa el servicio `conocimiento` (RAG) de una de estas dos formas, según `MODO_BUSQUEDA`:
  - `modelo` (por defecto): el modelo tiene una herramienta, `buscar_conocimiento`, y decide él cuándo usarla (reglas de juegos, recetas, trámites...). En la charla normal no busca nada y responde en una sola pasada. Cuando busca, hace dos pasadas: una para pedir la búsqueda y otra para responder con lo encontrado. La búsqueda y su resultado quedan en el historial, así que en el turno siguiente ("sí, sigue") todavía tiene el documento.
  - `umbral`: busca en cada turno. Un trozo entra si se parece mucho (`UMBRAL_ALTO`) o, si la frase nombra un tema de la base (juego, receta, trámite...), si supera `UMBRAL`.
- El prompt de sistema está en `src/app.py` (`PROMPT_BASE` más la parte de la base de conocimientos según el modo). En los registros (`docker compose logs -f llm`) se ve cada búsqueda que pide el modelo: `[herramienta] buscar_conocimiento('reglas de la brisca') → ['Brisca']`.

Se arranca con el `docker-compose.yml` de `prototipos/`. El modelo se elige con `MODELO` en ese fichero.

## Endpoints

| Método y ruta | Qué hace |
|---|---|
| `POST /conversar` | `{"partida": "...", "texto": "..."}` → respuesta completa y fuentes usadas |
| `POST /conversar/stream` | Igual, pero frase a frase según se genera |
| `GET /historial/{partida}` | Descarga el historial |
| `DELETE /historial/{partida}` | Borra el historial |
