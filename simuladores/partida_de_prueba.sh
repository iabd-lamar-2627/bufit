#!/usr/bin/env bash
# Un turno completo de Bufit, sin camaras, sin microfono y sin jugador.
#
#   ./partida_de_prueba.sh [host]
#
# Deja abierto en otra terminal:
#   mosquitto_sub -h localhost -t 'bufit/#' -v

set -euo pipefail
H="${1:-localhost}"
P() { mosquitto_pub -h "$H" -t "$1" -m "$2" ${3:+-r}; echo "  -> $1"; }
T() { date +%s.%N; }

echo "== El atril de Bufit (retenido)"
P 'bufit/vision/atril/mano' \
  "{\"ts\":$(T),\"posiciones\":{\"0\":\"6-3\",\"1\":\"5-5\",\"2\":\"4-0\"},\"conf\":{\"0\":0.99,\"1\":0.98,\"2\":0.95}}" r
sleep 1

echo "== La mesa antes de la jugada (retenido)"
P 'bufit/vision/mesa/tablero' \
  "{\"ts\":$(T),\"fichas\":[{\"valor\":\"3-3\"}],\"extremos\":[3,3],\"conf\":0.95}" r
sleep 1

echo "== El jugador mete la mano"
P 'bufit/vision/mesa/ocupada' "{\"ts\":$(T),\"ocupada\":true}" r
sleep 2
P 'bufit/vision/mesa/ocupada' "{\"ts\":$(T),\"ocupada\":false}" r
sleep 1

echo "== Se ve la ficha nueva"
P 'bufit/vision/mesa/tablero' \
  "{\"ts\":$(T),\"fichas\":[{\"valor\":\"3-3\"},{\"valor\":\"3-6\"}],\"extremos\":[3,6],\"conf\":0.93}" r
P 'bufit/vision/mesa/jugada' \
  "{\"ts\":$(T),\"ficha\":\"3-6\",\"extremo\":\"der\",\"accion\":\"puesta\",\"conf\":0.93}"
sleep 1

echo "== El jugador dice que ha terminado"
P 'bufit/voz/transcripcion' "{\"ts\":$(T),\"texto\":\"te toca\",\"idioma\":\"es\",\"conf\":0.91}"
sleep 1
P 'bufit/intencion' "{\"ts\":$(T),\"tipo\":\"he_terminado\",\"params\":{},\"conf\":0.95}"
sleep 2

echo "== El dedo recorre el atril"
for i in 0 1 2; do
  P 'bufit/vision/atril/dedo' "{\"ts\":$(T),\"posicion\":$i}"
  sleep 0.7
done

echo
echo "Listo. Mira la otra terminal."
