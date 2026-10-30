"""Ubicación de los datos, tanto ejecutando desde el código como empaquetado con PyInstaller."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _congelado() -> bool:
    return bool(getattr(sys, "frozen", False))


def directorio_datos_integrados() -> Path:
    if _congelado():
        return Path(sys._MEIPASS) / "creador" / "datos"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "datos"


def directorio_recursos_gui() -> Path:
    """Tema, tipografías e iconos de la interfaz."""
    if _congelado():
        return Path(sys._MEIPASS) / "creador" / "gui" / "recursos"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent / "gui" / "recursos"


def directorio_portable() -> Path:
    """Carpeta junto al ejecutable (o raíz del proyecto al ejecutar desde el código).

    En macOS el ejecutable está dentro de «Programa.app/Contents/MacOS»: la carpeta portable es la que
    contiene la .app, donde el usuario la ve.
    """
    if _congelado():
        ejecutable = Path(sys.executable).resolve()
        app = next((p for p in ejecutable.parents if p.suffix == ".app"), None)
        return app.parent if sys.platform == "darwin" and app is not None else ejecutable.parent
    return Path(__file__).resolve().parents[2]


def edicion() -> str:
    """«completa» o «libre» en los ejecutables (lo escribe herramientas/compilar.py); «desarrollo» desde el código."""
    try:
        return json.loads((directorio_datos_integrados() / "edicion.json").read_text(encoding="utf-8"))["edicion"]
    except (OSError, ValueError, KeyError):
        return "desarrollo"


def directorio_personal() -> Path:
    """Carpeta del usuario; en la versión web, la que la página guarda en el navegador (IndexedDB)."""
    return Path.home() / ".creador-personajes"


def directorios_paquetes() -> list[Path]:
    """Dónde se buscan paquetes, de mayor a menor prioridad."""
    if sys.platform == "emscripten":  # versión web: no hay carpeta junto al programa
        return [directorio_datos_integrados() / "paquetes", directorio_personal() / "paquetes"]
    return [
        directorio_datos_integrados() / "paquetes",
        directorio_portable() / "paquetes",
        directorio_personal() / "paquetes",
    ]
