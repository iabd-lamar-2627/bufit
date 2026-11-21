# Prototipo LLM

Servicio de conversación. No tiene modelos dentro: le pide las respuestas al contenedor `ollama`.

- Guarda un historial por partida, en memoria.
- En cada turno consulta al servicio `conocimiento` (RAG) y, si encuentra trozos de documentos parecidos a la pregunta, los añade al prompt.
- El prompt de sistema está en `src/app.py` (variable `SISTEMA`).

Se arranca con el `docker-compose.yml` de `prototipos/`. El modelo se elige con `MODELO` en ese fichero.

## Endpoints

| Método y ruta | Qué hace |
|---|---|
| `POST /conversar` | `{"partida": "...", "texto": "..."}` → respuesta completa y fuentes usadas |
| `POST /conversar/stream` | Igual, pero frase a frase según se genera |
| `GET /historial/{partida}` | Descarga el historial |
| `DELETE /historial/{partida}` | Borra el historial |
