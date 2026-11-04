# Motor de reglas

**La autoridad del juego.** Dice qué jugadas son legales, si una jugada vale, cuándo se acaba la partida y cuántos puntos hay.

Determinista: sin azar y sin inteligencia artificial. Dado el mismo estado, siempre responde lo mismo. Es el módulo más fácil de probar de todo el sistema y el que no puede fallar nunca.

## Lo que NO hace

- **No elige** la jugada. Eso es del selector.
- **No habla.** Devuelve códigos de motivo, no frases.
- **No sabe** que existen cámaras, ni micrófonos, ni una partida en marcha.

## Funciones

| Código | Función | Prioridad |
|---|---|---|
| F2.3 | Cargar los parámetros del juego elegido | Must |
| F2.9 | Determinar quién inicia la partida | Must |
| F3.5 | Validar la legalidad de una jugada | Must |
| F3.6 | Aplicar una jugada al estado | Must |
| F4.1 | Obtener las jugadas legales de Bufit | Must |
| F5.8 | Pasar turno por imposibilidad de jugar | Must |
| F7.3 | Calcular información pública para pistas | Could |
| F10.1 | Detectar el fin de la partida | Must |
| F10.2 | Calcular la puntuación final | Must |

Contrato: [`contratos/rest-endpoints.md`](../../contratos/rest-endpoints.md)

## Añadir un juego nuevo

1. Crea `src/juegos/<nombre>.py` con una clase que herede de `Juego`.
2. Implementa los cinco métodos del contrato.
3. Añade `src/juegos/<nombre>.json` con sus parámetros.
4. Regístralo en `src/juegos/__init__.py`.

**No toques nada fuera de esa carpeta.** Si añadir un juego te obliga a cambiar `app.py`, el diseño está mal y hay que hablarlo.

## Probarlo

```bash
cd modulos/motor-reglas
pip install -r requirements.txt
pytest -q                    # las pruebas unitarias
uvicorn src.app:app --reload # el servicio en http://localhost:8000/docs
```

Con Docker:

```bash
docker compose up -d motor-reglas
curl http://localhost:8001/salud
```
