"""Pruebas del motor de reglas.

Este modulo es la autoridad del juego: si se equivoca, la partida entera
esta mal. Por eso es el unico del proyecto que aspira a cobertura completa.
"""
import pytest

from src.juegos.domino import Domino, numeros, puntos, es_doble

J = Domino()


def estado(cadena=None, mano=None, turno="bufit", pozo=0, fichas_jugador=7, jugadas=None):
    cadena = cadena or []
    return {
        "juego": "domino",
        "turno": turno,
        "cadena": cadena,
        "extremos": list(J._extremos(cadena)) if cadena else [None, None],
        "mano_bufit": mano if mano is not None else [],
        "fichas_jugador": fichas_jugador,
        "pozo": pozo,
        "marcador": {"jugador": 0, "bufit": 0},
        "jugadas": jugadas or [],
    }


# ------------------------------------------------------------------ basicos
def test_puntos_y_dobles():
    assert puntos("6-3") == 9
    assert puntos("0-0") == 0
    assert es_doble("5-5")
    assert not es_doble("5-4")
    assert numeros("6-3") == (6, 3)


# ---------------------------------------------------------- jugadas legales
def test_mesa_vacia_todas_valen():
    e = estado(mano=["6-3", "5-5"])
    assert len(J.jugadas_legales(e, e["mano_bufit"])) == 2


def test_solo_las_que_encajan():
    e = estado(cadena=["3-3", "3-6"], mano=["6-1", "5-5", "0-3"])
    legales = J.jugadas_legales(e, e["mano_bufit"])
    fichas = {j["ficha"] for j in legales}
    assert fichas == {"6-1", "0-3"}      # 5-5 no encaja con 3 ni con 6
    assert {"ficha": "5-5", "extremo": "izq"} not in legales


def test_ficha_que_encaja_por_los_dos_lados_da_dos_jugadas():
    e = estado(cadena=["3-3", "3-6"], mano=["6-3"])
    assert len(J.jugadas_legales(e, e["mano_bufit"])) == 2


def test_sin_jugada_posible_devuelve_lista_vacia():
    e = estado(cadena=["3-3", "3-6"], mano=["5-4", "2-1"])
    assert J.jugadas_legales(e, e["mano_bufit"]) == []


# ---------------------------------------------------------------- legalidad
def test_es_legal():
    e = estado(cadena=["3-3", "3-6"])
    assert J.es_legal(e, {"ficha": "6-1", "extremo": "der"}) == (True, None)
    assert J.es_legal(e, {"ficha": "5-4", "extremo": "der"})[1] == "no_encaja"
    assert J.es_legal(e, {"ficha": "6-1", "extremo": "arriba"})[1] == "extremo_inexistente"


def test_en_mesa_vacia_cualquier_cosa_es_legal():
    assert J.es_legal(estado(), {"ficha": "0-0", "extremo": "izq"})[0]


# ------------------------------------------------------------------ aplicar
def test_aplicar_no_modifica_el_estado_recibido():
    e = estado(cadena=["3-3"], mano=["3-6"])
    original = [list(e["cadena"]), list(e["mano_bufit"])]
    J.aplicar(e, {"ficha": "3-6", "extremo": "der"})
    assert [e["cadena"], e["mano_bufit"]] == original


def test_aplicar_orienta_la_ficha_por_la_derecha():
    e = estado(cadena=["3-3"], mano=["6-3"])
    nuevo = J.aplicar(e, {"ficha": "6-3", "extremo": "der"})
    assert nuevo["cadena"] == ["3-3", "3-6"]
    assert nuevo["extremos"] == [3, 6]


def test_aplicar_orienta_la_ficha_por_la_izquierda():
    e = estado(cadena=["3-3"], mano=["6-3"])
    nuevo = J.aplicar(e, {"ficha": "6-3", "extremo": "izq"})
    assert nuevo["cadena"] == ["6-3", "3-3"]
    assert nuevo["extremos"] == [6, 3]


