# Documentación del proyecto

**Los documentos de análisis no están en este repositorio.** Viven en el repositorio de la web, que es quien los publica.

👉 **Léelos aquí: [iabd-lamar-2627.github.io/bufit](https://iabd-lamar-2627.github.io/bufit/)**

| Documento | Para qué | Enlace |
|---|---|---|
| En pocas palabras | Qué es Bufit, en lenguaje llano | [leer](https://iabd-lamar-2627.github.io/bufit/) |
| El proyecto | Descripción completa: hardware, fases, decisiones, riesgos | [leer](https://iabd-lamar-2627.github.io/bufit/proyecto/) |
| Casos de uso | Los 13 casos de uso, paso a paso | [leer](https://iabd-lamar-2627.github.io/bufit/casos-de-uso/) |
| Funciones | Las 117 funciones, con su módulo, entradas y salidas | [leer](https://iabd-lamar-2627.github.io/bufit/funciones/) |
| Requisitos | Las 94 fichas de fase 1, con sus siete apartados | [leer](https://iabd-lamar-2627.github.io/bufit/requisitos/) |
| Prioridades | La clasificación MoSCoW y los tres hitos | [leer](https://iabd-lamar-2627.github.io/bufit/prioridades/) |
| Arquitectura | Los 14 módulos y cómo se hablan | [leer](https://iabd-lamar-2627.github.io/bufit/arquitectura/) |

## Por qué están allí y no aquí

Para no tener lo mismo en dos sitios. La separación es esta:

| | Dónde | Por qué |
|---|---|---|
| **Documentos de análisis** | Repositorio de la web | Se publican solos, se leen cómodos y se enlazan entre sí |
| **Contratos** | [`contratos/`](../contratos/), aquí | Cambian con el código y tienen que ir en el mismo commit |
| **Matriz de funciones** | [`herramientas/matriz.csv`](../herramientas/matriz.csv), aquí | Es de donde salen los issues |
| **Quién hace qué y por dónde va** | Los [issues](https://github.com/iabd-lamar-2627/bufit/issues) | Se actualizan solos al cerrar un pull request |

## Para corregir un documento

Se edita en el repositorio de la web, en `docs/bufit/`. Cada push a `main` reconstruye la web automáticamente.

[github.com/iabd-lamar-2627/iabd-lamar-2627.github.io/tree/main/docs/bufit](https://github.com/iabd-lamar-2627/iabd-lamar-2627.github.io/tree/main/docs/bufit)
