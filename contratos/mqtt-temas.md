# Contratos MQTT

Broker: `broker:1883` dentro de Docker, `localhost:1883` desde el equipo.
Todos los mensajes son **JSON en UTF-8**. Todos los temas cuelgan de `bufit/`.

## Convenciones

| | |
|---|---|
| **Retenido** | El broker guarda el último mensaje y se lo entrega a quien se suscriba después. Se usa para **estados**, no para hechos puntuales |
| **Marca de tiempo** | Todo mensaje lleva `ts` en segundos desde época, con decimales |
| **Confianza** | Todo lo que venga de visión o de voz lleva `conf` entre 0 y 1 |
| **Solo al cambiar** | Los módulos de percepción publican cuando la lectura **cambia**, no en cada fotograma |

---

## Percepción

### `bufit/vision/mesa/tablero` · retenido
Publica: visión de mesa · Función: F0.12

```json
{
  "ts": 1762262400.12,
  "fichas": [{"valor": "6-3", "x": 0.42, "y": 0.55, "giro": 2.1}],
  "extremos": [6, 5],
  "conf": 0.94
}
```

### `bufit/vision/mesa/jugada`
Publica: visión de mesa · Función: F3.2

```json
{"ts": 1762262400.12, "ficha": "6-3", "extremo": "izq", "accion": "puesta", "conf": 0.92}
```

`accion` puede ser `puesta` o `retirada`.

### `bufit/vision/mesa/ocupada` · retenido
Publica: visión de mesa · Función: F0.13

```json
{"ts": 1762262400.12, "ocupada": true}
```

### `bufit/vision/mesa/presencia` · retenido
Publica: visión de mesa · Función: F1.1

```json
{"ts": 1762262400.12, "presencia": true}
```

### `bufit/vision/mesa/aviso`
Publica: visión de mesa · Funciones: F0.14, F8.2, F8.3

```json
{"ts": 1762262400.12, "tipo": "luz_insuficiente", "detalle": {"lux": 90}}
```

`tipo`: `luz_insuficiente` · `fuera_de_campo` · `ficha_problematica`

### `bufit/vision/atril/mano` · retenido
Publica: visión de atril · Función: F0.15
**Nunca se reenvía fuera del núcleo. No se muestra en pantalla con su valor.**

```json
{
  "ts": 1762262400.12,
  "posiciones": {"0": "6-3", "1": "5-5", "2": "4-0"},
  "conf": {"0": 0.99, "1": 0.98, "2": 0.91}
}
```

### `bufit/vision/atril/dedo`
Publica: visión de atril · Función: F4.5

```json
{"ts": 1762262400.12, "posicion": 2}
```

`posicion` es `null` cuando no hay dedo sobre el atril.

---

## Voz

### `bufit/voz/transcripcion`
Publica: escucha · Función: F0.1

```json
{"ts": 1762262400.12, "texto": "te toca", "idioma": "es", "conf": 0.88, "duracion": 0.9}
```

### `bufit/voz/jugador_habla`
Publica: escucha · Función: F0.5

```json
{"ts": 1762262400.12}
```

### `bufit/intencion`
Publica: intenciones · Función: F0.6

```json
{"ts": 1762262400.12, "tipo": "he_terminado", "params": {}, "conf": 0.95}
```

`tipo`: `he_terminado` · `pausa` · `reanudar` · `para` · `repite` · `ayuda` · `reglas` · `pista` · `revancha` · `cambiar_idioma` · `elegir_juego` · `despedida` · `charla_libre`

---

## Estado

### `bufit/estado/partida` · retenido
Publica: estado de partida · Función: F0.17

```json
{
  "ts": 1762262400.12,
  "partida_id": "p-20261104-001",
  "juego": "domino",
  "turno": "bufit",
  "cadena": ["3-3", "3-6", "6-1"],
  "extremos": [3, 1],
  "mano_bufit": ["5-5", "4-0"],
  "fichas_jugador": 5,
  "pozo": 9,
  "marcador": {"jugador": 0, "bufit": 0},
  "jugadas": [{"quien": "jugador", "ficha": "6-1", "extremo": "der", "ts": 1762262399.0}],
  "pausada": false
}
```

### `bufit/estado/resumen` · retenido
Publica: estado de partida · Función: F6.1
**Lo único de la partida que llega al módulo de diálogo.** No lleva ninguna mano.

```json
{
  "ts": 1762262400.12,
  "turno": "jugador",
  "fichas_jugador": 5,
  "fichas_bufit": 4,
  "extremos": [3, 1],
  "pozo": 9,
  "marcador": {"jugador": 0, "bufit": 0},
  "ultimas_jugadas": ["jugador: 6-1 por la derecha", "bufit: 3-6 por la izquierda"]
}
```

---

## Órdenes

Siguen el patrón `/set`, igual que Zigbee2MQTT. Las publica el orquestador y las obedece el módulo correspondiente.

### `bufit/pantalla/set`
Obedece: cara y pantalla · Funciones: F0.11, F3.8, F4.4, F4.6, F12.4

```json
{
  "ts": 1762262400.12,
  "vista": "juego",
  "ojos": "pensando",
  "indicador": {"total": 5, "objetivo": 2, "resaltado": 1},
  "marcador": {"jugador": 0, "bufit": 0},
  "texto": null
}
```

`vista`: `espera` · `menu` · `juego` · `reto` · `mensaje`
`ojos`: `espera` · `atento` · `pensando` · `sorprendido` · `contento` · `dudoso` · `dormido`

### `bufit/voz/set`
Obedece: voz · Funciones: F0.8, F0.10

```json
{"ts": 1762262400.12, "texto": "Juego el seis tres por la izquierda", "idioma": "es", "tono": "alegre", "velocidad": 1.0, "prioridad": "normal"}
```

`prioridad`: `normal` · `urgente` (se salta la cola) · `relleno` (se descarta si llega otra antes)

### `bufit/voz/parar`
Obedece: voz · Función: F0.9

```json
{"ts": 1762262400.12}
```

---

## Salud del sistema

### `bufit/<modulo>/online` · retenido · last will
Publica: cada módulo al conectarse · Funciones: F0.20, F0.21

```json
{"ts": 1762262400.12, "estado": "online", "version": "0.1.0"}
```

Cada módulo declara al conectar su **último testamento** en este mismo tema:

```json
{"estado": "offline"}
```

Así, si un contenedor muere, el broker lo anuncia solo y el orquestador se entera en segundos.

Ejemplo en Python:

```python
cliente.will_set(f"bufit/{MODULO}/online",
                 json.dumps({"estado": "offline"}),
                 qos=1, retain=True)
```

---

## Calidad de servicio

| Tipo de mensaje | QoS | Retenido |
|---|---|---|
| Lecturas de visión | 0 | Sí para estados, no para hechos |
| Transcripciones | 0 | No |
| Intenciones | 1 | No |
| Estado de partida | 1 | Sí |
| Órdenes `/set` | 1 | No |
| Presencia de módulos | 1 | Sí |

QoS 0 para los flujos continuos: si se pierde un fotograma no pasa nada y llega el siguiente. QoS 1 para lo que no se puede perder.
