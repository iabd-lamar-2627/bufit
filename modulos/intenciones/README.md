# Intenciones

Convierte una transcripción en una orden concreta, **por reglas y sin modelo de lenguaje**, para que las órdenes críticas sean rápidas y predecibles.

## Lo que NO hace

No genera respuestas. No ejecuta nada.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.6 | Clasificar la intención de una frase | F | 1 | Must |
| F7.1 | Clasificar el tipo de consulta | F | 1 | Should |

**1 de estas 2 son *Must***: sin ellas no se puede jugar una partida.

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
