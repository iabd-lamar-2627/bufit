# Visión de mesa

Lee la mesa con la cámara 1: la cadena de fichas, sus extremos y cuándo se coloca una nueva. También detecta si hay una mano encima y si alguien se ha sentado.

## Lo que NO hace

No mira nunca la zona del jugador. No decide si una jugada es legal. No toca el estado de la partida.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.12 | Leer el estado de la mesa | F | 1 | Must |
| F0.13 | Detectar una mano sobre la zona de juego | F | 1 | Must |
| F0.14 | Comprobar las condiciones de iluminación | NF | 1 | Could |
| F1.1 | Detectar la presencia de una persona | F | 1 | Should |
| F2.7 | Comprobar que la zona de juego está despejada | F | 1 | Could |
| F3.2 | Detectar que se ha colocado una ficha nueva | F | 1 | Must |
| F5.6 | Contar las fichas del pozo | F | 2 | Won't |
| F8.2 | Detectar que la cadena se sale del campo | F | 1 | Must |
| F8.3 | Detectar una ficha ilegible o mal colocada | F | 1 | Should |
| F9.6 | Comprobar que la mesa no ha cambiado | F | 2 | Won't |

**4 de estas 10 son *Must***: sin ellas no se puede jugar una partida.

## Contrato

Lee [`contratos/`](../../contratos/) antes de escribir nada. Ahí está exactamente lo que recibes y lo que tienes que publicar.

Este módulo es de tipo **suscriptor**. Como ejemplo de estructura, mira `modulos/registro/`.

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
