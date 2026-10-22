"""Cálculo de la ficha de D&D 5e (2014) a partir de las decisiones del personaje."""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterator
from typing import TYPE_CHECKING

from ...nucleo.efectos import EfectoAplicado, Resolucion, ResolutorEfectos
from ...nucleo.expresiones import ErrorExpresion, evaluar, rellenar
from ...nucleo.texto import clave_alfabetica
from .caracteristicas import bonificador_competencia, modificador, validar_base
from .constantes import (
    CARACTERISTICAS,
    ESPACIOS_LANZADOR_COMPLETO,
    GRUPO_ARMA,
    GRUPO_ARMADURA,
    GRUPOS_COMPETENCIA,
    HABILIDADES,
    MAGIA_DE_PACTO,
    NIVEL_INICIO_PROGRESION,
    NIVEL_MAXIMO,
    PASIVAS,
    PROGRESIONES_LANZAMIENTO,
    PUNTUACION_MAXIMA,
    TAMANOS,
)
from .ficha import Ataque, Ficha, Lanzador, Rasgo, Tirada, ValorCaracteristica

if TYPE_CHECKING:
    from ...nucleo.paquetes import Catalogo
    from ...nucleo.personaje import EntradaClase, ObjetoInventario, Personaje
    from ...nucleo.sistema import SistemaReglas


def resolver(sistema: SistemaReglas, personaje: Personaje, catalogo: Catalogo) -> Resolucion:
    resolutor = ResolutorEfectos(sistema, catalogo, personaje)
    for efectos, origen, etiqueta in _fuentes(personaje, catalogo, resolutor.resolucion.errores):
        resolutor.resolver(efectos, origen, etiqueta)
    return resolutor.resolucion


def _fuentes(personaje: Personaje, catalogo: Catalogo, errores: list[str]) -> Iterator[tuple[list, str, str]]:
    """Listas de efectos de raza, subraza, trasfondo, clases y subclases, en ese orden."""
    for categoria, id_, campo in (("razas", personaje.raza, "raza"), ("trasfondos", personaje.trasfondo, "trasfondo")):
        if not id_:
            continue
        entrada = catalogo.obtener(categoria, id_)
        if entrada is None:
            errores.append(f"No existe {campo} «{id_}» en los paquetes activos")
            continue
        yield entrada.get("efectos", []), f"{campo}:{id_}", entrada["nombre"]
        if campo == "raza" and personaje.subraza:
            subraza = catalogo.obtener("subrazas", personaje.subraza)
            if subraza is None:
                errores.append(f"No existe la subraza «{personaje.subraza}» en los paquetes activos")
            elif subraza["raza"] != id_:
                errores.append(f"La subraza «{subraza['nombre']}» no pertenece a {entrada['nombre']}")
            else:
                yield subraza.get("efectos", []), f"subraza:{subraza['id']}", subraza["nombre"]

    if personaje.subraza and not personaje.raza:
        errores.append("Hay subraza elegida pero no raza")
    if personaje.nivel_total > NIVEL_MAXIMO:
        errores.append(f"El nivel total ({personaje.nivel_total}) supera el máximo de {NIVEL_MAXIMO}")
    if len(personaje.clases) > 1 and not personaje.reglas_opcionales.get("multiclase", True):
        errores.append("El personaje tiene varias clases pero la regla opcional de multiclase está desactivada")

    for indice, entrada in enumerate(personaje.clases):
        clase = catalogo.obtener("clases", entrada.clase)
        if clase is None:
            errores.append(f"No existe la clase «{entrada.clase}» en los paquetes activos")
            continue
        if not 1 <= entrada.nivel <= NIVEL_MAXIMO:
            errores.append(f"{clase['nombre']}: el nivel debe estar entre 1 y {NIVEL_MAXIMO}")
            continue
        nombre, id_clase = clase["nombre"], clase["id"]
        if indice == 0:
            salvaciones = [{"tipo": "competencia", "categoria": "salvacion", "id": c} for c in clase["salvaciones"]]
            yield salvaciones + clase.get("competencias", []), f"clase:{id_clase}:inicial", nombre
        else:
            yield clase.get("competencias_multiclase", []), f"clase:{id_clase}:multiclase", nombre
        niveles = clase.get("niveles", {})
        for nivel in range(1, entrada.nivel + 1):
            yield niveles.get(str(nivel), []), f"clase:{id_clase}:{nivel}", f"{nombre} {nivel}"

        if not entrada.subclase:
            continue
        subclase = catalogo.obtener("subclases", entrada.subclase)
        nivel_subclase = clase.get("nivel_subclase", 1)
        if subclase is None:
            errores.append(f"No existe la subclase «{entrada.subclase}» en los paquetes activos")
        elif subclase["clase"] != id_clase:
            errores.append(f"La subclase «{subclase['nombre']}» no pertenece a {nombre}")
        elif entrada.nivel < nivel_subclase:
            errores.append(f"{nombre}: la subclase se elige a nivel {nivel_subclase}")
        else:
            sub_niveles = subclase.get("niveles", {})
            for nivel in range(1, entrada.nivel + 1):
                yield (
                    sub_niveles.get(str(nivel), []),
                    f"subclase:{subclase['id']}:{nivel}",
                    f"{subclase['nombre']} {nivel}",
                )


