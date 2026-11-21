# Prototipo · Ojos de Bufit

Página web a pantalla completa con los ojos de Bufit. Recibe los estados por MQTT (`bufit/pantalla/set` → `ojos`):
`espera`, `atento`, `pensando`, `sorprendido`, `contento`, `dudoso`, `dormido`, `escuchando`, `concentrado`, `tu_turno`, `repiteme`, `busca_carta` y `escaneando`.

- `escuchando` (8) levanta una ceja al entrar y sostiene la mirada. Envía `mirar` junto con el estado para orientarla hacia quien habla.
- `concentrado` (9) entorna los ojos, baja y acerca las cejas y dirige la mirada hacia la zona de juego.

- `tu_turno` (T) levanta ambas cejas para dar paso al jugador.
- `repiteme` (R) inclina una ceja y parpadea para pedir que repitan.
- `busca_carta` (B) mira a la bandeja un momento y vuelve a levantar la vista.
- `escaneando` (S) recorre la bandeja sin detenerse en el centro y hace pausas breves en los extremos hasta que llega otro estado. Envía `{"ojos":"escaneando"}` al empezar a evaluar las cartas o fichas y cambia de estado cuando Bufit termine.

## Probarla

Abre `index.html` en el navegador (doble clic). No necesita servidor ni instalar nada.

| Control | Qué hace |
|---|---|
| Botones o teclas 1–9 | Cambian de estado |
| T / R / B / S | Tu turno / Repíteme / Busca la carta / Escaneando |
| M | La mirada sigue al ratón (simula la cámara) |
| Espacio | Parpadea |
| H | Oculta los botones (para la demo) |
| F | Pantalla completa |

Sola ya parpadea cada pocos segundos y, en `espera` y `atento`, mueve un poco la mirada para parecer viva.

## Cómo la controlarán las demás piezas

La página expone tres funciones en `window.bufit`:

```js
bufit.estado("pensando")   // cambia de estado
bufit.mirar(0.5, -0.2)     // mirada: x e y entre -1 y 1 (izquierda/arriba → derecha/abajo)
bufit.parpadear()
```

El siguiente paso es conectarla al orquestador (por WebSocket o MQTT) para que esas llamadas lleguen desde la voz y la cámara.

## Cómo está hecha

Cada ojo tiene tres piezas:

- **Ceja**: un dibujo SVG con forma propia en cada ojo. No son simétricas ni están centradas: van desplazadas hacia fuera, como en una cara real. Cambian de altura, separación, inclinación y tamaño según el estado, acompañan a la mirada y bajan un poco al parpadear.
- **Globo**: el óvalo blanco con brillo. Dentro va la **pupila**, con su reflejo, que es lo que se mueve al mirar.
- **Párpados**: no son rectángulos encima del ojo, sino una máscara que recorta el globo. Así el brillo sigue el contorno y los cambios de estado se animan. El de arriba baja e inclina (entornar, dudar); el de abajo sube en curva (sonreír).

Cada estado solo cambia variables CSS, por eso las transiciones entre estados son suaves:

| Variable | Qué controla |
|---|---|
| `--cy`, `--cx` | Altura de la ceja y separación hacia fuera (negativo: hacia el centro) |
| `--cr`, `--cs` | Inclinación de la ceja (positivo: ceño) y su tamaño |
| `--px`, `--py` | Hacia dónde mira la pupila por el estado |
| `--ps`, `--pr` | Cuánto baja el párpado superior y su inclinación |
| `--sonrisa` | Cuánto sube el párpado inferior curvo |
| `--mx`, `--my` | Hacia dónde mira la persona (ratón, cámara o MQTT), de -1 a 1 |

Los gestos de ceja al entrar en un estado (subir, inclinar) se hacen con animaciones de JavaScript (`gestoCeja`).

## Conexión MQTT

1. Arranca el broker: `docker compose up -d mqtt` (desde `prototipos/`).
2. Abre `index.html`. Abajo a la derecha verás «MQTT: conectado» en verde.
3. Prueba a mandarle un estado desde el terminal:

```
docker compose exec mqtt mosquitto_pub -t bufit/pantalla/set -m '{"ojos":"contento"}'
docker compose exec mqtt mosquitto_pub -t bufit/pantalla/set -m '{"mirar":{"x":-0.8,"y":0}}'
docker compose exec mqtt mosquitto_pub -t bufit/pantalla/set -m '{"parpadear":true}'
```

Tema: `bufit/pantalla/set`. Mensajes en JSON con las claves `ojos`, `mirar` y `parpadear` (se pueden combinar).
Broker en otro equipo: `index.html?mqtt=ws://IP:9001`.
`mqtt.min.js` es la librería mqtt.js 5.10.1 copiada aquí para que funcione sin internet.
