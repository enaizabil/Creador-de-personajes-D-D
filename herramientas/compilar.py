"""Compila el programa portable para el sistema operativo actual con PyInstaller.

    pip install -r requirements.txt pyinstaller
    python herramientas/compilar.py                    # las dos ediciones
    python herramientas/compilar.py --edicion libre    # solo una

Ediciones:
- **completa**: SRD 5.1, Manual del Jugador, Guía del DM, cuestionario y hoja oficial editable. Lleva contenido
  con derechos de autor: solo para tu grupo de juego, no se comparte.
- **libre**: SRD 5.1 y cuestionario (sin hoja oficial). Se puede pasar a quien quieras.

Resultado: ``dist/CreadorPersonajes-<versión>-<edición>-<sistema>.zip`` con una carpeta (``--onedir``: arranca
rápido y da menos falsos positivos del antivirus que un único .exe; CustomTkinter tampoco funciona con
``--onefile``). En macOS la carpeta lleva la aplicación «.app».

En Windows se compila en una carpeta de ruta corta (``%USERPROFILE%\\.creador-compilar``) y se borra al acabar:
dentro de una carpeta con ruta larga, las rutas de PyInstaller pasan de 260 caracteres y la copia falla.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from creador import __version__  # noqa: E402

NOMBRE = "CreadorPersonajes"
PAQUETES = {
    "completa": ["srd-5.1", "phb-2014", "dmg-2014", "cuestionario-basico"],
    "libre": ["srd-5.1", "cuestionario-basico"],
}
PLANTILLAS = {"completa": True, "libre": False}
# Windows corta las rutas en 260 caracteres si no se activan las rutas largas: fuera del repositorio, cerca de la raíz.
TEMPORAL = Path.home() / ".creador-compilar" if sys.platform == "win32" else RAIZ / "build"

LEEME = """Creador de personajes de rol {version} (edición {edicion})
=============================================================

Cómo abrirlo
- Windows: doble clic en {nombre}.exe. Si el antivirus o SmartScreen avisa («editor desconocido»), es porque
  el programa no está firmado: «Más información» → «Ejecutar de todas formas».
- macOS: la primera vez, clic derecho sobre {nombre}.app → «Abrir» (no está firmado por Apple).
- Linux: ./{nombre} (necesita las librerías gráficas habituales del escritorio).

Es portable: no se instala. Copia la carpeta entera donde quieras (también a un USB).

Cómo desinstalarlo
- Windows: doble clic en Desinstalar.bat (con el programa cerrado). Borra esta carpeta y
  %USERPROFILE%\\.creador-personajes; lo que hayas guardado en otras carpetas no se toca.
- macOS y Linux: borra esta carpeta y ~/.creador-personajes.
- El programa no crea accesos directos ni escribe en el registro: no queda nada más.

Homebrew y expansiones
- Programa → «Paquetes…» → «Importar .zip…» o «Importar carpeta…». Se validan antes de instalarse.
- O copia la carpeta del paquete dentro de «paquetes», junto a este archivo.
- Ejemplo y formato: docs/ejemplos/homebrew-ejemplo y docs/formato-paquetes.md en el repositorio.

Línea de órdenes (desde una terminal en esta carpeta)
  {nombre} paquetes | validar | ficha personaje.json | exportar personaje.json | instalar paquete.zip | quitar id

