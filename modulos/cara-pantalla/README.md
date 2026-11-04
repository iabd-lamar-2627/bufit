# Cara y pantalla

Los ojos, el indicador de ficha, el marcador, los menús y los retos.

## Lo que NO hace

No decide qué mostrar: obedece al orquestador. Nunca dibuja el valor de las fichas de Bufit, solo su posición.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.11 | Mostrar la expresión de los ojos | F | 1 | Must |
| F2.2 | Mostrar el menú de juegos | F | 1 | Could |
| F3.8 | Actualizar el marcador en pantalla | F | 1 | Should |
| F4.4 | Señalar en pantalla la ficha elegida | F | 1 | Must |
| F4.6 | Acompañar el dedo con el indicador | F | 2 | Won't |
| F12.4 | Mostrar el reto en pantalla | F | 1 | Should |

**2 de estas 6 son *Must***: sin ellas no se puede jugar una partida.

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
