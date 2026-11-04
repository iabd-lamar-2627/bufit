# Escucha

Escucha de forma continua, limpia el ruido, cancela el eco de la propia voz de Bufit y transcribe.

## Lo que NO hace

No interpreta lo que significa la frase: eso es del módulo de intenciones.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.1 | Capturar y transcribir la voz | F | 1 | Must |
| F0.2 | Detectar el idioma hablado | F | 2 | Won't |
| F0.3 | Aislar la voz del ruido de fondo | NF | 1 | Should |
| F0.4 | Cancelar el eco de la propia voz | NF | 1 | Should |
| F0.5 | Detectar que el jugador empieza a hablar | F | 1 | Should |

**1 de estas 5 son *Must***: sin ellas no se puede jugar una partida.

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
