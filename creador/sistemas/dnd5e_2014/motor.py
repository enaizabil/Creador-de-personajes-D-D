"""Cálculo de la ficha de D&D 5e (2014) a partir de las decisiones del personaje."""
from __future__ import annotations

import math
import re
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
    TIPOS_DANO,
)
from .ficha import Ataque, Ficha, Lanzador, PlanConjuros, Rasgo, Tirada, ValorCaracteristica

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
        personalizado = personaje.reglas_opcionales.get("origen_personalizado", False)
        efectos = entrada.get("efectos", [])
        yield _origen_personalizado(efectos) if personalizado and campo == "raza" else efectos, f"{campo}:{id_}", \
            entrada["nombre"]
        if campo == "raza" and personaje.subraza:
            subraza = catalogo.obtener("subrazas", personaje.subraza)
            if subraza is None:
                errores.append(f"No existe la subraza «{personaje.subraza}» en los paquetes activos")
            elif subraza["raza"] != id_:
                errores.append(f"La subraza «{subraza['nombre']}» no pertenece a {entrada['nombre']}")
            else:
                efectos = subraza.get("efectos", [])
                yield _origen_personalizado(efectos) if personalizado else efectos, f"subraza:{subraza['id']}", \
                    subraza["nombre"]

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
        opcionales = [r for r in rasgos_opcionales_activos(personaje, catalogo) if r["clase"] == id_clase]
        reemplazados = {r for rasgo in opcionales for r in rasgo.get("sustituye", [])}

        def sin_reemplazados(efectos: list, reemplazados=reemplazados) -> list:
            # Rasgos de clase opcionales que sustituyen a otros (Explorador Hábil en lugar de Explorador Nato).
            return [e for e in efectos if not isinstance(e, dict) or (e.get("id") not in reemplazados
                                                                      and e.get("nombre") not in reemplazados)]

        if indice == 0:
            salvaciones = [{"tipo": "competencia", "categoria": "salvacion", "id": c} for c in clase["salvaciones"]]
            yield salvaciones + clase.get("competencias", []), f"clase:{id_clase}:inicial", nombre
        else:
            yield clase.get("competencias_multiclase", []), f"clase:{id_clase}:multiclase", nombre
        niveles = clase.get("niveles", {})
        for nivel in range(1, entrada.nivel + 1):
            yield sin_reemplazados(niveles.get(str(nivel), [])), f"clase:{id_clase}:{nivel}", f"{nombre} {nivel}"
        for rasgo in opcionales:
            if rasgo.get("subclase") and rasgo["subclase"] != entrada.subclase:
                continue
            for nivel in range(1, entrada.nivel + 1):
                yield rasgo.get("niveles", {}).get(str(nivel), []), f"opcional:{rasgo['id']}:{nivel}", rasgo["nombre"]

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
                    sin_reemplazados(sub_niveles.get(str(nivel), [])),
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
    armadura, escudo, objetos, bonificador_ca = _equipo(personaje, catalogo, avisos)
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
    contexto = {"nivel": nivel, "competencia": competencia, **{f"mod_{c}": m for c, m in mods.items()}}
    extra_salvacion = _bonificadores_salvacion(de_tipo("bonificador_salvacion"), contexto, avisos)

    salvaciones = {
        c: Tirada(nombre, c, mods[c] + (competencia if c in competencias["salvacion"] else 0) + extra_salvacion[c],
                  c in competencias["salvacion"])
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
    if armadura and armadura["armadura"].get("desventaja_sigilo") and not any(
            e.get("tipo_armadura") in (None, armadura["armadura"]["tipo"]) for e in de_tipo("sin_desventaja_sigilo")):
        habilidades["sigilo"].notas = f"Desventaja ({armadura['nombre']})"
    pasivas = {h: 10 + habilidades[h].valor for h in PASIVAS}
    for efecto in de_tipo("pasiva"):
        pasivas[efecto["habilidad"]] += efecto["valor"]

    _avisos_competencia_armadura(armadura, escudo, competencias["armadura"], avisos)
    pg_maximos, dados_golpe = _puntos_golpe(personaje, catalogo, mods["con"], de_tipo("pg_maximos"), avisos)
    libro_extra = libro_por_efectos(de_tipo("conjuro"))
    espacios, pacto, lanzadores = _magia(personaje, catalogo, mods, competencia, avisos,
                                         conocidos_por_efectos(de_tipo("conjuro")), libro_extra,
                                         listas_por_efectos(de_tipo("lista_ampliada")))
    _avisos_en_libro(aplicables, personaje, catalogo, libro_extra, avisos)
    conjuros_innatos = _repartir_conjuros_de_efectos(de_tipo("conjuro"), lanzadores, catalogo, avisos)
    niveles_clase = _niveles_por_clase(personaje, catalogo)
    _avisos_requisitos(personaje, catalogo, aplicables, puntuaciones, competencias,
                       bool(lanzadores or conjuros_innatos), avisos)
    _avisos_repeticiones(aplicables, catalogo, avisos)
    if personaje.reglas_opcionales.get("origen_personalizado", False):
        _avisos_origen_personalizado(personaje, avisos)
    _avisos_reglas_opcionales(personaje, catalogo, avisos)
    _avisos_niveles_sin_datos(personaje, catalogo, avisos)
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
        ca=_clase_armadura(mods, armadura, escudo, _primera_de_cada(de_tipo("ca_alternativa")), de_tipo("bonificador_ca"),
                           de_tipo("max_des_armadura_media")) + bonificador_ca,
        iniciativa=mods["des"] + medio.get("des", 0) + _bonificador_iniciativa(de_tipo("iniciativa"), contexto, avisos),
        velocidades=_velocidades(raza, de_tipo("velocidad"), puntuaciones["fue"], armadura,
                                 bool(de_tipo("ignora_penalizacion_armadura"))),
        pg_maximos=pg_maximos,
        dados_golpe=dados_golpe,
        tamano=TAMANOS.get((raza or {}).get("tamano", ""), ""),
        competencias=_nombres_competencias(competencias, catalogo),
        ataques=_ataques(objetos, mods, competencia, competencias["arma"], de_tipo("bonificador_ataque"),
                         de_tipo("ataque_des"), (raza or {}).get("tamano") == "pequeno", de_tipo("ataque_caracteristica"))
                + _ataques_de_rasgos(aplicables, catalogo, mods, competencia, niveles_clase, contexto, avisos),
        rasgos=_rasgos(aplicables, catalogo, niveles_clase, contexto, avisos),
        sentidos=_sentidos(de_tipo("sentido")),
        resistencias=sorted({TIPOS_DANO.get(e["dano"], e["dano"]) for e in de_tipo("resistencia")}),
        inmunidades=sorted({e["id"] for e in de_tipo("inmunidad")}),
        espacios_conjuro=espacios,
        magia_pacto=pacto,
        lanzadores=lanzadores,
        conjuros_innatos=conjuros_innatos,
        equipo=[_describir_objeto(item, entrada) for item, entrada in objetos],
        monedas=dict(personaje.monedas),
        detalles=dict(personaje.detalles),
        avisos=avisos,
        entrenamiento=[dict(e) for e in personaje.extra.get("entrenamiento", []) if e.get("pendiente")],
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
    if tipo in ("subclase", "opcional"):
        entrada = catalogo.obtener("subclases" if tipo == "subclase" else "rasgos_opcionales", id_)
        return entrada["clase"] if entrada else None
    return None


def rasgos_opcionales_activos(personaje: Personaje, catalogo: Catalogo) -> list[dict]:
    """Rasgos de clase opcionales (Tasha) que se aplican: con la regla activa, de una clase del personaje (y de su
    subclase, si el rasgo es de una) y sin desactivar uno a uno («opcional:<id>»: false)."""
    if not personaje.reglas_opcionales.get("rasgos_opcionales", False):
        return []
    clases = {e.clase: e.subclase for e in personaje.clases}
    return [r for r in catalogo.listar("rasgos_opcionales")
            if r["clase"] in clases and personaje.reglas_opcionales.get(f"opcional:{r['id']}", True)]


def _contexto_efecto(efecto: dict, origen: str, catalogo: Catalogo, niveles_clase: dict[str, int],
                     contexto: dict) -> dict:
    """Variables para las {expresiones}: nivel de la clase del efecto y el valor de su «escala»."""
    clase = _clase_de_origen(efecto, origen, catalogo)
    nivel_clase = niveles_clase.get(clase, contexto["nivel"]) if clase else contexto["nivel"]
    escala = ""
    for umbral, valor in sorted(((int(n), v) for n, v in efecto.get("escala", {}).items())):
        if umbral <= nivel_clase:
            escala = valor
    variables = {**contexto, "nivel_clase": nivel_clase, "escala": escala}
    if efecto.get("conjuro"):
        # Rasgo ligado a un conjuro elegido (Maestría sobre Conjuros…): su nombre para el resumen.
        variables["conjuro"] = (catalogo.obtener("conjuros", efecto["conjuro"]) or {}).get("nombre", efecto["conjuro"])
    return variables


def _rasgos(aplicables: list[EfectoAplicado], catalogo: Catalogo, niveles_clase: dict[str, int],
            contexto: dict, avisos: list[str]) -> list[Rasgo]:
    rasgos: list[Rasgo] = []
    no_acumula: dict[str, int] = {}  # nombre -> posición del rasgo que se queda
    compartidos: dict[str, list[int]] = {}  # clave -> posiciones de rasgos con una sola reserva de usos
    for aplicado in aplicables:
        if aplicado.tipo != "rasgo":
            continue
        efecto = aplicado.efecto
        variables = _contexto_efecto(efecto, aplicado.origen, catalogo, niveles_clase, contexto)
        try:
            resumen = rellenar(efecto.get("resumen", ""), variables)
            usos = _por_nivel(efecto.get("usos"), variables["nivel_clase"])
            usos = None if usos == "" else max(0, int(evaluar(usos, variables))) if isinstance(usos, str) else usos
        except (ErrorExpresion, TypeError, ValueError) as exc:
            avisos.append(f"{efecto['nombre']}: {exc}")
            resumen, usos = efecto.get("resumen", ""), None
        rasgo = Rasgo(efecto["nombre"], efecto.get("descripcion", ""), aplicado.etiqueta,
                      resumen, usos, _por_nivel(efecto.get("recarga", ""), variables["nivel_clase"]))
        if efecto.get("usos_compartidos"):
            compartidos.setdefault(efecto["usos_compartidos"], []).append(len(rasgos))
        if efecto.get("no_acumula"):
            # Multiclase: Ataque Adicional, Defensa sin Armadura… de dos clases no se suman; queda el mejor.
            previo = no_acumula.get(efecto["nombre"])
            if previo is not None:
                if _numero_inicial(rasgo.resumen) > _numero_inicial(rasgos[previo].resumen):
                    rasgos[previo] = rasgo
                continue
            no_acumula[efecto["nombre"]] = len(rasgos)
        rasgos.append(rasgo)
    for posiciones in compartidos.values():
        _compartir_usos([rasgos[i] for i in posiciones])
    return rasgos


def _compartir_usos(grupo: list[Rasgo]) -> None:
    """Multiclase: el mismo rasgo de dos clases no suma usos; los conserva el que más tiene."""
    if len(grupo) < 2:
        return
    mejor = max(grupo, key=lambda r: r.usos or 0)
    for rasgo in grupo:
        if rasgo is not mejor:
            sin_usos = re.sub(r"^usos: [^;]*; ", "", rasgo.resumen)
            rasgo.resumen = f"usos: los de {mejor.origen} (no se suman); {sin_usos}"
            rasgo.usos, rasgo.recarga = None, ""


def _primera_de_cada(efectos: list[dict]) -> list[dict]:
    """Efectos con la misma clave «no_acumula»: solo cuenta el primero (Defensa sin Armadura de bárbaro y monje:
    vale la de la clase que la dio antes)."""
    vistas: set[str] = set()
    resultado = []
    for efecto in efectos:
        clave = efecto.get("no_acumula")
        if isinstance(clave, str):
            if clave in vistas:
                continue
            vistas.add(clave)
        resultado.append(efecto)
    return resultado


def _numero_inicial(texto: str) -> int:
    """«3 ataques al usar…» -> 3 (0 si no empieza por un número)."""
    cifras = ""
    for caracter in texto:
        if not caracter.isdigit():
            break
        cifras += caracter
    return int(cifras or 0)


def _por_nivel(valor, nivel: int):
    """Un valor fijo o una tabla {"nivel": valor} de la que se toma el último umbral alcanzado."""
    if not isinstance(valor, dict):
        return valor
    resultado = ""
    for umbral, dato in sorted((int(n), v) for n, v in valor.items()):
        if umbral <= nivel:
            resultado = dato
    return resultado


def _origen_personalizado(efectos: list) -> list:
    """Tasha, «Personalizar tu origen»: cada mejora fija de característica de la raza pasa a elegirse."""
    nuevos = []
    for n, efecto in enumerate(efectos):
        fija = isinstance(efecto, dict) and efecto.get("tipo") == "caracteristica" and not str(efecto.get("car", "$"))\
            .startswith("$")
        if fija:
            nombre = f"Mejora de raza +{efecto['valor']} (Personalizar tu origen; antes {efecto['car'].upper()})"
            nuevos.append({"tipo": "eleccion", "id": f"origen_{n}", "nombre": nombre, "opciones": {"desde": "caracteristicas"},
                           "aplicar": [{**efecto, "car": "$opcion"}]})
        else:
            nuevos.append(efecto)
    return nuevos


def _avisos_origen_personalizado(personaje: Personaje, avisos: list[str]) -> None:
    """Las mejoras de raza movidas no pueden ir dos a la misma característica."""
    elegidas = [v for clave, valores in personaje.elecciones.items() if "/origen_" in clave for v in valores]
    for car in sorted({c for c in elegidas if elegidas.count(c) > 1}):
        avisos.append(f"Personalizar tu origen: dos mejoras de raza en {car.upper()}; deben ir a características distintas")


def _avisos_repeticiones(aplicables: list[EfectoAplicado], catalogo: Catalogo, avisos: list[str]) -> None:
    """Competencias que llegan dos veces cuando una es elegida, y dotes tomadas dos veces."""
    origenes: dict[tuple[str, str], list[EfectoAplicado]] = defaultdict(list)
    for aplicado in aplicables:
        if aplicado.tipo == "competencia":
            origenes[(aplicado.efecto["categoria"], aplicado.efecto["id"])].append(aplicado)
    for (categoria, id_), lista in origenes.items():
        elegidas = [a for a in lista if "=" in a.origen]
        if len(lista) > 1 and elegidas:
            nombre = _nombre_competencia(categoria, id_, catalogo)
            avisos.append(f"Competencia repetida con {nombre}: en «{elegidas[-1].etiqueta}» elige otra opción")
    for campo, categoria, texto in (("dote", "dotes", "La dote"), ("opcion", "opciones", "La opción")):
        elegidas = [a.efecto[campo] for a in aplicables if a.tipo == "rasgo" and a.efecto.get(campo)]
        for id_ in sorted({e for e in elegidas if elegidas.count(e) > 1}):
            entrada = catalogo.obtener(categoria, id_) or {}
            if not entrada.get("repetible"):
                avisos.append(f"{texto} {entrada.get('nombre', id_)} está elegida más de una vez")


def _avisos_niveles_sin_datos(personaje: Personaje, catalogo: Catalogo, avisos: list[str]) -> None:
    """Clases y subclases a un nivel por encima de los que tienen completos sus datos («niveles_completos»)."""
    for entrada in personaje.clases:
        for categoria, id_ in (("clases", entrada.clase), ("subclases", entrada.subclase)):
            datos = catalogo.obtener(categoria, id_) if id_ else None
            if datos and entrada.nivel > datos.get("niveles_completos", NIVEL_MAXIMO):
                avisos.append(f"Los datos de {datos['nombre']} solo llegan a nivel {datos['niveles_completos']}: "
                              f"faltan los rasgos de los niveles {datos['niveles_completos'] + 1}–{entrada.nivel}")


def _avisos_reglas_opcionales(personaje: Personaje, catalogo: Catalogo, avisos: list[str]) -> None:
    """Entradas que exigen una regla opcional («requiere_reglas») desactivada en el personaje."""
    usadas = [("razas", personaje.raza), ("subrazas", personaje.subraza), ("trasfondos", personaje.trasfondo)]
    for entrada in personaje.clases:
        usadas += [("clases", entrada.clase), ("subclases", entrada.subclase)]
    for categoria, id_ in usadas:
        entrada = catalogo.obtener(categoria, id_) if id_ else None
        for regla in (entrada or {}).get("requiere_reglas", []):
            if not personaje.reglas_opcionales.get(regla, True):
                avisos.append(f"{entrada['nombre']} requiere la regla opcional «{regla}», que está desactivada")


def texto_requisito(requisito: dict) -> str:
    """«FUE 13 o DES 13», «INT 13»… (para la interfaz)."""
    return _texto_requisito(requisito)


def cumple_puntuaciones(requisito: dict, puntuaciones: dict[str, int]) -> bool:
    """Solo la parte de puntuaciones de un requisito (lo que piden las clases para la multiclase)."""
    return _cumple_requisito({k: v for k, v in requisito.items() if k in ("caracteristicas", "alguna_caracteristica")},
                             puntuaciones, defaultdict(set), True)


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


def cumple_requisito(requisito: dict, puntuaciones: dict[str, int], competencias: dict[str, set[str]],
                     lanzador: bool) -> bool:
    """Prerrequisito completo (de una dote): el cuestionario lo usa para no proponer lo que no se puede tomar."""
    return _cumple_requisito(requisito, puntuaciones, competencias, lanzador)


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


def _bonificadores_salvacion(efectos: list[dict], contexto: dict, avisos: list[str]) -> dict[str, int]:
    """Bonificadores a las tiradas de salvación (Aura de Protección…); «valor» puede ser una expresión."""
    resultado = dict.fromkeys(CARACTERISTICAS, 0)
    for efecto in efectos:
        try:
            valor = int(evaluar(efecto["valor"], contexto)) if isinstance(efecto["valor"], str) else efecto["valor"]
        except (ErrorExpresion, TypeError, ValueError) as exc:
            avisos.append(f"Bonificador a las salvaciones: {exc}")
            continue
        cars = efecto.get("caracteristicas", "todas")
        for car in CARACTERISTICAS if cars == "todas" else cars:
            resultado[car] += valor
    return resultado


def _bonificador_iniciativa(efectos: list[dict], contexto: dict, avisos: list[str]) -> int:
    """Bonificadores a la iniciativa (Alerta: 5; Aura del Centinela: «competencia»); «valor» puede ser una expresión."""
    total = 0
    for efecto in efectos:
        try:
            total += int(evaluar(efecto["valor"], contexto)) if isinstance(efecto["valor"], str) else efecto["valor"]
        except (ErrorExpresion, TypeError, ValueError) as exc:
            avisos.append(f"Bonificador a la iniciativa: {exc}")
    return total


def libro_por_efectos(efectos: list[dict]) -> dict[str, list[str]]:
    """Conjuros que un rasgo añade gratis al libro de una clase («al_libro»: Siervos No Muertos, Cambiaformas)."""
    resultado: dict[str, list[str]] = defaultdict(list)
    for efecto in efectos:
        if efecto.get("al_libro") and efecto.get("clase") and efecto["id"] not in resultado[efecto["clase"]]:
            resultado[efecto["clase"]].append(efecto["id"])
    return dict(resultado)


def _avisos_en_libro(aplicables: list[EfectoAplicado], personaje: Personaje, catalogo: Catalogo,
                     libro_extra: dict[str, list[str]], avisos: list[str]) -> None:
    """Rasgos que exigen que su conjuro esté en el libro («en_libro»: Maestría sobre Conjuros, característicos)."""
    for aplicado in aplicables:
        efecto = aplicado.efecto
        clase = efecto.get("en_libro")
        if aplicado.tipo != "rasgo" or not clase or not efecto.get("conjuro"):
            continue
        if efecto["conjuro"] not in [*personaje.conjuros.get(clase, []), *libro_extra.get(clase, [])]:
            nombre = (catalogo.obtener("conjuros", efecto["conjuro"]) or {}).get("nombre", efecto["conjuro"])
            avisos.append(f"{efecto['nombre']}: {nombre} no está en tu libro de conjuros")


def listas_por_efectos(efectos: list[dict]) -> dict[str, set[str]]:
    """Efectos «lista_ampliada»: conjuros que se suman a la lista de una clase según lo elegido (el tipo de genio
    del brujo Genio, p. ej.). Son elegibles como los de la lista, pero no se dan solos."""
    listas: dict[str, set[str]] = defaultdict(set)
    for efecto in efectos:
        if efecto.get("tipo") == "lista_ampliada":
            listas[efecto["clase"]].update(efecto["conjuros"])
    return dict(listas)


def conocidos_por_efectos(efectos: list[dict]) -> dict[str, int]:
    """Conjuros que llegan por efectos pero cuentan para los conocidos de su clase (Secretos Mágicos del bardo)."""
    resultado: dict[str, int] = defaultdict(int)
    for efecto in efectos:
        if efecto.get("cuenta_como_conocido") and efecto.get("clase"):
            resultado[efecto["clase"]] += 1
    return dict(resultado)


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
) -> tuple[dict | None, dict | None, list[tuple[ObjetoInventario, dict | None]], int]:
    """Armadura y escudo equipados, todos los objetos y lo que suman a la CA si son mágicos (+1 a +3)."""
    armadura = escudo = None
    bonificador_ca = 0
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
                bonificador_ca += item.bonificador or 0
        elif entrada["categoria"] == "escudo":
            if escudo:
                avisos.append("Hay más de un escudo equipado; solo cuenta uno")
            else:
                escudo = entrada
                bonificador_ca += item.bonificador or 0
    return armadura, escudo, objetos, bonificador_ca


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
    for efecto in efectos:  # «igual_a»: trepar o nadar a la velocidad de caminar (Explorador Hábil)
        if efecto.get("igual_a") in velocidades:
            modo = efecto.get("modo", "caminar")
            velocidades[modo] = max(velocidades.get(modo, 0), velocidades[efecto["igual_a"]])
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