def calcular(sistema: SistemaReglas, personaje: Personaje, catalogo: Catalogo) -> Ficha:
    resolucion = resolver(sistema, personaje, catalogo)
    avisos = list(resolucion.errores)
    avisos += [f"Elección pendiente en {p.etiqueta}: {p.nombre} (faltan {p.faltan})" for p in resolucion.pendientes]
    avisos += validar_base(personaje.metodo_caracteristicas, personaje.caracteristicas_base)

    nivel = personaje.nivel_total
    competencia = bonificador_competencia(nivel)
    armadura, escudo, objetos = _equipo(personaje, catalogo, avisos)
    aplicables = [a for a in resolucion.aplicados if _cumple_condicion(a.efecto.get("condicion"), armadura, escudo)]

    def de_tipo(tipo: str) -> list[dict]:
        return [a.efecto for a in aplicables if a.tipo == tipo]

    puntuaciones = _puntuaciones(personaje, de_tipo("caracteristica"))
    mods = {c: modificador(v) for c, v in puntuaciones.items()}

    competencias: dict[str, set[str]] = defaultdict(set)
    for efecto in de_tipo("competencia"):
        competencias[efecto["categoria"]].add(efecto["id"])
    pericias = {e["id"] for e in de_tipo("pericia")}
    medio = _medio_competencia(de_tipo("medio_competencia"), competencia)

    salvaciones = {
        c: Tirada(nombre, c, mods[c] + (competencia if c in competencias["salvacion"] else 0), c in competencias["salvacion"])
        for c, nombre in CARACTERISTICAS.items()
    }
    habilidades = {}
    for id_, (nombre, car) in HABILIDADES.items():
        competente = id_ in competencias["habilidad"]
        experto = competente and id_ in pericias
        extra = 2 * competencia if experto else competencia if competente else medio.get(car, 0)
        habilidades[id_] = Tirada(nombre, car, mods[car] + extra, competente, experto)
    for id_ in pericias - competencias["habilidad"] - competencias["herramienta"]:
        avisos.append(f"Pericia en «{id_}» sin tener competencia: no tiene efecto")
    if armadura and armadura["armadura"].get("desventaja_sigilo"):
        habilidades["sigilo"].notas = f"Desventaja ({armadura['nombre']})"
    pasivas = {h: 10 + habilidades[h].valor for h in PASIVAS}
    for efecto in de_tipo("pasiva"):
        pasivas[efecto["habilidad"]] += efecto["valor"]

    _avisos_competencia_armadura(armadura, escudo, competencias["armadura"], avisos)
    pg_maximos, dados_golpe = _puntos_golpe(personaje, catalogo, mods["con"], de_tipo("pg_maximos"), avisos)
    espacios, pacto, lanzadores = _magia(personaje, catalogo, mods, competencia, avisos)
    conjuros_innatos = _repartir_conjuros_de_efectos(de_tipo("conjuro"), lanzadores, catalogo, avisos)
    niveles_clase = _niveles_por_clase(personaje, catalogo)
    contexto = {"nivel": nivel, "competencia": competencia, **{f"mod_{c}": m for c, m in mods.items()}}
    _avisos_requisitos(personaje, catalogo, aplicables, puntuaciones, competencias,
                       bool(lanzadores or conjuros_innatos), avisos)
    raza = catalogo.obtener("razas", personaje.raza) if personaje.raza else None
    subraza = catalogo.obtener("subrazas", personaje.subraza) if personaje.subraza else None
    trasfondo = catalogo.obtener("trasfondos", personaje.trasfondo) if personaje.trasfondo else None

    return Ficha(
        nombre=personaje.nombre,
        jugador=personaje.jugador,
        raza=(subraza or raza or {}).get("nombre", ""),
        clase_y_nivel=_clase_y_nivel(personaje, catalogo),
        trasfondo=(trasfondo or {}).get("nombre", ""),
        nivel=nivel,
        experiencia=personaje.experiencia,
        caracteristicas={
            c: ValorCaracteristica(puntuaciones[c], mods[c], personaje.caracteristicas_base.get(c, 10))
            for c in CARACTERISTICAS
        },
        bonificador_competencia=competencia,
        salvaciones=salvaciones,
        habilidades=habilidades,
        percepcion_pasiva=pasivas["percepcion"],
        pasivas=pasivas,
        ca=_clase_armadura(mods, armadura, escudo, de_tipo("ca_alternativa"), de_tipo("bonificador_ca"),
                           de_tipo("max_des_armadura_media")),
        iniciativa=mods["des"] + medio.get("des", 0) + sum(e["valor"] for e in de_tipo("iniciativa")),
        velocidades=_velocidades(raza, de_tipo("velocidad"), puntuaciones["fue"], armadura,
                                 bool(de_tipo("ignora_penalizacion_armadura"))),
        pg_maximos=pg_maximos,
        dados_golpe=dados_golpe,
        tamano=TAMANOS.get((raza or {}).get("tamano", ""), ""),
        competencias=_nombres_competencias(competencias, catalogo),
        ataques=_ataques(objetos, mods, competencia, competencias["arma"], de_tipo("bonificador_ataque"),
                         de_tipo("ataque_des"))
                + _ataques_desarmados(aplicables, catalogo, mods, competencia, niveles_clase, contexto, avisos),
        rasgos=_rasgos(aplicables, catalogo, niveles_clase, contexto, avisos),
        sentidos=_sentidos(de_tipo("sentido")),
        resistencias=sorted({e["dano"] for e in de_tipo("resistencia")}),
        inmunidades=sorted({e["id"] for e in de_tipo("inmunidad")}),
        espacios_conjuro=espacios,
        magia_pacto=pacto,
        lanzadores=lanzadores,
        conjuros_innatos=conjuros_innatos,
        equipo=[_describir_objeto(item, entrada) for item, entrada in objetos],
        monedas=dict(personaje.monedas),
        detalles=dict(personaje.detalles),
        avisos=avisos,
    )


