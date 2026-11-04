# Selector de jugada

Elige una jugada entre las legales según el nivel de dificultad. Primero al azar, después con un modelo entrenado.

## Lo que NO hace

**Nunca recibe las fichas del jugador.** No comprueba legalidad: confía en la lista que le llega.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F4.2 | Elegir una jugada según el nivel | F | 1 (azar), 3 (modelo) | Must |
| F11.2 | Evaluar el desempeño del jugador | F | 2 | Won't |
| F11.3 | Ajustar el nivel de juego | F | 2 | Won't |

**1 de estas 3 son *Must***: sin ellas no se puede jugar una partida.

## Contrato

Lee [`contratos/`](../../contratos/) antes de escribir nada. Ahí está exactamente lo que recibes y lo que tienes que publicar.

Este módulo es de tipo **REST**. Como ejemplo de estructura, mira `modulos/motor-reglas/`.

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
