# Contratos REST

Servicios que **responden preguntas**. No publican nada por su cuenta ni saben que existe una partida en marcha: solo contestan.

Se les llama cuando el que pregunta **no puede continuar sin la respuesta**. Todo lo demás va por MQTT.

| Servicio | Dirección dentro de Docker | Puerto fuera |
|---|---|---|
| Motor de reglas | `http://motor-reglas:8000` | 8001 |
| Selector de jugada | `http://selector-jugada:8000` | 8002 |
| Perfil | `http://perfil:8000` | 8003 |
| Diálogo | `http://dialogo:8000` | 8004 |

Todos exponen `GET /salud` que devuelve `{"estado": "ok", "version": "0.1.0"}`.

---

## Motor de reglas

Determinista. Sin azar y sin inteligencia artificial. Es la autoridad del juego.

### `POST /jugadas_legales` · F4.1

```json
{"estado": {...}, "mano": ["6-3", "5-5", "4-0"]}
```
```json
{"jugadas": [{"ficha": "6-3", "extremo": "izq"}, {"ficha": "4-0", "extremo": "der"}]}
```

Una lista vacía es una respuesta válida y significa que hay que robar o pasar.

### `POST /es_legal` · F3.5

```json
{"estado": {...}, "jugada": {"ficha": "6-3", "extremo": "izq"}}
```
```json
{"legal": false, "motivo": "no_encaja"}
```

`motivo`: `no_encaja` · `extremo_inexistente` · `ficha_no_en_mano` · `no_es_su_turno`

### `POST /aplicar` · F3.6

```json
{"estado": {...}, "jugada": {"ficha": "6-3", "extremo": "izq"}}
```
```json
{"estado": {...}}
```

**No modifica el estado que recibe: devuelve uno nuevo.** Es lo que permite deshacer una jugada (F8.6).

### `POST /fin_partida` · F10.1

```json
{"estado": {...}}
```
```json
{"terminada": true, "motivo": "domino", "ganador": "jugador"}
```

`motivo`: `domino` (alguien se quedó sin fichas) · `cierre` (nadie puede jugar) · `abandono`

### `POST /puntuacion` · F10.2

```json
{"estado": {...}, "puntos_jugador": 12}
```
```json
{"ganador": "bufit", "puntos": {"jugador": 12, "bufit": 5}, "desglose": {"bufit": [["5-5", 10], ["4-0", 4]]}}
```

`puntos_jugador` lo dice el propio jugador en voz alta: Bufit no ve su mano.

### `GET /parametros/{juego}` · F2.3

```json
{"juego": "domino", "fichas": 28, "mano": 7, "pozo": true, "puntos_para_ganar": 100, "empieza": "jugador"}
```

### `POST /info_publica` · F7.3

```json
{"estado": {...}}
```
```json
{"extremos": [3, 1], "fichas_no_vistas": ["2-2", "6-6"], "pozo": 9, "fichas_jugador": 5}
```

Solo lo que cualquiera deduciría mirando la mesa. **Nunca incluye manos.**

---

## Selector de jugada

### `POST /elegir` · F4.2

```json
{
  "jugadas": [{"ficha": "6-3", "extremo": "izq"}],
  "nivel": 5,
  "estado_publico": {"extremos": [6, 5], "fichas_jugador": 5, "pozo": 9, "marcador": {}}
}
```
```json
{"jugada": {"ficha": "6-3", "extremo": "izq"}, "motivo": "azar"}
```

**Fíjate en lo que NO hay en la entrada: las fichas del jugador.** No es un olvido, es la garantía de que Bufit no puede hacer trampas. Si algún día alguien necesita añadirlas, la respuesta es no.

---

## Perfil

### `GET /perfil/{mote}` · F1.4
### `POST /perfil` · F1.5
### `POST /perfil/{mote}/partida` · F10.6
### `DELETE /perfil/{mote}` · borrado a petición del jugador

```json
{"mote": "pepe", "nivel": 5, "idioma": "es", "partidas": 12, "creado": "2026-11-04"}
```

Devuelve 404 si el mote no existe. En sesión anónima no se llama a este servicio en ningún momento.

---

## Diálogo

Todas las respuestas incluyen `emocion`, para que los ojos acompañen.

### `POST /conversar` · F0.7
### `POST /narrar_jugada` · F4.3
### `POST /explicar_regla` · F7.2
### `POST /generar_pista` · F7.4
### `POST /avisar_incidencia` · F8.4

```json
{"resumen": {...}, "texto_jugador": "¿me queda mucho?", "idioma": "es", "perfil": {...}}
```
```json
{"texto": "Te quedan cinco, vas bien.", "emocion": "contento"}
```

**Nunca recibe el estado completo, solo el resumen.** Nunca decide ni valida jugadas.

Si tarda más de lo permitido, el que llama corta y usa su frase de reserva: ningún dato del juego puede depender de que el modelo responda.
