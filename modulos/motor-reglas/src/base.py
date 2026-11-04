"""Contrato que cumple todo juego de mesa de Bufit.

Esta es la pieza clave del diseno: el resto del sistema habla con este
contrato y no sabe a que se esta jugando. Anadir un juego nuevo es escribir
una clase mas, no tocar el sistema.
"""
from abc import ABC, abstractmethod


class Juego(ABC):
    """Interfaz comun a todos los juegos."""

    nombre: str

    @abstractmethod
    def parametros(self) -> dict:
        """Numero de fichas, tamano de mano, si hay pozo, puntos para ganar."""

    @abstractmethod
    def jugadas_legales(self, estado: dict, mano: list[str]) -> list[dict]:
        """Todas las jugadas posibles. Una lista vacia es respuesta valida."""

    @abstractmethod
    def es_legal(self, estado: dict, jugada: dict) -> tuple[bool, str | None]:
        """(legal, motivo). El motivo es un codigo, no una frase."""

    @abstractmethod
    def aplicar(self, estado: dict, jugada: dict) -> dict:
        """Devuelve un estado NUEVO. No modifica el que recibe.

        Esto es lo que permite deshacer una jugada (F8.6).
        """

    @abstractmethod
    def ha_terminado(self, estado: dict) -> tuple[bool, str | None, str | None]:
        """(terminada, motivo, ganador)."""

    @abstractmethod
    def puntuacion(self, estado: dict, puntos_jugador: int) -> dict:
        """Puntos de cada uno y desglose."""