def _niveles_por_clase(personaje: Personaje, catalogo: Catalogo) -> dict[str, int]:
    return {e.clase: e.nivel for e in personaje.clases if catalogo.obtener("clases", e.clase)}


def _clase_de_origen(efecto: dict, origen: str, catalogo: Catalogo) -> str | None:
    """Clase a la que pertenece un efecto: la indicada en «clase» o la de su origen."""
    if efecto.get("clase"):
        return efecto["clase"]
    tipo, _, resto = origen.split("/")[0].split(">")[0].partition(":")
    id_ = resto.split(":")[0]
    if tipo == "clase":
        return id_
    if tipo == "subclase":
        subclase = catalogo.obtener("subclases", id_)
        return subclase["clase"] if subclase else None
    return None


def _contexto_efecto(efecto: dict, origen: str, catalogo: Catalogo, niveles_clase: dict[str, int],
                     contexto: dict) -> dict:
    """Variables para las {expresiones}: nivel de la clase del efecto y el valor de su «escala»."""
    clase = _clase_de_origen(efecto, origen, catalogo)
    nivel_clase = niveles_clase.get(clase, contexto["nivel"]) if clase else contexto["nivel"]
    escala = ""
    for umbral, valor in sorted(((int(n), v) for n, v in efecto.get("escala", {}).items())):
        if umbral <= nivel_clase:
            escala = valor
    return {**contexto, "nivel_clase": nivel_clase, "escala": escala}


def _rasgos(aplicables: list[EfectoAplicado], catalogo: Catalogo, niveles_clase: dict[str, int],
            contexto: dict, avisos: list[str]) -> list[Rasgo]:
    rasgos = []
    for aplicado in aplicables:
        if aplicado.tipo != "rasgo":
            continue
        efecto = aplicado.efecto
        variables = _contexto_efecto(efecto, aplicado.origen, catalogo, niveles_clase, contexto)
        try:
            resumen = rellenar(efecto.get("resumen", ""), variables)
            usos = efecto.get("usos")
            usos = max(0, int(evaluar(usos, variables))) if isinstance(usos, str) else usos
        except (ErrorExpresion, TypeError, ValueError) as exc:
            avisos.append(f"{efecto['nombre']}: {exc}")
            resumen, usos = efecto.get("resumen", ""), None
        rasgos.append(Rasgo(efecto["nombre"], efecto.get("descripcion", ""), aplicado.etiqueta,
                            resumen, usos, efecto.get("recarga", "")))
    return rasgos


