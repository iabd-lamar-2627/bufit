#!/usr/bin/env python3
"""Crea en GitHub las etiquetas y un issue por funcion, desde la matriz.

    python3 herramientas/crear_issues.py --repo iabd-lamar-2627/bufit --simular
    python3 herramientas/crear_issues.py --repo iabd-lamar-2627/bufit

Necesita la herramienta `gh` autenticada. Es idempotente: si un issue con ese
codigo ya existe, no lo duplica.

Usa la API REST y no `gh issue create`, porque esta ultima va por GraphQL y
no esta disponible en todos los entornos.
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

MATRIZ = Path(__file__).parent / "matriz.csv"

MOD2DIR = {
    "Visión de mesa": "vision-mesa", "Visión de atril": "vision-atril",
    "Escucha": "escucha", "Intenciones": "intenciones", "Diálogo": "dialogo",
    "Voz": "voz", "Cara y pantalla": "cara-pantalla", "Orquestador": "orquestador",
    "Estado de partida": "estado-partida", "Motor de reglas": "motor-reglas",
    "Selector de jugada": "selector-jugada", "Perfil": "perfil",
    "Juegos de pantalla": "juegos-pantalla", "Registro": "registro",
}

COLOR_MODULO = {
    "vision-mesa": "8d6ea8", "vision-atril": "a98cc6", "escucha": "3f8a86",
    "intenciones": "5fb3ae", "dialogo": "2f6b47", "voz": "5b7fae",
    "cara-pantalla": "7fa3d0", "orquestador": "c98a2e", "estado-partida": "e0a458",
    "motor-reglas": "b03a2e", "selector-jugada": "d4654f", "perfil": "5a9c70",
    "juegos-pantalla": "8fbf9f", "registro": "9b9589",
}

COLOR_PRIORIDAD = {"must": "b60205", "should": "d93f0b",
                   "could": "fbca04", "wont": "cfd3d7"}

COLOR_FASE = {"1": "0e8a16", "2": "1d76db", "3": "c5def5"}


def gh(args, simular=False, capturar=True):
    if simular:
        print("  gh " + " ".join(args))
        return ""
    r = subprocess.run(["gh", *args], capture_output=capturar, text=True)
    if r.returncode != 0 and "already exists" not in (r.stderr or ""):
        print(f"  ! {r.stderr.strip()[:200]}", file=sys.stderr)
    return (r.stdout or "").strip()


def crear_etiquetas(repo, simular):
    print("Etiquetas")
    etiquetas = [("funcion", "ededed", "Función del catálogo"),
                 ("incidencia", "ee0701", "Algo no funciona"),
                 ("ayuda", "0075ca", "Atascado, hace falta una mano"),
                 ("nf", "bfd4f2", "Requisito no funcional")]
    for d, c in COLOR_MODULO.items():
        etiquetas.append((f"m:{d}", c, f"Módulo {d}"))
    for p, c in COLOR_PRIORIDAD.items():
        etiquetas.append((f"p:{p}", c, f"Prioridad {p}"))
    for f, c in COLOR_FASE.items():
        etiquetas.append((f"fase-{f}", c, f"Fase {f}"))

    for nombre, color, desc in etiquetas:
        gh(["label", "create", nombre, "--repo", repo, "--color", color,
            "--description", desc, "--force"], simular)
    print(f"  {len(etiquetas)} etiquetas")


def existentes(repo, simular):
    """Titulos de los issues que ya hay, por la API REST."""
    if simular:
        return set()
    salida = gh(["api", f"repos/{repo}/issues", "--paginate",
                 "-X", "GET", "-f", "state=all", "-q", ".[].title"])
    return {linea.split(" ·")[0].strip() for linea in salida.splitlines() if linea}


def cuerpo(fila):
    codigo, modulo = fila["Codigo"], MOD2DIR[fila["Modulo"]]
    return f"""**Módulo:** `{modulo}` · **Prioridad:** {fila['Prioridad']} · **Fase:** {fila['Fase']} · **Caso de uso:** {fila['CU']}

{fila['Funcion']}

### Antes de empezar

- [ ] He leído el contrato de mi módulo en [`contratos/`](../tree/main/contratos)
- [ ] He leído la ficha de requisitos de {codigo} en la documentación

### Criterios de aceptación

Sácalos de la ficha de requisitos y escríbelos aquí como una lista. Cada cifra
del apartado de rendimiento es una comprobación.

- [ ]
- [ ] Cumple el tiempo máximo de la ficha
- [ ] Gestiona los fallos previstos en la ficha
- [ ] Tiene prueba automática o procedimiento de prueba escrito

### Rama

```
{modulo}/{codigo}-descripcion-corta
```
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--simular", action="store_true", help="no crea nada, solo enseña")
    ap.add_argument("--solo-fase", default=None, help="por ejemplo 1")
    args = ap.parse_args()

    filas = list(csv.DictReader(MATRIZ.open(encoding="utf-8")))
    if args.solo_fase:
        filas = [f for f in filas if f["Fase"].startswith(args.solo_fase)]

    crear_etiquetas(args.repo, args.simular)

    ya = existentes(args.repo, args.simular)
    print(f"\nIssues ({len(filas)} funciones, {len(ya)} ya existen)")
    creados = 0
    for f in filas:
        codigo = f["Codigo"]
        if codigo in ya:
            continue
        titulo = f"{codigo} · {f['Funcion']}"
        prio = f["Prioridad"].lower().replace("'", "").replace("t", "t")
        prio = {"must": "must", "should": "should", "could": "could"}.get(
            f["Prioridad"].lower(), "wont")
        etiquetas = ["funcion", f"m:{MOD2DIR[f['Modulo']]}",
                     f"p:{prio}", f"fase-{f['Fase'][0]}"]
        if f["Tipo"] != "Funcional":
            etiquetas.append("nf")
        orden = ["api", f"repos/{args.repo}/issues", "-X", "POST",
                 "-f", f"title={titulo}", "-f", f"body={cuerpo(f)}"]
        for e in etiquetas:
            orden += ["-f", f"labels[]={e}"]
        gh(orden, args.simular)
        creados += 1
        if not args.simular:
            # GitHub limita la creacion de contenido: sin pausa salta el
            # limite secundario a partir de unas decenas de issues.
            time.sleep(0.8)
            if creados % 10 == 0:
                print(f"  {creados}...")
    print(f"  {creados} issues creados")


if __name__ == "__main__":
    main()
