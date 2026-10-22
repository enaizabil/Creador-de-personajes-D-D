"""Registro de sistemas de reglas disponibles.

Para añadir una edición nueva: crear su subpaquete con una clase que herede de
``SistemaReglas`` y registrarla aquí.
"""
from __future__ import annotations

from ..nucleo.sistema import SistemaReglas
from .dnd5e_2014 import Sistema5e2014

_SISTEMAS: dict[str, SistemaReglas] = {s.id: s for s in (Sistema5e2014(),)}


def obtener_sistema(id_: str) -> SistemaReglas:
    try:
        return _SISTEMAS[id_]
    except KeyError:
        raise KeyError(f"Sistema de reglas desconocido «{id_}» (disponibles: {', '.join(_SISTEMAS)})") from None


def listar_sistemas() -> list[SistemaReglas]:
    return list(_SISTEMAS.values())
