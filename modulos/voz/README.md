# Voz

Convierte texto en habla y se calla en cuanto el jugador empieza a hablar.

## Lo que NO hace

No decide qué decir.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.8 | Sintetizar y reproducir voz | F | 1 | Must |
| F0.9 | Interrumpir la locución en curso | F | 1 | Should |
| F0.10 | Reproducir una frase de relleno | NF | 1 | Could |
| F6.5 | Ajustar el ritmo de la locución al jugador | NF | 2 | Won't |

**1 de estas 4 son *Must***: sin ellas no se puede jugar una partida.

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
