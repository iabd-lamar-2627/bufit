# Registro

Escucha **todo** el bus y lo escribe en disco. No habla con nadie y nadie le habla.

Parece el módulo más tonto del proyecto y es de los más importantes: con catorce contenedores repartidos, sin trazas es imposible saber por qué algo ha fallado. Es la diferencia entre "no sé qué ha pasado" y "mira, a las 19:42 la visión publicó una ficha con confianza 0,62".

Sirve además de **ejemplo de suscriptor MQTT**: cópialo para tu módulo.

## Funciones

| Código | Función | Prioridad |
|---|---|---|
| F0.19 | Registrar los eventos del sistema | Must |

## Lo que NO hace

- No guarda audio ni imágenes. Nunca.
- No bloquea a nadie: si falla, el sistema sigue.

## Formato

Un JSON por línea en `/trazas/bufit-AAAA-MM-DD.jsonl`:

```json
{"ts": 1762262400.12, "tema": "bufit/vision/mesa/tablero", "datos": {...}}
```

Se puede volver a leer con `jq`, con pandas o reproducirlo para repetir una partida.

## Probarlo

```bash
docker compose up -d broker registro
docker compose exec broker mosquitto_pub -t 'bufit/prueba' -m '{"hola":1}'
tail -f datos/trazas/bufit-*.jsonl
```
