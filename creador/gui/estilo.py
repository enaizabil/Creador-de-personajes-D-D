"""Aspecto de la interfaz: tema pergamino y granate, títulos en Cinzel e iconos de game-icons.net.

Los iconos se guardan como máscaras (solo transparencia) y se colorean al cargarlos, con una variante para el modo
claro y otra para el oscuro. Créditos y licencias en recursos/CREDITOS.md.
"""
from __future__ import annotations

import customtkinter as ctk
from PIL import Image

from ..nucleo.rutas import directorio_recursos_gui
from ..sistemas.dnd5e_2014.interfaz import nombre_icono

FUENTE_TITULOS = "Cinzel"
# Color de los iconos: [modo claro, modo oscuro]. «acento» va sobre el fondo; «claro», sobre un botón granate.
COLORES_ICONO = {"acento": ("#6b1d1d", "#e6cf9f"), "claro": ("#fbf3e2", "#fbf3e2"), "suave": ("#8c7552", "#a8927a")}

_cache: dict[tuple[str, int, str], ctk.CTkImage] = {}
_mascaras: dict[str, Image.Image] = {}


def aplicar_tema() -> None:
    """Tema y tipografías; se llama antes de crear la ventana. Si Cinzel no se puede cargar (macOS), los títulos usan
    la tipografía por defecto."""
    recursos = directorio_recursos_gui()
    for archivo in sorted((recursos / "fuentes").glob("*.ttf")):
        ctk.FontManager.load_font(str(archivo))
    ctk.set_default_color_theme(str(recursos / "tema_pergamino.json"))


def fuente_titulo(tamano: int = 18) -> ctk.CTkFont:
    return ctk.CTkFont(family=FUENTE_TITULOS, size=tamano, weight="bold")


def _colorear(mascara: Image.Image, color: str) -> Image.Image:
    imagen = Image.new("RGBA", mascara.size, color)
    imagen.putalpha(mascara)
    return imagen


def icono(nombre: str | None, tamano: int = 24, color: str = "acento") -> ctk.CTkImage | None:
    """Icono por nombre de archivo (sin .png), coloreado para los dos modos; None si no existe."""
    if not nombre:
        return None
    clave = (nombre, tamano, color)
    if clave not in _cache:
        if nombre not in _mascaras:
            ruta = directorio_recursos_gui() / "iconos" / f"{nombre}.png"
            if not ruta.exists():
                return None
            _mascaras[nombre] = Image.open(ruta).convert("L")
        claro, oscuro = COLORES_ICONO[color]
        _cache[clave] = ctk.CTkImage(_colorear(_mascaras[nombre], claro), _colorear(_mascaras[nombre], oscuro),
                                     size=(tamano, tamano))
    return _cache[clave]


def icono_de(categoria: str, id_: str | None, tamano: int = 24, color: str = "acento",
             generico: bool = True) -> ctk.CTkImage | None:
    """Icono de una clase, raza (o subraza: la de su raza), paso o trasfondo."""
    return icono(nombre_icono(categoria, id_, generico), tamano, color)
