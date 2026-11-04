# Simuladores

Mensajes falsos para probar tu módulo **sin el resto del sistema**. Es lo que permite que nueve personas avancen a la vez sin esperarse.

## Ver lo que pasa por el bus

```bash
mosquitto_sub -h localhost -t 'bufit/#' -v
```

Déjalo abierto en una terminal mientras trabajas. Con `-t 'bufit/vision/#'` filtras solo lo tuyo.

## Mandarte mensajes a mano

```bash
mosquitto_pub -h localhost -t 'bufit/vision/atril/dedo' -m '{"ts":0,"posicion":2}'
```

## Un turno entero sin cámaras ni micrófono

```bash
./partida_de_prueba.sh
```

Publica la secuencia completa de un turno: el jugador coloca una ficha, avisa,
Bufit lee la mesa, piensa y señala la suya. Si tu módulo reacciona como debe,
funciona. Y como es un fichero, se repite igual todas las veces: eso es un
caso de prueba.

## Llamar a un servicio REST

```bash
curl -s -X POST http://localhost:8001/jugadas_legales \
  -H 'Content-Type: application/json' \
  -d '{"estado":{"juego":"domino","cadena":["3-3","3-6"],"turno":"bufit"},"mano":["6-1","5-5"]}' | jq
```