def _texto_requisito(requisito: dict) -> str:
    partes = [" y ".join(f"{c.upper()} {v}" for c, v in requisito.get("caracteristicas", {}).items()),
              " o ".join(f"{c.upper()} {v}" for c, v in requisito.get("alguna_caracteristica", {}).items())]
    if requisito.get("competencia"):
        partes.append(f"competencia con {GRUPOS_COMPETENCIA.get(requisito['competencia'], requisito['competencia'])}")
    if requisito.get("lanzador"):
        partes.append("poder lanzar al menos un conjuro")
    return "; ".join(p for p in partes if p) or requisito.get("texto", "")


def _cumple_requisito(requisito: dict, puntuaciones: dict[str, int], competencias: dict[str, set[str]],
                      lanzador: bool) -> bool:
    if any(puntuaciones[c] < v for c, v in requisito.get("caracteristicas", {}).items()):
        return False
    alguna = requisito.get("alguna_caracteristica", {})
    if alguna and not any(puntuaciones[c] >= v for c, v in alguna.items()):
        return False
    if requisito.get("competencia") and not any(requisito["competencia"] in ids for ids in competencias.values()):
        return False
    return not (requisito.get("lanzador") and not lanzador)


def _avisos_requisitos(personaje: Personaje, catalogo: Catalogo, aplicables: list[EfectoAplicado],
                       puntuaciones: dict[str, int], competencias: dict[str, set[str]], lanzador: bool,
                       avisos: list[str]) -> None:
    """Prerrequisitos de dotes y de multiclase, comprobados con las puntuaciones finales (aproximación)."""
    for aplicado in aplicables:
        dote = catalogo.obtener("dotes", aplicado.efecto.get("dote", "")) if aplicado.tipo == "rasgo" else None
        requisito = (dote or {}).get("prerrequisito")
        if requisito and not _cumple_requisito(requisito, puntuaciones, competencias, lanzador):
            avisos.append(f"Dote {dote['nombre']}: no cumple el prerrequisito ({_texto_requisito(requisito)})")
    if len(personaje.clases) < 2:
        return
    for entrada in personaje.clases:
        clase = catalogo.obtener("clases", entrada.clase)
        requisito = (clase or {}).get("requisitos_multiclase")
        if requisito and not _cumple_requisito(requisito, puntuaciones, competencias, lanzador):
            avisos.append(f"Multiclase: {clase['nombre']} requiere {_texto_requisito(requisito)}")


def _cumple_condicion(condicion, armadura: dict | None, escudo: dict | None) -> bool:
    for c in [condicion] if isinstance(condicion, str) else (condicion or []):
        cumple = {
            "sin_armadura": armadura is None,
            "con_armadura": armadura is not None,
            "sin_armadura_pesada": armadura is None or armadura["armadura"]["tipo"] != "pesada",
            "sin_escudo": escudo is None,
            "con_escudo": escudo is not None,
        }.get(c, False)
        if not cumple:
            return False
    return True


def _puntuaciones(personaje: Personaje, mejoras: list[dict]) -> dict[str, int]:
    """Base + mejoras, sin superar 20 salvo efectos con un «maximo» mayor (que se aplican al final)."""
    valores = {c: int(personaje.caracteristicas_base.get(c, 10)) for c in CARACTERISTICAS}
    normales = [e for e in mejoras if e.get("maximo", PUNTUACION_MAXIMA) <= PUNTUACION_MAXIMA]
    elevadas = [e for e in mejoras if e.get("maximo", PUNTUACION_MAXIMA) > PUNTUACION_MAXIMA]
    for efecto in normales + elevadas:
        car, maximo = efecto["car"], efecto.get("maximo", PUNTUACION_MAXIMA)
        nuevo = valores[car] + efecto["valor"]
        valores[car] = nuevo if nuevo <= maximo else max(valores[car], maximo)
    return valores


