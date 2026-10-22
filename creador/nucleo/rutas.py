"""Ubicación de los datos, tanto ejecutando desde el código como empaquetado con PyInstaller."""
from __future__ import annotations

import sys
from pathlib import Path


def _congelado() -> bool:
    return bool(getattr(sys, "frozen", False))


def directorio_datos_integrados() -> Path:
    if _congelado():
        return Path(sys._MEIPASS) / "creador" / "datos"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "datos"


def directorio_portable() -> Path:
    """Carpeta junto al ejecutable (o raíz del proyecto al ejecutar desde el código)."""
    if _congelado():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def directorios_paquetes() -> list[Path]:
    """Dónde se buscan paquetes, de mayor a menor prioridad."""
    return [
        directorio_datos_integrados() / "paquetes",
        directorio_portable() / "paquetes",
        Path.home() / ".creador-personajes" / "paquetes",
    ]
