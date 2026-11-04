# Juegos de pantalla

Cálculo mental y palabras, jugados por voz. Lógica propia e independiente del dominó.

## Lo que NO hace

No usa el motor de reglas ni las cámaras.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F12.1 | Listar los juegos de pantalla | F | 1 | Should |
| F12.2 | Generar un reto de cálculo mental | F | 1 | Should |
| F12.3 | Generar un reto de palabras | F | 1 | Could |
| F12.5 | Evaluar la respuesta hablada | F | 1 | Should |
| F12.6 | Dar la respuesta y comentarla | F | 1 | Should |
| F12.7 | Ajustar la dificultad del reto | F | 1 | Could |
| F12.8 | Resumir la sesión de juego | F | 1 | Could |

**0 de estas 7 son *Must***: sin ellas no se puede jugar una partida.

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
