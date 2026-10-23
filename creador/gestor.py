"""Gestor de paquetes: instalar (desde un .zip o una carpeta), validar y quitar paquetes del usuario.

Un paquete solo contiene datos (JSON y, si acaso, Markdown o texto): nunca código. Antes de copiar nada se
comprueba que el manifiesto es válido, que no pisa un paquete integrado, que sus dependencias están instaladas
y que su contenido carga sin errores. Los paquetes del usuario se guardan junto al ejecutable (versión
portable) o, si esa carpeta no se puede escribir, en la carpeta personal.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from .entorno import paquetes_instalados
from .nucleo.paquetes import NOMBRE_MANIFIESTO, ErrorPaquete, InfoPaquete, cargar_catalogo
from .nucleo.rutas import directorio_datos_integrados, directorios_paquetes
from .sistemas import obtener_sistema

EXTENSIONES_DATOS = {".json", ".md", ".txt"}
TAMANO_MAXIMO = 20 * 1024 * 1024  # bytes descomprimidos
FORMATO_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ErrorInstalacion(Exception):
    """El paquete no se puede instalar o quitar; el mensaje explica por qué (puede tener varias líneas)."""


@dataclass(frozen=True)
class Instalado:
    info: InfoPaquete
    ruta: Path
    reemplazado: bool


def es_integrado(info: InfoPaquete) -> bool:
    """Viene dentro del programa (no se puede quitar ni reemplazar)."""
    return info.ruta.resolve().is_relative_to((directorio_datos_integrados() / "paquetes").resolve())


def directorio_usuario() -> Path:
    """Dónde se instalan los paquetes: la carpeta «paquetes» junto al programa o, si no se puede escribir, la personal."""
    for candidato in directorios_paquetes()[1:]:
        try:
            candidato.mkdir(parents=True, exist_ok=True)
            prueba = candidato / ".prueba-escritura"
            prueba.write_text("", encoding="utf-8")
            prueba.unlink()
            return candidato
        except OSError:
            continue
    raise ErrorInstalacion("No hay ninguna carpeta de paquetes en la que se pueda escribir")


def _extraer_zip(origen: Path, destino: Path) -> None:
    with zipfile.ZipFile(origen) as archivo:
        miembros = [m for m in archivo.infolist() if not m.is_dir()]
        if sum(m.file_size for m in miembros) > TAMANO_MAXIMO:
            raise ErrorInstalacion("El .zip ocupa demasiado descomprimido para ser un paquete de datos")
        for miembro in miembros:
            ruta = Path(miembro.filename)
            if ruta.is_absolute() or ".." in ruta.parts or miembro.filename.startswith(("/", "\\")):
                raise ErrorInstalacion(f"El .zip tiene una ruta no permitida: {miembro.filename}")
            if ruta.parts[0] in ("__MACOSX",) or ruta.name.startswith("."):
                continue  # restos de macOS y archivos ocultos
            if ruta.suffix.lower() not in EXTENSIONES_DATOS:
                raise ErrorInstalacion(f"El paquete solo puede tener datos (JSON, Markdown o texto): {miembro.filename}")
            salida = destino / ruta
            salida.parent.mkdir(parents=True, exist_ok=True)
            with archivo.open(miembro) as entrada, open(salida, "wb") as fichero:
                shutil.copyfileobj(entrada, fichero)


def _copiar_carpeta(origen: Path, destino: Path) -> None:
    total = 0
    for ruta in sorted(origen.rglob("*")):
        relativa = ruta.relative_to(origen)
        if ruta.is_dir() or any(p.startswith(".") for p in relativa.parts):
            continue
        if ruta.is_symlink():
            raise ErrorInstalacion(f"El paquete no puede tener enlaces simbólicos: {relativa}")
        if ruta.suffix.lower() not in EXTENSIONES_DATOS:
            raise ErrorInstalacion(f"El paquete solo puede tener datos (JSON, Markdown o texto): {relativa}")
        total += ruta.stat().st_size
        if total > TAMANO_MAXIMO:
            raise ErrorInstalacion("La carpeta ocupa demasiado para ser un paquete de datos")
        (destino / relativa).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ruta, destino / relativa)


def _carpeta_del_paquete(raiz: Path) -> Path:
    manifiestos = list(raiz.rglob(NOMBRE_MANIFIESTO))
    if not manifiestos:
        raise ErrorInstalacion(f"No hay ningún {NOMBRE_MANIFIESTO}: no parece un paquete de contenido")
    if len(manifiestos) > 1:
        raise ErrorInstalacion("Hay varios paquetes juntos; instálalos de uno en uno")
    return manifiestos[0].parent


def comprobar(origen: Path, directorios: Iterable[Path] | None = None) -> tuple[InfoPaquete, list[str]]:
    """Lee y valida un paquete sin instalarlo. Devuelve su información y los errores encontrados."""
    with tempfile.TemporaryDirectory() as temporal:
        carpeta = _preparar(Path(origen), Path(temporal))
        return _validar(carpeta, directorios, reemplazar=True)


def _preparar(origen: Path, temporal: Path) -> Path:
    if origen.is_dir():
        _copiar_carpeta(origen, temporal)
    elif zipfile.is_zipfile(origen):
        _extraer_zip(origen, temporal)
    else:
        raise ErrorInstalacion(f"{origen.name} no es un .zip ni una carpeta")
    return _carpeta_del_paquete(temporal)


def _validar(carpeta: Path, directorios: Iterable[Path] | None, reemplazar: bool) -> tuple[InfoPaquete, list[str]]:
    try:
        info = InfoPaquete.desde_manifiesto(carpeta / NOMBRE_MANIFIESTO)
    except ErrorPaquete as exc:
        raise ErrorInstalacion(str(exc)) from exc
    if not FORMATO_ID.match(info.id):
        raise ErrorInstalacion(f"El id «{info.id}» solo puede tener minúsculas, números, puntos y guiones")
    try:
        sistema = obtener_sistema(info.sistema)
    except KeyError as exc:
        raise ErrorInstalacion(str(exc.args[0])) from exc
    disponibles, _ = paquetes_instalados(directorios)
    existente = disponibles.get(info.id)
    if existente is not None and es_integrado(existente):
        raise ErrorInstalacion(f"Ya hay un paquete integrado con el id «{info.id}»: cambia el id del tuyo")
    if existente is not None and not reemplazar:
        raise ErrorInstalacion(f"El paquete «{info.id}» ya está instalado ({existente.version}). Quítalo antes o "
                               "elige reemplazarlo.")
    faltan = [d for d in info.depende_de if d not in disponibles]
    if faltan:
        raise ErrorInstalacion(f"«{info.nombre}» necesita {', '.join(faltan)}, que no está instalado")
    for archivo in info.archivos:
        if not (carpeta / archivo).is_file():
            raise ErrorInstalacion(f"El manifiesto cita «{archivo}», que no está en el paquete")
    prueba = {**disponibles, info.id: replace(info, ruta=carpeta)}
    try:
        _, errores = cargar_catalogo(sistema, [info.id], prueba)
    except ErrorPaquete as exc:
        raise ErrorInstalacion(str(exc)) from exc
    return info, errores


def instalar(origen: Path, reemplazar: bool = False, directorios: Iterable[Path] | None = None,
             destino: Path | None = None) -> Instalado:
    """Valida el paquete y lo copia a la carpeta de paquetes del usuario. Si tiene errores, no se instala."""
    directorios = list(directorios) if directorios is not None else None
    with tempfile.TemporaryDirectory() as temporal:
        carpeta = _preparar(Path(origen), Path(temporal))
        info, errores = _validar(carpeta, directorios, reemplazar)
        if errores:
            resumen = "\n".join(f"- {e}" for e in errores[:15])
            mas = f"\n… y {len(errores) - 15} más" if len(errores) > 15 else ""
            raise ErrorInstalacion(f"«{info.nombre}» tiene errores y no se ha instalado:\n{resumen}{mas}")
        disponibles, _ = paquetes_instalados(directorios)
        anterior = disponibles.get(info.id)
        if anterior is not None:
            _borrar(anterior, directorios)
        final = (destino or directorio_usuario()) / info.id
        if final.exists():
            raise ErrorInstalacion(f"Ya existe la carpeta {final}; quítala o cambia el id del paquete")
        shutil.copytree(carpeta, final)
    return Instalado(replace(info, ruta=final), final, anterior is not None)


def _borrar(info: InfoPaquete, directorios: Iterable[Path] | None) -> None:
    """Borra la carpeta de un paquete del usuario, comprobando que está dentro de una carpeta de paquetes."""
    raices = [Path(d).resolve() for d in (directorios if directorios is not None else directorios_paquetes())]
    ruta = info.ruta.resolve()
    if es_integrado(info) or not any(ruta.is_relative_to(r) and ruta != r for r in raices):
        raise ErrorInstalacion(f"«{info.nombre}» no está en una carpeta de paquetes del usuario; no se borra")
    shutil.rmtree(ruta)


def quitar(id_: str, directorios: Iterable[Path] | None = None) -> InfoPaquete:
    """Quita un paquete del usuario (no los integrados ni los que otros necesitan)."""
    directorios = list(directorios) if directorios is not None else None
    disponibles, _ = paquetes_instalados(directorios)
    info = disponibles.get(id_)
    if info is None:
        raise ErrorInstalacion(f"No hay ningún paquete instalado con el id «{id_}»")
    if es_integrado(info):
        raise ErrorInstalacion(f"«{info.nombre}» viene con el programa y no se puede quitar (sí desmarcarlo)")
    dependientes = [o.nombre for o in disponibles.values() if id_ in o.depende_de]
    if dependientes:
        raise ErrorInstalacion(f"No se puede quitar «{info.nombre}»: lo necesitan {', '.join(dependientes)}")
    _borrar(info, directorios)
    return info
