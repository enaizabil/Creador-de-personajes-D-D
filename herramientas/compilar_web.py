"""Prepara la versión web: una carpeta estática que se sirve tal cual (GitHub Pages o cualquier servidor).

    python herramientas/compilar_web.py                      # en dist/web
    python herramientas/compilar_web.py --salida otra/carpeta
    python -m http.server -d dist/web 8000                   # para probarla en http://localhost:8000

La página (web/) carga Pyodide (Python en WebAssembly) desde jsDelivr y, dentro, el mismo creador que el programa de
escritorio, sin la interfaz de escritorio: ``creador.zip`` lleva el código y los datos de la edición completa.
reportlab y pypdf (para los PDF) van en ``ruedas/``: son ruedas de Python puro que se descargan aquí una vez, con
la versión fijada, y la página las instala con micropip. Las máscaras de los iconos se convierten a PNG con canal
alfa, que es lo que usa ``mask-image``.

Los nombres de los archivos de la página llevan ``?h=<huella>`` para que el navegador no use una versión vieja
de la caché tras publicar una nueva.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from compilar import preparar_datos  # noqa: E402
from PIL import Image  # noqa: E402

from creador import __version__  # noqa: E402

RUEDAS = ("reportlab==5.1.0", "pypdf==6.21.4")
EDICION = "completa"
PAGINA = ("index.html", "app.js", "worker.js", "estilo.css")
RECURSOS = RAIZ / "creador" / "gui" / "recursos"
CACHE_RUEDAS = RAIZ / "build" / "ruedas-web"
FECHA_ZIP = (1980, 1, 1, 0, 0, 0)  # fija: el mismo código da el mismo zip y la misma huella
COLOR_FAVICON = (125, 31, 31)  # el granate del tema


def archivos_codigo() -> list[tuple[str, Path]]:
    """(ruta dentro del zip, archivo) del paquete creador sin la interfaz de escritorio ni los datos."""
    origen = RAIZ / "creador"
    elegidos = []
    for ruta in sorted(origen.rglob("*")):
        relativa = ruta.relative_to(RAIZ)
        partes = relativa.parts
        if not ruta.is_file() or "__pycache__" in partes or ruta.suffix == ".pyc":
            continue
        if partes[1] in ("gui", "datos"):
            continue
        elegidos.append((relativa.as_posix(), ruta))
    return elegidos


def crear_zip(destino: Path, temporal: Path) -> None:
    datos = preparar_datos(EDICION, temporal / "datos")
    entradas = archivos_codigo()
    entradas += [(f"creador/datos/{r.relative_to(datos).as_posix()}", r) for r in sorted(datos.rglob("*")) if r.is_file()]
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archivo:
        for nombre, ruta in entradas:
            info = zipfile.ZipInfo(nombre, FECHA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archivo.writestr(info, ruta.read_bytes())


def descargar_ruedas() -> list[Path]:
    """Las ruedas de RUEDAS, de Python puro (py3-none-any); se guardan en build/ y no se vuelven a bajar."""
    CACHE_RUEDAS.mkdir(parents=True, exist_ok=True)
    faltan = [r for r in RUEDAS if not list(CACHE_RUEDAS.glob(f"{r.replace('==', '-')}-*.whl"))]
    if faltan:
        subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:", "--platform", "any",
                        "--python-version", "3.13", "--implementation", "py", "--abi", "none", "-d", str(CACHE_RUEDAS),
                        *faltan], check=True)
    ruedas = []
    for rueda in RUEDAS:
        encontradas = sorted(CACHE_RUEDAS.glob(f"{rueda.replace('==', '-')}-*.whl"))
        if len(encontradas) != 1 or not encontradas[0].name.endswith("-py3-none-any.whl"):
            raise SystemExit(f"No hay una rueda pura de {rueda} en {CACHE_RUEDAS}: {[e.name for e in encontradas]}")
        ruedas.append(encontradas[0])
    return ruedas


def mascara_a_alfa(origen: Path, destino: Path, color: tuple[int, int, int] = (0, 0, 0)) -> None:
    """Las máscaras son de un canal (la forma en blanco); mask-image usa el canal alfa."""
    mascara = Image.open(origen).convert("L")
    imagen = Image.new("RGBA", mascara.size, (*color, 255))
    imagen.putalpha(mascara)
    imagen.save(destino, optimize=True)


def copiar_recursos(salida: Path) -> None:
    iconos = salida / "recursos" / "iconos"
    iconos.mkdir(parents=True)
    for origen in sorted((RECURSOS / "iconos").glob("*.png")):
        mascara_a_alfa(origen, iconos / origen.name)
    shutil.copy2(RECURSOS / "iconos" / "LICENCIA-game-icons.txt", iconos)
    shutil.copytree(RECURSOS / "fuentes", salida / "recursos" / "fuentes")
    shutil.copy2(RECURSOS / "CREDITOS.md", salida / "CREDITOS.md")
    favicon = Image.open(RECURSOS / "iconos" / "dice-twenty-faces-twenty.png").convert("L").resize((64, 64), Image.LANCZOS)
    icono = Image.new("RGBA", favicon.size, (*COLOR_FAVICON, 255))
    icono.putalpha(favicon)
    icono.save(salida / "recursos" / "favicon.png", optimize=True)


def huella(*rutas: Path) -> str:
    resumen = hashlib.sha256()
    for ruta in rutas:
        resumen.update(ruta.name.encode())
        resumen.update(ruta.read_bytes())
    return resumen.hexdigest()[:12]


def compilar(salida: Path) -> Path:
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as temporal:
        crear_zip(salida / "creador.zip", Path(temporal))
    (salida / "ruedas").mkdir()
    ruedas = [Path(shutil.copy2(r, salida / "ruedas")) for r in descargar_ruedas()]
    copiar_recursos(salida)
    fuentes_pagina = [RAIZ / "web" / nombre for nombre in PAGINA]
    marca = huella(salida / "creador.zip", *ruedas, *fuentes_pagina)
    for origen in fuentes_pagina:
        (salida / origen.name).write_text(origen.read_text(encoding="utf-8").replace("__HASH__", marca), encoding="utf-8")
    manifiesto = {"version": __version__, "edicion": EDICION, "huella": marca, "ruedas": [r.name for r in ruedas]}
    (salida / "version.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: servir los archivos tal cual
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara la versión web del creador de personajes.")
    parser.add_argument("--salida", type=Path, default=RAIZ / "dist" / "web")
    salida = compilar(parser.parse_args().salida.resolve())
    tamano = sum(r.stat().st_size for r in salida.rglob("*") if r.is_file())
    print(f"Versión web en {salida} ({tamano / 1e6:.1f} MB). Para probarla: python -m http.server -d {salida} 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
