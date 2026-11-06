# Coordinación entre módulos — Bufit

> **Para el equipo de desarrollo.**
> Este documento responde tres preguntas prácticas: quién hace qué, qué funciones son obligatorias para el MVP y qué datos se intercambian entre módulos.

---

## 1. Mapa de módulos

```
┌─────────────────────────────────────────────────────────────┐
│  PERCEPCIÓN                                                  │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ visión-mesa  │  │ visión-atril │   ← cámaras             │
│  └──────┬───────┘  └──────┬───────┘                         │
│         │ MQTT             │ MQTT (solo interno)             │
└─────────┼─────────────────┼─────────────────────────────────┘
          │                 │
┌─────────▼─────────────────▼─────────────────────────────────┐
│  INTERPRETACIÓN                                              │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   escucha    │  │  intenciones │   ← micrófono / NLP     │
│  └──────┬───────┘  └──────┬───────┘                         │
└─────────┼─────────────────┼─────────────────────────────────┘
          │ MQTT             │ MQTT
┌─────────▼─────────────────▼─────────────────────────────────┐
│  CONTROL                                                     │
│                 ┌──────────────┐                             │
│                 │ orquestador  │   ← cerebro del flujo       │
│                 └──────┬───────┘                             │
└────────────────────────┼────────────────────────────────────┘
                         │ REST (síncrono) + MQTT (órdenes)
┌────────────────────────▼────────────────────────────────────┐
│  LÓGICA                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐     │
│  │ motor-reglas │  │selector-jugada│  │    diálogo     │     │
│  └──────────────┘  └──────────────┘  └────────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │estado-partida│  │    perfil    │                          │
│  └──────────────┘  └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
          │ MQTT órdenes
┌─────────▼───────────────────────────────────────────────────┐
│  SALIDA                                                      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │     voz      │  │ cara-pantalla│                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
          │ interno
┌─────────▼───────────────────────────────────────────────────┐
│  DATOS                                                       │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   registro   │  │  simuladores │   (solo para pruebas)   │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

**Regla de oro:** los módulos de capas superiores nunca llaman a los de capas inferiores. El orquestador coordina; los módulos de lógica responden cuando se les pregunta.

---

## 2. Funciones Must por módulo

Son las únicas que deben estar listas para que el sistema funcione de punta a punta. El resto puede llegar después.

| Código | Función | Módulo |
|--------|---------|--------|
| F0.1 | Capturar y transcribir la voz | **escucha** |
| F0.6 | Clasificar la intención de una frase | **intenciones** |
| F0.8 | Sintetizar y reproducir voz | **voz** |
| F0.11 | Mostrar la expresión de los ojos | **cara-pantalla** |
| F0.12 | Leer el estado de la mesa | **visión-mesa** |
| F0.13 | Detectar una mano sobre la zona de juego | **visión-mesa** |
| F0.15 | Leer el contenido del atril | **visión-atril** |
| F0.17 | Publicar el estado de la partida | **estado-partida** |
| F0.19 | Registrar los eventos del sistema | **registro** |
| F1.2 | Abrir la sesión y saludar | **orquestador** |
| F2.3 | Cargar los parámetros del juego elegido | **motor-reglas** |
| F2.4 | Explicar cómo preparar la partida | **diálogo** |
| F2.5 | Comprobar el número de fichas del atril | **orquestador** |
| F2.8 | Inicializar el estado de la partida | **estado-partida** |
| F2.9 | Determinar quién inicia la partida | **motor-reglas** |
| F2.10 | Anunciar el comienzo de la partida | **orquestador** |
| F3.1 | Anunciar el turno del jugador | **orquestador** |
| F3.2 | Detectar que se ha colocado una ficha nueva | **visión-mesa** |
| F3.3 | Confirmar el fin del turno del jugador | **orquestador** |
| F3.5 | Validar la legalidad de una jugada | **motor-reglas** |
| F3.6 | Aplicar una jugada al estado | **motor-reglas** |
| F3.9 | Solicitar una lectura de mayor calidad | **orquestador** |
| F4.1 | Obtener las jugadas legales de Bufit | **motor-reglas** |
| F4.2 | Elegir una jugada según el nivel | **selector-jugada** |
| F4.3 | Narrar la jugada de Bufit | **diálogo** |
| F4.4 | Señalar en pantalla la ficha elegida | **cara-pantalla** |
| F4.8 | Indicar la ficha de viva voz | **orquestador** |
| F4.9 | Verificar que se ha colocado la ficha indicada | **orquestador** |
| F4.11 | Retirar la ficha jugada de la mano de Bufit | **estado-partida** |
| F5.1 | Detectar que Bufit no tiene jugada posible | **orquestador** |
| F5.2 | Solicitar el robo de una ficha | **orquestador** |
| F5.3 | Detectar una ficha nueva en el atril | **visión-atril** |
| F5.5 | Incorporar la ficha robada a la mano | **estado-partida** |
| F5.7 | Llevar la cuenta del pozo | **estado-partida** |
| F5.8 | Pasar turno por imposibilidad de jugar | **motor-reglas** |
| F6.4 | Pedir que repita lo dicho | **orquestador** |
| F8.1 | Detectar una discrepancia entre la mesa y el estado | **orquestador** |
| F8.2 | Detectar que la cadena se sale del campo | **visión-mesa** |
| F8.4 | Comunicar la incidencia con tacto | **diálogo** |
| F8.5 | Proponer la corrección concreta | **orquestador** |
| F8.6 | Revertir una jugada no válida | **estado-partida** |
| F8.7 | Aceptar la versión del jugador | **orquestador** |
| F10.1 | Detectar el fin de la partida | **motor-reglas** |
| F10.2 | Calcular la puntuación final | **motor-reglas** |
| F10.3 | Anunciar el resultado con deportividad | **diálogo** |

---

## 3. Estructuras de datos compartidas

Todos los mensajes llevan `ts` (segundos desde época, con decimales). Los mensajes de visión y voz llevan además `conf` (confianza, 0–1).

### 3.1 Ficha

Formato de cadena: `"V1-V2"` donde `V1 ≤ V2`, ambos de 0 a 6.

```
"6-3"  →  NO válido (3 < 6, debe ser "3-6")
"3-6"  →  válido
"5-5"  →  válido
```

Este formato se usa en todos los esquemas. La validación es `^[0-6]-[0-6]$` pero el módulo que la produce debe garantizar `V1 ≤ V2`.

---

### 3.2 `bufit/estado/partida` — estado completo (retenido)

Lo publica **estado-partida**. Lo consumen orquestador y motor-reglas.

```json
{
  "ts": 1762262400.12,
  "partida_id": "p-20261104-001",
  "juego": "domino",
  "turno": "jugador",
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

**La mano de Bufit nunca sale del orquestador hacia módulos de salida.** El diálogo recibe solo `bufit/estado/resumen` (sin manos).

---

### 3.3 `bufit/intencion` — intención clasificada

Lo publica **intenciones**. Lo consume orquestador.

```json
{
  "ts": 1762262400.12,
  "tipo": "he_terminado",
  "params": {},
  "conf": 0.95
}
```

**Tipos de intención:**

| `tipo` | Crítica (por reglas) | Descripción |
|--------|---------------------|-------------|
| `he_terminado` | ✓ | El jugador dice que ha puesto su ficha |
| `pausa` | ✓ | Parar la partida temporalmente |
| `reanudar` | ✓ | Continuar después de una pausa |
| `para` | ✓ | Apagar el sistema |
| `repite` | ✓ | Que Bufit repita lo que dijo |
| `ayuda` | ✓ | Pedir ayuda general |
| `cambiar_idioma` | ✓ | Cambiar el idioma de la sesión |
| `elegir_juego` | — | Seleccionar un juego al inicio |
| `reglas` | — | Preguntar por las reglas |
| `pista` | — | Pedir una pista de juego |
| `revancha` | — | Proponer otra partida |
| `despedida` | — | Terminar la sesión |
| `charla_libre` | — | Cualquier otra cosa → va al LLM |

Las intenciones críticas se reconocen con expresiones regulares (rápido y predecible). Las no críticas pasan por el LLM de diálogo solo si el contexto lo permite.

---

### 3.4 `bufit/voz/transcripcion` — lo que dijo el jugador

Lo publica **escucha**. Lo consume intenciones.

```json
{
  "ts": 1762262400.12,
  "texto": "te toca",
  "idioma": "es",
  "conf": 0.88,
  "duracion": 0.9
}
```

---

### 3.5 `bufit/vision/mesa/tablero` — estado visual de la mesa (retenido)

Lo publica **visión-mesa**. Lo consumen orquestador y estado-partida.

```json
{
  "ts": 1762262400.12,
  "fichas": [{"valor": "6-3", "x": 0.42, "y": 0.55, "giro": 2.1}],
  "extremos": [6, 5],
  "conf": 0.94
}
```

`x`, `y` son coordenadas normalizadas (0–1) relativas a la zona de juego.

---

### 3.6 `bufit/vision/mesa/jugada` — ficha detectada en mesa

Lo publica **visión-mesa**. Lo consume orquestador.

```json
{"ts": 1762262400.12, "ficha": "6-3", "extremo": "izq", "accion": "puesta", "conf": 0.92}
```

`accion`: `puesta` | `retirada`

---

### 3.7 `bufit/vision/atril/mano` — fichas en el atril de Bufit (retenido)

Lo publica **visión-atril**. Lo consume orquestador (y nadie más).  
**⚠️ No sale hacia módulos de salida. No se muestra en pantalla con valor.**

```json
{
  "ts": 1762262400.12,
  "posiciones": {"0": "6-3", "1": "5-5", "2": "4-0"},
  "conf": {"0": 0.99, "1": 0.98, "2": 0.91}
}
```

---

### 3.8 `bufit/pantalla/set` — orden a la pantalla

Lo publica **orquestador**. Lo obedece cara-pantalla.

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

`ojos`: `espera` | `atento` | `pensando` | `sorprendido` | `contento` | `dudoso` | `dormido`

---

### 3.9 `bufit/voz/set` — orden de habla

Lo publica **orquestador**. Lo obedece voz.

```json
{
  "ts": 1762262400.12,
  "texto": "Juego el seis tres por la izquierda",
  "idioma": "es",
  "tono": "alegre",
  "velocidad": 1.0,
  "prioridad": "normal"
}
```

`prioridad`: `normal` | `urgente` (se salta la cola) | `relleno` (se descarta si llega otra)

---

## 4. Interfaces REST (síncronas)

Solo para cuando el que llama **no puede continuar sin la respuesta**. Todo lo demás es MQTT.

| Servicio | Puerto externo | Llama | Funciones Must |
|----------|---------------|-------|---------------|
| motor-reglas | 8001 | orquestador | F2.3, F2.9, F3.5, F3.6, F4.1, F5.8, F10.1, F10.2 |
| selector-jugada | 8002 | orquestador | F4.2 |
| perfil | 8003 | orquestador | — (no es Must en MVP) |
| diálogo | 8004 | orquestador | F2.4, F4.3, F8.4, F10.3 |

**motor-reglas** es determinista. Sin azar, sin IA. Es la autoridad del juego:
- `POST /jugadas_legales` → lista de movimientos posibles
- `POST /es_legal` → ¿esta jugada es válida?
- `POST /aplicar` → aplica jugada y devuelve estado nuevo (no modifica el que recibe)
- `POST /fin_partida` → ¿ha acabado?
- `POST /puntuacion` → marcador final
- `GET /parametros/{juego}` → configuración del juego

**selector-jugada**: recibe jugadas legales + nivel + estado público (sin la mano del jugador).  
`POST /elegir` → `{"jugada": ..., "motivo": "azar"}`

**diálogo**: nunca recibe el estado completo. Solo el resumen. Nunca decide jugadas.

---

## 5. Temas MQTT resumen

| Tema | Publica | Retenido | QoS |
|------|---------|----------|-----|
| `bufit/vision/mesa/tablero` | visión-mesa | ✓ | 0 |
| `bufit/vision/mesa/jugada` | visión-mesa | — | 0 |
| `bufit/vision/mesa/ocupada` | visión-mesa | ✓ | 0 |
| `bufit/vision/mesa/presencia` | visión-mesa | ✓ | 0 |
| `bufit/vision/atril/mano` | visión-atril | ✓ | 0 |
| `bufit/vision/atril/dedo` | visión-atril | — | 0 |
| `bufit/voz/transcripcion` | escucha | — | 0 |
| `bufit/voz/jugador_habla` | escucha | — | 0 |
| `bufit/intencion` | intenciones | — | 1 |
| `bufit/estado/partida` | estado-partida | ✓ | 1 |
| `bufit/estado/resumen` | estado-partida | ✓ | 1 |
| `bufit/pantalla/set` | orquestador | — | 1 |
| `bufit/voz/set` | orquestador | — | 1 |
| `bufit/voz/parar` | orquestador | — | 1 |
| `bufit/<modulo>/online` | cada módulo | ✓ | 1 |

---

## 6. Restricciones de privacidad de las fichas

Bufit no hace trampas. Para garantizarlo:

1. **`visión-atril`** publica la mano de Bufit solo en `bufit/vision/atril/mano` (retenido, solo orquestador).
2. **`estado/partida`** incluye `mano_bufit` pero este topic **nunca llega a módulos de salida**.
3. **`estado/resumen`** no lleva manos. Es lo único que recibe `diálogo`.
4. **`selector-jugada`** recibe `jugadas_legales` + `estado_publico` (sin manos del jugador).

Si en una revisión de código ves que un módulo de salida accede a `mano_bufit`, es un bug de diseño.

---

## 7. Interacción tipo de un turno del jugador

```
orquestador → voz/set         "Es tu turno"
orquestador → pantalla/set    ojos=atento, indicador de fichas
              [jugador habla]
escucha     → voz/transcripcion  "te toca"
intenciones → intencion         tipo=he_terminado
orquestador → (espera visión de mesa)
visión-mesa → vision/mesa/jugada  ficha=3-6, extremo=izq, accion=puesta
orquestador → motor-reglas REST  POST /es_legal
              [respuesta: legal=true]
orquestador → motor-reglas REST  POST /aplicar
              [respuesta: nuevo estado]
estado-partida ← (orquestador actualiza estado)
estado-partida → estado/partida  (publicar nuevo estado retenido)
orquestador → diálogo REST      POST /narrar_jugada (si es turno Bufit después)
```

---

*Documento generado a partir de `herramientas/matriz.csv` y `contratos/`. Para cualquier discrepancia, los contratos en `contratos/` son la fuente de verdad.*
