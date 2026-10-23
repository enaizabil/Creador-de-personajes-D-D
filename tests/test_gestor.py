"""Gestor de paquetes: instalar, validar y quitar paquetes del usuario."""
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from creador.entorno import abrir_catalogo, paquetes_instalados
from creador.gestor import ErrorInstalacion, comprobar, instalar, quitar
from creador.nucleo.rutas import directorio_datos_integrados

EJEMPLO = Path(__file__).resolve().parents[1] / "docs" / "ejemplos" / "homebrew-ejemplo"


@pytest.fixture
def usuario(tmp_path):
    carpeta = tmp_path / "paquetes"
    carpeta.mkdir()
    return carpeta


def directorios(usuario):
    return [directorio_datos_integrados() / "paquetes", usuario]


def zip_de(carpeta: Path, destino: Path, extra: dict[str, str] | None = None) -> Path:
    with zipfile.ZipFile(destino, "w") as archivo:
        for ruta in carpeta.rglob("*"):
            if ruta.is_file():
                archivo.write(ruta, f"{carpeta.name}/{ruta.relative_to(carpeta)}")
        for nombre, texto in (extra or {}).items():
            archivo.writestr(nombre, texto)
    return destino


def copia_del_ejemplo(tmp_path, **cambios) -> Path:
    carpeta = tmp_path / "mi-homebrew"
    shutil.copytree(EJEMPLO, carpeta)
    manifiesto = json.loads((carpeta / "paquete.json").read_text(encoding="utf-8"))
    manifiesto.update(cambios)
    (carpeta / "paquete.json").write_text(json.dumps(manifiesto, ensure_ascii=False), encoding="utf-8")
    return carpeta


def test_el_ejemplo_es_valido():
    info, errores = comprobar(EJEMPLO)
    assert info.id == "homebrew-ejemplo" and errores == []


def test_instalar_carpeta_y_usarlo(usuario):
    instalado = instalar(EJEMPLO, directorios=directorios(usuario), destino=usuario)
    assert instalado.ruta == usuario / "homebrew-ejemplo" and not instalado.reemplazado
    assert (instalado.ruta / "LEEME.md").exists()
    _, catalogo, errores = abrir_catalogo("dnd5e-2014", ["homebrew-ejemplo"], directorios(usuario))
    assert errores == [] and catalogo.obtener("razas", "duende_del_brezo")
    assert catalogo.obtener("razas", "enano")  # y su dependencia, el SRD


def test_instalar_zip_reemplazar_y_quitar(usuario, tmp_path):
    archivo = zip_de(EJEMPLO, tmp_path / "ejemplo.zip", {"__MACOSX/._x.json": "basura"})
    instalar(archivo, directorios=directorios(usuario), destino=usuario)
    with pytest.raises(ErrorInstalacion, match="ya está instalado"):
        instalar(archivo, directorios=directorios(usuario), destino=usuario)
    assert instalar(archivo, reemplazar=True, directorios=directorios(usuario), destino=usuario).reemplazado
    quitar("homebrew-ejemplo", directorios(usuario))
    assert "homebrew-ejemplo" not in paquetes_instalados(directorios(usuario))[0]
    assert usuario.exists()  # solo se borra la carpeta del paquete


def test_no_se_instala_codigo_ni_rutas_fuera(usuario, tmp_path):
    with pytest.raises(ErrorInstalacion, match="solo puede tener datos"):
        instalar(zip_de(EJEMPLO, tmp_path / "a.zip", {"homebrew-ejemplo/malo.py": "print(1)"}),
                 directorios=directorios(usuario), destino=usuario)
    with pytest.raises(ErrorInstalacion, match="ruta no permitida"):
        instalar(zip_de(EJEMPLO, tmp_path / "b.zip", {"../fuera.json": "{}"}), directorios=directorios(usuario), destino=usuario)
    assert not (tmp_path / "fuera.json").exists() and list(usuario.iterdir()) == []


def test_no_pisa_integrados_ni_instala_con_errores(usuario, tmp_path):
    with pytest.raises(ErrorInstalacion, match="integrado"):
        instalar(copia_del_ejemplo(tmp_path, id="srd-5.1"), directorios=directorios(usuario), destino=usuario)
    shutil.rmtree(tmp_path / "mi-homebrew")
    roto = copia_del_ejemplo(tmp_path, id="roto")
    razas = json.loads((roto / "razas.json").read_text(encoding="utf-8"))
    razas["razas"][0]["tamano"] = "gigantesco"
    (roto / "razas.json").write_text(json.dumps(razas, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ErrorInstalacion, match="tiene errores"):
        instalar(roto, directorios=directorios(usuario), destino=usuario)
    assert list(usuario.iterdir()) == []


def test_dependencias(usuario, tmp_path):
    with pytest.raises(ErrorInstalacion, match="necesita no-existe"):
        instalar(copia_del_ejemplo(tmp_path, id="huerfano", depende_de=["no-existe"]), directorios=directorios(usuario),
                 destino=usuario)
    instalar(EJEMPLO, directorios=directorios(usuario), destino=usuario)
    shutil.rmtree(tmp_path / "mi-homebrew")
    hijo = copia_del_ejemplo(tmp_path, id="hijo", depende_de=["homebrew-ejemplo"], archivos=["dotes.json"])
    datos = json.loads((hijo / "dotes.json").read_text(encoding="utf-8"))
    datos["dotes"][0]["id"] = "otra_dote"
    (hijo / "dotes.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    instalar(hijo, directorios=directorios(usuario), destino=usuario)
    with pytest.raises(ErrorInstalacion, match="lo necesitan"):
        quitar("homebrew-ejemplo", directorios(usuario))


def test_no_se_quitan_los_integrados(usuario):
    with pytest.raises(ErrorInstalacion, match="viene con el programa"):
        quitar("srd-5.1", directorios(usuario))
    with pytest.raises(ErrorInstalacion, match="No hay ningún paquete"):
        quitar("nada", directorios(usuario))


def test_no_es_un_paquete(usuario, tmp_path):
    (tmp_path / "vacia").mkdir()
    with pytest.raises(ErrorInstalacion, match="No hay ningún paquete.json"):
        instalar(tmp_path / "vacia", directorios=directorios(usuario), destino=usuario)
    (tmp_path / "texto.txt").write_text("hola", encoding="utf-8")
    with pytest.raises(ErrorInstalacion, match="no es un .zip ni una carpeta"):
        instalar(tmp_path / "texto.txt", directorios=directorios(usuario), destino=usuario)