def _medio_competencia(efectos: list[dict], competencia: int) -> dict[str, int]:
    """Bonificador a pruebas sin competencia (Polivalente, Atleta extraordinario…)."""
    resultado: dict[str, int] = {}
    for efecto in efectos:
        cars = CARACTERISTICAS if efecto["caracteristicas"] == "todas" else efecto["caracteristicas"]
        valor = math.ceil(competencia / 2) if efecto.get("redondeo") == "arriba" else competencia // 2
        for car in cars:
            resultado[car] = max(resultado.get(car, 0), valor)
    return resultado


def _equipo(
    personaje: Personaje, catalogo: Catalogo, avisos: list[str]
) -> tuple[dict | None, dict | None, list[tuple[ObjetoInventario, dict | None]]]:
    armadura = escudo = None
    objetos = []
    for item in personaje.equipo:
        entrada = catalogo.obtener("objetos", item.id) if item.id else None
        if item.id and entrada is None:
            avisos.append(f"Objeto desconocido «{item.id}»")
        objetos.append((item, entrada))
        if not (entrada and item.equipado):
            continue
        if entrada["categoria"] == "armadura":
            if armadura:
                avisos.append(f"Hay más de una armadura equipada; se usa {armadura['nombre']}")
            else:
                armadura = entrada
        elif entrada["categoria"] == "escudo":
            if escudo:
                avisos.append("Hay más de un escudo equipado; solo cuenta uno")
            else:
                escudo = entrada
    return armadura, escudo, objetos


def _avisos_competencia_armadura(armadura: dict | None, escudo: dict | None, competentes: set[str], avisos: list[str]) -> None:
    if armadura and not {armadura["id"], GRUPO_ARMADURA[armadura["armadura"]["tipo"]]} & competentes:
        avisos.append(
            f"Sin competencia con {armadura['nombre']}: desventaja en pruebas, salvaciones y ataques "
            "de FUE y DES, y no puede lanzar conjuros"
        )
    if escudo and not {escudo["id"], "escudos"} & competentes:
        avisos.append(f"Sin competencia con {escudo['nombre']}")


def _clase_armadura(mods: dict[str, int], armadura: dict | None, escudo: dict | None,
                    alternativas: list[dict], bonificadores: list[dict], max_des_media: list[dict]) -> int:
    if armadura:
        datos = armadura["armadura"]
        if datos["tipo"] == "ligera":
            ca = datos["ca"] + mods["des"]
        elif datos["tipo"] == "media":
            maximo = max([datos.get("max_des", 2), *(e["valor"] for e in max_des_media)])
            ca = datos["ca"] + min(mods["des"], maximo)
        else:
            ca = datos["ca"]
    else:
        ca = 10 + mods["des"]
        for alternativa in alternativas:
            ca = max(ca, alternativa["base"] + sum(mods[c] for c in alternativa.get("suma", [])))
    if escudo:
        ca += escudo.get("escudo", {}).get("bonificador", 2)
    return ca + sum(b["valor"] for b in bonificadores)


def _velocidades(raza: dict | None, efectos: list[dict], fuerza: int, armadura: dict | None,
                 ignora_armadura: bool) -> dict[str, int]:
    velocidades = {"caminar": raza["velocidad"] if raza else 0}
    for efecto in efectos:
        modo = efecto.get("modo", "caminar")
        if "valor" in efecto:
            velocidades[modo] = max(velocidades.get(modo, 0), efecto["valor"])
    for efecto in efectos:
        modo = efecto.get("modo", "caminar")
        if efecto.get("bonificador") and modo in velocidades:
            velocidades[modo] += efecto["bonificador"]
    if armadura and fuerza < armadura["armadura"].get("fuerza_minima", 0) and not ignora_armadura:
        velocidades["caminar"] = max(0, velocidades["caminar"] - 10)
    return velocidades


def _puntos_golpe(personaje: Personaje, catalogo: Catalogo, mod_con: int, extras: list[dict],
                  avisos: list[str]) -> tuple[int, dict[str, int]]:
    total = 0
    dados: dict[str, int] = defaultdict(int)
    niveles_por_clase: dict[str, int] = {}
    for indice, entrada in enumerate(personaje.clases):
        clase = catalogo.obtener("clases", entrada.clase)
        if clase is None or not 1 <= entrada.nivel <= NIVEL_MAXIMO:
            continue
        niveles_por_clase[clase["id"]] = entrada.nivel
        dado = clase["dado_golpe"]
        dados[f"d{dado}"] += entrada.nivel
        for nivel in range(1, entrada.nivel + 1):
            if indice == 0 and nivel == 1:
                valor = dado
            else:
                valor = _tirada_pg(personaje, entrada, indice, nivel, dado, clase["nombre"], avisos)
            # Decisión de diseño: cada nivel aporta al menos 1 PG aunque la CON sea negativa.
            total += max(1, valor + mod_con)
    for efecto in extras:
        niveles = niveles_por_clase.get(efecto["clase"], 0) if "clase" in efecto else personaje.nivel_total
        total += efecto.get("por_nivel", 0) * niveles + efecto.get("valor", 0)
    return total, dict(dados)


