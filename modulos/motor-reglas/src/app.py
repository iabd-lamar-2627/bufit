"""Motor de reglas de Bufit.

Servicio REST. Responde preguntas sobre las reglas del juego y nada mas:
no elige jugadas, no habla y no sabe que existe una partida en marcha.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .juegos import JUEGOS

VERSION = "0.1.0"

app = FastAPI(
    title="Bufit · motor de reglas",
    version=VERSION,
    description="La autoridad del juego. Determinista, sin azar y sin IA.",
)


# ------------------------------------------------------------------ modelos
class Jugada(BaseModel):
    ficha: str | None = Field(None, examples=["6-3"])
    extremo: str | None = Field(None, examples=["izq", "der"])


class PeticionLegales(BaseModel):
    estado: dict
    mano: list[str]


class PeticionJugada(BaseModel):
    estado: dict
    jugada: Jugada


class PeticionEstado(BaseModel):
    estado: dict


class PeticionPuntuacion(BaseModel):
    estado: dict
    puntos_jugador: int = 0


def juego_de(estado: dict):
    nombre = estado.get("juego", "domino")
    if nombre not in JUEGOS:
        raise HTTPException(404, f"juego desconocido: {nombre}")
    return JUEGOS[nombre]


# ----------------------------------------------------------------- endpoints
@app.get("/salud")
def salud():
    return {"estado": "ok", "version": VERSION, "juegos": list(JUEGOS)}


@app.get("/parametros/{juego}")
def parametros(juego: str):
    """F2.3 · Cargar los parametros del juego elegido."""
    if juego not in JUEGOS:
        raise HTTPException(404, f"juego desconocido: {juego}")
    return JUEGOS[juego].parametros()


@app.post("/jugadas_legales")
def jugadas_legales(p: PeticionLegales):
    """F4.1 · Todas las jugadas posibles. Lista vacia es respuesta valida."""
    return {"jugadas": juego_de(p.estado).jugadas_legales(p.estado, p.mano)}


@app.post("/es_legal")
def es_legal(p: PeticionJugada):
    """F3.5 · Valida una jugada concreta."""
    legal, motivo = juego_de(p.estado).es_legal(p.estado, p.jugada.model_dump())
    return {"legal": legal, "motivo": motivo}


@app.post("/aplicar")
def aplicar(p: PeticionJugada):
    """F3.6 · Devuelve un estado nuevo. No modifica el recibido."""
    j = juego_de(p.estado)
    jugada = p.jugada.model_dump()
    if jugada.get("ficha") is not None:
        legal, motivo = j.es_legal(p.estado, jugada)
        if not legal:
            raise HTTPException(409, f"jugada ilegal: {motivo}")
    return {"estado": j.aplicar(p.estado, jugada)}


@app.post("/fin_partida")
def fin_partida(p: PeticionEstado):
    """F10.1 · Detecta domino o cierre."""
    terminada, motivo, ganador = juego_de(p.estado).ha_terminado(p.estado)
    return {"terminada": terminada, "motivo": motivo, "ganador": ganador}


@app.post("/puntuacion")
def puntuacion(p: PeticionPuntuacion):
    """F10.2 · Puntos y desglose.

    Bufit no ve la mano del jugador, asi que sus puntos llegan de fuera:
    se los dice el propio jugador en voz alta.
    """
    return juego_de(p.estado).puntuacion(p.estado, p.puntos_jugador)


@app.post("/info_publica")
def info_publica(p: PeticionEstado):
    """F7.3 · Solo lo deducible mirando la mesa. Nunca incluye manos."""
    return juego_de(p.estado).info_publica(p.estado)
