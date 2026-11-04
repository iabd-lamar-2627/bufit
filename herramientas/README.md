# Herramientas

## `crear_issues.py`

Crea en GitHub las etiquetas del proyecto y **un issue por función**, leyendo `matriz.csv`.

```bash
python3 herramientas/crear_issues.py --repo iabd-lamar-2627/bufit --simular   # ver qué haría
python3 herramientas/crear_issues.py --repo iabd-lamar-2627/bufit             # hacerlo
python3 herramientas/crear_issues.py --repo iabd-lamar-2627/bufit --solo-fase 1
```

Es **idempotente**: si un issue con ese código ya existe, no lo duplica. Se puede volver a lanzar cuando se añadan funciones nuevas.

Necesita [`gh`](https://cli.github.com/) autenticado.

## `matriz.csv`

La matriz de trazabilidad: caso de uso, función, módulo, tipo, fase y prioridad de las 117 funciones.

**Ojo con tener dos registros:** el seguimiento vivo (quién lo hace, por dónde va) son los issues de GitHub, no este fichero. Aquí solo está el análisis, que no cambia a diario.