def test_aplicar_retira_la_ficha_de_la_mano_y_cambia_el_turno():
    e = estado(cadena=["3-3"], mano=["3-6", "5-5"], turno="bufit")
    nuevo = J.aplicar(e, {"ficha": "3-6", "extremo": "der"})
    assert nuevo["mano_bufit"] == ["5-5"]
    assert nuevo["turno"] == "jugador"


def test_aplicar_descuenta_ficha_al_jugador():
    e = estado(cadena=["3-3"], turno="jugador", fichas_jugador=5)
    nuevo = J.aplicar(e, {"ficha": "3-6", "extremo": "der"})
    assert nuevo["fichas_jugador"] == 4


def test_pasar_turno():
    e = estado(cadena=["3-3"], turno="bufit")
    nuevo = J.aplicar(e, {"ficha": None, "extremo": None})
    assert nuevo["turno"] == "jugador"
    assert nuevo["jugadas"][-1]["ficha"] is None


# ---------------------------------------------------------------------- fin
def test_gana_quien_se_queda_sin_fichas():
    e = estado(cadena=["3-3"], mano=[], jugadas=[{"quien": "bufit", "ficha": "3-3"}])
    assert J.ha_terminado(e) == (True, "domino", "bufit")

    e = estado(cadena=["3-3"], mano=["5-5"], fichas_jugador=0,
               jugadas=[{"quien": "jugador", "ficha": "3-3"}])
    assert J.ha_terminado(e) == (True, "domino", "jugador")


def test_cierre_con_dos_pasos_y_pozo_agotado():
    """El caso que siempre se olvida: nadie puede jugar y no queda pozo."""
    e = estado(cadena=["3-3"], mano=["5-5"], pozo=0, jugadas=[
        {"quien": "jugador", "ficha": None},
        {"quien": "bufit", "ficha": None},
    ])
    terminada, motivo, ganador = J.ha_terminado(e)
    assert terminada and motivo == "cierre" and ganador is None


def test_no_hay_cierre_si_queda_pozo():
    e = estado(cadena=["3-3"], mano=["5-5"], pozo=3, jugadas=[
        {"quien": "jugador", "ficha": None},
        {"quien": "bufit", "ficha": None},
    ])
    assert J.ha_terminado(e)[0] is False


def test_partida_recien_empezada_no_esta_terminada():
    assert J.ha_terminado(estado(mano=["5-5"]))[0] is False


# -------------------------------------------------------------- puntuacion
def test_puntuacion_suma_la_mano_de_bufit():
    e = estado(cadena=["3-3"], mano=["5-5", "4-0"],
               jugadas=[{"quien": "jugador", "ficha": None},
                        {"quien": "bufit", "ficha": None}])
    r = J.puntuacion(e, puntos_jugador=12)
    assert r["puntos"]["bufit"] == 14
    assert r["puntos"]["jugador"] == 12
    assert r["ganador"] == "jugador"          # menos puntos gana en el cierre


def test_puntuacion_empate():
    e = estado(cadena=["3-3"], mano=["5-5"],
               jugadas=[{"quien": "jugador", "ficha": None},
                        {"quien": "bufit", "ficha": None}])
    assert J.puntuacion(e, puntos_jugador=10)["ganador"] is None


# ------------------------------------------------------------ info publica
def test_info_publica_no_revela_la_mano_de_bufit():
    e = estado(cadena=["3-3", "3-6"], mano=["5-5", "4-0"])
    info = J.info_publica(e)
    assert "mano_bufit" not in info
    # Las fichas de Bufit tampoco aparecen como "no vistas":
    # se descuentan para el calculo, pero no se entregan.
    assert "5-5" not in info["fichas_no_vistas"]
    assert "0-4" not in info["fichas_no_vistas"]
    assert "3-3" not in info["fichas_no_vistas"]
    assert len(info["fichas_no_vistas"]) == 28 - 2 - 2
