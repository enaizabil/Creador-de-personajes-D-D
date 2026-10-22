"""Utilidades de texto independientes del sistema."""
from __future__ import annotations

import unicodedata


def clave_alfabetica(texto: str) -> str:
    """Clave de ordenación que ignora tildes y mayúsculas («Élfico» va entre «Dracónico» y «Enano»)."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().casefold()
