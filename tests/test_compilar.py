"""Preparación de las ediciones del ejecutable y rutas de la versión portable."""
import importlib.util
import json
import sys
from pathlib import Path

from creador.nucleo import rutas

RAIZ = Path(__file__).resolve().parents[1]


def cargar_compilar():
    spec = importlib.util.spec_from_file_location("compilar", RAIZ / "herramientas" / "compilar.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_edicion_libre_no_lleva_contenido_privado(tmp_path):
    compilar = cargar_compilar()
    datos = compilar.preparar_datos("libre", tmp_path / "libre")
    paquetes = sorted(p.name for p in (datos / "paquetes" / "dnd5e-2014").iterdir())
    assert paquetes == ["cuestionario-basico", "srd-5.1"]
    assert not (datos / "plantillas").exists()
    assert json.loads((datos / "edicion.json").read_text(encoding="utf-8"))["edicion"] == "libre"


def test_la_edicion_completa_lleva_todo(tmp_path):
    datos = cargar_compilar().preparar_datos("completa", tmp_path / "completa")
    paquetes = {p.name for p in (datos / "paquetes" / "dnd5e-2014").iterdir()}
    assert {"srd-5.1", "phb-2014", "dmg-2014", "tasha-2020", "cuestionario-basico"} == paquetes
    assert (datos / "plantillas" / "dnd5e-2014" / "hoja_editable_es.pdf").is_file()


def test_edicion_desde_el_codigo():
    assert rutas.edicion() == "desarrollo"


def test_carpeta_portable_congelado(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    ejecutable = tmp_path / "CreadorPersonajes" / "CreadorPersonajes.exe"
    monkeypatch.setattr(sys, "executable", str(ejecutable))
    monkeypatch.setattr(sys, "platform", "win32")
    assert rutas.directorio_portable() == ejecutable.parent
    app = tmp_path / "CreadorPersonajes" / "CreadorPersonajes.app" / "Contents" / "MacOS" / "CreadorPersonajes"
    monkeypatch.setattr(sys, "executable", str(app))
    monkeypatch.setattr(sys, "platform", "darwin")
    assert rutas.directorio_portable() == tmp_path / "CreadorPersonajes"  # junto a la .app, donde se ve


def cargar_compilar_web():
    sys.path.insert(0, str(RAIZ / "herramientas"))
    spec = importlib.util.spec_from_file_location("compilar_web", RAIZ / "herramientas" / "compilar_web.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_web_lleva_el_motor_sin_la_interfaz_de_escritorio(tmp_path):
    import zipfile

    web = cargar_compilar_web()
    web.crear_zip(tmp_path / "a.zip", tmp_path / "a")
    nombres = zipfile.ZipFile(tmp_path / "a.zip").namelist()
    assert "creador/web/sesion.py" in nombres and "creador/datos/edicion.json" in nombres
    assert not [n for n in nombres if n.startswith("creador/gui/") or "__pycache__" in n]
    paquetes = {n.split("/")[4] for n in nombres if n.startswith("creador/datos/paquetes/dnd5e-2014/")}
    assert paquetes == {"srd-5.1", "phb-2014", "dmg-2014", "tasha-2020", "cuestionario-basico"}
    web.crear_zip(tmp_path / "b.zip", tmp_path / "b")
    assert (tmp_path / "a.zip").read_bytes() == (tmp_path / "b.zip").read_bytes()  # misma huella si no cambia nada


def test_las_mascaras_de_los_iconos_pasan_a_canal_alfa(tmp_path):
    from PIL import Image

    web = cargar_compilar_web()
    web.mascara_a_alfa(web.RECURSOS / "iconos" / "elf-ear.png", tmp_path / "icono.png")
    imagen = Image.open(tmp_path / "icono.png")
    assert imagen.mode == "RGBA" and imagen.getextrema()[3] == (0, 255)
