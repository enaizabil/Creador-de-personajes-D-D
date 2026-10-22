"""Utilidades compartidas por los tests."""
from pathlib import Path

from creador.nucleo.personaje import EntradaClase, ObjetoInventario, Personaje

DIRECTORIO_PAQUETES = Path(__file__).parent / "datos" / "paquetes"

BASE_ESTANDAR = {"fue": 15, "des": 13, "con": 14, "int": 8, "sab": 12, "car": 10}


def nuevo_personaje(**campos) -> Personaje:
    datos = {
        "sistema": "dnd5e-2014",
        "paquetes": ["prueba"],
        "metodo_caracteristicas": "estandar",
        "caracteristicas_base": dict(BASE_ESTANDAR),
    }
    datos.update(campos)
    return Personaje(**datos)


__all__ = ["EntradaClase", "ObjetoInventario", "nuevo_personaje", "DIRECTORIO_PAQUETES", "BASE_ESTANDAR"]
