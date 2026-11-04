# Diálogo

Conversa, explica reglas, narra las jugadas y comenta. Es el modelo de lenguaje.

## Lo que NO hace

**No decide jugadas. No valida legalidad. No ve ninguna mano.** Solo recibe el resumen del estado y devuelve texto.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F0.7 | Generar una respuesta conversacional | F | 1 | Should |
| F2.4 | Explicar cómo preparar la partida | F | 1 | Must |
| F3.7 | Comentar la jugada del jugador | F | 1 | Could |
| F4.3 | Narrar la jugada de Bufit | F | 1 | Must |
| F6.2 | Reconducir la conversación al juego | F | 1 | Could |
| F6.3 | Filtrar temas inapropiados | NF | 1 | Should |
| F7.2 | Explicar una regla del juego | F | 1 | Should |
| F7.4 | Generar una pista sin ver la mano del jugador | F | 1 | Could |
| F8.4 | Comunicar la incidencia con tacto | F | 1 | Must |
| F9.5 | Resumir cómo iba la partida | F | 1 | Could |
| F10.3 | Anunciar el resultado con deportividad | F | 1 | Must |
| F10.4 | Comentar el desarrollo de la partida | F | 2 | Won't |
| F10.5 | Explicar el recuento ficha a ficha | F | 1 | Could |
| F13.2 | Despedirse | F | 1 | Should |

**4 de estas 14 son *Must***: sin ellas no se puede jugar una partida.

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
