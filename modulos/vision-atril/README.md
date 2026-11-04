# Visión de atril

Lee las fichas de Bufit en el atril con la cámara 2 y sigue el dedo del jugador por encima.

## Lo que NO hace

No ve la mesa. No decide qué ficha jugar. Su lectura **no sale del núcleo** ni se muestra en pantalla con su valor.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.15 | Leer el contenido del atril | F | 1 | Must |
| F0.16 | Localizar el atril mediante marcadores | NF | 2 | Won't |
| F4.5 | Seguir la posición del dedo sobre el atril | F | 2 | Won't |
| F5.3 | Detectar una ficha nueva en el atril | F | 1 | Must |
| F5.4 | Detectar una ficha colocada al revés | F | 1 | Could |

**2 de estas 5 son *Must***: sin ellas no se puede jugar una partida.

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
