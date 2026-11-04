# Pruebas

| Dónde | Qué se prueba | Quién |
|---|---|---|
| `modulos/<x>/tests/` | Lo de cada módulo por separado | Su responsable |
| `pruebas/` | Que los módulos encajan entre sí | Todo el equipo |

Las pruebas de integración salen de las cifras del documento de requisitos: **una prueba por cifra**. La lista completa está en la documentación del proyecto.

Las más importantes, las que no dependen de ningún módulo concreto:

- **RS1** · Ninguna espera supera 800 ms en silencio.
- **RS2** · Ningún mensaje del bus ni ninguna llamada REST contiene las fichas del jugador.
- **RS4** · Parar cada contenedor uno a uno durante una partida y comprobar que Bufit lo dice y no se bloquea.
- **RS8** · Jugar una partida entera con el cable de red desenchufado.
