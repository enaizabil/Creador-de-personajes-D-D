"""Línea de órdenes provisional (la interfaz gráfica llega en una fase posterior).

    python -m creador paquetes
    python -m creador validar srd-5.1 phb-2014
    python -m creador ficha personaje.json
"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .entorno import abrir_catalogo, paquetes_instalados
from .nucleo.paquetes import ErrorPaquete
from .nucleo.personaje import Personaje


def _orden_paquetes() -> int:
    disponibles, avisos = paquetes_instalados()
    if not disponibles:
        print("No hay paquetes de contenido instalados.")
    for info in sorted(disponibles.values(), key=lambda i: (i.sistema, i.id)):
        dependencias = f" (requiere: {', '.join(info.depende_de)})" if info.depende_de else ""
        print(f"[{info.sistema}] {info.id} {info.version} – {info.nombre}{dependencias}")
    for aviso in avisos:
        print(f"AVISO: {aviso}", file=sys.stderr)
    return 0


def _orden_validar(sistema_id: str, paquetes: list[str]) -> int:
    disponibles, avisos = paquetes_instalados()
    if not paquetes:
        paquetes = [i.id for i in disponibles.values() if i.sistema == sistema_id]
    try:
        _, catalogo, errores = abrir_catalogo(sistema_id, paquetes)
    except (ErrorPaquete, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for error in errores:
        print(error)
    resumen = ", ".join(f"{c}: {len(catalogo.listar(c))}" for c in catalogo.categorias())
    print(f"{len(errores)} errores · {resumen}", file=sys.stderr)
    return 1 if errores else 0


def _orden_ficha(archivo: str) -> int:
    personaje = Personaje.cargar(archivo)
    try:
        sistema, catalogo, errores = abrir_catalogo(personaje.sistema, personaje.paquetes)
    except (ErrorPaquete, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for error in errores:
        print(f"ERROR DE PAQUETE: {error}", file=sys.stderr)
    ficha = sistema.calcular(personaje, catalogo)
    print(f"{ficha.nombre or '(sin nombre)'} – {ficha.raza} – {ficha.clase_y_nivel} – {ficha.trasfondo}")
    print("  ".join(f"{c.upper()} {v.puntuacion} ({v.modificador:+d})" for c, v in ficha.caracteristicas.items()))
    print(f"CA {ficha.ca} · Iniciativa {ficha.iniciativa:+d} · Velocidad {ficha.velocidades.get('caminar', 0)} pies · "
          f"PG {ficha.pg_maximos} · Competencia +{ficha.bonificador_competencia}")
    for aviso in ficha.avisos:
        print(f"AVISO: {aviso}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="creador", description="Creador de personajes de rol")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ordenes = parser.add_subparsers(dest="orden")
    ordenes.add_parser("paquetes", help="lista los paquetes de contenido instalados")
    validar = ordenes.add_parser("validar", help="carga paquetes y muestra sus errores (todos si no se indica ninguno)")
    validar.add_argument("paquetes", nargs="*")
    validar.add_argument("--sistema", default="dnd5e-2014")
    ficha = ordenes.add_parser("ficha", help="calcula la ficha de un personaje guardado en JSON")
    ficha.add_argument("archivo")
    args = parser.parse_args(argv)

    if args.orden == "paquetes":
        return _orden_paquetes()
    if args.orden == "validar":
        return _orden_validar(args.sistema, args.paquetes)
    if args.orden == "ficha":
        return _orden_ficha(args.archivo)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
