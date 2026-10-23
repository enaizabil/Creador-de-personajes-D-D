"""Validación del contenido de los paquetes de 5e (2014).

Pensada para quien escribe paquetes a mano: cada error indica la ruta exacta
dentro de la entrada (p. ej. ``niveles.4[0].aplicar[1]: falta «car»``).
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from ...nucleo.efectos import MARCADOR_OPCION
from ...nucleo.expresiones import comprobar
from .constantes import (
    CARACTERISTICAS,
    CATEGORIAS_COMPETENCIA,
    CATEGORIAS_OBJETO,
    CONDICIONES,
    ESCUELAS_MAGIA,
    GRUPOS_COMPETENCIA,
    HABILIDADES,
    NIVEL_INICIO_PROGRESION,
    PASIVAS,
    RASGOS_PERFIL,
    RECARGAS,
    REGLAS_OPCIONALES,
    TAMANOS,
    VALOR_MAXIMO_PERFIL,
)

if TYPE_CHECKING:
    from ...nucleo.paquetes import Catalogo

CATEGORIAS = (
    "razas", "subrazas", "clases", "subclases", "trasfondos", "dotes", "opciones", "conjuros", "objetos", "idiomas",
    "preguntas", "recomendaciones",
)
# Lo que el cuestionario puede recomendar o pesar directamente («clases:guerrero»).
CATEGORIAS_RECOMENDABLES = ("razas", "subrazas", "clases", "subclases", "trasfondos")
EJES_ALINEAMIENTO = ("orden", "moral")

# Variables disponibles en los textos con {expresiones} y en «usos».
VARIABLES_EXPRESION = {
    "nivel", "nivel_clase", "competencia", "escala", "conjuro",
    *(f"mod_{c}" for c in CARACTERISTICAS),
}
FUENTES_EQUIPO = ("objetos", "armas", "herramientas")
CLAVES_REQUISITO = ("caracteristicas", "alguna_caracteristica", "competencia", "lanzador", "texto")

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
    "bonificador_salvacion": ("valor",),
    "iniciativa": ("valor",),
    "ignora_penalizacion_armadura": (),
    "pasiva": ("habilidad", "valor"),
    "max_des_armadura_media": ("valor",),
    "sin_desventaja_sigilo": (),
    "ataque_des": ("armas",),
    "ataque_desarmado": ("dano",),
    "rasgo": ("nombre",),
    "conjuro": ("id",),
    "dote": ("id",),
    "opcion": ("id",),
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
    "opciones": {"nombre": str, "grupo": str},
    "conjuros": {"nombre": str, "nivel": int, "escuela": str, "listas": list},
    "objetos": {"nombre": str, "categoria": str},
    "idiomas": {"nombre": str},
    "preguntas": {"nombre": str, "texto": str, "respuestas": list},
    "recomendaciones": {"nombre": str},
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
    for campo in ("nivel_minimo", "nivel_clase_minimo"):
        valor = efecto.get(campo)
        if valor is not None and (not isinstance(valor, int) or not 1 <= valor <= 20):
            errores.append(f"«{campo}» debe ser un entero entre 1 y 20")
    if "nivel_clase_minimo" in efecto and not efecto.get("clase"):
        errores.append("«nivel_clase_minimo» necesita «clase»")

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
    elif tipo == "pasiva":
        if efecto.get("habilidad") not in PASIVAS:
            errores.append(f"«habilidad» debe ser una de {', '.join(PASIVAS)}")
    elif tipo == "rasgo":
        errores.extend(_validar_rasgo(efecto))
    elif tipo == "ataque_desarmado":
        errores.extend(_validar_escala(efecto))
        if isinstance(efecto.get("dano"), str):
            errores.extend(comprobar(efecto["dano"], VARIABLES_EXPRESION))
    elif tipo == "conjuro":
        if efecto.get("siempre_preparado") and not efecto.get("clase"):
            errores.append("un conjuro «siempre_preparado» necesita «clase»")
        if efecto.get("cuenta_como_conocido") and not efecto.get("clase"):
            errores.append("un conjuro «cuenta_como_conocido» necesita «clase»")
    elif tipo == "bonificador_salvacion":
        valor = efecto.get("valor")
        if isinstance(valor, str):
            errores.extend(comprobar(valor, VARIABLES_EXPRESION, es_expresion=True))
        elif not isinstance(valor, int) or isinstance(valor, bool):
            errores.append("«valor» debe ser un número o una expresión")
        cars = efecto.get("caracteristicas", "todas")
        if cars != "todas" and (not isinstance(cars, list) or any(c not in CARACTERISTICAS for c in cars)):
            errores.append("«caracteristicas» debe ser \"todas\" o una lista de características")
    return errores


def _validar_escala(efecto: dict) -> list[str]:
    escala = efecto.get("escala")
    if escala is None:
        return []
    if not isinstance(escala, dict) or not all(str(n).isdigit() and 1 <= int(n) <= 20 for n in escala):
        return ["«escala» debe ser un objeto {\"nivel\": valor} con niveles de 1 a 20"]
    return []


def _validar_rasgo(efecto: dict) -> list[str]:
    errores = _validar_escala(efecto)
    if isinstance(efecto.get("resumen"), str):
        errores.extend(comprobar(efecto["resumen"], VARIABLES_EXPRESION))
    if "usos" in efecto:
        usos = efecto["usos"]
        # Tabla {"nivel": usos}: null quita el límite desde ese nivel (Furia a nivel 20).
        if isinstance(usos, dict):
            if not all(str(n).isdigit() and 1 <= int(n) <= 20 for n in usos):
                errores.append("«usos» por nivel debe usar niveles de 1 a 20")
            valores = list(usos.values())
        else:
            valores = [usos]
        for valor in valores:
            if isinstance(valor, str):
                errores.extend(comprobar(valor, VARIABLES_EXPRESION, es_expresion=True))
            elif not (valor is None and isinstance(usos, dict)) and (not isinstance(valor, int) or isinstance(valor, bool)):
                errores.append("«usos» debe ser un número, una expresión o una tabla {\"nivel\": usos}")
    recarga = efecto.get("recarga")
    recargas = recarga.values() if isinstance(recarga, dict) else [recarga]
    if any(r not in (None, *RECARGAS) for r in recargas):
        errores.append(f"«recarga» debe ser una de {', '.join(RECARGAS)} (o una tabla {{\"nivel\": recarga}})")
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
    if "perfil" in entrada:
        errores.extend(_validar_perfil(entrada["perfil"]))
    requeridas = entrada.get("requiere_reglas", [])
    if not isinstance(requeridas, list) or any(r not in REGLAS_OPCIONALES for r in requeridas):
        errores.append(f"«requiere_reglas» debe ser una lista con: {', '.join(REGLAS_OPCIONALES)}")
    if "niveles" in entrada:
        errores.extend(_validar_niveles(entrada["niveles"]))

    if categoria == "razas" and entrada["tamano"] not in TAMANOS:
        errores.append(f"tamaño desconocido «{entrada['tamano']}»")
    elif categoria == "clases":
        errores.extend(_validar_clase(entrada))
    elif categoria == "subclases":
        completos = entrada.get("niveles_completos", 20)
        if not isinstance(completos, int) or not 1 <= completos <= 20:
            errores.append("«niveles_completos» debe estar entre 1 y 20")
        if "lanzamiento" in entrada:
            errores.extend(_validar_lanzamiento(entrada["lanzamiento"]))
        if not isinstance(entrada.get("conjuros_adicionales", []), list):
            errores.append("«conjuros_adicionales» debe ser una lista de ids")
    elif categoria == "dotes" and "prerrequisito" in entrada:
        errores.extend(_validar_requisito(entrada["prerrequisito"], "prerrequisito"))
    elif categoria == "preguntas":
        errores.extend(_validar_pregunta(entrada))
    elif categoria == "recomendaciones":
        errores.extend(f"«{c}» debe ser una lista de ids" for c in ("conjuros", "opciones", "dotes")
                       if not isinstance(entrada.get(c, []), list) or not all(isinstance(i, str) for i in entrada.get(c, [])))
    elif categoria == "trasfondos":
        if "equipo" in entrada:
            errores.extend(_validar_equipo(entrada["equipo"], "equipo"))
        if "personalidad" in entrada:
            errores.extend(_validar_personalidad(entrada["personalidad"]))
    elif categoria == "conjuros":
        if not 0 <= entrada["nivel"] <= 9:
            errores.append("«nivel» debe estar entre 0 (truco) y 9")
        if entrada["escuela"] not in ESCUELAS_MAGIA:
            errores.append(f"escuela desconocida «{entrada['escuela']}»")
    elif categoria == "objetos":
        errores.extend(_validar_objeto(entrada))
    return errores


def _validar_perfil(perfil) -> list[str]:
    if not isinstance(perfil, dict):
        return ["«perfil» debe ser un objeto {rasgo: valor}"]
    errores = [f"perfil: rasgo desconocido «{r}» (válidos: {', '.join(RASGOS_PERFIL)})" for r in perfil if r not in RASGOS_PERFIL]
    errores += [f"perfil: «{r}» debe ser un entero de 0 a {VALOR_MAXIMO_PERFIL}" for r, v in perfil.items()
                if r in RASGOS_PERFIL and (not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= VALOR_MAXIMO_PERFIL)]
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
    completos = clase.get("niveles_completos", 20)
    if not isinstance(completos, int) or not 1 <= completos <= 20:
        errores.append("«niveles_completos» debe estar entre 1 y 20")
    if "lanzamiento" in clase:
        errores.extend(_validar_lanzamiento(clase["lanzamiento"]))
    if "requisitos_multiclase" in clase:
        errores.extend(_validar_requisito(clase["requisitos_multiclase"], "requisitos_multiclase"))
    if "equipo_inicial" in clase:
        errores.extend(_validar_equipo(clase["equipo_inicial"], "equipo_inicial"))
    return errores


def _validar_requisito(requisito, campo: str) -> list[str]:
    if not isinstance(requisito, dict):
        return [f"«{campo}» debe ser un objeto"]
    errores = [f"{campo}: clave desconocida «{k}»" for k in requisito if k not in CLAVES_REQUISITO]
    for clave in ("caracteristicas", "alguna_caracteristica"):
        valores = requisito.get(clave, {})
        if not isinstance(valores, dict) or any(c not in CARACTERISTICAS or not isinstance(v, int)
                                                for c, v in valores.items()):
            errores.append(f"{campo}.{clave}: debe ser {{característica: mínimo}}")
    return errores


def _validar_equipo(bloques, campo: str) -> list[str]:
    """Equipo: lista de bloques; cada bloque, lista de alternativas; cada alternativa, lista de líneas."""
    if not isinstance(bloques, list):
        return [f"«{campo}» debe ser una lista de bloques"]
    errores: list[str] = []
    for i, bloque in enumerate(bloques):
        if not isinstance(bloque, list) or not bloque:
            errores.append(f"{campo}[{i}]: cada bloque es una lista no vacía de alternativas")
            continue
        for j, alternativa in enumerate(bloque):
            if not isinstance(alternativa, list):
                errores.append(f"{campo}[{i}][{j}]: cada alternativa es una lista de líneas")
                continue
            for k, linea in enumerate(alternativa):
                ruta = f"{campo}[{i}][{j}][{k}]"
                if not isinstance(linea, dict) or ("id" in linea) == ("desde" in linea):
                    errores.append(f"{ruta}: cada línea lleva «id» o «desde» (no ambos)")
                elif "desde" in linea and linea["desde"] not in FUENTES_EQUIPO:
                    errores.append(f"{ruta}: «desde» debe ser una de {', '.join(FUENTES_EQUIPO)}")
                elif not isinstance(linea.get("cantidad", 1), int):
                    errores.append(f"{ruta}: «cantidad» debe ser un entero")
    return errores


def _validar_personalidad(personalidad) -> list[str]:
    if not isinstance(personalidad, dict):
        return ["«personalidad» debe ser un objeto"]
    errores = []
    for clave in ("rasgos", "vinculos", "defectos"):
        valores = personalidad.get(clave)
        if not isinstance(valores, list) or not valores or not all(isinstance(v, str) for v in valores):
            errores.append(f"personalidad.{clave}: debe ser una lista de textos")
    ideales = personalidad.get("ideales")
    if not isinstance(ideales, list) or not ideales or not all(isinstance(i, dict) and "texto" in i for i in ideales):
        errores.append("personalidad.ideales: debe ser una lista de {\"texto\", \"alineamiento\"}")
    return errores


def _referencia_valida(referencia) -> bool:
    """«clases:guerrero»: categoría recomendable e id."""
    if not isinstance(referencia, str) or ":" not in referencia:
        return False
    categoria, id_ = referencia.split(":", 1)
    return categoria in CATEGORIAS_RECOMENDABLES and bool(id_)


def _validar_pregunta(pregunta: dict) -> list[str]:
    errores: list[str] = []
    requiere = pregunta.get("requiere", [])
    if not isinstance(requiere, list) or not all(_referencia_valida(r) for r in requiere):
        errores.append("«requiere» debe ser una lista como [\"clases:paladin\"]")
    respuestas = pregunta["respuestas"]
    if len(respuestas) < 2:
        errores.append("una pregunta necesita al menos dos respuestas")
    vistas: set[str] = set()
    for n, respuesta in enumerate(respuestas):
        ruta = f"respuestas[{n}]"
        if not isinstance(respuesta, dict) or not isinstance(respuesta.get("id"), str) \
                or not isinstance(respuesta.get("texto"), str):
            errores.append(f"{ruta}: necesita «id» y «texto»")
            continue
        if respuesta["id"] in vistas:
            errores.append(f"{ruta}: id repetido «{respuesta['id']}»")
        vistas.add(respuesta["id"])
        if "perfil" in respuesta:
            errores.extend(f"{ruta}: {e}" for e in _validar_perfil(respuesta["perfil"]))
        pesos = respuesta.get("pesos", {})
        if not isinstance(pesos, dict) or not all(_referencia_valida(r) and isinstance(v, int) and -5 <= v <= 5
                                                  for r, v in pesos.items()):
            errores.append(f"{ruta}: «pesos» debe ser {{\"clases:guerrero\": n}} con n de -5 a 5")
        eje = respuesta.get("eje", {})
        if not isinstance(eje, dict) or not all(k in EJES_ALINEAMIENTO and isinstance(v, int) and -3 <= v <= 3
                                                for k, v in eje.items()):
            errores.append(f"{ruta}: «eje» debe ser {{\"orden\": n, \"moral\": n}} con n de -3 a 3")
        if not any(c in respuesta for c in ("perfil", "pesos", "eje")):
            errores.append(f"{ruta}: no puntúa nada (falta «perfil», «pesos» o «eje»)")
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
    if "libro" in config:
        libro = config["libro"]
        if not isinstance(libro, dict) or not all(isinstance(libro.get(c), int) for c in ("inicial", "por_nivel")):
            errores.append("lanzamiento: «libro» debe ser {\"inicial\": n, \"por_nivel\": n}")
        elif not config.get("preparados"):
            errores.append("lanzamiento: «libro» necesita «preparados»")
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

    for subclase in catalogo.listar("subclases"):
        for id_ in subclase.get("conjuros_adicionales", []):
            if catalogo.obtener("conjuros", id_) is None:
                errores.append(f"subclases/{subclase['id']}: el conjuro adicional «{id_}» no existe")
    for categoria, campo in (("clases", "equipo_inicial"), ("trasfondos", "equipo")):
        for entrada in catalogo.listar(categoria):
            for id_ in _ids_de_equipo(entrada.get(campo, [])):
                if catalogo.obtener("objetos", id_) is None:
                    errores.append(f"{categoria}/{entrada['id']}: el objeto «{id_}» de «{campo}» no existe")

    referencias = {"dote": "dotes", "conjuro": "conjuros", "opcion": "opciones"}
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


def _ids_de_equipo(bloques) -> Iterator[str]:
    for bloque in bloques if isinstance(bloques, list) else []:
        for alternativa in bloque if isinstance(bloque, list) else []:
            for linea in alternativa if isinstance(alternativa, list) else []:
                if isinstance(linea, dict) and isinstance(linea.get("id"), str):
                    yield linea["id"]
