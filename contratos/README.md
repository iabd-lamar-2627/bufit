# Contratos

**Esta carpeta es la fuente de verdad del proyecto.**

Un contrato es el acuerdo sobre qué mensajes circulan y qué forma tienen. Mientras se respete, cada módulo se puede programar y probar por separado, sin esperar a nadie.

- [`mqtt-temas.md`](mqtt-temas.md) · los temas del bus y el contenido de cada mensaje
- [`rest-endpoints.md`](rest-endpoints.md) · los servicios que responden a preguntas
- [`esquemas/`](esquemas/) · el JSON Schema de cada mensaje, para validarlo automáticamente

## Reglas

1. **Un contrato no se cambia por libre.** Si tu módulo necesita un campo nuevo, se habla en clase y se cambia aquí primero, con pull request.
2. **Antes de publicar un mensaje, valídalo** contra su esquema. Hay un ayudante en `simuladores/`.
3. **Si no está en el contrato, no existe.** Nadie debe depender de un campo que alguien publica "por si acaso".

## Las tres reglas de oro del sistema

Están aquí porque afectan a todos los contratos:

1. **La visión propone, las reglas validan, el estado confirma.** Ningún módulo de visión modifica el estado de la partida.
2. **El selector de jugada nunca recibe las fichas del jugador.** Mira la firma de `/elegir`: no hay forma de colárselas.
3. **El módulo de diálogo nunca decide ni valida una jugada.** Solo recibe un resumen y devuelve texto.
