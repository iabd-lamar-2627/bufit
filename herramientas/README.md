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

La matriz de trazabilidad: caso de uso, función, módulo, tipo, fase y prioridad de las 117 funciones. Separado por comas, para que GitHub lo muestre como tabla ordenable.

**Aquí solo está el análisis.** No lleva columnas de responsable ni de estado a propósito: el seguimiento vivo son los **issues**, que se actualizan solos al cerrar un pull request. Dos registros en paralelo siempre acaban descuadrados.

Este fichero solo se toca cuando **se añade o se quita una función**, y entonces se vuelve a lanzar `crear_issues.py`, que no duplica los que ya existen.
