# Estado de partida

La única fuente de verdad: mano de Bufit, cadena, turno, pozo y marcador. Guarda y recupera.

## Lo que NO hace

No decide nada. Solo guarda y entrega lo que le confirman.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.17 | Publicar el estado de la partida | F | 1 | Must |
| F0.18 | Guardar y recuperar el estado | F | 1 | Should |
| F2.8 | Inicializar el estado de la partida | F | 1 | Must |
| F4.11 | Retirar la ficha jugada de la mano de Bufit | F | 1 | Must |
| F5.5 | Incorporar la ficha robada a la mano | F | 1 | Must |
| F5.7 | Llevar la cuenta del pozo | F | 1 | Must |
| F6.1 | Resumir el estado para la conversación | F | 1 | Should |
| F8.6 | Revertir una jugada no válida | F | 1 | Must |
| F9.2 | Pausar la partida | F | 1 | Should |
| F11.1 | Registrar las métricas de juego | F | 2 | Won't |
| F13.3 | Guardar una partida sin terminar | F | 2 | Won't |

**6 de estas 11 son *Must***: sin ellas no se puede jugar una partida.

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