def _configuracion_lanzador(entrada: EntradaClase, catalogo: Catalogo) -> tuple[dict, dict | None, dict] | None:
    """(clase, subclase, lanzamiento) si esa entrada de clase ya lanza conjuros a su nivel."""
    clase = catalogo.obtener("clases", entrada.clase)
    if clase is None or not 1 <= entrada.nivel <= NIVEL_MAXIMO:
        return None
    subclase = catalogo.obtener("subclases", entrada.subclase) if entrada.subclase else None
    config = clase.get("lanzamiento") or (subclase or {}).get("lanzamiento")
    if not config or entrada.nivel < config.get("desde_nivel", NIVEL_INICIO_PROGRESION[config["progresion"]]):
        return None
    return clase, subclase, config


def configuracion_lanzamiento(personaje: Personaje, catalogo: Catalogo, clase_id: str) -> dict | None:
    """El bloque «lanzamiento» que usa esa clase del personaje (de la clase o de su subclase)."""
    entrada = next((e for e in personaje.clases if e.clase == clase_id), None)
    configuracion = _configuracion_lanzador(entrada, catalogo) if entrada else None
    return configuracion[2] if configuracion else None


def nivel_maximo_conjuro(config: dict, nivel: int) -> int:
    """Nivel de conjuro más alto que tiene esa configuración de lanzamiento a ese nivel de clase."""
    return _nivel_maximo_conjuro(config, nivel)