{licencia}
"""
LICENCIAS = {
    "completa": "EDICIÓN COMPLETA - USO PERSONAL\nIncluye contenido del Manual del Jugador y de la Guía del Dungeon Master "
                "(redactado con palabras propias) y la hoja de personaje oficial editable, todos con derechos de autor de "
                "Wizards of the Coast. Úsala solo en tu grupo de juego: no la compartas ni la publiques.",
    "libre": "EDICIÓN LIBRE\nIncluye el SRD 5.1 en español (Wizards of the Coast, licencia CC BY 4.0) y contenido propio del "
             "programa. Se puede compartir. Para el Manual del Jugador, cada mesa puede añadir sus propios paquetes.",
}


def plataforma() -> str:
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux") + "-" + platform.machine().lower()


def preparar_datos(edicion: str, destino: Path) -> Path:
    """Copia de creador/datos con solo lo que lleva esa edición."""
    origen = RAIZ / "creador" / "datos"
    if destino.exists():
        shutil.rmtree(destino)
    for id_ in PAQUETES[edicion]:
        shutil.copytree(origen / "paquetes" / "dnd5e-2014" / id_, destino / "paquetes" / "dnd5e-2014" / id_)
    if PLANTILLAS[edicion]:
        shutil.copytree(origen / "plantillas", destino / "plantillas")
    (destino / "edicion.json").write_text(json.dumps({"edicion": edicion, "version": __version__}), encoding="utf-8")
    return destino


def compilar(edicion: str) -> Path:
    import customtkinter
    import PyInstaller.__main__

    nombre = f"{NOMBRE}-{edicion}"
    trabajo = TEMPORAL / nombre
    datos = preparar_datos(edicion, trabajo / "datos")
    # Sin __pycache__: no hace falta y sus rutas son las más largas.
    ctk = trabajo / "customtkinter"
    if ctk.exists():
        shutil.rmtree(ctk)
    shutil.copytree(Path(customtkinter.__file__).parent, ctk, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    distribucion = TEMPORAL / "dist" / edicion
    PyInstaller.__main__.run([
        str(RAIZ / "herramientas" / "lanzador.py"),
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", NOMBRE,
        "--distpath", str(distribucion), "--workpath", str(trabajo / "pyinstaller"), "--specpath", str(trabajo),
        "--paths", str(RAIZ),
        "--add-data", f"{datos}{os.pathsep}creador/datos",
        "--add-data", f"{ctk}{os.pathsep}customtkinter",
        "--collect-submodules", "reportlab.pdfbase",
        "--collect-submodules", "creador",
    ])
    carpeta = distribucion / NOMBRE
    if sys.platform == "darwin" and (distribucion / f"{NOMBRE}.app").exists():
        # En macOS se reparte la .app; la carpeta suelta sobra.
        shutil.rmtree(carpeta)
        carpeta.mkdir()
        shutil.move(str(distribucion / f"{NOMBRE}.app"), carpeta / f"{NOMBRE}.app")
    (carpeta / "paquetes").mkdir(exist_ok=True)
    (carpeta / "paquetes" / "LEEME.txt").write_text(
        "Pon aquí las carpetas de tus paquetes (homebrew, expansiones) o impórtalos desde el programa: «Paquetes…».\n",
        encoding="utf-8")
    (carpeta / "LEEME.txt").write_text(LEEME.format(version=__version__, edicion=edicion, nombre=NOMBRE,
                                                    licencia=LICENCIAS[edicion]), encoding="utf-8")
    if sys.platform == "win32":
        # Con saltos de línea CRLF: cmd.exe falla con «goto» en archivos con LF.
        desinstalar = (RAIZ / "herramientas" / "desinstalar_windows.bat").read_text(encoding="ascii")
        (carpeta / "Desinstalar.bat").write_bytes(desinstalar.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"))
    (RAIZ / "dist").mkdir(exist_ok=True)
    archivo = shutil.make_archive(str(RAIZ / "dist" / f"{NOMBRE}-{__version__}-{edicion}-{plataforma()}"), "zip",
                                  root_dir=distribucion, base_dir=NOMBRE)
    return Path(archivo)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila el creador de personajes portable con PyInstaller.")
    parser.add_argument("--edicion", choices=["completa", "libre", "ambas"], default="ambas")
    args = parser.parse_args()
    try:
        import customtkinter  # noqa: F401
        import PyInstaller  # noqa: F401
        import tkinter  # noqa: F401
    except ImportError as exc:
        print(f"Falta algo para compilar: {exc}\nInstala: pip install -r requirements.txt pyinstaller "
              "(y Python con Tkinter: el de python.org lo trae).", file=sys.stderr)
        return 1
    ediciones = ["completa", "libre"] if args.edicion == "ambas" else [args.edicion]
    try:
        for edicion in ediciones:
            print(f"Listo: {compilar(edicion)}")
    finally:
        if TEMPORAL != RAIZ / "build":
            shutil.rmtree(TEMPORAL, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
