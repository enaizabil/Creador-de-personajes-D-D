"""Interfaz común que implementa cada sistema de reglas (5e 2014, 5e 2024, 3.5…).

El núcleo no sabe nada de D&D: carga paquetes, resuelve elecciones y delega
en el sistema todo lo que depende de las reglas concretas.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .efectos import EleccionPendiente, Resolucion
    from .paquetes import Catalogo
    from .personaje import Personaje


class ErrorReferencia(Exception):
    """Un efecto apunta a una entrada que no existe en el catálogo."""


@dataclass(frozen=True)
class Opcion:
    id: str
    nombre: str


class SistemaReglas(ABC):
    id: str = ""
    nombre: str = ""
    # Categorías de contenido que admite el sistema en sus paquetes.
    categorias: tuple[str, ...] = ()

    def validar_entrada(self, categoria: str, entrada: dict) -> list[str]:
        """Errores de forma de una entrada ya fusionada (sin contexto del catálogo)."""
        return []

    def validar_catalogo(self, catalogo: Catalogo) -> list[str]:
        """Errores de referencias cruzadas entre entradas del catálogo."""
        return []

    @abstractmethod
    def opciones_desde(self, fuente: str, filtro: dict | None, catalogo: Catalogo) -> list[Opcion]:
        """Opciones de una elección declarada como ``{"desde": fuente, "filtro": ...}``."""

    def efecto_activo(self, efecto: dict, personaje: Personaje) -> bool:
        """Si el efecto (o la elección) se aplica ya; p. ej. rasgos que llegan a cierto nivel."""
        return True

    def expandir_efecto(self, efecto: dict, catalogo: Catalogo, personaje: Personaje) -> list[dict] | None:
        """Sustituye un efecto por otros (p. ej. una dote por sus efectos) o None si es terminal."""
        return None

    @abstractmethod
    def resolver(self, personaje: Personaje, catalogo: Catalogo) -> Resolucion:
        """Recorre todas las fuentes del personaje y resuelve sus efectos."""

    def elecciones_pendientes(self, personaje: Personaje, catalogo: Catalogo) -> list[EleccionPendiente]:
        return self.resolver(personaje, catalogo).pendientes

    @abstractmethod
    def calcular(self, personaje: Personaje, catalogo: Catalogo) -> Any:
        """Ficha con todos los valores derivados."""

    def crear_asistente(self, personaje: Personaje, catalogo: Catalogo, **opciones) -> Any:
        """Asistente paso a paso del modo normal (cada edición define sus pasos)."""
        raise NotImplementedError(f"El sistema «{self.id}» no tiene asistente de creación")