def _nivel_maximo_conjuro(config: dict, nivel: int) -> int:
    if config["progresion"] == "pacto":
        return MAGIA_DE_PACTO[nivel][1]
    return len(ESPACIOS_LANZADOR_COMPLETO[math.ceil(nivel / PROGRESIONES_LANZAMIENTO[config["progresion"]])])


def _limites(config: dict, nivel: int, mod: int, ocupados: int = 0) -> tuple[int | None, int | None]:
    """(trucos, conjuros) que puede conocer o preparar la clase a ese nivel; None si no hay límite.

    «ocupados»: plazas de conjuros conocidos que ya llenan efectos (Secretos Mágicos del bardo).
    """
    trucos = config["trucos_conocidos"][nivel - 1] if "trucos_conocidos" in config else None
    if "conjuros_conocidos" in config:
        conjuros = config["conjuros_conocidos"][nivel - 1]
    elif config.get("preparados") == "nivel":
        conjuros = max(1, mod + nivel)
    elif config.get("preparados") == "mitad_nivel":
        conjuros = max(1, mod + nivel // 2)
    else:
        conjuros = None
    if conjuros is not None:
        conjuros = max(0, conjuros - ocupados)
    return trucos, conjuros


def limite_libro(config: dict, nivel: int) -> int | None:
    """Conjuros que caben en el libro al llegar a ese nivel (mago: 6 a nivel 1 y 2 más por nivel)."""
    libro = config.get("libro")
    return libro["inicial"] + libro["por_nivel"] * (nivel - 1) if libro else None


def avisos_libro(config: dict, nivel: int, niveles: list[int], clase: str) -> list[str]:
    """Comprueba que los conjuros del libro (sus niveles) se pudieron copiar al subir de nivel.

    Cada conjuro ganado a un nivel de clase k es de un nivel para el que hay espacios a nivel k. Como las
    capacidades están anidadas, basta con que, para cada nivel de conjuro L, los conjuros de nivel ≥ L
    no superen los ganados en niveles de clase que ya llegaban a L.
    """
    libro = config["libro"]
    ganados = [(libro["inicial"], _nivel_maximo_conjuro(config, 1))]
    ganados += [(libro["por_nivel"], _nivel_maximo_conjuro(config, k)) for k in range(2, nivel + 1)]
    avisos = []
    for minimo in range(2, max(niveles, default=0) + 1):
        tienes = sum(1 for n in niveles if n >= minimo)
        caben = sum(cantidad for cantidad, maximo in ganados if maximo >= minimo)
        if tienes > caben:
            avisos.append(f"{clase}: el libro tiene {tienes} conjuros de nivel {minimo} o más; "
                          f"a nivel {nivel} solo pueden ser {caben}")
    return avisos


def _listas_validas(clase: dict, subclase: dict | None, config: dict,
                    extra: set[str] | None = None) -> tuple[set[str], set[str]]:
    """(listas de conjuros de la clase, ids adicionales de la subclase y de efectos «lista_ampliada»)."""
    listas = {clase["id"], *config.get("listas", [])} | ({subclase["id"]} if subclase else set())
    return listas, set((subclase or {}).get("conjuros_adicionales", [])) | (extra or set())


def planes_de_conjuros(personaje: Personaje, catalogo: Catalogo, mods: dict[str, int],
                       conocidos_extra: dict[str, int] | None = None,
                       listas_extra: dict[str, set[str]] | None = None) -> list[PlanConjuros]:
    """Para cada clase que ya lanza conjuros: límites y conjuros elegibles hasta su nivel máximo.

    «conocidos_extra»: conjuros por clase que ya ocupan plazas de conocidos (ver conocidos_por_efectos).
    """
    planes = []
    for entrada in personaje.clases:
        configuracion = _configuracion_lanzador(entrada, catalogo)
        if configuracion is None:
            continue
        clase, subclase, config = configuracion
        nivel_maximo = _nivel_maximo_conjuro(config, entrada.nivel)
        trucos, conjuros = _limites(config, entrada.nivel, mods[config["caracteristica"]],
                                    (conocidos_extra or {}).get(clase["id"], 0))
        listas, adicionales = _listas_validas(clase, subclase, config, (listas_extra or {}).get(clase["id"]))
        disponibles: dict[int, list[tuple[str, str]]] = {}
        for conjuro in catalogo.listar("conjuros"):
            if conjuro["nivel"] <= nivel_maximo and (listas & set(conjuro["listas"]) or conjuro["id"] in adicionales):
                disponibles.setdefault(conjuro["nivel"], []).append((conjuro["id"], conjuro["nombre"]))
        for opciones in disponibles.values():
            opciones.sort(key=lambda o: clave_alfabetica(o[1]))
        modo = "libro" if config.get("libro") else "conocidos" if "conjuros_conocidos" in config else "preparados"
        planes.append(PlanConjuros(clase["id"], clase["nombre"], config["caracteristica"], nivel_maximo, modo,
                                   trucos, conjuros, dict(sorted(disponibles.items())),
                                   limite_libro(config, entrada.nivel)))
    return planes


def _magia(personaje: Personaje, catalogo: Catalogo, mods: dict[str, int], competencia: int,
           avisos: list[str], conocidos_extra: dict[str, int], libro_extra: dict[str, list[str]] | None = None,
           listas_extra: dict[str, set[str]] | None = None) -> tuple[dict[int, int], dict[str, int] | None, list[Lanzador]]:
    lanzadores: list[Lanzador] = []
    niveles_espacios: list[tuple[int, dict]] = []  # (nivel de clase, configuración) sin magia de pacto
    pacto = None
    for entrada in personaje.clases:
        configuracion = _configuracion_lanzador(entrada, catalogo)
        if configuracion is None:
            clase = catalogo.obtener("clases", entrada.clase)
            if clase and personaje.conjuros.get(clase["id"]):
                avisos.append(f"{clase['nombre']} aún no lanza conjuros a nivel {entrada.nivel}")
            continue
        clase, subclase, config = configuracion
        nivel_maximo = _nivel_maximo_conjuro(config, entrada.nivel)
        if config["progresion"] == "pacto":
            espacios, nivel_espacio = MAGIA_DE_PACTO[entrada.nivel]
            pacto = {"espacios": espacios, "nivel": nivel_espacio}
        else:
            niveles_espacios.append((entrada.nivel, config))
        car = config["caracteristica"]
        lanzador = Lanzador(clase["id"], clase["nombre"], car, 8 + competencia + mods[car], competencia + mods[car],
                            nivel_maximo)
        _conjuros_elegidos(lanzador, entrada, clase, subclase, config, personaje, catalogo, mods[car], avisos,
                           conocidos_extra.get(clase["id"], 0), (libro_extra or {}).get(clase["id"], []),
                           (listas_extra or {}).get(clase["id"]))
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
                       personaje: Personaje, catalogo: Catalogo, mod: int, avisos: list[str],
                       conocidos_extra: int = 0, libro_extra: list[str] | None = None,
                       listas_extra: set[str] | None = None) -> None:
    listas, adicionales = _listas_validas(clase, subclase, config, listas_extra)
    trucos = conjuros = 0
    vistos: set[str] = set()
    niveles_libro: list[int] = []
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
        destino = lanzador.libro if config.get("libro") and conjuro["nivel"] > 0 else lanzador.conjuros
        destino.setdefault(conjuro["nivel"], []).append(conjuro["nombre"])
        if conjuro["nivel"] == 0:
            trucos += 1
        else:
            conjuros += 1
            niveles_libro.append(conjuro["nivel"])

    limite_trucos, limite = _limites(config, entrada.nivel, mod, conocidos_extra)
    if config.get("libro"):
        # Los que un rasgo añade gratis al libro están en él pero no cuentan para su límite.
        for id_ in libro_extra or []:
            conjuro = catalogo.obtener("conjuros", id_)
            if conjuro and id_ not in vistos:
                lanzador.libro.setdefault(conjuro["nivel"], []).append(conjuro["nombre"])
                vistos.add(id_)
        maximo_libro = limite_libro(config, entrada.nivel)
        if conjuros > maximo_libro:
            avisos.append(f"{clase['nombre']}: {conjuros} conjuros en el libro, máximo {maximo_libro}")
        avisos.extend(avisos_libro(config, entrada.nivel, niveles_libro, clase["nombre"]))
        conjuros = 0
        for id_ in dict.fromkeys(personaje.preparados.get(clase["id"], [])):
            conjuro = catalogo.obtener("conjuros", id_)
            if conjuro is None or id_ not in vistos or conjuro["nivel"] == 0:
                avisos.append(f"{clase['nombre']}: «{conjuro['nombre'] if conjuro else id_}» está preparado "
                              "pero no está en el libro")
                continue
            lanzador.conjuros.setdefault(conjuro["nivel"], []).append(conjuro["nombre"])
            conjuros += 1
    for nombres in (*lanzador.conjuros.values(), *lanzador.libro.values()):
        nombres.sort()

    if limite_trucos is not None and trucos > limite_trucos:
        avisos.append(f"{clase['nombre']}: {trucos} trucos elegidos, máximo {limite_trucos}")
    if limite is not None and conjuros > limite:
        palabra = "preparados" if config.get("libro") else "elegidos"
        avisos.append(f"{clase['nombre']}: {conjuros} conjuros {palabra}, máximo {limite}")


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
        if efecto.get("al_libro"):
            continue  # va al libro (ver _conjuros_elegidos), no a los siempre preparados
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
             competentes: set[str], bonificadores: list[dict], efectos_des: list[dict],
             pequeno: bool = False, otras_caracteristicas: list[dict] | None = None) -> list[Ataque]:
    """Un ataque por arma distinta (la misma arma +1 cuenta aparte). «otras_caracteristicas»: rasgos que dejan atacar
    con otra característica si es mejor (Listo para la Batalla: Inteligencia con armas mágicas)."""
    ataques, vistos = [], set()
    for item, entrada in objetos:
        if not entrada or entrada["categoria"] != "arma" or (entrada["id"], item.bonificador) in vistos:
            continue
        vistos.add((entrada["id"], item.bonificador))
        arma = entrada["arma"]
        propiedades = arma.get("propiedades", [])
        if "sutil" in propiedades or _admite_destreza(entrada, efectos_des):
            car = "des" if mods["des"] > mods["fue"] else "fue"
        elif arma["tipo"] == "distancia":
            car = "des"
        else:
            car = "fue"
        for efecto in otras_caracteristicas or []:
            if (item.bonificador is not None or not efecto.get("solo_magicas")) and mods[efecto["caracteristica"]] > mods[car]:
                car = efecto["caracteristica"]
        magia = item.bonificador or 0
        competente = bool({entrada["id"], GRUPO_ARMA[arma["categoria"]]} & competentes)
        bono = mods[car] + (competencia if competente else 0) + magia
        bono += sum(b["valor"] for b in bonificadores if b.get("tipo_arma") in (None, arma["tipo"]))
        notas = []
        if arma.get("dano_versatil"):
            notas.append(f"A dos manos: {_formula_dano(arma['dano_versatil'], mods[car] + magia)}")
        if arma.get("alcance"):
            notas.append(f"Alcance {arma['alcance']} pies")
        if not competente:
            notas.append("Sin competencia")
        if pequeno and "pesada" in propiedades:
            notas.append("Desventaja (arma pesada y criatura Pequeña)")
        dano = _formula_dano(arma["dano"], mods[car] + magia)
        ataques.append(Ataque(_nombre_magico(entrada["nombre"], item.bonificador), bono, dano,
                              TIPOS_DANO.get(arma["tipo_dano"], arma["tipo_dano"]), "; ".join(notas)))
    return ataques


