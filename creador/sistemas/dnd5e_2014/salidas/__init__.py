"""Salidas de un personaje de 5e (2014): nota para Obsidian con la guía de Nivel20 y fichas en PDF."""
from ....nucleo.rutas import directorio_datos_integrados

RUTA_HOJA_OFICIAL = directorio_datos_integrados() / "plantillas" / "dnd5e-2014" / "hoja_editable_es.pdf"


def hay_hoja_oficial() -> bool:
    """La plantilla de la hoja oficial no va en la edición libre (es de uso personal)."""
    return RUTA_HOJA_OFICIAL.is_file()