def _tirada_pg(personaje: Personaje, entrada: EntradaClase, indice: int, nivel: int, dado: int,
               nombre_clase: str, avisos: list[str]) -> int:
    media = dado // 2 + 1
    if personaje.metodo_pg != "tiradas":
        return media
    posicion = nivel - 2 if indice == 0 else nivel - 1
    if posicion >= len(entrada.tiradas_pg):
        avisos.append(f"{nombre_clase} {nivel}: falta la tirada de PG, se usa la media ({media})")
        return media
    valor = entrada.tiradas_pg[posicion]
    if not 1 <= valor <= dado:
        avisos.append(f"{nombre_clase} {nivel}: la tirada de PG {valor} está fuera de 1–{dado}")
        return max(1, min(valor, dado))
    return valor


def _magia(personaje: Personaje, catalogo: Catalogo, mods: dict[str, int], competencia: int,
           avisos: list[str]) -> tuple[dict[int, int], dict[str, int] | None, list[Lanzador]]:
    lanzadores: list[Lanzador] = []
    niveles_espacios: list[tuple[int, dict]] = []  # (nivel de clase, configuración) sin magia de pacto
    pacto = None
    for entrada in personaje.clases:
        clase = catalogo.obtener("clases", entrada.clase)
        if clase is None or not 1 <= entrada.nivel <= NIVEL_MAXIMO:
            continue
        subclase = catalogo.obtener("subclases", entrada.subclase) if entrada.subclase else None
        config = clase.get("lanzamiento") or (subclase or {}).get("lanzamiento")
        if not config:
            continue
        progresion = config["progresion"]
        if entrada.nivel < config.get("desde_nivel", NIVEL_INICIO_PROGRESION[progresion]):
            if personaje.conjuros.get(clase["id"]):
                avisos.append(f"{clase['nombre']} aún no lanza conjuros a nivel {entrada.nivel}")
            continue
        if progresion == "pacto":
            espacios, nivel_espacio = MAGIA_DE_PACTO[entrada.nivel]
            pacto = {"espacios": espacios, "nivel": nivel_espacio}
            nivel_maximo = nivel_espacio
        else:
            nivel_unico = math.ceil(entrada.nivel / PROGRESIONES_LANZAMIENTO[progresion])
            nivel_maximo = len(ESPACIOS_LANZADOR_COMPLETO[nivel_unico])
            niveles_espacios.append((entrada.nivel, config))
        car = config["caracteristica"]
        lanzador = Lanzador(clase["id"], clase["nombre"], car, 8 + competencia + mods[car], competencia + mods[car],
                            nivel_maximo)
        _conjuros_elegidos(lanzador, entrada, clase, subclase, config, personaje, catalogo, mods[car], avisos)
        lanzadores.append(lanzador)

    if len(niveles_espacios) == 1:
        nivel, config = niveles_espacios[0]
        nivel_espacios = math.ceil(nivel / PROGRESIONES_LANZAMIENTO[config["progresion"]])
    else:
        nivel_espacios = sum(_nivel_multiclase(nivel, config) for nivel, config in niveles_espacios)
    nivel_espacios = min(nivel_espacios, NIVEL_MAXIMO)
    espacios = dict(enumerate(ESPACIOS_LANZADOR_COMPLETO[nivel_espacios], start=1)) if nivel_espacios else {}
    return espacios, pacto, lanzadores


def _nivel_multiclase(nivel: int, config: dict) -> int:
    divisor = PROGRESIONES_LANZAMIENTO[config["progresion"]]
    if config.get("redondeo_multiclase") == "arriba":
        return math.ceil(nivel / divisor)
    return nivel // divisor


