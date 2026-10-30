"""Modo sencillo de 5e (2014): preguntas de situaciones cotidianas que deciden el personaje.

Cada respuesta suma puntos a los rasgos del perfil (combate, sigilo, fe…), puede dar pesos directos
(«clases:guerrero»: +2) y empuja el alineamiento. Razas, clases y trasfondos se recomiendan por
afinidad entre su perfil y el del jugador. El resto (características, habilidades, equipo, conjuros y
elecciones) se completa aquí para que salga un personaje jugable, que luego se puede retocar con el
asistente del modo normal.

Solo cuentan las preguntas, perfiles y recomendaciones de los paquetes cargados: un homebrew entra en
el cuestionario con declarar su «perfil», y un paquete puede añadir preguntas propias.

Al subir de nivel (o al crear por encima de nivel 1) hay otras preguntas. Unas son hitos («momento»:
«subida»), planteados desde la Guía del DM (p. 261: un objetivo cumplido, un descubrimiento, un destino
alcanzado) y el entrenamiento entre aventuras (p. 131), que empujan el perfil. Las otras son concretas: una por
cada elección real de esos niveles, con lo que el personaje tiene (sus subclases posibles, sus puntuaciones de
ahora, las dotes cuyo prerrequisito cumple, sus opciones de clase, las escuelas de su lista de conjuros). Lo que
no se responde se decide con el perfil, a través de la tabla rasgo → dotes, opciones y escuelas de las
recomendaciones.
"""
from __future__ import annotations

import copy
import json
import math
import random
import re
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from itertools import zip_longest
from typing import TYPE_CHECKING

from ...nucleo.efectos import EleccionPendiente
from . import motor
from .asistente import Asistente5e, BloqueEquipo, LineaEquipo, OpcionDetallada
from .constantes import (ARRAY_ESTANDAR, CARACTERISTICAS, ESCUELAS_MAGIA, GRUPO_ARMADURA, GRUPO_ARMA, HABILIDADES,
                         PUNTUACION_MAXIMA, VALOR_MAXIMO_PERFIL)

from ...nucleo.personaje import Personaje

if TYPE_CHECKING:
    from ...nucleo.paquetes import Catalogo
    from ...nucleo.sistema import SistemaReglas

PUNTOS_POR_PESO = 5  # cada punto de «pesos» suma esto a la afinidad (que va de 0 a 100)
MINIMO_RESPUESTAS = 6  # por debajo, la recomendación es poco fiable
UMBRAL_ALINEAMIENTO = 2
BONO_CONSTITUCION = 4  # todo aventurero agradece la Constitución
NIVEL_MINIMO_MULTICLASE = 4  # antes, repartir deja a la clase principal sin lo básico (p. ej., su subclase)
MAXIMO_NIVELES_SECUNDARIA = 5
CANDIDATAS_SECUNDARIA = 4  # la secundaria sale de las clases más afines tras la principal
# Cuántas preguntas: cada pregunta tiene un «detalle» (1-3) y entra en ese nivel y en los siguientes.
CANTIDADES = {"rapido": 1, "recomendado": 2, "preciso": 3}
ESTILOS = ("cotidiana", "fantasia", "mezcla")
CONFIGURACION_INICIAL = {"cantidad": "recomendado", "estilo": "cotidiana", "sensible": False}
PESO_SUBIDA_ACTUAL = 2  # las respuestas de esta subida pesan más que las antiguas en lo que se decide ahora
# Preguntas concretas de subida: sus ids empiezan así y su respuesta es la lista de lo elegido.
PREFIJO_CONCRETA = "c:"
MAXIMO_RESPUESTAS_CONCRETAS = 16  # las listas largas (invocaciones, Secretos Mágicos) se acortan a las que mejor encajan
DOTES_PROPUESTAS = 4
REPARTOS_PROPUESTOS = 4  # formas de repartir los puntos de una mejora de característica
EJEMPLOS_POR_ESCUELA = 3
PESO_ESCUELA_CONCRETA = 3  # una escuela elegida a propósito pesa más que la que sugiere un hito (2)
LARGO_DETALLE = 170

# Qué características y habilidades empuja cada rasgo del perfil.
CARACTERISTICAS_POR_RASGO = {
    "combate": {"fue": 2, "con": 1}, "agilidad": {"des": 2}, "aguante": {"con": 2}, "proteccion": {"con": 1, "fue": 1},
    "sigilo": {"des": 1}, "astucia": {"int": 1, "car": 1}, "carisma": {"car": 2}, "saber": {"int": 2},
    "naturaleza": {"sab": 2}, "fe": {"sab": 2}, "arcano": {"int": 1, "car": 1}, "curacion": {"sab": 2},
}
HABILIDADES_POR_RASGO = {
    "combate": {"atletismo": 2, "intimidacion": 1}, "agilidad": {"acrobacias": 2, "juego_de_manos": 1},
    "aguante": {"atletismo": 1, "supervivencia": 1}, "proteccion": {"percepcion": 2, "perspicacia": 1},
    "sigilo": {"sigilo": 2, "juego_de_manos": 1}, "astucia": {"engano": 2, "juego_de_manos": 1, "investigacion": 1},
    "carisma": {"persuasion": 2, "interpretacion": 1}, "saber": {"historia": 2, "investigacion": 2, "conocimiento_arcano": 1},
    "naturaleza": {"supervivencia": 2, "trato_con_animales": 2, "naturaleza": 1}, "fe": {"religion": 2, "perspicacia": 1},
    "arcano": {"conocimiento_arcano": 2}, "curacion": {"medicina": 2, "perspicacia": 1},
}
BONO_HABILIDAD = {"percepcion": 1}  # la más tirada de la mesa


@dataclass(frozen=True)
class Respuesta:
    id: str
    texto: str
    detalle: str = ""  # qué hace (la dote, la subclase…) o cómo queda (las puntuaciones)
    propuesta: bool = False  # la que se elegiría si no se responde


@dataclass(frozen=True)
class Pregunta:
    id: str
    titulo: str
    texto: str
    respuestas: tuple[Respuesta, ...]
    elegir: int = 1  # las concretas de varias opciones (invocaciones, pericia…) piden más de una

    @property
    def concreta(self) -> bool:
        return self.id.startswith(PREFIJO_CONCRETA)


@dataclass(frozen=True)
class Motivo:
    """Una respuesta y cuánto pesó en una recomendación (puntos de afinidad o pasos en un eje de alineamiento)."""
    pregunta: str
    respuesta: str
    puntos: float
    detalle: str = ""


@dataclass(frozen=True)
class Recomendacion:
    id: str
    nombre: str
    afinidad: int  # 0-100
    descripcion: str = ""
    subraza: str | None = None
    subraza_nombre: str = ""

    @property
    def nombre_completo(self) -> str:
        return self.subraza_nombre or self.nombre


def afinidad(perfil_entrada: dict, perfil_jugador: dict) -> float:
    """Coseno entre los dos perfiles (0 = nada que ver, 1 = idénticos en proporción)."""
    producto = sum(v * perfil_jugador.get(r, 0) for r, v in perfil_entrada.items())
    normas = math.sqrt(sum(v * v for v in perfil_entrada.values())) * math.sqrt(sum(v * v for v in perfil_jugador.values()))
    return producto / normas if normas else 0.0


def _nivel_de(clave: str) -> int:
    """Nivel de clase de una elección de clase, subclase o rasgo opcional («clase:brujo:5/invocacion_nivel_5» → 5); 0
    si no lo es."""
    coincidencia = re.match(r"(?:clase|subclase|opcional):[^:/]+:(\d+)/", clave)
    return int(coincidencia[1]) if coincidencia else 0


