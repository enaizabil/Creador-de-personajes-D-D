"""Descubrimiento y carga de paquetes de contenido (SRD, PHB, expansiones, homebrew).

Un paquete es una carpeta con un ``paquete.json`` (manifiesto) y uno o más
archivos JSON de contenido con la forma ``{"categoria": [entradas…]}``.
Ver ``docs/formato-paquetes.md``.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sistema import SistemaReglas

NOMBRE_MANIFIESTO = "paquete.json"
CLAVES_CONTROL = ("reemplaza", "modifica")


class ErrorPaquete(Exception):
    pass


@dataclass(frozen=True)
class InfoPaquete:
    id: str
    nombre: str
    sistema: str
    version: str
    ruta: Path
    archivos: tuple[str, ...]
    depende_de: tuple[str, ...] = ()
    tipo: str = "homebrew"  # oficial | homebrew
    licencia: str = ""
    descripcion: str = ""

    @classmethod
    def desde_manifiesto(cls, ruta_manifiesto: Path) -> InfoPaquete:
        try:
            datos = json.loads(ruta_manifiesto.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ErrorPaquete(f"{ruta_manifiesto}: no se puede leer el manifiesto ({exc})") from exc
        faltan = [c for c in ("id", "nombre", "sistema", "version", "archivos") if c not in datos]
        if faltan:
            raise ErrorPaquete(f"{ruta_manifiesto}: faltan campos {', '.join(faltan)}")
        return cls(
            id=datos["id"],
            nombre=datos["nombre"],
            sistema=datos["sistema"],
            version=str(datos["version"]),
            ruta=ruta_manifiesto.parent,
            archivos=tuple(datos["archivos"]),
            depende_de=tuple(datos.get("depende_de", [])),
            tipo=datos.get("tipo", "homebrew"),
            licencia=datos.get("licencia", ""),
            descripcion=datos.get("descripcion", ""),
        )


def descubrir_paquetes(directorios: Iterable[Path]) -> tuple[dict[str, InfoPaquete], list[str]]:
    """Busca manifiestos en los directorios, en orden de prioridad."""
    encontrados: dict[str, InfoPaquete] = {}
    avisos: list[str] = []
    for directorio in directorios:
        if not directorio.is_dir():
            continue
        for manifiesto in sorted(directorio.rglob(NOMBRE_MANIFIESTO)):
            try:
                info = InfoPaquete.desde_manifiesto(manifiesto)
            except ErrorPaquete as exc:
                avisos.append(str(exc))
                continue
            previo = encontrados.get(info.id)
            if previo is not None:
                avisos.append(f"Paquete «{info.id}» duplicado: se usa {previo.ruta} y se ignora {info.ruta}")
                continue
            encontrados[info.id] = info
    return encontrados, avisos


def coincide(entrada: dict, filtro: dict | None) -> bool:
    """Filtro por igualdad; si el campo de la entrada es una lista, basta con que contenga el valor."""
    for campo, esperado in (filtro or {}).items():
        actual = entrada.get(campo)
        esperados = esperado if isinstance(esperado, list) else [esperado]
        actuales = actual if isinstance(actual, list) else [actual]
        if not any(valor in actuales for valor in esperados):
            return False
    return True


def fusionar(base: dict, cambios: dict) -> dict:
    """Fusión profunda: los dicts se combinan, las listas se amplían y el resto se sobrescribe."""
    resultado = copy.deepcopy(base)
    for clave, valor in cambios.items():
        actual = resultado.get(clave)
        if isinstance(actual, dict) and isinstance(valor, dict):
            resultado[clave] = fusionar(actual, valor)
        elif isinstance(actual, list) and isinstance(valor, list):
            resultado[clave] = actual + [copy.deepcopy(v) for v in valor if v not in actual]
        else:
            resultado[clave] = copy.deepcopy(valor)
    return resultado


class Catalogo:
    """Contenido combinado de los paquetes activos de un sistema."""

    def __init__(self, sistema_id: str):
        self.sistema_id = sistema_id
        self.paquetes: list[InfoPaquete] = []
        self._entradas: dict[str, dict[str, dict]] = {}
        self._origen: dict[tuple[str, str], str] = {}

    def categorias(self) -> list[str]:
        return list(self._entradas)

    def obtener(self, categoria: str, id_: str) -> dict | None:
        return self._entradas.get(categoria, {}).get(id_)

    def listar(self, categoria: str, filtro: dict | None = None) -> list[dict]:
        return [e for e in self._entradas.get(categoria, {}).values() if coincide(e, filtro)]

    def origen(self, categoria: str, id_: str) -> str | None:
        return self._origen.get((categoria, id_))

    def agregar(self, categoria: str, entrada: dict, paquete_id: str) -> str | None:
        """Añade, reemplaza o modifica una entrada. Devuelve un mensaje de error o None."""
        id_ = entrada["id"]
        actuales = self._entradas.setdefault(categoria, {})
        limpia = {k: v for k, v in entrada.items() if k not in CLAVES_CONTROL}
        if entrada.get("modifica"):
            if id_ not in actuales:
                return f"«{id_}» ({categoria}) está marcado como «modifica» pero no existe en paquetes anteriores"
            actuales[id_] = fusionar(actuales[id_], limpia)
            return None
        if id_ in actuales and not entrada.get("reemplaza"):
            return f"«{id_}» ({categoria}) duplicado: ya lo define «{self._origen[(categoria, id_)]}»"
        actuales[id_] = limpia
        self._origen[(categoria, id_)] = paquete_id
        return None


def ordenar_por_dependencias(ids: Iterable[str], disponibles: dict[str, InfoPaquete]) -> list[InfoPaquete]:
    """Orden de carga con las dependencias primero; incluye las dependencias no pedidas."""
    orden: list[InfoPaquete] = []
    estado: dict[str, str] = {}

    def visitar(id_: str, cadena: list[str]) -> None:
        if estado.get(id_) == "hecho":
            return
        if estado.get(id_) == "visitando":
            raise ErrorPaquete(f"Dependencia circular: {' → '.join([*cadena, id_])}")
        info = disponibles.get(id_)
        if info is None:
            if cadena:
                raise ErrorPaquete(f"«{cadena[-1]}» necesita el paquete «{id_}», que no está instalado")
            raise ErrorPaquete(f"Paquete «{id_}» no encontrado")
        estado[id_] = "visitando"
        for dependencia in info.depende_de:
            visitar(dependencia, [*cadena, id_])
        estado[id_] = "hecho"
        orden.append(info)

    for id_ in ids:
        visitar(id_, [])
    return orden


def cargar_catalogo(
    sistema: SistemaReglas, ids: Iterable[str], disponibles: dict[str, InfoPaquete]
) -> tuple[Catalogo, list[str]]:
    """Carga los paquetes pedidos (y sus dependencias). Los errores de contenido no detienen la carga."""
    paquetes = ordenar_por_dependencias(ids, disponibles)
    catalogo = Catalogo(sistema.id)
    errores: list[str] = []
    for info in paquetes:
        if info.sistema != sistema.id:
            raise ErrorPaquete(f"«{info.id}» es para el sistema «{info.sistema}», no para «{sistema.id}»")
        catalogo.paquetes.append(info)
        for nombre_archivo in info.archivos:
            errores.extend(_cargar_archivo(sistema, catalogo, info, nombre_archivo))

    for categoria in catalogo.categorias():
        for entrada in catalogo.listar(categoria):
            for error in sistema.validar_entrada(categoria, entrada):
                errores.append(f"[{catalogo.origen(categoria, entrada['id'])}] {categoria}/{entrada['id']}: {error}")
    errores.extend(sistema.validar_catalogo(catalogo))
    return catalogo, errores


def _cargar_archivo(sistema: SistemaReglas, catalogo: Catalogo, info: InfoPaquete, nombre_archivo: str) -> list[str]:
    prefijo = f"[{info.id}] {nombre_archivo}"
    try:
        contenido = json.loads((info.ruta / nombre_archivo).read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"{prefijo}: no se puede leer ({exc.strerror})"]
    except json.JSONDecodeError as exc:
        return [f"{prefijo}: JSON inválido en línea {exc.lineno}, columna {exc.colno}: {exc.msg}"]
    if not isinstance(contenido, dict):
        return [f"{prefijo}: el archivo debe ser un objeto {{categoría: [entradas]}}"]

    errores: list[str] = []
    for categoria, entradas in contenido.items():
        if categoria not in sistema.categorias:
            errores.append(f"{prefijo}: categoría desconocida «{categoria}» (válidas: {', '.join(sistema.categorias)})")
            continue
        if not isinstance(entradas, list):
            errores.append(f"{prefijo}: «{categoria}» debe ser una lista")
            continue
        for indice, entrada in enumerate(entradas):
            if not isinstance(entrada, dict) or not isinstance(entrada.get("id"), str):
                errores.append(f"{prefijo}: {categoria}[{indice}] necesita un «id» de texto")
                continue
            error = catalogo.agregar(categoria, entrada, info.id)
            if error:
                errores.append(f"{prefijo}: {error}")
    return errores
