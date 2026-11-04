# Perfil

Guarda el mote del jugador, su nivel, su idioma y sus partidas, en un JSON local.

## Lo que NO hace

No sale de la máquina. En sesión anónima no se le llama en ningún momento.

## Funciones

| Código | Función | Tipo | Fase | Prioridad |
|---|---|---|---|---|
| F1.4 | Buscar un perfil por mote | F | 2 | Won't |
| F1.5 | Crear un perfil nuevo | F | 2 | Won't |
| F10.6 | Guardar el resultado en el histórico | F | 2 | Won't |
| F11.7 | Guardar el nivel alcanzado | F | 2 | Won't |

**0 de estas 4 son *Must***: sin ellas no se puede jugar una partida.

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
