# Cómo trabajamos en Bufit

Somos nueve personas tocando catorce módulos a la vez. Estas reglas existen para que eso no acabe en caos.

## 1 · El contrato manda

Antes de escribir código, lee `contratos/`. Ahí está lo que tu módulo recibe y lo que debe publicar.

**Si necesitas cambiar un contrato**, no lo cambies y ya: abre un pull request **solo con el cambio del contrato**, avisa en clase y espera a que se apruebe. Un contrato roto deja a varias personas tiradas sin que se enteren.

## 2 · Una rama por función

```bash
git switch -c vision-mesa/F0.12-leer-tablero
```

El patrón es `<modulo>/<codigo>-<descripcion-corta>`.

`main` está protegida: no se puede empujar directamente.

## 3 · Commits en castellano y en presente

```
Añade lectura de extremos de la cadena
Corrige el recuento de puntos en fichas dobles
```

No: `cambios`, `arreglos varios`, `asdf`.

## 4 · Pull request y revisión

Cuando acabes, abre un pull request contra `main` y pide revisión **al segundo de tu módulo**. Revisar no es buscar fallos: es asegurarse de que hay dos personas que entienden ese código.

El pull request se fusiona cuando está aprobado y `docker compose up` sigue funcionando.

## 5 · Prueba lo tuyo sin el resto

No esperes a que los demás terminen. Mira `simuladores/`:

```bash
# tu módulo escucha → le mandas mensajes falsos
mosquitto_pub -h localhost -t 'bufit/vision/atril/dedo' -m '{"ts":0,"posicion":2}'

# tu módulo publica → compruebas lo que sale
mosquitto_sub -h localhost -t 'bufit/#' -v

# tu módulo responde preguntas → lo llamas directamente
curl -X POST http://localhost:8001/jugadas_legales -H 'Content-Type: application/json' -d @ejemplo.json
```

## 6 · Estructura de un módulo

```
modulos/mi-modulo/
├── Dockerfile
├── requirements.txt
├── README.md          ← qué hace, qué funciones cubre, cómo probarlo
├── src/
└── tests/
```

Mira `modulos/motor-reglas/` si es un servicio REST, o `modulos/registro/` si es un suscriptor MQTT.

## 7 · Qué no se sube nunca

Repositorio **público**:

- Grabaciones de voz, fotos o vídeos de personas reales.
- Datos de jugadores o perfiles con nombres.
- Claves, tokens o contraseñas. Van en un `.env` que está en el `.gitignore`.
- Modelos pesados. Se descargan al arrancar, no se versionan.

## 8 · Si te atascas

Abre un issue con la etiqueta `ayuda`, describe lo que has probado y pega las trazas. Mejor perder diez minutos preguntando que dos días atascado.