def _ataques_de_rasgos(aplicables: list[EfectoAplicado], catalogo: Catalogo, mods: dict[str, int], competencia: int,
                       niveles_clase: dict[str, int], contexto: dict, avisos: list[str]) -> list[Ataque]:
    """Ataques que da un rasgo y no un objeto: el sin armas mejorado (Artes Marciales del monje y similares) y las
    armas que crea el rasgo (Espadas Psíquicas, los guanteletes de la Armadura Arcana). Siempre hay competencia."""
    ataques = []
    for aplicado in aplicables:
        if aplicado.tipo not in ("ataque_desarmado", "ataque"):
            continue
        efecto = aplicado.efecto
        nombre = efecto.get("nombre", "Ataque sin armas")
        variables = _contexto_efecto(efecto, aplicado.origen, catalogo, niveles_clase, contexto)
        try:
            dado = rellenar(efecto["dano"], variables)
        except ErrorExpresion as exc:
            avisos.append(f"{nombre}: {exc}")
            continue
        car = max(efecto.get("caracteristicas", ["fue"]), key=lambda c: mods[c])
        tipo_dano = efecto.get("tipo_dano", "contundente")
        ataques.append(Ataque(nombre, mods[car] + competencia, _formula_dano(dado, mods[car]),
                              TIPOS_DANO.get(tipo_dano, tipo_dano), efecto.get("notas", "")))
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