def _conjuros_elegidos(lanzador: Lanzador, entrada: EntradaClase, clase: dict, subclase: dict | None, config: dict,
                       personaje: Personaje, catalogo: Catalogo, mod: int, avisos: list[str]) -> None:
    listas = {clase["id"], *config.get("listas", [])} | ({subclase["id"]} if subclase else set())
    adicionales = set((subclase or {}).get("conjuros_adicionales", []))
    trucos = conjuros = 0
    vistos: set[str] = set()
    for id_ in personaje.conjuros.get(clase["id"], []):
        if id_ in vistos:
            avisos.append(f"{clase['nombre']}: el conjuro «{id_}» está repetido")
            continue
        vistos.add(id_)
        conjuro = catalogo.obtener("conjuros", id_)
        if conjuro is None:
            avisos.append(f"Conjuro desconocido «{id_}»")
            continue
        if not listas & set(conjuro["listas"]) and id_ not in adicionales:
            avisos.append(f"{conjuro['nombre']} no está en la lista de conjuros de {clase['nombre']}")
        if conjuro["nivel"] > lanzador.nivel_maximo:
            avisos.append(
                f"{conjuro['nombre']} es de nivel {conjuro['nivel']}; {clase['nombre']} {entrada.nivel} "
                f"solo llega a nivel {lanzador.nivel_maximo}"
            )
        lanzador.conjuros.setdefault(conjuro["nivel"], []).append(conjuro["nombre"])
        if conjuro["nivel"] == 0:
            trucos += 1
        else:
            conjuros += 1
    for nombres in lanzador.conjuros.values():
        nombres.sort()

    limite_trucos = config["trucos_conocidos"][entrada.nivel - 1] if "trucos_conocidos" in config else None
    if limite_trucos is not None and trucos > limite_trucos:
        avisos.append(f"{clase['nombre']}: {trucos} trucos elegidos, máximo {limite_trucos}")
    if "conjuros_conocidos" in config:
        limite = config["conjuros_conocidos"][entrada.nivel - 1]
    elif config.get("preparados") == "nivel":
        limite = max(1, mod + entrada.nivel)
    elif config.get("preparados") == "mitad_nivel":
        limite = max(1, mod + entrada.nivel // 2)
    else:
        limite = None
    if limite is not None and conjuros > limite:
        avisos.append(f"{clase['nombre']}: {conjuros} conjuros elegidos, máximo {limite}")


def _repartir_conjuros_de_efectos(efectos: list[dict], lanzadores: list[Lanzador], catalogo: Catalogo,
                                  avisos: list[str]) -> list[str]:
    """Los conjuros con «clase» van a ese lanzador como siempre preparados; el resto son innatos."""
    por_clase = {lanzador.clase_id: lanzador for lanzador in lanzadores}
    innatos = []
    for efecto in efectos:
        conjuro = catalogo.obtener("conjuros", efecto["id"])
        if conjuro is None:
            avisos.append(f"Conjuro desconocido «{efecto['id']}»")
            continue
        lanzador = por_clase.get(efecto.get("clase", ""))
        if lanzador is not None:
            nombres = lanzador.siempre_preparados.setdefault(conjuro["nivel"], [])
            if conjuro["nombre"] not in nombres:
                nombres.append(conjuro["nombre"])
            continue
        car = efecto.get("caracteristica")
        innatos.append(f"{conjuro['nombre']} ({CARACTERISTICAS[car]})" if car in CARACTERISTICAS else conjuro["nombre"])
    for lanzador in lanzadores:
        for nombres in lanzador.siempre_preparados.values():
            nombres.sort(key=clave_alfabetica)
    return innatos


def _admite_destreza(entrada: dict, efectos_des: list[dict]) -> bool:
    """Si algún efecto (p. ej. Artes Marciales) permite usar DES con esta arma."""
    arma = entrada["arma"]
    for efecto in efectos_des:
        if not {entrada["id"], GRUPO_ARMA[arma["categoria"]]} & set(efecto["armas"]):
            continue
        if set(arma.get("propiedades", [])) & set(efecto.get("excluir_propiedades", [])):
            continue
        if efecto.get("tipo_arma") in (None, arma["tipo"]):
            return True
    return False


def _ataques(objetos: list[tuple[ObjetoInventario, dict | None]], mods: dict[str, int], competencia: int,
             competentes: set[str], bonificadores: list[dict], efectos_des: list[dict]) -> list[Ataque]:
    ataques, vistos = [], set()
    for _, entrada in objetos:
        if not entrada or entrada["categoria"] != "arma" or entrada["id"] in vistos:
            continue
        vistos.add(entrada["id"])
        arma = entrada["arma"]
        propiedades = arma.get("propiedades", [])
        if "sutil" in propiedades or _admite_destreza(entrada, efectos_des):
            car = "des" if mods["des"] > mods["fue"] else "fue"
        elif arma["tipo"] == "distancia":
            car = "des"
        else:
            car = "fue"
        competente = bool({entrada["id"], GRUPO_ARMA[arma["categoria"]]} & competentes)
        bono = mods[car] + (competencia if competente else 0)
        bono += sum(b["valor"] for b in bonificadores if b.get("tipo_arma") in (None, arma["tipo"]))
        notas = []
        if arma.get("dano_versatil"):
            notas.append(f"A dos manos: {_formula_dano(arma['dano_versatil'], mods[car])}")
        if arma.get("alcance"):
            notas.append(f"Alcance {arma['alcance']} pies")
        if not competente:
            notas.append("Sin competencia")
        dano = _formula_dano(arma["dano"], mods[car])
        ataques.append(Ataque(entrada["nombre"], bono, dano, arma["tipo_dano"], "; ".join(notas)))
    return ataques


def _ataques_desarmados(aplicables: list[EfectoAplicado], catalogo: Catalogo, mods: dict[str, int], competencia: int,
                        niveles_clase: dict[str, int], contexto: dict, avisos: list[str]) -> list[Ataque]:
    """Ataque sin armas mejorado (Artes Marciales del monje y similares). Siempre hay competencia."""
    ataques = []
    for aplicado in aplicables:
        if aplicado.tipo != "ataque_desarmado":
            continue
        efecto = aplicado.efecto
        variables = _contexto_efecto(efecto, aplicado.origen, catalogo, niveles_clase, contexto)
        try:
            dado = rellenar(efecto["dano"], variables)
        except ErrorExpresion as exc:
            avisos.append(f"Ataque sin armas: {exc}")
            continue
        car = max(efecto.get("caracteristicas", ["fue"]), key=lambda c: mods[c])
        ataques.append(Ataque(efecto.get("nombre", "Ataque sin armas"), mods[car] + competencia,
                              _formula_dano(dado, mods[car]), efecto.get("tipo_dano", "contundente")))
    return ataques


def _formula_dano(dado: str, mod: int) -> str:
    """«1d8» + 3 -> «1d8+3». Un arma sin daño (la red) se queda en «—»."""
    if not dado or dado == "—":
        return "—"
    return f"{dado}{mod:+d}" if mod else dado


def _sentidos(efectos: list[dict]) -> dict[str, int]:
    sentidos: dict[str, int] = {}
    for efecto in efectos:
        nombre = efecto.get("nombre") or efecto["id"].replace("_", " ").capitalize()
        sentidos[nombre] = max(sentidos.get(nombre, 0), efecto["alcance"])
    return sentidos


def _nombres_competencias(competencias: dict[str, set[str]], catalogo: Catalogo) -> dict[str, list[str]]:
    def nombre(id_: str, categoria: str) -> str:
        if id_ in GRUPOS_COMPETENCIA:
            return GRUPOS_COMPETENCIA[id_]
        entrada = catalogo.obtener(categoria, id_)
        return entrada["nombre"] if entrada else id_

    return {
        "armaduras": sorted((nombre(i, "objetos") for i in competencias["armadura"]), key=clave_alfabetica),
        "armas": sorted((nombre(i, "objetos") for i in competencias["arma"]), key=clave_alfabetica),
        "herramientas": sorted((nombre(i, "objetos") for i in competencias["herramienta"]), key=clave_alfabetica),
        "idiomas": sorted((nombre(i, "idiomas") for i in competencias["idioma"]), key=clave_alfabetica),
    }


def _describir_objeto(item: ObjetoInventario, entrada: dict | None) -> str:
    nombre = item.nombre or (entrada or {}).get("nombre") or item.id or "?"
    return f"{nombre} (x{item.cantidad})" if item.cantidad != 1 else nombre


def _clase_y_nivel(personaje: Personaje, catalogo: Catalogo) -> str:
    partes = []
    for entrada in personaje.clases:
        clase = catalogo.obtener("clases", entrada.clase)
        texto = f"{(clase or {}).get('nombre', entrada.clase)} {entrada.nivel}"
        subclase = catalogo.obtener("subclases", entrada.subclase) if entrada.subclase else None
        if subclase:
            texto += f" ({subclase['nombre']})"
        partes.append(texto)
    return " / ".join(partes)
