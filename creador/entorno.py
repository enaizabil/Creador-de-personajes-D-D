"""Punto de entrada único para preparar sistema + catálogo a partir de los paquetes instalados."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .nucleo.paquetes import Catalogo, InfoPaquete, cargar_catalogo, descubrir_paquetes
from .nucleo.rutas import directorios_paquetes
from .nucleo.sistema import SistemaReglas
from .sistemas import obtener_sistema


def paquetes_instalados(directorios: Iterable[Path] | None = None) -> tuple[dict[str, InfoPaquete], list[str]]:
    return descubrir_paquetes(directorios_paquetes() if directorios is None else directorios)


def abrir_catalogo(
    sistema_id: str, paquetes: Iterable[str], directorios: Iterable[Path] | None = None
) -> tuple[SistemaReglas, Catalogo, list[str]]:
    """Devuelve el sistema, el catálogo combinado y los avisos/errores de carga."""
    sistema = obtener_sistema(sistema_id)
    disponibles, avisos = paquetes_instalados(directorios)
    catalogo, errores = cargar_catalogo(sistema, paquetes, disponibles)
    return sistema, catalogo, avisos + errores
