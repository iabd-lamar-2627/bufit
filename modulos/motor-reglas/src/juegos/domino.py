"""Domino doble seis para dos jugadores.

Representacion de una ficha: la cadena "a-b" con a y b entre 0 y 6.
La cadena de la mesa se guarda en orden, de izquierda a derecha, con cada
ficha ya orientada: el segundo numero de una ficha siempre encaja con el
primero de la siguiente.
"""
from ..base import Juego

MAX = 6


def numeros(ficha: str) -> tuple[int, int]:
    a, b = ficha.split("-")
    return int(a), int(b)


def puntos(ficha: str) -> int:
    a, b = numeros(ficha)
    return a + b


def es_doble(ficha: str) -> bool:
    a, b = numeros(ficha)
    return a == b


def misma_ficha(f1: str, f2: str) -> bool:
    return sorted(numeros(f1)) == sorted(numeros(f2))


class Domino(Juego):
    nombre = "domino"

    def parametros(self) -> dict:
        return {
            "juego": "domino",
            "fichas": 28,
            "mano": 7,
            "pozo": True,
            "puntos_para_ganar": 100,
            "empieza": "jugador",
            "segundos_por_turno_recomendado": 60,
        }

    # ---------------------------------------------------------------- jugadas
    def jugadas_legales(self, estado: dict, mano: list[str]) -> list[dict]:
        cadena = estado.get("cadena") or []
        jugadas = []

        if not cadena:
            # Mesa vacia: cualquier ficha vale, y solo por un lado.
            return [{"ficha": f, "extremo": "izq"} for f in mano]

        izq, der = self._extremos(cadena)
        for f in mano:
            a, b = numeros(f)
            if izq in (a, b):
                jugadas.append({"ficha": f, "extremo": "izq"})
            if der in (a, b):
                jugadas.append({"ficha": f, "extremo": "der"})
        return jugadas

    def es_legal(self, estado: dict, jugada: dict) -> tuple[bool, str | None]:
        ficha = jugada.get("ficha")
        extremo = jugada.get("extremo")

        if extremo not in ("izq", "der"):
            return False, "extremo_inexistente"

        cadena = estado.get("cadena") or []
        if not cadena:
            return True, None

        izq, der = self._extremos(cadena)
        a, b = numeros(ficha)
        objetivo = izq if extremo == "izq" else der
        if objetivo in (a, b):
            return True, None
        return False, "no_encaja"

    def aplicar(self, estado: dict, jugada: dict) -> dict:
        nuevo = {k: (list(v) if isinstance(v, list) else v) for k, v in estado.items()}
        nuevo["cadena"] = list(estado.get("cadena") or [])
        nuevo["jugadas"] = list(estado.get("jugadas") or [])

        quien = estado.get("turno", "jugador")
        ficha = jugada.get("ficha")
        extremo = jugada.get("extremo")

        if ficha is None:
            # Paso de turno (F5.8).
            nuevo["jugadas"].append({"quien": quien, "ficha": None, "extremo": None})
            nuevo["turno"] = "bufit" if quien == "jugador" else "jugador"
            nuevo["extremos"] = self._extremos(nuevo["cadena"]) if nuevo["cadena"] else [None, None]
            return nuevo

        if not nuevo["cadena"]:
            nuevo["cadena"] = [self._normaliza_inicial(ficha)]
        elif extremo == "izq":
            izq, _ = self._extremos(nuevo["cadena"])
            nuevo["cadena"].insert(0, self._orienta(ficha, encaja_por_la_derecha=izq))
        else:
            _, der = self._extremos(nuevo["cadena"])
            nuevo["cadena"].append(self._orienta(ficha, encaja_por_la_izquierda=der))

        if quien == "bufit":
            nuevo["mano_bufit"] = [f for f in (estado.get("mano_bufit") or [])
                                   if not misma_ficha(f, ficha)]
        else:
            nuevo["fichas_jugador"] = max(0, int(estado.get("fichas_jugador", 0)) - 1)

        nuevo["jugadas"].append({"quien": quien, "ficha": ficha, "extremo": extremo})
        nuevo["extremos"] = list(self._extremos(nuevo["cadena"]))
        nuevo["turno"] = "bufit" if quien == "jugador" else "jugador"
        return nuevo

    # ------------------------------------------------------------------- fin
    def ha_terminado(self, estado: dict) -> tuple[bool, str | None, str | None]:
        if not (estado.get("mano_bufit") or []) and estado.get("jugadas"):
            return True, "domino", "bufit"
        if estado.get("fichas_jugador") == 0 and estado.get("jugadas"):
            return True, "domino", "jugador"

        # Cierre: dos pasos seguidos con el pozo agotado.
        # Es el caso que siempre se olvida al programar el domino.
        jugadas = estado.get("jugadas") or []
        ultimas = jugadas[-2:]
        if (len(ultimas) == 2
                and all(j.get("ficha") is None for j in ultimas)
                and int(estado.get("pozo", 0)) == 0):
            return True, "cierre", None
        return False, None, None

    def puntuacion(self, estado: dict, puntos_jugador: int) -> dict:
        mano_bufit = estado.get("mano_bufit") or []
        desglose_bufit = [[f, puntos(f)] for f in mano_bufit]
        puntos_bufit = sum(p for _, p in desglose_bufit)

        terminada, motivo, ganador = self.ha_terminado(estado)
        if motivo == "cierre" or ganador is None:
            # Gana quien menos puntos suma. Empate si coinciden.
            if puntos_bufit < puntos_jugador:
                ganador = "bufit"
            elif puntos_jugador < puntos_bufit:
                ganador = "jugador"
            else:
                ganador = None

        return {
            "ganador": ganador,
            "puntos": {"jugador": puntos_jugador, "bufit": puntos_bufit},
            "desglose": {"bufit": desglose_bufit},
            "motivo": motivo,
        }

    def info_publica(self, estado: dict) -> dict:
        """Solo lo que cualquiera deduciria mirando la mesa (F7.3).

        OJO: descuenta la mano de Bufit para saber que fichas quedan por
        salir, pero NO la incluye en la respuesta.
        """
        cadena = estado.get("cadena") or []
        todas = {f"{a}-{b}" for a in range(MAX + 1) for b in range(a, MAX + 1)}
        vistas = {"-".join(map(str, sorted(numeros(f)))) for f in cadena}
        mias = {"-".join(map(str, sorted(numeros(f)))) for f in (estado.get("mano_bufit") or [])}
        return {
            "extremos": list(self._extremos(cadena)) if cadena else [None, None],
            "fichas_no_vistas": sorted(todas - vistas - mias),
            "pozo": estado.get("pozo", 0),
            "fichas_jugador": estado.get("fichas_jugador", 0),
        }

    # ----------------------------------------------------------------- apoyo
    @staticmethod
    def _extremos(cadena: list[str]) -> tuple[int, int]:
        izq = numeros(cadena[0])[0]
        der = numeros(cadena[-1])[1]
        return izq, der

    @staticmethod
    def _normaliza_inicial(ficha: str) -> str:
        return ficha

    @staticmethod
    def _orienta(ficha: str, encaja_por_la_derecha: int | None = None,
                 encaja_por_la_izquierda: int | None = None) -> str:
        a, b = numeros(ficha)
        if encaja_por_la_derecha is not None:
            # La ficha va a la izquierda: su segundo numero debe ser el extremo.
            return f"{a}-{b}" if b == encaja_por_la_derecha else f"{b}-{a}"
        # La ficha va a la derecha: su primer numero debe ser el extremo.
        return f"{a}-{b}" if a == encaja_por_la_izquierda else f"{b}-{a}"
