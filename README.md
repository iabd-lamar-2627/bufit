# Bufit

**Un compañero de juegos de mesa con inteligencia artificial.**

Bufit se monta sobre la pantalla de un ordenador, mira la mesa con dos cámaras, escucha y habla, y juega una partida real de dominó contra una persona: ve las fichas, comprueba las jugadas, decide la suya, la narra en voz alta y conversa mientras tanto.

Proyecto del Curso de Especialización en Inteligencia Artificial y Big Data · IES La Mar, Xàbia · 2026-27.

📖 **Documentación del proyecto:** https://iabd-lamar-2627.github.io/bufit/

---

## Arranque rápido

```bash
git clone https://github.com/iabd-lamar-2627/bufit.git
cd bufit
docker compose up -d
```

Comprueba que el bus funciona:

```bash
# Terminal 1 · escuchar todo
docker compose exec broker mosquitto_sub -t 'bufit/#' -v

# Terminal 2 · publicar algo
docker compose exec broker mosquitto_pub -t 'bufit/prueba' -m 'hola'
```

Si en la primera terminal aparece `bufit/prueba hola`, ya tienes el sistema montado.

## Cómo está organizado

```
contratos/      Los temas MQTT y los endpoints REST. La fuente de verdad.
modulos/        Un contenedor por módulo. Cada uno con su carpeta y su README.
simuladores/    Mensajes falsos para probar tu módulo sin el resto del sistema.
pruebas/        Pruebas de integración.
hardware/       Piezas 3D y montaje.
herramientas/   Scripts de apoyo del proyecto.
```

## Antes de escribir una línea de código

1. Lee **`contratos/`**. Ahí está lo que tu módulo recibe y lo que tiene que publicar.
2. Lee el **README de tu módulo**, que dice qué funciones te tocan.
3. Mira **`modulos/motor-reglas/`** (servicio REST) o **`modulos/registro/`** (suscriptor MQTT) como ejemplo de cómo se estructura un módulo.

## Cómo se trabaja

- `main` está protegida. Nadie empuja directamente.
- Una rama por función: `vision-mesa/F0.12-leer-tablero`.
- Un issue por función. El título empieza por el código: `F0.12 · Leer el estado de la mesa`.
- Pull request, revisión del segundo del módulo, y se fusiona.

Está todo explicado en [CONTRIBUTING.md](CONTRIBUTING.md).

## Qué NO se sube

Este repositorio es **público**:

- Ni grabaciones de voz, ni fotos, ni vídeos de personas reales.
- Ni datos de jugadores, ni perfiles con nombres.
- Ni claves, ni tokens, ni contraseñas.
- Ni modelos pesados: van fuera del repositorio y se descargan al arrancar.

Para las pruebas, usa el dominó del aula y manos del propio equipo, sin caras.
