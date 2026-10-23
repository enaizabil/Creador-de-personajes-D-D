"""Deja en blanco una hoja de personaje rellenable (AcroForm): borra valores y desmarca casillas.

    python herramientas/vaciar_hoja_pdf.py hoja_rellena.pdf creador/datos/plantillas/dnd5e-2014/hoja_editable_es.pdf

Se usó para crear la plantilla que rellena el programa a partir de una hoja ya usada. Mantiene el diseño,
los cálculos y los formatos; al reescribir el archivo, pypdf repara también su tabla de referencias.
"""
from __future__ import annotations

import sys

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


def _campos(anotacion):
    """La anotación y sus antecesores (donde puede estar el valor del campo)."""
    nodo = anotacion
    while nodo is not None:
        yield nodo
        nodo = nodo["/Parent"].get_object() if "/Parent" in nodo else None


def vaciar(origen: str, destino: str) -> int:
    lector = PdfReader(origen, strict=False)
    escritor = PdfWriter(clone_from=lector)
    vaciados = 0
    for pagina in escritor.pages:
        for anotacion in pagina.get("/Annots", []) or []:
            widget = anotacion.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            for nodo in _campos(widget):
                if "/V" in nodo:
                    del nodo["/V"]
                    vaciados += 1
                if "/I" in nodo:  # opción elegida de un desplegable: el visor la redibuja si se deja
                    del nodo["/I"]
            tipo = next((n.get("/FT") for n in _campos(widget) if "/FT" in n), None)
            if tipo == "/Btn":
                widget[NameObject("/AS")] = NameObject("/Off")
            elif "/AP" in widget:
                del widget["/AP"]  # sin apariencia: el visor la dibuja vacía
    escritor.set_need_appearances_writer(True)
    # Las apariencias quitadas siguen en el archivo como objetos huérfanos (con el texto de antes): fuera.
    escritor.compress_identical_objects(remove_duplicates=False, remove_unreferenced=True)
    with open(destino, "wb") as salida:
        escritor.write(salida)
    return vaciados


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(f"{vaciar(sys.argv[1], sys.argv[2])} valores borrados → {sys.argv[2]}")
