# Ollama

Este servicio no tiene código ni `Dockerfile`: usa la imagen oficial `ollama/ollama` tal cual, definida en el `docker-compose.yml` de `prototipos/`.

`modelos/` es donde Ollama guarda todos los modelos descargados: los de conversación (que usa `llm`) y el de embeddings `bge-m3` (que usa `conocimiento`). No se sube a git.

Para ver y borrar modelos, con los contenedores arrancados:

```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama rm <modelo>
```
