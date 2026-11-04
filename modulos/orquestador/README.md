# Orquestador

La máquina de estados de la sesión: espera, saludo, preparación, turnos, pausa, incidencias y despedida. Decide qué módulo actúa en cada momento.

## Lo que NO hace

No conoce las reglas de ningún juego. No procesa imágenes ni audio.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.20 | Vigilar la disponibilidad de los módulos | NF | 1 | Should |
| F0.21 | Informar al jugador de una avería | NF | 1 | Should |
| F1.2 | Abrir la sesión y saludar | F | 1 | Must |
| F1.3 | Solicitar la identificación del jugador | F | 2 | Won't |
| F1.6 | Fijar y confirmar el idioma de la sesión | F | 2 | Won't |
| F1.7 | Volver a la espera por falta de respuesta | F | 1 | Could |
| F2.1 | Listar los juegos disponibles | F | 1 | Should |
| F2.5 | Comprobar el número de fichas del atril | F | 1 | Must |
| F2.6 | Solicitar la recolocación de fichas ilegibles | F | 1 | Should |
| F2.10 | Anunciar el comienzo de la partida | F | 1 | Must |
| F3.1 | Anunciar el turno del jugador | F | 1 | Must |
| F3.3 | Confirmar el fin del turno del jugador | F | 1 | Must |
| F3.4 | Preguntar al jugador si ha terminado | F | 1 | Should |
| F3.9 | Solicitar una lectura de mayor calidad | F | 1 | Must |
| F4.7 | Confirmar la ficha señalada | F | 2 | Won't |
| F4.8 | Indicar la ficha de viva voz | F | 1 | Must |
| F4.9 | Verificar que se ha colocado la ficha indicada | F | 1 | Must |
| F4.10 | Detectar que el jugador no mueve la ficha | F | 1 | Should |
| F5.1 | Detectar que Bufit no tiene jugada posible | F | 1 | Must |
| F5.2 | Solicitar el robo de una ficha | F | 1 | Must |
| F6.4 | Pedir que repita lo dicho | F | 1 | Must |
| F7.5 | Confirmar que la explicación ha quedado clara | F | 1 | Could |
| F8.1 | Detectar una discrepancia entre la mesa y el estado | F | 1 | Must |
| F8.5 | Proponer la corrección concreta | F | 1 | Must |
| F8.7 | Aceptar la versión del jugador | F | 1 | Must |
| F8.8 | Ofrecer ayuda tras incidencias repetidas | F | 2 | Won't |
| F9.1 | Detectar inactividad prolongada | F | 1 | Could |
| F9.3 | Confirmar la pausa al jugador | F | 1 | Should |
| F9.4 | Reanudar la partida | F | 1 | Should |
| F9.7 | Cerrar la partida por ausencia prolongada | F | 1 | Could |
| F10.7 | Ofrecer la revancha | F | 1 | Should |
| F11.4 | Ajustar el ritmo de la partida | F | 2 | Won't |
| F11.5 | Respetar la negativa a recibir ayuda | F | 2 | Won't |
| F11.6 | Detectar signos de cansancio | F | 3 | Won't |
| F13.1 | Detectar el fin de la sesión | F | 1 | Should |
| F13.4 | Volver al estado de espera | F | 1 | Should |

**14 de estas 36 son *Must***: sin ellas no se puede jugar una partida.

## Contrato

Lee [`contratos/`](../../contratos/) antes de escribir nada. Ahí está exactamente lo que recibes y lo que tienes que publicar.

Este módulo es de tipo **mixto**. Como ejemplo de estructura, mira `modulos/motor-reglas/` (REST) y `modulos/registro/` (MQTT): usa los dos.

## Por hacer

- [ ] `Dockerfile` y `requirements.txt`
- [ ] Esqueleto que conecta y anuncia su presencia
- [ ] Las funciones *Must*
- [ ] Pruebas
- [ ] Descomentar su bloque en `docker-compose.yml`

## Probarlo sin el resto del sistema

```bash
# ver lo que publicas
mosquitto_sub -h localhost -t 'bufit/#' -v

# mandarte mensajes falsos
mosquitto_pub -h localhost -t 'bufit/...' -m '{"ts":0}'
```