def _nombre_competencia(categoria: str, id_: str, catalogo: Catalogo) -> str:
    if categoria == "habilidad" and id_ in HABILIDADES:
        return HABILIDADES[id_][0]
    if categoria == "salvacion" and id_ in CARACTERISTICAS:
        return f"salvaciones de {CARACTERISTICAS[id_]}"
    if id_ in GRUPOS_COMPETENCIA:
        return GRUPOS_COMPETENCIA[id_]
    entrada = catalogo.obtener("idiomas" if categoria == "idioma" else "objetos", id_)
    return entrada["nombre"] if entrada else id_


def _nombres_competencias(competencias: dict[str, set[str]], catalogo: Catalogo) -> dict[str, list[str]]:
    def nombres(categoria: str) -> list[str]:
        return sorted((_nombre_competencia(categoria, i, catalogo) for i in competencias[categoria]), key=clave_alfabetica)

    return {"armaduras": nombres("armadura"), "armas": nombres("arma"),
            "herramientas": nombres("herramienta"), "idiomas": nombres("idioma")}


def _nombre_magico(nombre: str, bonificador: int | None) -> str:
    """«Espada larga +1»; con +0, «Espada larga (mágica)»."""
    if bonificador is None:
        return nombre
    return f"{nombre} +{bonificador}" if bonificador else f"{nombre} (mágica)"


def _describir_objeto(item: ObjetoInventario, entrada: dict | None) -> str:
    nombre = _nombre_magico(item.nombre or (entrada or {}).get("nombre") or item.id or "?", item.bonificador)
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
