"""Validación del contenido de los paquetes de 5e (2014).

Pensada para quien escribe paquetes a mano: cada error indica la ruta exacta
dentro de la entrada (p. ej. ``niveles.4[0].aplicar[1]: falta «car»``).
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from ...nucleo.efectos import MARCADOR_OPCION
from .constantes import (
    CARACTERISTICAS,
    CATEGORIAS_COMPETENCIA,
    CATEGORIAS_OBJETO,
    CONDICIONES,
    ESCUELAS_MAGIA,
    GRUPOS_COMPETENCIA,
    HABILIDADES,
    NIVEL_INICIO_PROGRESION,
    TAMANOS,
)

if TYPE_CHECKING:
    from ...nucleo.paquetes import Catalogo

CATEGORIAS = ("razas", "subrazas", "clases", "subclases", "trasfondos", "dotes", "conjuros", "objetos", "idiomas")

# Fuentes válidas para elecciones con ``"opciones": {"desde": ...}``.
FUENTES_OPCIONES = ("caracteristicas", "habilidades", "herramientas", "armas", *CATEGORIAS)

# Campos obligatorios por tipo de efecto.
CAMPOS_EFECTO: dict[str, tuple[str, ...]] = {
    "caracteristica": ("car", "valor"),
    "competencia": ("categoria", "id"),
    "pericia": ("id",),
    "medio_competencia": ("caracteristicas",),
    "velocidad": (),
    "sentido": ("id", "alcance"),
    "resistencia": ("dano",),
    "inmunidad": ("id",),
    "pg_maximos": (),
    "ca_alternativa": ("base",),
    "bonificador_ca": ("valor",),
    "bonificador_ataque": ("valor",),
    "iniciativa": ("valor",),
    "ignora_penalizacion_armadura": (),
    "rasgo": ("nombre",),
    "conjuro": ("id",),
    "dote": ("id",),
    "mejora_caracteristica": (),
    "eleccion": ("id", "opciones"),
}

CAMPOS_ENTRADA: dict[str, dict[str, type]] = {
    "razas": {"nombre": str, "velocidad": int, "tamano": str},
    "subrazas": {"nombre": str, "raza": str},
    "clases": {"nombre": str, "dado_golpe": int, "salvaciones": list},
    "subclases": {"nombre": str, "clase": str},
    "trasfondos": {"nombre": str},
    "dotes": {"nombre": str},
    "conjuros": {"nombre": str, "nivel": int, "escuela": str, "listas": list},
    "objetos": {"nombre": str, "categoria": str},
    "idiomas": {"nombre": str},
}
NOMBRE_TIPO = {str: "texto", int: "número entero", list: "lista", dict: "objeto"}


def _variable(valor) -> bool:
    """Valores que dependen de una elección (``$opcion``) no se pueden comprobar aquí."""
    return isinstance(valor, str) and MARCADOR_OPCION in valor


def listas_de_efectos(entrada: dict) -> Iterator[tuple[str, list]]:
    for campo in ("efectos", "competencias", "competencias_multiclase"):
        if campo in entrada:
            yield campo, entrada[campo]
    niveles = entrada.get("niveles", {})
    if isinstance(niveles, dict):
        for nivel, efectos in niveles.items():
            yield f"niveles.{nivel}", efectos


def recorrer_efectos(efectos) -> Iterator[dict]:
    """Todos los efectos, incluidos los anidados en elecciones."""
    for efecto in efectos if isinstance(efectos, list) else []:
        if not isinstance(efecto, dict):
            continue
        yield efecto
        if efecto.get("tipo") == "eleccion":
            yield from recorrer_efectos(efecto.get("aplicar", []))
            opciones = efecto.get("opciones")
            if isinstance(opciones, list):
                for opcion in opciones:
                    if isinstance(opcion, dict):
                        yield from recorrer_efectos(opcion.get("efectos", []))


def validar_efectos(efectos, ruta: str) -> list[str]:
    if not isinstance(efectos, list):
        return [f"{ruta}: debe ser una lista de efectos"]
    errores: list[str] = []
    for indice, efecto in enumerate(efectos):
        r = f"{ruta}[{indice}]"
        if not isinstance(efecto, dict):
            errores.append(f"{r}: cada efecto debe ser un objeto")
            continue
        tipo = efecto.get("tipo")
        if tipo not in CAMPOS_EFECTO:
            errores.append(f"{r}: tipo de efecto desconocido «{tipo}»")
            continue
        errores.extend(f"{r}: falta «{campo}»" for campo in CAMPOS_EFECTO[tipo] if campo not in efecto)
        errores.extend(f"{r}: {e}" for e in _validar_efecto(tipo, efecto))
        if tipo == "eleccion":
            errores.extend(_validar_eleccion(efecto, r))
    return errores


def _validar_efecto(tipo: str, efecto: dict) -> list[str]:
    errores: list[str] = []
    condicion = efecto.get("condicion")
    condiciones = [condicion] if isinstance(condicion, str) else (condicion or [])
    errores.extend(f"condición desconocida «{c}»" for c in condiciones if c not in CONDICIONES)

    if tipo == "caracteristica":
        car = efecto.get("car")
        if car is not None and not _variable(car) and car not in CARACTERISTICAS:
            errores.append(f"característica desconocida «{car}»")
    elif tipo == "competencia":
        categoria, id_ = efecto.get("categoria"), efecto.get("id")
        if categoria is not None and categoria not in CATEGORIAS_COMPETENCIA:
            errores.append(f"categoría de competencia desconocida «{categoria}»")
        if categoria == "habilidad" and id_ is not None and not _variable(id_) and id_ not in HABILIDADES:
            errores.append(f"habilidad desconocida «{id_}»")
        if categoria == "salvacion" and id_ is not None and not _variable(id_) and id_ not in CARACTERISTICAS:
            errores.append(f"salvación desconocida «{id_}»")
    elif tipo == "medio_competencia":
        cars = efecto.get("caracteristicas")
        if cars != "todas" and (not isinstance(cars, list) or any(c not in CARACTERISTICAS for c in cars)):
            errores.append("«caracteristicas» debe ser \"todas\" o una lista de características")
    elif tipo == "ca_alternativa":
        if any(c not in CARACTERISTICAS for c in efecto.get("suma", [])):
            errores.append("«suma» contiene características desconocidas")
    return errores


def _validar_eleccion(efecto: dict, ruta: str) -> list[str]:
    errores: list[str] = []
    elegir = efecto.get("elegir", 1)
    if not isinstance(elegir, int) or elegir < 1:
        errores.append(f"{ruta}: «elegir» debe ser un entero mayor que 0")
    opciones = efecto.get("opciones")
    if isinstance(opciones, dict):
        if opciones.get("desde") not in FUENTES_OPCIONES:
            errores.append(f"{ruta}: fuente de opciones desconocida «{opciones.get('desde')}»")
    elif isinstance(opciones, list):
        if efecto.get("fuente") is not None and efecto["fuente"] not in FUENTES_OPCIONES:
            errores.append(f"{ruta}: fuente desconocida «{efecto['fuente']}»")
        for indice, opcion in enumerate(opciones):
            if isinstance(opcion, dict):
                if "id" not in opcion:
                    errores.append(f"{ruta}.opciones[{indice}]: falta «id»")
                if "efectos" in opcion:
                    errores.extend(validar_efectos(opcion["efectos"], f"{ruta}.opciones[{indice}].efectos"))
            elif not isinstance(opcion, str):
                errores.append(f"{ruta}.opciones[{indice}]: debe ser un id o un objeto con «id»")
    elif opciones is not None:
        errores.append(f"{ruta}: «opciones» debe ser una lista o {{\"desde\": ...}}")
    if "aplicar" in efecto:
        errores.extend(validar_efectos(efecto["aplicar"], f"{ruta}.aplicar"))
    return errores


def validar_entrada(categoria: str, entrada: dict) -> list[str]:
    errores: list[str] = []
    for campo, tipo in CAMPOS_ENTRADA.get(categoria, {}).items():
        if campo not in entrada:
            errores.append(f"falta el campo «{campo}»")
        elif not isinstance(entrada[campo], tipo):
            errores.append(f"«{campo}» debe ser {NOMBRE_TIPO[tipo]}")
    if errores:
        return errores

    for ruta, efectos in listas_de_efectos(entrada):
        errores.extend(validar_efectos(efectos, ruta))
    if "niveles" in entrada:
        errores.extend(_validar_niveles(entrada["niveles"]))

    if categoria == "razas" and entrada["tamano"] not in TAMANOS:
        errores.append(f"tamaño desconocido «{entrada['tamano']}»")
    elif categoria == "clases":
        errores.extend(_validar_clase(entrada))
    elif categoria == "subclases" and "lanzamiento" in entrada:
        errores.extend(_validar_lanzamiento(entrada["lanzamiento"]))
    elif categoria == "conjuros":
        if not 0 <= entrada["nivel"] <= 9:
            errores.append("«nivel» debe estar entre 0 (truco) y 9")
        if entrada["escuela"] not in ESCUELAS_MAGIA:
            errores.append(f"escuela desconocida «{entrada['escuela']}»")
    elif categoria == "objetos":
        errores.extend(_validar_objeto(entrada))
    return errores


def _validar_niveles(niveles) -> list[str]:
    if not isinstance(niveles, dict):
        return ["«niveles» debe ser un objeto {\"1\": [efectos], ...}"]
    return [f"nivel «{n}» fuera de 1–20" for n in niveles if not (str(n).isdigit() and 1 <= int(n) <= 20)]


def _validar_clase(clase: dict) -> list[str]:
    errores: list[str] = []
    if clase["dado_golpe"] not in (6, 8, 10, 12):
        errores.append("«dado_golpe» debe ser 6, 8, 10 o 12")
    errores.extend(f"salvación desconocida «{c}»" for c in clase["salvaciones"] if c not in CARACTERISTICAS)
    nivel_subclase = clase.get("nivel_subclase", 1)
    if not isinstance(nivel_subclase, int) or not 1 <= nivel_subclase <= 20:
        errores.append("«nivel_subclase» debe estar entre 1 y 20")
    if "lanzamiento" in clase:
        errores.extend(_validar_lanzamiento(clase["lanzamiento"]))
    return errores


def _validar_lanzamiento(config) -> list[str]:
    if not isinstance(config, dict):
        return ["«lanzamiento» debe ser un objeto"]
    errores: list[str] = []
    if config.get("caracteristica") not in CARACTERISTICAS:
        errores.append("lanzamiento: «caracteristica» desconocida o ausente")
    if config.get("progresion") not in NIVEL_INICIO_PROGRESION:
        errores.append(f"lanzamiento: «progresion» debe ser una de {', '.join(NIVEL_INICIO_PROGRESION)}")
    for tabla in ("trucos_conocidos", "conjuros_conocidos"):
        if tabla in config and (not isinstance(config[tabla], list) or len(config[tabla]) != 20):
            errores.append(f"lanzamiento: «{tabla}» debe ser una lista de 20 valores (niveles 1–20)")
    if config.get("preparados") not in (None, "nivel", "mitad_nivel"):
        errores.append("lanzamiento: «preparados» debe ser \"nivel\" o \"mitad_nivel\"")
    return errores


def _validar_objeto(objeto: dict) -> list[str]:
    categoria = objeto["categoria"]
    if categoria not in CATEGORIAS_OBJETO:
        return [f"categoría de objeto desconocida «{categoria}»"]
    if categoria == "arma":
        arma = objeto.get("arma")
        if not isinstance(arma, dict):
            return ["un arma necesita el objeto «arma»"]
        errores = [f"arma: falta «{c}»" for c in ("categoria", "tipo", "dano", "tipo_dano") if c not in arma]
        if arma.get("categoria") not in (None, "sencilla", "marcial"):
            errores.append("arma: «categoria» debe ser sencilla o marcial")
        if arma.get("tipo") not in (None, "cuerpo_a_cuerpo", "distancia"):
            errores.append("arma: «tipo» debe ser cuerpo_a_cuerpo o distancia")
        return errores
    if categoria == "armadura":
        armadura = objeto.get("armadura")
        if not isinstance(armadura, dict):
            return ["una armadura necesita el objeto «armadura»"]
        errores = [f"armadura: falta «{c}»" for c in ("tipo", "ca") if c not in armadura]
        if armadura.get("tipo") not in (None, "ligera", "media", "pesada"):
            errores.append("armadura: «tipo» debe ser ligera, media o pesada")
        return errores
    return []


def validar_catalogo(catalogo: Catalogo) -> list[str]:
    """Referencias cruzadas: subrazas→razas, subclases→clases y ids citados en efectos."""
    errores: list[str] = []
    for subraza in catalogo.listar("subrazas"):
        if catalogo.obtener("razas", subraza.get("raza", "")) is None:
            errores.append(f"subrazas/{subraza['id']}: la raza «{subraza.get('raza')}» no existe")
    for subclase in catalogo.listar("subclases"):
        if catalogo.obtener("clases", subclase.get("clase", "")) is None:
            errores.append(f"subclases/{subclase['id']}: la clase «{subclase.get('clase')}» no existe")

    referencias = {"dote": "dotes", "conjuro": "conjuros"}
    for categoria in CATEGORIAS:
        for entrada in catalogo.listar(categoria):
            for _, efectos in listas_de_efectos(entrada):
                for efecto in recorrer_efectos(efectos):
                    tipo, id_ = efecto.get("tipo"), efecto.get("id")
                    if not isinstance(id_, str) or _variable(id_):
                        continue
                    destino = referencias.get(tipo)
                    if tipo == "competencia" and efecto.get("categoria") == "idioma":
                        destino = "idiomas"
                    elif tipo == "competencia" and efecto.get("categoria") in ("arma", "armadura", "herramienta"):
                        destino = None if id_ in GRUPOS_COMPETENCIA else "objetos"
                    if destino and catalogo.obtener(destino, id_) is None:
                        errores.append(f"{categoria}/{entrada['id']}: «{id_}» no existe en {destino}")
    return errores