def _a_id(texto: str) -> str:
    """«Pacto de la Cadena» → «pacto_de_la_cadena» (así se escriben los ids)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")


def _recortar(texto: str, largo: int = LARGO_DETALLE) -> str:
    """En una línea, con mayúscula inicial (los resúmenes de los datos empiezan en minúscula) y sin pasar de «largo»."""
    texto = " ".join((texto or "").split())
    texto = texto[:1].upper() + texto[1:]
    if len(texto) <= largo:
        return texto
    return texto[:largo].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def _modificador(puntuacion: int) -> int:
    return puntuacion // 2 - 5


def _media_dano(dano: str) -> float:
    coincidencia = re.fullmatch(r"(\d+)d(\d+)", dano or "")
    return int(coincidencia[1]) * (int(coincidencia[2]) + 1) / 2 if coincidencia else 1.0


class Cuestionario5e:
    def __init__(self, sistema: SistemaReglas, catalogo: Catalogo, personaje: Personaje):
        self.catalogo = catalogo
        self.personaje = personaje
        self.asistente = Asistente5e(sistema, catalogo, personaje)
        # Al simular una subida para preguntarla: (nivel, decisión, pregunta) de cada elección concreta.
        self._registro: list[tuple[int, str, Pregunta]] | None = None
        self._nivel_minimo_registro = 1

    # ── preguntas y respuestas ─────────────────────────────────────────────

    @property
    def respuestas(self) -> dict[str, str]:
        """pregunta -> respuesta; se guardan en el personaje para poder repetir el resultado."""
        return self.personaje.extra.setdefault("cuestionario", {}).setdefault("respuestas", {})

    def _existe(self, referencia: str) -> bool:
        categoria, id_ = referencia.split(":", 1)
        return self.catalogo.obtener(categoria, id_) is not None

    @property
    def configuracion(self) -> dict:
        """Cantidad («rapido», «recomendado», «preciso»), estilo («cotidiana», «fantasia», «mezcla») y si se
        incluyen las preguntas de contenido sensible o bizarro."""
        guardada = self.personaje.extra.setdefault("cuestionario", {}).setdefault("configuracion", {})
        return {**CONFIGURACION_INICIAL, **guardada}

    def configurar(self, cantidad: str | None = None, estilo: str | None = None, sensible: bool | None = None) -> None:
        if cantidad is not None and cantidad not in CANTIDADES:
            raise ValueError(f"Cantidad desconocida «{cantidad}»")
        if estilo is not None and estilo not in ESTILOS:
            raise ValueError(f"Estilo desconocido «{estilo}»")
        guardada = self.personaje.extra.setdefault("cuestionario", {}).setdefault("configuracion", {})
        for clave, valor in (("cantidad", cantidad), ("estilo", estilo), ("sensible", sensible)):
            if valor is not None:
                guardada[clave] = valor

    def preguntas(self, **configuracion) -> list[Pregunta]:
        """Las preguntas de creación según la configuración (o la que se pase para contarlas).

        Solo las de paquetes cargados cuyos requisitos («requiere») también lo están; una pregunta con
        «sustituye» (p. ej. de Tasha) ocupa el sitio de la que nombra. Con «mezcla», se alternan los dos estilos
        hasta el tamaño de uno solo; las de detalle 1 van primero porque son las que más distinguen.
        """
        conf = {**self.configuracion, **configuracion}
        tope = CANTIDADES[conf["cantidad"]]
        validas = [p for p in self.catalogo.listar("preguntas")
                   if p.get("momento", "creacion") == "creacion" and all(self._existe(r) for r in p.get("requiere", []))
                   and p.get("detalle", 1) <= tope and (conf["sensible"] or not p.get("sensible"))]
        sustitutas = {p["sustituye"]: p for p in validas if p.get("sustituye")}
        validas = [sustitutas.get(p["id"], p) for p in validas if not p.get("sustituye")]
        comunes = [p for p in validas if p.get("estilo") == "comun"]
        por_estilo = {e: sorted((p for p in validas if p.get("estilo", "cotidiana") == e), key=lambda p: p.get("detalle", 1))
                      for e in ("cotidiana", "fantasia")}
        if conf["estilo"] == "mezcla":
            largo = max(len(lista) for lista in por_estilo.values())
            elegidas = [p for par in zip_longest(por_estilo["cotidiana"], por_estilo["fantasia"]) for p in par if p][:largo]
        else:
            # Un paquete sin preguntas de ese estilo (homebrew) usa las que tenga.
            elegidas = por_estilo[conf["estilo"]] or por_estilo["cotidiana"] or por_estilo["fantasia"]
        return [self._pregunta(p) for p in comunes + elegidas]

    @staticmethod
    def _pregunta(datos: dict) -> Pregunta:
        return Pregunta(datos["id"], datos["nombre"], datos["texto"],
                        tuple(Respuesta(r["id"], r["texto"]) for r in datos["respuestas"]))

    def responder(self, pregunta: str, respuesta: str | None) -> None:
        if respuesta is None:
            self.respuestas.pop(pregunta, None)
            return
        datos = self.catalogo.obtener("preguntas", pregunta)
        if datos is None or not any(r["id"] == respuesta for r in datos["respuestas"]):
            raise ValueError(f"No existe la respuesta «{respuesta}» a la pregunta «{pregunta}»")
        self.respuestas[pregunta] = respuesta

    def _elegidas(self, respuestas: dict[str, str] | None = None) -> list[dict]:
        elegidas = []
        for pregunta, respuesta in (self.respuestas if respuestas is None else respuestas).items():
            datos = self.catalogo.obtener("preguntas", pregunta) or {}
            elegidas += [r for r in datos.get("respuestas", []) if r["id"] == respuesta]
        return elegidas

    def _respondidas(self) -> list[tuple[dict, dict]]:
        """(pregunta, respuesta) de las preguntas de creación respondidas."""
        pares = []
        for pregunta, respuesta in self.respuestas.items():
            datos = self.catalogo.obtener("preguntas", pregunta) or {}
            pares += [(datos, r) for r in datos.get("respuestas", []) if r["id"] == respuesta]
        return pares

    def _perfil_de(self, categoria: str, id_: str, subraza: str | None = None) -> tuple[dict, list[str]]:
        entrada = self.catalogo.obtener(categoria, id_) or {}
        perfil = dict(entrada.get("perfil", {}))
        referencias = [f"{categoria}:{id_}"]
        if subraza:
            for rasgo, valor in (self.catalogo.obtener("subrazas", subraza) or {}).get("perfil", {}).items():
                perfil[rasgo] = perfil.get(rasgo, 0) + valor
            referencias.append(f"subrazas:{subraza}")
        return perfil, referencias

    def explicar(self, categoria: str, id_: str, subraza: str | None = None) -> list[Motivo]:
        """Qué respuestas han pesado en la afinidad con una raza, clase o trasfondo, de más a menos.

        Los puntos son lo que bajaría (o subiría, si son negativos) la afinidad si esa pregunta no se hubiera
        respondido: así se ve qué preguntas han decidido y en qué medida.
        """
        perfil_entrada, referencias = self._perfil_de(categoria, id_, subraza)
        respondidas = self._respondidas()

        def puntuacion(pares) -> float:
            respuestas = [r for _, r in pares]
            pesos = self._sumar(respuestas, "pesos")
            return 100 * afinidad(perfil_entrada, self._sumar(respuestas, "perfil")) + \
                PUNTOS_POR_PESO * sum(pesos.get(r, 0) for r in referencias)

        total = puntuacion(respondidas)
        motivos = []
        for n, (pregunta, respuesta) in enumerate(respondidas):
            puntos = total - puntuacion(respondidas[:n] + respondidas[n + 1:])
            if abs(puntos) >= 0.5:
                rasgos = [f"{r} {v:+d}" for r, v in respuesta.get("perfil", {}).items() if perfil_entrada.get(r)]
                directos = [f"{v:+d} directo" for r, v in respuesta.get("pesos", {}).items() if r in referencias]
                motivos.append(Motivo(pregunta["nombre"], respuesta["texto"], round(puntos, 1), ", ".join(rasgos + directos)))
        return sorted(motivos, key=lambda m: -abs(m.puntos))

    def explicar_alineamiento(self) -> list[Motivo]:
        """Respuestas que han movido el alineamiento: puntos de orden (+ legal, − caótico) y de moral (+ bueno, − malo)."""
        motivos = []
        for pregunta, respuesta in self._respondidas():
            eje = respuesta.get("eje", {})
            if eje:
                partes = [f"{'orden' if k == 'orden' else 'moral'} {v:+d}" for k, v in eje.items()]
                motivos.append(Motivo(pregunta["nombre"], respuesta["texto"], sum(abs(v) for v in eje.values()),
                                      ", ".join(partes)))
        return sorted(motivos, key=lambda m: -m.puntos)

    def totales_alineamiento(self) -> dict[str, int]:
        return {k: v for k, v in self._sumar([r for _, r in self._respondidas()], "eje").items()}

    def _todas_las_elegidas(self) -> list[dict]:
        """Las de la creación y las de todas las subidas de nivel (las ya aplicadas y la que está en curso)."""
        elegidas = self._elegidas()
        for subida in self.subidas_anteriores:
            elegidas += self._elegidas(subida["respuestas"])
        return elegidas + self._elegidas(self.respuestas_subida)

    @staticmethod
    def _sumar(respuestas: list[dict], campo: str, factor: int = 1) -> dict[str, int]:
        total: dict[str, int] = defaultdict(int)
        for respuesta in respuestas:
            for clave, valor in respuesta.get(campo, {}).items():
                total[clave] += valor * factor
        return dict(total)

    def perfil(self) -> dict[str, int]:
        return self._sumar(self._todas_las_elegidas(), "perfil")

    def pesos(self) -> dict[str, int]:
        return self._sumar(self._todas_las_elegidas(), "pesos")

    def alineamiento(self) -> str:
        ejes = {"orden": 0, "moral": 0}
        for respuesta in self._elegidas():
            for eje, valor in respuesta.get("eje", {}).items():
                ejes[eje] += valor
        orden = "Legal" if ejes["orden"] >= UMBRAL_ALINEAMIENTO else "Caótico" if ejes["orden"] <= -UMBRAL_ALINEAMIENTO else ""
        moral = "bueno" if ejes["moral"] >= UMBRAL_ALINEAMIENTO else "malvado" if ejes["moral"] <= -UMBRAL_ALINEAMIENTO else ""
        if not orden and not moral:
            return "Neutral"
        return f"{orden or 'Neutral'} {moral or 'neutral'}"

    def _rng(self, sal: str = "") -> random.Random:
        """Azar reproducible: mismas respuestas, mismo personaje (los empates no dependen de la suerte)."""
        return random.Random(json.dumps(sorted(self.respuestas.items())) + sal)

    # ── preguntas al subir de nivel ────────────────────────────────────────

    @property
    def respuestas_subida(self) -> dict[str, str | list[str]]:
        """Respuestas de la subida de nivel en curso (se archivan al aplicarla): id del hito o, en las concretas,
        lista de lo elegido."""
        return self.personaje.extra.setdefault("cuestionario", {}).setdefault("subida", {})

    @property
    def subidas_anteriores(self) -> list[dict]:
        """[{«desde», «hasta», «respuestas»}] de cada subida ya aplicada."""
        return self.personaje.extra.setdefault("cuestionario", {}).setdefault("subidas", [])

    def decisiones_de_subida(self, niveles: int = 1, clase: str | None = None) -> set[str]:
        """Qué traen esos niveles: «mejora», «subclase», «conjuros» u «opciones» (se prueba sobre una copia)."""
        copia = Personaje.desde_dict(copy.deepcopy(self.personaje.a_dict()))
        a = Asistente5e(self.asistente.sistema, self.catalogo, copia)
        limites = {p.clase_id: (p.limite_trucos, p.limite_conjuros, p.limite_libro) for p in a.planes_conjuros()}
        a.subir_nivel(niveles, clase)
        decisiones = set()
        if any(e.subclase is None and a.subclases(e.clase) for e in copia.clases):
            decisiones.add("subclase")
        for eleccion in (e for e in a.sistema.resolver(copia, self.catalogo).elecciones if e.faltan > 0):
            decisiones.add("mejora" if "caracteristicas" in {o.id for o in eleccion.opciones} else "opciones")
        if any(limites.get(p.clase_id) != (p.limite_trucos, p.limite_conjuros, p.limite_libro) for p in a.planes_conjuros()):
            decisiones.add("conjuros")
        return decisiones

    def preguntas_de_subida(self, niveles: int = 1, clase: str | None = None) -> list[Pregunta]:
        """Las preguntas de una subida: hitos de la Guía del DM y una concreta por cada elección real de esos niveles
        (con su subclase posible, sus puntuaciones de ahora, las dotes que puede coger…). Cuantas más decisiones
        traen los niveles, más preguntas; si no traen ninguna, ninguna.

        Se simula la subida sobre una copia con las respuestas que ya haya: lo respondido cambia lo siguiente (la
        subclase trae sus opciones; una mejora, las puntuaciones de la próxima).
        """
        registro = self._simular(lambda q: q.subir_nivel(niveles, clase), nivel_minimo=1)
        return self._con_hitos(registro, niveles)

    def preguntas_de_historia(self, nivel: int, **eleccion) -> list[Pregunta]:
        """Al crear por encima de nivel 1, con raza, clase y trasfondo ya elegidos (lo que admite «generar»): lo
        mismo que una subida desde nivel 1. Las elecciones de nivel 1 siguen saliendo del perfil."""
        if nivel <= 1:
            return []
        registro = self._simular(lambda q: q.generar(nivel=nivel, **eleccion), nivel_minimo=2)
        return self._con_hitos(registro, nivel - 1)

    def _simular(self, operacion: Callable[[Cuestionario5e], None], nivel_minimo: int) -> list[tuple[int, str, Pregunta]]:
        copia = Personaje.desde_dict(copy.deepcopy(self.personaje.a_dict()))
        simulado = Cuestionario5e(self.asistente.sistema, self.catalogo, copia)
        simulado._registro, simulado._nivel_minimo_registro = [], nivel_minimo
        operacion(simulado)
        return simulado._registro

    def _con_hitos(self, registro: list[tuple[int, str, Pregunta]], niveles: int) -> list[Pregunta]:
        """Delante de las concretas, uno a tres hitos (según cuántos niveles se suben) que tocan lo que se decide.

        Se saltan los hitos de un solo propósito que ya cubre una concreta (entrenar para la mejora, la escuela de
        magia): preguntar las dos cosas sería repetirse. Primero, los que no salieron en subidas anteriores.
        """
        decisiones = {decision for _, decision, _ in registro}
        if not decisiones:
            return []
        cuantos = 1 if niveles < 5 else 2 if niveles < 10 else 3
        hechas = {p for subida in self.subidas_anteriores for p in subida["respuestas"]}
        candidatas = [p for p in self.catalogo.listar("preguntas")
                      if p.get("momento") == "subida" and all(self._existe(r) for r in p.get("requiere", []))
                      and set(p.get("decide", [])) & decisiones
                      and not (len(p.get("decide", [])) == 1 and p["decide"][0] in decisiones)]
        candidatas.sort(key=lambda p: p["id"] in hechas)
        concretas = [pregunta for _, _, pregunta in sorted(registro, key=lambda r: r[0])]
        return [self._pregunta(p) for p in candidatas[:cuantos]] + concretas

    def responder_subida(self, pregunta: str, respuesta: str | list[str] | None) -> None:
        """Un hito se responde con el id de la respuesta; una concreta («c:…»), con la lista de lo elegido. Si lo
        elegido deja de valer (otra respuesta cambió las opciones), se decide como si no se hubiera respondido."""
        if not respuesta:
            self.respuestas_subida.pop(pregunta, None)
            return
        if pregunta.startswith(PREFIJO_CONCRETA):
            valores = [respuesta] if isinstance(respuesta, str) else list(respuesta)
            if not all(isinstance(v, str) and v for v in valores):
                raise ValueError(f"Respuesta no válida a la pregunta «{pregunta}»")
            self.respuestas_subida[pregunta] = valores
            return
        datos = self.catalogo.obtener("preguntas", pregunta)
        if datos is None or datos.get("momento") != "subida" or not any(r["id"] == respuesta for r in datos["respuestas"]):
            raise ValueError(f"No existe la respuesta «{respuesta}» a la pregunta de subida «{pregunta}»")
        self.respuestas_subida[pregunta] = respuesta

    def conservar_respuestas_subida(self, vigentes: set[str]) -> None:
        """Descarta las respuestas a preguntas que ya no se plantean (p. ej., de otra clase elegida antes)."""
        for pregunta in [p for p in self.respuestas_subida if p not in vigentes]:
            del self.respuestas_subida[pregunta]

    def _respuesta_concreta(self, pregunta: str) -> list[str]:
        valor = self.respuestas_subida.get(pregunta) or []
        return [valor] if isinstance(valor, str) else list(valor)

    def _se_pregunta(self, clave: str) -> bool:
        """Si se está simulando para preguntar y esa elección es de las que se preguntan: de clase o subclase, de
        fuera (no anidada en otra) y de los niveles que cuentan (al crear, desde el 2)."""
        return self._registro is not None and "=" not in clave and _nivel_de(clave) >= self._nivel_minimo_registro

    def _registrar(self, nivel: int, decision: str, pregunta: Pregunta) -> None:
        if self._registro is not None and all(p.id != pregunta.id for _, _, p in self._registro):
            self._registro.append((nivel, decision, pregunta))

    def _hay_subidas(self) -> bool:
        return bool(self.respuestas_subida or self.subidas_anteriores)

    def _perfil_decision(self) -> dict[str, float]:
        """El perfil de siempre, llevado a 0-3, más las respuestas de esta subida reforzadas: lo vivido ahora decide y
        el carácter de siempre desempata."""
        total = self.perfil()
        maximo = max(total.values(), default=0) or 1
        perfil = {rasgo: VALOR_MAXIMO_PERFIL * valor / maximo for rasgo, valor in total.items()}
        for rasgo, valor in self._sumar(self._elegidas(self.respuestas_subida), "perfil", PESO_SUBIDA_ACTUAL).items():
            perfil[rasgo] = perfil.get(rasgo, 0) + valor
        return perfil

    def _quiere_dote(self) -> bool:
        """Mejora de característica o dote, según cómo dice el jugador que ha entrenado en esta subida."""
        mejoras = [r["mejora"] for r in self._elegidas(self.respuestas_subida) if "mejora" in r]
        return mejoras.count("dote") > mejoras.count("caracteristicas")

    def _por_rasgo(self, campo: str) -> list[str]:
        """Ids de «dotes», «opciones» o «conjuros» que encajan con el perfil (tabla rasgo → ids de las
        recomendaciones), de más a menos. Solo cuando ha habido preguntas de subida: al crear sin ellas, el
        cuestionario sigue con las recomendaciones de la clase."""
        if not self._hay_subidas():
            return []
        perfil = self._perfil_decision()
        puntos: dict[str, float] = defaultdict(float)
        # Cada id toma su mejor rasgo: Observador sale en tres y no debe ganar siempre por sumarlos.
        for entrada in self.catalogo.listar("recomendaciones"):
            valor = perfil.get(entrada.get("rasgo", ""), 0)
            for posicion, id_ in enumerate(entrada.get(campo, []) if valor > 0 else []):
                puntos[id_] = max(puntos[id_], valor - posicion / 100)
        for referencia, valor in self.pesos().items():
            categoria, id_ = referencia.split(":", 1)
            if categoria == campo:
                puntos[id_] += valor
        return [i for i, p in sorted(puntos.items(), key=lambda x: -x[1]) if p > 0]

    def _puntos_escuela(self) -> dict[str, float]:
        """Escuelas de magia preferidas: las de los rasgos del perfil y las que piden las respuestas de subida."""
        if not self._hay_subidas():
            return {}
        perfil = self._perfil_decision()
        puntos: dict[str, float] = defaultdict(float)
        # Cada escuela toma su mejor rasgo (la abjuración sale de cuatro: no debe ganar por sumarlos).
        for entrada in self.catalogo.listar("recomendaciones"):
            for escuela in entrada.get("escuelas", []):
                puntos[escuela] = max(puntos[escuela], perfil.get(entrada.get("rasgo", ""), 0))
        anteriores = [r for s in self.subidas_anteriores for r in self._elegidas(s["respuestas"])]
        for escuela, valor in self._sumar(anteriores, "escuelas").items():
            puntos[escuela] += valor
        for escuela, valor in self._sumar(self._elegidas(self.respuestas_subida), "escuelas", PESO_SUBIDA_ACTUAL).items():
            puntos[escuela] += valor
        return puntos

    def _contexto_requisitos(self) -> dict:
        """Puntuaciones, competencias y si lanza conjuros: lo que miran los prerrequisitos de las dotes."""
        ficha = self.asistente.ficha()
        competencias: dict[str, set[str]] = defaultdict(set)
        for aplicado in self.asistente.sistema.resolver(self.personaje, self.catalogo).aplicados:
            if aplicado.tipo == "competencia":
                competencias[aplicado.efecto["categoria"]].add(aplicado.efecto["id"])
        return {"puntuaciones": {c: v.puntuacion for c, v in ficha.caracteristicas.items()},
                "competencias": competencias, "lanzador": bool(ficha.lanzadores)}

    def _prerrequisito(self, id_: str, contexto: dict | None = None) -> bool | None:
        """Si cumple ya el prerrequisito de una dote u opción: True (o no tiene), False, o None si no se sabe.

        Los de las opciones (invocaciones, disciplinas) son texto: se leen «nivel N de <clase>», «Pacto de…» y
        «truco <conjuro>». Un truco cuenta como desconocido mientras no haya conjuros elegidos (al crear, se eligen
        después de las opciones); cualquier otra cosa, también.
        """
        dote = self.catalogo.obtener("dotes", id_)
        if dote is not None:
            if not dote.get("prerrequisito"):
                return True
            contexto = contexto or self._contexto_requisitos()
            return motor.cumple_requisito(dote["prerrequisito"], contexto["puntuaciones"], contexto["competencias"],
                                          contexto["lanzador"])
        texto = ((self.catalogo.obtener("opciones", id_) or {}).get("prerrequisito") or {}).get("texto", "").strip()
        resultado: bool | None = True
        for parte in re.split(r"\s+y\s+|,\s*", texto) if texto else []:
            if coincidencia := re.fullmatch(r"nivel (\d+) de (.+)", parte, re.IGNORECASE):
                clase = _a_id(coincidencia[2])
                if sum(e.nivel for e in self.personaje.clases if e.clase == clase) < int(coincidencia[1]):
                    return False
            elif parte.lower().startswith("pacto "):
                if not any(_a_id(parte) in valores for valores in self.personaje.elecciones.values()):
                    return False
            elif coincidencia := re.fullmatch(r"truco (.+)", parte, re.IGNORECASE):
                conocidos = {i for ids in self.personaje.conjuros.values() for i in ids}
                if _a_id(coincidencia[1]) not in conocidos:
                    if conocidos:
                        return False
                    resultado = None
            else:
                resultado = None
        return resultado

    # ── recomendaciones ────────────────────────────────────────────────────

    def _puntuacion(self, perfil: dict, *referencias: str) -> float:
        pesos = self.pesos()
        return 100 * afinidad(perfil, self.perfil()) + PUNTOS_POR_PESO * sum(pesos.get(r, 0) for r in referencias)

    def _ordenar(self, candidatos: list[tuple[float, Recomendacion]], sal: str) -> list[tuple[float, Recomendacion]]:
        """De más a menos afín; los empates (p. ej. los colores de dracónido) se deciden con azar reproducible."""
        rng = self._rng(sal)
        con_desempate = [(puntuacion, rng.random(), r) for puntuacion, r in candidatos]
        return [(puntuacion, r) for puntuacion, _, r in sorted(con_desempate, key=lambda c: (-c[0], c[1]))]

    @staticmethod
    def _recomendacion(opcion: OpcionDetallada, puntuacion: float, **extra) -> Recomendacion:
        return Recomendacion(opcion.id, opcion.nombre, max(0, min(100, round(puntuacion))), opcion.descripcion, **extra)

    def recomendar_razas(self) -> list[Recomendacion]:
        """Una por raza, con la subraza que mejor encaja (el perfil de la subraza se suma al de la raza)."""
        candidatos = []
        for raza in self.asistente.razas():
            mejores = []
            for subraza in self.asistente.subrazas_de(raza.id):
                perfil = dict(raza.perfil)
                for rasgo, valor in subraza.perfil.items():
                    perfil[rasgo] = perfil.get(rasgo, 0) + valor
                puntuacion = self._puntuacion(perfil, f"razas:{raza.id}", f"subrazas:{subraza.id}")
                mejores.append((puntuacion, self._recomendacion(raza, puntuacion, subraza=subraza.id,
                                                                subraza_nombre=subraza.nombre)))
            if mejores:
                candidatos.append(self._ordenar(mejores, raza.id)[0])
            else:
                puntuacion = self._puntuacion(raza.perfil, f"razas:{raza.id}")
                candidatos.append((puntuacion, self._recomendacion(raza, puntuacion)))
        return [r for _, r in self._ordenar(candidatos, "razas")]

    def _recomendar(self, categoria: str, opciones: list[OpcionDetallada]) -> list[Recomendacion]:
        candidatos = [(p, self._recomendacion(o, p)) for o in opciones
                      for p in [self._puntuacion(o.perfil, f"{categoria}:{o.id}")]]
        return [r for _, r in self._ordenar(candidatos, categoria)]

    def recomendar_clases(self) -> list[Recomendacion]:
        return self._recomendar("clases", self.asistente.clases())

    def recomendar_trasfondos(self) -> list[Recomendacion]:
        return self._recomendar("trasfondos", self.asistente.trasfondos())

    def _mejor_subclase(self, clase_id: str | None = None) -> str | None:
        ordenadas = self._recomendar("subclases", self.asistente.subclases(clase_id))
        return ordenadas[0].id if ordenadas else None

    # ── multiclase ─────────────────────────────────────────────────────────

    @property
    def acepta_multiclase(self) -> bool:
        return bool(self.personaje.extra.get("cuestionario", {}).get("multiclase", False))

    def aceptar_multiclase(self, acepta: bool) -> None:
        """Lo primero que se pregunta: si el jugador quiere una sola clase o acepta una propuesta de multiclase."""
        self.personaje.extra.setdefault("cuestionario", {})["multiclase"] = acepta
        # Aceptarla es activar la regla opcional, que viene apagada.
        self.personaje.reglas_opcionales["multiclase"] = acepta

    def _claves(self, clase_id: str) -> set[str]:
        """Características que la clase necesita altas: la de lanzar conjuros y las de su requisito de multiclase."""
        clase = self.catalogo.obtener("clases", clase_id) or {}
        requisitos = clase.get("requisitos_multiclase", {})
        claves = set(requisitos.get("caracteristicas", {}))
        claves |= set(list(requisitos.get("alguna_caracteristica", {}))[:1])
        lanzamiento = (clase.get("lanzamiento") or {}).get("caracteristica")
        return claves | ({lanzamiento} if lanzamiento else set())

    def compatibles(self, principal: str, secundaria: str) -> bool:
        """Entre las dos no piden más de tres características (el array estándar solo tiene 15, 14 y 13)."""
        return principal != secundaria and len(self._claves(principal) | self._claves(secundaria)) <= 3

    def proponer_reparto(self, nivel: int, clase: str | None = None) -> list[tuple[str, int]]:
        """[(clase, niveles)]: una sola clase, o la principal y la más afín compatible tras ella.

        La secundaria se queda un tercio de los niveles (de 1 a 5): suficiente para sus rasgos de entrada sin
        quitarle a la principal lo que la define (como mínimo, llega al nivel de su subclase).
        """
        clase = clase or self.recomendar_clases()[0].id
        if not self.acepta_multiclase or nivel < NIVEL_MINIMO_MULTICLASE or not self.asistente.multiclase_activa():
            return [(clase, nivel)]
        candidatas = [r.id for r in self.recomendar_clases() if r.id != clase][:CANDIDATAS_SECUNDARIA]
        secundaria = next((c for c in candidatas if self.compatibles(clase, c)), None)
        if secundaria is None:
            return [(clase, nivel)]
        niveles = max(1, min(nivel // 3, MAXIMO_NIVELES_SECUNDARIA))
        # La principal no baja del nivel en que gana su subclase.
        nivel_subclase = (self.catalogo.obtener("clases", clase) or {}).get("nivel_subclase", 1)
        niveles = min(niveles, nivel - nivel_subclase)
        if niveles < 1:
            return [(clase, nivel)]
        return [(clase, nivel - niveles), (secundaria, niveles)]

    # ── generación del personaje ───────────────────────────────────────────

    def generar(self, nivel: int = 1, raza: str | None = None, subraza: str | None = None,
                clase: str | None = None, trasfondo: str | None = None,
                reparto: list[tuple[str, int]] | None = None) -> None:
        """Rellena el personaje entero con lo recomendado (o lo indicado) y decisiones razonables para el resto.

        «reparto» fuerza las clases y sus niveles; si no se da y el jugador acepta multiclase, se propone uno.
        """
        a = self.asistente
        if raza is None:
            mejor = self.recomendar_razas()[0]
            raza, subraza = mejor.id, mejor.subraza
        clase = clase or self.recomendar_clases()[0].id
        trasfondo = trasfondo or self.recomendar_trasfondos()[0].id

        a.elegir_raza(raza)
        if subraza:
            a.elegir_subraza(subraza)
        nivel = min(nivel, a.nivel_maximo())
        reparto = reparto or self.proponer_reparto(nivel, clase)
        if len(reparto) > 1:  # un reparto explícito en varias clases es pedir la multiclase
            self.personaje.reglas_opcionales["multiclase"] = True
        a.personaje.clases = []
        a.establecer_nivel(sum(n for _, n in reparto))
        a.elegir_clase(reparto[0][0])
        for otra, niveles in reparto[1:]:
            a.anadir_clase(otra, niveles)
        for entrada in list(a.personaje.clases):
            self._decidir_subclase(entrada.clase)
        a.elegir_trasfondo(trasfondo)
        self._caracteristicas()
        self._completar_elecciones()
        self._equipo()
        if a.nivel > 1:
            self._registrar_escuelas(None)
        self._conjuros()
        self._ajustar_al_libro()
        self._detalles()
        self.personaje.extra.setdefault("cuestionario", {})["generado"] = True
        # Al crear por encima de nivel 1, las preguntas de «tu historia hasta ahora» cuentan como una subida.
        if self.respuestas_subida:
            self.subidas_anteriores.append({"desde": 1, "hasta": a.nivel, "respuestas": dict(self.respuestas_subida)})
            self.respuestas_subida.clear()

    def subir_nivel(self, niveles: int = 1, clase: str | None = None) -> None:
        """Sube al personaje conservando lo elegido; solo se decide lo nuevo: subclase, mejoras, opciones de clase y
        conjuros (los que ya tenía se quedan)."""
        a = self.asistente
        desde = a.nivel
        limites = {p.clase_id: (p.limite_trucos, p.limite_conjuros, p.limite_libro) for p in a.planes_conjuros()}
        a.subir_nivel(niveles, clase)
        for entrada in list(self.personaje.clases):
            if entrada.subclase is None:
                self._decidir_subclase(entrada.clase)
        self._completar_elecciones()
        self._corregir_repetidas()
        self._registrar_escuelas(limites)
        self._conjuros(conservar=True)
        self._ajustar_al_libro()
        # Las respuestas de esta subida quedan en el historial: siguen contando en el perfil, pero ya sin refuerzo.
        self.subidas_anteriores.append({"desde": desde, "hasta": a.nivel, "respuestas": dict(self.respuestas_subida)})
        self.respuestas_subida.clear()

    def _puntos_caracteristicas(self) -> dict[str, float]:
        puntos = dict.fromkeys(CARACTERISTICAS, 0.0)
        for rasgo, valor in self.perfil().items():
            for car, peso in CARACTERISTICAS_POR_RASGO.get(rasgo, {}).items():
                puntos[car] += valor * peso
        return puntos

    def orden_caracteristicas(self) -> list[str]:
        """Primero lo que la clase necesita (y, entre «fue o des», lo que dicen las respuestas); luego, las respuestas."""
        puntos = self._puntos_caracteristicas()
        clase = self.catalogo.obtener("clases", self.personaje.clases[0].clase) if self.personaje.clases else {}
        requisitos = (clase or {}).get("requisitos_multiclase", {})
        claves = []
        if ((clase or {}).get("lanzamiento") or {}).get("caracteristica"):
            claves.append(clase["lanzamiento"]["caracteristica"])
        claves += list(requisitos.get("caracteristicas", {}))
        alguna = list(requisitos.get("alguna_caracteristica", {}))
        if alguna:
            claves.append(max(alguna, key=lambda c: (puntos[c], -alguna.index(c))))
        claves = list(dict.fromkeys(claves))
        claves.sort(key=lambda c: -puntos[c])
        # Multiclase: lo que piden las otras clases va justo detrás (necesita 13).
        for entrada in self.personaje.clases[1:]:
            claves += [c for c in sorted(self._claves(entrada.clase), key=lambda c: -puntos[c]) if c not in claves]
        resto = [c for c in CARACTERISTICAS if c not in claves]
        resto.sort(key=lambda c: -(puntos[c] + (BONO_CONSTITUCION if c == "con" else 0)))
        return claves + resto

    def _caracteristicas(self) -> None:
        self.asistente.establecer_metodo("estandar")
        self.personaje.caracteristicas_base = dict(zip(self.orden_caracteristicas(), ARRAY_ESTANDAR, strict=True))

    # ── elecciones del motor (habilidades, idiomas, estilos, mejoras…) ────

    def _recomendados(self, campo: str) -> list[str]:
        """Ids recomendados para la clase (y los generales), en orden de preferencia."""
        ids = []
        for id_ in [e.clase for e in self.personaje.clases] + ["general"]:
            ids += (self.catalogo.obtener("recomendaciones", id_) or {}).get(campo, [])
        return ids

    def _completar_elecciones(self) -> None:
        for vuelta in range(20):  # las elecciones anidadas aparecen al resolver las de fuera
            resolucion = self.asistente.sistema.resolver(self.personaje, self.catalogo)
            pendientes = [e for e in resolucion.elecciones if e.faltan > 0]
            if not pendientes:
                return
            # Las mejoras de característica, enteras, de una en una y por nivel: cada una parte de las puntuaciones
            # que deja la anterior.
            for eleccion in sorted((e for e in pendientes if self._es_mejora(e)), key=lambda e: _nivel_de(e.clave)):
                self._decidir_mejora(eleccion, vuelta)
            # Primero las más restringidas (Bendiciones del Conocimiento: 2 de 4), para que las amplias
            # (Versatilidad con Habilidades del semielfo: 2 de 18) no les quiten las opciones.
            pendientes = sorted((e for e in pendientes if not self._es_mejora(e)), key=lambda e: len(e.opciones) - e.faltan)
            hechas: set[str] = set()
            for eleccion in pendientes:
                if eleccion.clave not in hechas:
                    grupo = self._grupo(eleccion, pendientes)
                    hechas |= {e.clave for e in grupo}
                    self._decidir(grupo, vuelta)

    def _corregir_repetidas(self) -> None:
        """Competencias elegidas antes que ahora llegan por otra vía (la subclase nueva da Perspicacia y el monje la
        eligió a nivel 1): se cambia la repetida por otra, como pide la ficha. De una en una, para que de dos
        elecciones que repiten lo mismo solo cambie una."""
        for eleccion in self.asistente.sistema.resolver(self.personaje, self.catalogo).elecciones:
            efectos = [e for o in eleccion.opciones for e in eleccion.efectos_de(o.id)]
            if not eleccion.seleccion or not efectos or any(e.get("tipo") != "competencia" for e in efectos):
                continue
            conocidas = self.asistente.conocidas(eleccion)
            quedan = [v for v in eleccion.seleccion if v not in conocidas]
            if len(quedan) < len(eleccion.seleccion):
                nuevas = self._elegir(replace(eleccion, seleccion=quedan), self._rng(f"{eleccion.clave}/repetidas"))
                self.asistente.elegir(eleccion.clave, quedan + nuevas)

    @staticmethod
    def _es_mejora(eleccion: EleccionPendiente) -> bool:
        return "caracteristicas" in {o.id for o in eleccion.opciones}

    def _tipo_concreta(self, eleccion: EleccionPendiente) -> str | None:
        """Qué decisión es, si es de las que se preguntan en concreto: «mejora», «opciones» (de clase, dotes,
        pericias y competencias en habilidades o herramientas) o «conjuros» (Secretos Mágicos, Arcanum Místico…).
        Idiomas y demás, no: salen del perfil sin preguntar."""
        ids = [o.id for o in eleccion.opciones]
        if not ids:
            return None
        if "caracteristicas" in ids:
            return "mejora"
        if all(self.catalogo.obtener("opciones", i) or self.catalogo.obtener("dotes", i) for i in ids):
            return "opciones"
        if all(self.catalogo.obtener("conjuros", i) for i in ids):
            # Los que deben estar en el libro (Maestría sobre Conjuros) se ajustan al libro, que se elige después.
            return None if any(isinstance(e, dict) and e.get("en_libro") for e in eleccion.aplicar) else "conjuros"
        efectos = [e for i in ids for e in eleccion.efectos_de(i)]
        if efectos and all(e.get("tipo") == "pericia" or (e.get("tipo") == "competencia" and
                                                           e.get("categoria") in ("habilidad", "herramienta"))
                           for e in efectos):
            return "opciones"
        return None

    def _firma(self, eleccion: EleccionPendiente) -> tuple | None:
        """Lo que hace iguales dos huecos de elección de distintos niveles (las invocaciones de los niveles 2, 5,
        7…): mismas opciones y mismo efecto. None si la elección no se pregunta."""
        if "=" in eleccion.clave or not _nivel_de(eleccion.clave) or self._tipo_concreta(eleccion) is None:
            return None
        return tuple(o.id for o in eleccion.opciones), json.dumps(eleccion.aplicar, sort_keys=True)

    def _grupo(self, eleccion: EleccionPendiente, pendientes: list[EleccionPendiente]) -> list[EleccionPendiente]:
        """La elección y los huecos iguales de otros niveles, por nivel: se preguntan juntos («elige 8»)."""
        firma = self._firma(eleccion)
        if firma is None:
            return [eleccion]
        return sorted((e for e in pendientes if self._firma(e) == firma), key=lambda e: _nivel_de(e.clave))

    def _decidir(self, grupo: list[EleccionPendiente], vuelta: int) -> None:
        """Una elección (o varios huecos iguales): lo respondido en su pregunta concreta, mientras siga valiendo, y
        lo que falte con el perfil."""
        primera = grupo[0]
        if self._registro is not None and self._firma(primera) and \
                max(_nivel_de(e.clave) for e in grupo) >= self._nivel_minimo_registro:
            self._registrar_eleccion(grupo, vuelta)
        respuesta = self._respuesta_concreta(PREFIJO_CONCRETA + primera.clave)
        for eleccion in grupo:
            libres = self._libres(eleccion) if respuesta else []
            toma = [v for v in respuesta if v in libres][: eleccion.faltan]
            respuesta = [v for v in respuesta if v not in toma]
            resto = replace(eleccion, seleccion=eleccion.seleccion + toma)
            elegidas = toma + (self._elegir(resto, self._rng(f"{eleccion.clave}/{vuelta}")) if resto.faltan > 0 else [])
            if elegidas:
                self.asistente.elegir(eleccion.clave, eleccion.seleccion + elegidas)

    def _elegir(self, eleccion: EleccionPendiente, rng: random.Random) -> list[str]:
        n = eleccion.faltan
        ids = [o.id for o in eleccion.opciones]
        if set(ids) <= set(CARACTERISTICAS):
            # Resiliente: no en una salvación que ya tiene (si las tiene todas, como el monje 14, da igual).
            conocidas = self.asistente.conocidas(eleccion)
            evitar = set(conocidas) if len(conocidas) < len(ids) else set()
            if "/origen_" in eleccion.clave:  # Personalizar tu origen: cada mejora de raza a una característica distinta
                evitar |= {v for clave, valores in self.personaje.elecciones.items()
                           if "/origen_" in clave and clave != eleccion.clave for v in valores}
            return self._mejoras(eleccion, n, evitar=evitar)
        elegidas = self._ranking(eleccion, rng)[:n]
        if len(elegidas) < n:
            # Sin bastantes opciones nuevas (Lanzador Ritual con la lista del brujo, para un brujo que ya conoce uno de
            # sus dos rituales): mejor repetir algo que ya tiene por otra vía que dejar la elección a medias.
            conocidas = self.asistente.conocidas(eleccion)
            elegidas += [o.id for o in eleccion.opciones if o.id in conocidas and o.id not in elegidas
                         and (eleccion.repetible or o.id not in eleccion.seleccion)][: n - len(elegidas)]
        return elegidas

    def _libres(self, eleccion: EleccionPendiente) -> list[str]:
        """Las opciones que vale la pena elegir: ni repetidas, ni conseguidas ya por otra vía, ni pericias sin
        competencia, ni dotes u opciones cuyo prerrequisito no cumple."""
        conocidas = self.asistente.conocidas(eleccion)
        sin_competencia = self.asistente.sin_competencia(eleccion)  # pericia: solo donde ya hay competencia
        libres = [o.id for o in eleccion.opciones if o.id not in conocidas and o.id not in sin_competencia
                  and (eleccion.repetible or o.id not in eleccion.seleccion)]
        con_requisito = [i for i in libres if self._tiene_prerrequisito(i)]
        if con_requisito:
            contexto = self._contexto_requisitos()
            incumplidos = {i for i in con_requisito if self._prerrequisito(i, contexto) is False}
            libres = [i for i in libres if i not in incumplidos]
        return libres

    def _ranking(self, eleccion: EleccionPendiente, rng: random.Random) -> list[str]:
        """Las opciones libres de la elección, de la que mejor encaja a la que menos: las primeras son las que se
        eligen si no se responde."""
        libres = self._libres(eleccion)
        if libres and set(libres) <= set(HABILIDADES):
            return self._habilidades(libres, len(libres), rng)
        conjuros = [self.catalogo.obtener("conjuros", i) for i in libres]
        if libres and all(conjuros) and len({c["nivel"] for c in conjuros}) > 1:
            return self._conjuros_de_cualquier_nivel(eleccion, conjuros, len(conjuros), rng)
        # Lo que encaja con lo vivido al subir de nivel va primero; después, lo recomendado para la clase.
        por_rasgo = [i for i in self._por_rasgo("opciones") + self._por_rasgo("dotes") if i in libres]
        if por_rasgo:
            contexto = self._contexto_requisitos()
            por_rasgo = [i for i in por_rasgo if self._prerrequisito(i, contexto) is True]
        preferidas = por_rasgo + self._recomendados("opciones") + self._recomendados("dotes") + self._recomendados("conjuros")
        elegidas = [i for i in dict.fromkeys(preferidas) if i in libres]
        resto = [i for i in libres if i not in elegidas]
        # Sin recomendación: primero lo que no tiene prerrequisitos y, entre eso, al azar.
        rng.shuffle(resto)
        resto.sort(key=lambda i: self._tiene_prerrequisito(i))
        return elegidas + resto

    # ── preguntas concretas (las de cada elección real) ───────────────────

    def _origen(self, clave: str) -> str:
        """Nombre de la clase, subclase o rasgo opcional que da la elección («clase:brujo:2/…» → «Brujo»)."""
        coincidencia = re.match(r"(clase|subclase|opcional):([^:/]+):", clave)
        if not coincidencia:
            return ""
        categoria = {"clase": "clases", "subclase": "subclases", "opcional": "rasgos_opcionales"}[coincidencia[1]]
        return (self.catalogo.obtener(categoria, coincidencia[2]) or {}).get("nombre", coincidencia[2])

    @staticmethod
    def _niveles_texto(niveles: list[int]) -> str:
        if len(niveles) == 1:
            return f"nivel {niveles[0]}"
        return "niveles " + ", ".join(str(n) for n in niveles[:-1]) + f" y {niveles[-1]}"

    def _detalle(self, id_: str, ficha=None) -> str:
        """Qué hace una opción, dote o conjuro (o cómo está ahora la habilidad), en una línea."""
        if id_ in HABILIDADES:
            caracteristica = CARACTERISTICAS[HABILIDADES[id_][1]]
            tirada = (ficha or self.asistente.ficha()).habilidades.get(id_)
            return f"{caracteristica}; ahora {tirada.valor:+d}" if tirada else caracteristica
        conjuro = self.catalogo.obtener("conjuros", id_)
        if conjuro:
            nivel = "truco" if conjuro["nivel"] == 0 else f"nivel {conjuro['nivel']}"
            texto = conjuro.get("resumen") or conjuro.get("descripcion", "")
            return _recortar(f"{ESCUELAS_MAGIA.get(conjuro.get('escuela'), '')}, {nivel}. {texto}")
        for categoria in ("opciones", "dotes", "subclases"):
            entrada = self.catalogo.obtener(categoria, id_)
            if entrada:
                # Los resúmenes con fórmulas («+{mod_car} al daño») no se leen bien sueltos: mejor la descripción.
                resumen = entrada.get("resumen", "")
                return _recortar(resumen if resumen and "{" not in resumen else entrada.get("descripcion", ""))
        return ""

    def _registrar_eleccion(self, grupo: list[EleccionPendiente], vuelta: int) -> None:
        """La pregunta concreta de una elección (o de sus huecos iguales): sus opciones reales, de la que mejor
        encaja a la que menos, marcadas las que se elegirían sin responder."""
        primera = grupo[0]
        total = sum(e.faltan for e in grupo)
        ranking = self._ranking(primera, self._rng(f"{primera.clave}/{vuelta}"))
        if len(ranking) <= total:  # nada que decidir: entran todas
            return
        id_ = PREFIJO_CONCRETA + primera.clave
        respondidas = self._respuesta_concreta(id_)
        mostradas = ranking[:MAXIMO_RESPUESTAS_CONCRETAS]
        mostradas += [r for r in respondidas if r in ranking and r not in mostradas]
        nombres = {o.id: o.nombre for o in primera.opciones}
        ficha = self.asistente.ficha()
        respuestas = tuple(Respuesta(i, nombres.get(i, i), self._detalle(i, ficha), i in ranking[:total]) for i in mostradas)
        niveles = sorted({_nivel_de(e.clave) for e in grupo})
        nombre = primera.nombre if len(grupo) == 1 else re.sub(r"\s*\([^)]*\)$", "", primera.nombre)
        texto = ("¿Cuál encaja con lo que ha vivido tu personaje?" if total == 1 else
                 f"¿Cuáles encajan con lo que ha vivido tu personaje? Elige {total}.")
        self._registrar(niveles[0], self._tipo_concreta(primera) or "opciones",
                        Pregunta(id_, f"{self._origen(primera.clave)} · {self._niveles_texto(niveles)} · {nombre}", texto,
                                 respuestas, total))

    def _anidada(self, clave: str, opcion: str) -> EleccionPendiente | None:
        """La elección que abre una opción: «…/mejora» con «dote» abre «…/mejora=dote/dote»."""
        prefijo = f"{clave}={opcion}/"
        return next((e for e in self.asistente.sistema.resolver(self.personaje, self.catalogo).elecciones
                     if e.clave.startswith(prefijo) and "=" not in e.clave[len(prefijo):]), None)

    def _reparto_valido(self, puntos: EleccionPendiente, reparto: list[str], actuales: dict[str, int]) -> bool:
        validas = {o.id for o in puntos.opciones}
        return (len(reparto) == puntos.faltan and all(c in validas for c in reparto)
                and (puntos.repetible or len(set(reparto)) == len(reparto))
                and all(actuales[c] + reparto.count(c) <= PUNTUACION_MAXIMA for c in reparto))

    def _repartos(self, puntos: EleccionPendiente, actuales: dict[str, int]) -> list[tuple[str, ...]]:
        """Formas de repartir los puntos de una mejora: la de siempre (lo que más necesita la clase) y +2 o +1/+1
        entre sus tres características más importantes, sin pasar de 20."""
        candidatos = [tuple(self._mejoras(puntos, puntos.faltan))]
        if puntos.faltan == 2:
            orden = [c for c in self.orden_caracteristicas() if actuales.get(c, PUNTUACION_MAXIMA) < PUNTUACION_MAXIMA][:3]
            candidatos += [(x, y) for i, x in enumerate(orden) for y in orden[i:]]
        repartos: list[tuple[str, ...]] = []
        for reparto in candidatos:
            if self._reparto_valido(puntos, list(reparto), actuales) and sorted(reparto) not in [sorted(r) for r in repartos]:
                repartos.append(reparto)
        return repartos[:REPARTOS_PROPUESTOS]

    def _decidir_mejora(self, eleccion: EleccionPendiente, vuelta: int) -> None:
        """Mejora de característica o dote, entera (con sus puntos o con su dote): la respuesta concreta si sigue
        valiendo; si no, una dote si lo vivido lo pide (entrenar con un maestro…) y, si no, los puntos donde más
        rinden."""
        a = self.asistente
        clave = eleccion.clave
        a.elegir(clave, ["caracteristicas"])
        puntos = self._anidada(clave, "caracteristicas")
        actuales = {c: v.puntuacion for c, v in a.ficha().caracteristicas.items()}
        opciones: dict[str, tuple[EleccionPendiente, str, list[str]]] = {}
        if puntos is not None:
            for reparto in self._repartos(puntos, actuales):
                opciones[f"car:{'+'.join(reparto)}"] = (puntos, "caracteristicas", list(reparto))
        repartos = list(opciones)
        respondidas = self._respuesta_concreta(PREFIJO_CONCRETA + clave)
        for respuesta in respondidas:  # un reparto respondido que sigue valiendo, aunque ya no esté entre los propuestos
            reparto = respuesta.removeprefix("car:").split("+")
            if respuesta.startswith("car:") and puntos is not None and self._reparto_valido(puntos, reparto, actuales):
                opciones.setdefault(respuesta, (puntos, "caracteristicas", reparto))
        dotes: list[str] = []
        if "dote" in {o.id for o in eleccion.opciones}:
            a.elegir(clave, ["dote"])
            anidada = self._anidada(clave, "dote")
            if anidada is not None:
                dotes = self._ranking(anidada, self._rng(f"{anidada.clave}/{vuelta + 1}"))
                opciones |= {f"dote:{d}": (anidada, "dote", [d]) for d in dotes}
        propuesta = f"dote:{dotes[0]}" if dotes and self._quiere_dote() else (repartos[0] if repartos else None)
        if self._se_pregunta(clave) and len(opciones) > 1:
            mostradas = [*repartos, *(f"dote:{d}" for d in dotes[:DOTES_PROPUESTAS])]
            mostradas += [r for r in [*respondidas, propuesta] if r in opciones and r not in mostradas]
            self._registrar(_nivel_de(clave), "mejora", self._pregunta_mejora(clave, mostradas, propuesta, actuales))
        elegida = next((r for r in respondidas if r in opciones), propuesta)
        if elegida is None:
            a.elegir(clave, ["caracteristicas"])  # sin puntos que repartir (todo a 20): lo resuelve la vuelta siguiente
            return
        anidada, tipo, valores = opciones[elegida]
        a.elegir(clave, [tipo])
        a.elegir(anidada.clave, valores)

    def _pregunta_mejora(self, clave: str, mostradas: list[str], propuesta: str | None,
                         actuales: dict[str, int]) -> Pregunta:
        respuestas = []
        for id_ in mostradas:
            if id_.startswith("dote:"):
                dote = id_.removeprefix("dote:")
                nombre = (self.catalogo.obtener("dotes", dote) or {}).get("nombre", dote)
                respuestas.append(Respuesta(id_, f"Dote: {nombre}", self._detalle(dote), id_ == propuesta))
                continue
            reparto = id_.removeprefix("car:").split("+")
            cambios = {c: reparto.count(c) for c in dict.fromkeys(reparto)}
            texto = " y ".join(f"{CARACTERISTICAS[c]} {actuales[c]} → {actuales[c] + n}" for c, n in cambios.items())
            suben = [f"{CARACTERISTICAS[c]} {_modificador(actuales[c]):+d} → {_modificador(actuales[c] + n):+d}"
                     for c, n in cambios.items() if _modificador(actuales[c] + n) > _modificador(actuales[c])]
            detalle = ("Modificador: " + ", ".join(suben) if suben else
                       "Ningún modificador sube todavía: lo hará con la próxima mejora.")
            respuestas.append(Respuesta(id_, f"Mejorar {texto}", detalle, id_ == propuesta))
        nivel = _nivel_de(clave)
        return Pregunta(PREFIJO_CONCRETA + clave, f"{self._origen(clave)} · nivel {nivel} · Mejora de característica o dote",
                        f"Al llegar a nivel {nivel}, ¿en qué se ha volcado tu personaje?", tuple(respuestas))

    def _decidir_subclase(self, clase_id: str) -> None:
        """La subclase: la respondida en su pregunta concreta o la más afín al perfil."""
        a = self.asistente
        ordenadas = self._recomendar("subclases", a.subclases(clase_id))
        if not ordenadas:
            return
        propuesta = self._mejor_subclase(clase_id)
        id_ = f"{PREFIJO_CONCRETA}subclase_de:{clase_id}"
        if self._registro is not None and len(ordenadas) > 1:
            clase = self.catalogo.obtener("clases", clase_id) or {}
            nivel = clase.get("nivel_subclase", 1)
            respuestas = tuple(Respuesta(r.id, r.nombre, _recortar(r.descripcion), r.id == propuesta) for r in ordenadas)
            self._registrar(nivel, "subclase", Pregunta(
                id_, f"{clase.get('nombre', clase_id)} · nivel {nivel} · Subclase",
                "¿Qué camino ha tomado tu personaje? Es lo que más le marca a partir de ahora.", respuestas))
        validas = {r.id for r in ordenadas}
        a.elegir_subclase(next((v for v in self._respuesta_concreta(id_) if v in validas), propuesta), clase_id)

    def _registrar_escuelas(self, limites: dict | None) -> None:
        """Pregunta concreta de conjuros, una por clase lanzadora que aprende conjuros en esta subida (o, al crear,
        cada una): qué magia ha estudiado, con ejemplos reales de su lista y de los niveles más altos a los que
        llega. «limites»: los de antes de subir, para saber qué clases aprenden algo."""
        if self._registro is None:
            return
        for plan in self.asistente.planes_conjuros():
            if limites is not None and limites.get(plan.clase_id) == (plan.limite_trucos, plan.limite_conjuros,
                                                                     plan.limite_libro):
                continue
            conocidos = set(self.personaje.conjuros.get(plan.clase_id, []))
            ejemplos: dict[str, list[str]] = defaultdict(list)
            for nivel in sorted((n for n in plan.disponibles if n > 0), reverse=True):
                for id_, nombre in plan.disponibles[nivel]:
                    escuela = (self.catalogo.obtener("conjuros", id_) or {}).get("escuela")
                    if escuela and id_ not in conocidos:
                        ejemplos[escuela].append(f"{nombre} ({nivel})")
            if len(ejemplos) < 2:
                continue
            puntos = self._escuelas_sin_responder(plan.clase_id)
            escuelas = sorted(ejemplos, key=lambda e: (-puntos.get(e, 0), -len(ejemplos[e])))
            propuesta = escuelas[0] if puntos.get(escuelas[0], 0) > 0 else None
            respuestas = tuple(Respuesta(e, ESCUELAS_MAGIA.get(e, e), "Por ejemplo: " + ", ".join(
                ejemplos[e][:EJEMPLOS_POR_ESCUELA]), e == propuesta) for e in escuelas)
            self._registrar(99, "conjuros", Pregunta(
                f"{PREFIJO_CONCRETA}escuela:{plan.clase_id}", f"{plan.clase} · Conjuros nuevos",
                "¿Qué clase de magia ha estudiado o descubierto? Sus conjuros nuevos irán por ahí (los de nivel más alto "
                "entre paréntesis).", respuestas))

    def _escuelas_sin_responder(self, clase_id: str) -> dict[str, float]:
        """Las escuelas preferidas sin contar la respuesta a su pregunta concreta: así la propuesta es lo que se elegiría
        si no se responde, y el orden no cambia al pulsar una (la pulsada no salta arriba)."""
        respuestas = dict(self.respuestas_subida)
        self.respuestas_subida.pop(f"{PREFIJO_CONCRETA}escuela:{clase_id}", None)
        try:
            return self._escuelas_de(clase_id)
        finally:
            self.respuestas_subida.clear()
            self.respuestas_subida.update(respuestas)

    def _escuelas_de(self, clase_id: str) -> dict[str, float]:
        """Escuelas preferidas para los conjuros de esa clase: las del perfil y los hitos, más la elegida en su
        pregunta concreta (en esta subida, con más peso, y en las anteriores)."""
        puntos = dict(self._puntos_escuela())
        id_ = f"{PREFIJO_CONCRETA}escuela:{clase_id}"
        respuestas = [(s["respuestas"], 1) for s in self.subidas_anteriores] + [(self.respuestas_subida, PESO_SUBIDA_ACTUAL)]
        for respuesta, peso in respuestas:
            valor = respuesta.get(id_) or []
            for escuela in [valor] if isinstance(valor, str) else valor:
                puntos[escuela] = puntos.get(escuela, 0) + PESO_ESCUELA_CONCRETA * peso
        return puntos

    @staticmethod
    def _conjuros_de_cualquier_nivel(eleccion: EleccionPendiente, conjuros: list[dict], n: int,
                                     rng: random.Random) -> list[str]:
        """Secretos Mágicos y similares: lo más valioso es un conjuro de nivel alto que la clase no tenga ya."""
        clase = next((e.get("clase") for e in eleccion.aplicar if isinstance(e, dict) and e.get("clase")), None)
        rng.shuffle(conjuros)
        conjuros.sort(key=lambda c: (clase in c["listas"], -c["nivel"]))
        return [c["id"] for c in conjuros[:n]]

    def _tiene_prerrequisito(self, id_: str) -> bool:
        return any("prerrequisito" in (self.catalogo.obtener(c, id_) or {}) for c in ("opciones", "dotes"))

    def _mejoras(self, eleccion: EleccionPendiente, n: int, evitar: set[str] | frozenset = frozenset()) -> list[str]:
        """Mejora de característica: lo más importante para la clase, sin pasar de 20."""
        puntuaciones = {c: v.puntuacion for c, v in self.asistente.ficha().caracteristicas.items()}
        validas = {o.id for o in eleccion.opciones} - (set() if eleccion.repetible else set(eleccion.seleccion)) - evitar
        elegidas: list[str] = []
        for car in (c for c in self.orden_caracteristicas() if c in validas):
            while len(elegidas) < n and puntuaciones[car] < 20 and (eleccion.repetible or car not in elegidas):
                elegidas.append(car)
                puntuaciones[car] += 1
        return elegidas

    def _habilidades(self, libres: list[str], n: int, rng: random.Random) -> list[str]:
        puntos = {h: BONO_HABILIDAD.get(h, 0) + rng.random() / 10 for h in libres}
        for rasgo, valor in self.perfil().items():
            for habilidad, peso in HABILIDADES_POR_RASGO.get(rasgo, {}).items():
                if habilidad in puntos:
                    puntos[habilidad] += valor * peso
        return sorted(libres, key=lambda h: -puntos[h])[:n]

    # ── equipo ─────────────────────────────────────────────────────────────

    def _prefiere_destreza(self) -> bool:
        mods = self.asistente.modificadores()
        return mods["des"] > mods["fue"]

    def _competencias_equipo(self) -> set[str]:
        resolucion = self.asistente.sistema.resolver(self.personaje, self.catalogo)
        return {a.efecto["id"] for a in resolucion.aplicados
                if a.tipo == "competencia" and a.efecto["categoria"] in ("arma", "armadura")}

    def _competente(self, objeto: dict, competencias: set[str]) -> bool:
        if objeto["categoria"] == "armadura":
            return bool({objeto["id"], GRUPO_ARMADURA.get(objeto.get("armadura", {}).get("tipo"), "")} & competencias)
        if objeto["categoria"] == "escudo":
            return bool({objeto["id"], "escudos"} & competencias)
        if objeto["categoria"] == "arma":
            return bool({objeto["id"], GRUPO_ARMA.get(objeto["arma"].get("categoria"), "")} & competencias)
        return True

    def _valor_objeto(self, id_: str | None, destreza: bool, competencias: set[str]) -> float:
        objeto = self.catalogo.obtener("objetos", id_) if id_ else None
        if not objeto:
            return 0.0
        if not self._competente(objeto, competencias):
            return -100.0
        if objeto["categoria"] == "armadura":
            tipo = objeto.get("armadura", {}).get("tipo")
            return {"ligera": 1, "media": 0, "pesada": -2}.get(tipo, 0) if destreza else {"pesada": 2, "media": 1}.get(tipo, 0)
        if objeto["categoria"] == "arma":
            arma = objeto["arma"]
            agil = "sutil" in arma.get("propiedades", []) or arma.get("tipo") == "distancia"
            return 1.0 if agil == destreza else -0.5
        return 0.0

    def _alternativa(self, bloque: BloqueEquipo) -> int:
        destreza = self._prefiere_destreza()
        competencias = self._competencias_equipo()
        valores = [sum(self._valor_objeto(linea.id, destreza, competencias) for linea in alternativa)
                   for alternativa in bloque.alternativas]
        return max(range(len(valores)), key=lambda i: (valores[i], -i))  # en empate, la primera (la del libro)

    def _objeto(self, linea: LineaEquipo, con_escudo: bool, ya: list[str], rng: random.Random) -> str:
        candidatos = [i for i, _ in linea.opciones if i not in ya] or [i for i, _ in linea.opciones]
        armas = {i: self.catalogo.obtener("objetos", i) for i in candidatos}
        if not all(o and o["categoria"] == "arma" for o in armas.values()):
            return rng.choice(candidatos)
        destreza = self._prefiere_destreza()
        competencias = self._competencias_equipo()
        raza = self.catalogo.obtener("razas", self.personaje.raza or "") or {}

        def valor(id_: str) -> float:
            arma = armas[id_]["arma"]
            propiedades = arma.get("propiedades", [])
            descartada = (not self._competente(armas[id_], competencias) or "especial" in propiedades
                          or (con_escudo and "a_dos_manos" in propiedades)
                          or (raza.get("tamano") == "pequeno" and "pesada" in propiedades))
            if descartada:
                return -100.0
            agil = "sutil" in propiedades or arma.get("tipo") == "distancia"
            return _media_dano(arma.get("dano", "")) + (2 if agil == destreza else 0) + rng.random() / 10

        return max(candidatos, key=valor)

    def _equipo(self) -> None:
        a = self.asistente
        for bloque in a.bloques_equipo():
            if bloque.elegida is None:
                a.elegir_alternativa(bloque.origen, bloque.indice, self._alternativa(bloque))
        for bloque in a.bloques_equipo():
            alternativa = bloque.alternativas[bloque.elegida]
            con_escudo = any(linea.id == "escudo" for linea in alternativa)
            rng = self._rng(f"equipo/{bloque.origen}/{bloque.indice}")
            ya: list[str] = []
            for n, linea in enumerate(alternativa):
                for hueco in range(linea.cantidad if linea.id is None else 0):
                    objeto = self._objeto(linea, con_escudo, ya, rng)
                    ya.append(objeto)
                    a.elegir_objeto(bloque.origen, bloque.indice, bloque.elegida, n, hueco, objeto)
        a.aplicar_equipo()

    # ── conjuros ───────────────────────────────────────────────────────────

    @staticmethod
    def _repartir(por_nivel: dict[int, list[str]], cantidad: int) -> list[str]:
        """Hasta 2 de cada nivel alto (del más alto al 2) y el resto de nivel 1; si falta de uno, de los demás."""
        niveles = sorted((n for n in por_nivel if n > 0 and por_nivel[n]), reverse=True)
        cupo = dict.fromkeys(niveles, 0)
        restante = cantidad
        for nivel in niveles[:-1]:
            cupo[nivel] = min(2, len(por_nivel[nivel]), max(0, restante - 1))
            restante -= cupo[nivel]
        for nivel in reversed(niveles):  # lo que quede, empezando por el nivel más bajo
            extra = min(restante, len(por_nivel[nivel]) - cupo[nivel])
            cupo[nivel] += extra
            restante -= extra
        return [i for nivel in niveles for i in por_nivel[nivel][: cupo[nivel]]]

    @staticmethod
    def _lo_mas_alto(por_nivel: dict[int, list[str]], cantidad: int) -> list[str]:
        """Al subir de nivel, los conjuros nuevos: de los niveles más altos, hasta 2 de cada uno antes de bajar."""
        niveles = sorted((n for n in por_nivel if n > 0 and por_nivel[n]), reverse=True)
        elegidos: list[str] = []
        while len(elegidos) < cantidad:
            antes = len(elegidos)
            for nivel in niveles:
                elegidos += [i for i in por_nivel[nivel] if i not in elegidos][: min(2, cantidad - len(elegidos))]
            if len(elegidos) == antes:
                break
        return elegidos

    def _conjuros(self, conservar: bool = False) -> None:
        """Trucos y conjuros de cada clase lanzadora. Al subir de nivel («conservar») se quedan los que ya tenía y
        solo se añaden los que faltan hasta el nuevo límite."""
        a = self.asistente
        otras = a.conjuros_de_otras_fuentes()
        por_rasgo = self._por_rasgo("conjuros")
        # Conjuros propuestos por el perfil (curación…): cuanto antes en la lista, más puntos.
        extra = {id_: len(por_rasgo) - posicion for posicion, id_ in enumerate(por_rasgo)}
        escuela = {c["id"]: c["escuela"] for c in self.catalogo.listar("conjuros")}
        for plan in a.planes_conjuros():
            escuelas = self._escuelas_de(plan.clase_id)
            afinidad = {c["id"]: escuelas.get(c["escuela"], 0) + extra.get(c["id"], 0)
                        for c in self.catalogo.listar("conjuros")}
            recomendados = self._recomendados("conjuros")
            rng = self._rng(f"conjuros/{plan.clase_id}")
            # Maestría sobre Conjuros y Conjuros Característicos ya están elegidos y tienen que ir al libro.
            fijos = self._exigidos_en_libro(plan.clase_id) if plan.modo == "libro" else set()
            previos = list(self.personaje.conjuros.get(plan.clase_id, [])) if conservar else []
            previos_trucos = [i for i in previos if (self.catalogo.obtener("conjuros", i) or {}).get("nivel") == 0]
            previos_resto = [i for i in previos if i not in previos_trucos]

            # La escuela elegida a propósito en esta subida va por delante incluso de lo recomendado para la clase.
            escogidas = set(self._respuesta_concreta(f"{PREFIJO_CONCRETA}escuela:{plan.clase_id}"))

            def orden(nivel: int, plan=plan, recomendados=recomendados, rng=rng, fijos=fijos, previos=previos,
                      afinidad=afinidad, escogidas=escogidas) -> list[str]:
                ids = [i for i, _ in plan.disponibles.get(nivel, []) if (i not in otras or i in fijos) and i not in previos]
                rng.shuffle(ids)
                # Tras preguntas de subida, entre los recomendados (y luego entre el resto) van antes los de las
                # escuelas y conjuros que encajan con lo vivido.
                return sorted(ids, key=lambda i: (i not in fijos, escuela[i] not in escogidas, i not in recomendados,
                                                  -afinidad.get(i, 0),
                                                  recomendados.index(i) if i in recomendados else len(recomendados)))

            trucos = previos_trucos + orden(0)[: max(0, (plan.limite_trucos or 0) - len(previos_trucos))]
            por_nivel = {nivel: orden(nivel) for nivel in plan.disponibles if nivel > 0}
            if plan.modo != "libro":
                faltan = max(0, (plan.limite_conjuros or 0) - len(previos_resto))
                nuevos = self._lo_mas_alto(por_nivel, faltan) if conservar else self._repartir(por_nivel, faltan)
                a.elegir_conjuros(plan.clase_id, trucos + previos_resto + nuevos)
                continue
            libro = previos_resto + self._libro(plan.clase_id, por_nivel, ya=len(previos_resto))
            a.elegir_conjuros(plan.clase_id, trucos + libro)
            por_nivel = {nivel: [*ids, *(i for i in previos_resto if (self.catalogo.obtener("conjuros", i) or {})
                                         .get("nivel") == nivel)] for nivel, ids in por_nivel.items()}
            # Los que ya están siempre preparados (Característicos) no gastan preparación.
            del_libro = {nivel: [i for i in ids if i in libro and i not in otras] for nivel, ids in por_nivel.items()}
            a.elegir_preparados(plan.clase_id, self._repartir(del_libro, plan.limite_conjuros or 0))

    def _exigidos_en_libro(self, clase_id: str) -> set[str]:
        """Conjuros elegidos en rasgos que exigen tenerlos en el libro de esa clase."""
        resolucion = self.asistente.sistema.resolver(self.personaje, self.catalogo)
        return {i for eleccion in resolucion.elecciones
                if any(isinstance(e, dict) and e.get("en_libro") == clase_id for e in eleccion.aplicar)
                for i in eleccion.seleccion}

    def _ajustar_al_libro(self) -> None:
        """Maestría sobre Conjuros y Conjuros Característicos: deben ser conjuros del libro, que se elige después."""
        resolucion = self.asistente.sistema.resolver(self.personaje, self.catalogo)
        for eleccion in resolucion.elecciones:
            clase = next((e.get("en_libro") for e in eleccion.aplicar if isinstance(e, dict) and e.get("en_libro")), None)
            if not clase:
                continue
            libro = set(self.personaje.conjuros.get(clase, []))
            quedan = [i for i in eleccion.seleccion if i in libro]
            if len(quedan) == len(eleccion.seleccion) == eleccion.elegir:
                continue
            candidatos = [o.id for o in eleccion.opciones if o.id in libro and o.id not in quedan]
            self._rng(eleccion.clave).shuffle(candidatos)
            self.asistente.elegir(eleccion.clave, quedan + candidatos[: eleccion.elegir - len(quedan)])

    def _libro(self, clase_id: str, por_nivel: dict[int, list[str]], ya: int = 0) -> list[str]:
        """Libro del mago: cada conjuro ganado al subir es del nivel más alto que permitía ese nivel de clase.

        «ya»: conjuros que el libro ya tiene (al subir de nivel); ocupan los primeros huecos y solo se llenan los
        de los niveles nuevos.
        """
        config = motor.configuracion_lanzamiento(self.personaje, self.catalogo, clase_id)
        nivel_clase = next(e.nivel for e in self.personaje.clases if e.clase == clase_id)
        huecos = [motor.nivel_maximo_conjuro(config, 1)] * config["libro"]["inicial"]
        for nivel in range(2, nivel_clase + 1):
            huecos += [motor.nivel_maximo_conjuro(config, nivel)] * config["libro"]["por_nivel"]
        libro: list[str] = []
        for tope in sorted(huecos[ya:], reverse=True):
            for nivel in range(tope, 0, -1):
                siguiente = next((i for i in por_nivel.get(nivel, []) if i not in libro), None)
                if siguiente:
                    libro.append(siguiente)
                    break
        return libro

    # ── detalles ───────────────────────────────────────────────────────────

    def _detalles(self) -> None:
        a = self.asistente
        alineamiento = self.alineamiento()
        a.establecer_detalle("alineamiento", alineamiento)
        trasfondo = self.catalogo.obtener("trasfondos", self.personaje.trasfondo or "") or {}
        personalidad = trasfondo.get("personalidad", {})
        rng = self._rng("personalidad")
        if personalidad.get("rasgos"):
            a.establecer_detalle("rasgos_personalidad", " ".join(rng.sample(personalidad["rasgos"],
                                                                            min(2, len(personalidad["rasgos"])))))
        ideales = personalidad.get("ideales", [])
        if ideales:
            palabras = {p.lower().replace("ó", "o") for p in alineamiento.split()}
            afines = [i for i in ideales if i.get("alineamiento") in palabras] or \
                     [i for i in ideales if i.get("alineamiento") in ("cualquiera", "neutral")] or ideales
            a.establecer_detalle("ideales", rng.choice(afines)["texto"])
        for campo in ("vinculos", "defectos"):
            if personalidad.get(campo):
                a.establecer_detalle(campo, rng.choice(personalidad[campo]))
