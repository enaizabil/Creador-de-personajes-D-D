"""Modo sencillo de 5e (2014): preguntas de situaciones cotidianas que deciden el personaje.

Cada respuesta suma puntos a los rasgos del perfil (combate, sigilo, fe…), puede dar pesos directos
(«clases:guerrero»: +2) y empuja el alineamiento. Razas, clases y trasfondos se recomiendan por
afinidad entre su perfil y el del jugador. El resto (características, habilidades, equipo, conjuros y
elecciones) se completa aquí para que salga un personaje jugable, que luego se puede retocar con el
asistente del modo normal.

Solo cuentan las preguntas, perfiles y recomendaciones de los paquetes cargados: un homebrew entra en
el cuestionario con declarar su «perfil», y un paquete puede añadir preguntas propias.
"""
from __future__ import annotations

import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...nucleo.efectos import EleccionPendiente
from . import motor
from .asistente import Asistente5e, BloqueEquipo, LineaEquipo, OpcionDetallada
from .constantes import ARRAY_ESTANDAR, CARACTERISTICAS, GRUPO_ARMADURA, GRUPO_ARMA, HABILIDADES

if TYPE_CHECKING:
    from ...nucleo.paquetes import Catalogo
    from ...nucleo.personaje import Personaje
    from ...nucleo.sistema import SistemaReglas

PUNTOS_POR_PESO = 5  # cada punto de «pesos» suma esto a la afinidad (que va de 0 a 100)
MINIMO_RESPUESTAS = 6  # por debajo, la recomendación es poco fiable
UMBRAL_ALINEAMIENTO = 2
BONO_CONSTITUCION = 4  # todo aventurero agradece la Constitución
NIVEL_MINIMO_MULTICLASE = 4  # antes, repartir deja a la clase principal sin lo básico (p. ej., su subclase)
MAXIMO_NIVELES_SECUNDARIA = 5
CANDIDATAS_SECUNDARIA = 4  # la secundaria sale de las clases más afines tras la principal

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


@dataclass(frozen=True)
class Pregunta:
    id: str
    titulo: str
    texto: str
    respuestas: tuple[Respuesta, ...]


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


def _media_dano(dano: str) -> float:
    coincidencia = re.fullmatch(r"(\d+)d(\d+)", dano or "")
    return int(coincidencia[1]) * (int(coincidencia[2]) + 1) / 2 if coincidencia else 1.0


class Cuestionario5e:
    def __init__(self, sistema: SistemaReglas, catalogo: Catalogo, personaje: Personaje):
        self.catalogo = catalogo
        self.personaje = personaje
        self.asistente = Asistente5e(sistema, catalogo, personaje)

    # ── preguntas y respuestas ─────────────────────────────────────────────

    @property
    def respuestas(self) -> dict[str, str]:
        """pregunta -> respuesta; se guardan en el personaje para poder repetir el resultado."""
        return self.personaje.extra.setdefault("cuestionario", {}).setdefault("respuestas", {})

    def _existe(self, referencia: str) -> bool:
        categoria, id_ = referencia.split(":", 1)
        return self.catalogo.obtener(categoria, id_) is not None

    def preguntas(self) -> list[Pregunta]:
        """Las preguntas de los paquetes cargados cuyos requisitos («requiere») también están cargados."""
        return [Pregunta(p["id"], p["nombre"], p["texto"], tuple(Respuesta(r["id"], r["texto"]) for r in p["respuestas"]))
                for p in self.catalogo.listar("preguntas") if all(self._existe(r) for r in p.get("requiere", []))]

    def responder(self, pregunta: str, respuesta: str | None) -> None:
        if respuesta is None:
            self.respuestas.pop(pregunta, None)
            return
        datos = self.catalogo.obtener("preguntas", pregunta)
        if datos is None or not any(r["id"] == respuesta for r in datos["respuestas"]):
            raise ValueError(f"No existe la respuesta «{respuesta}» a la pregunta «{pregunta}»")
        self.respuestas[pregunta] = respuesta

    def _elegidas(self) -> list[dict]:
        elegidas = []
        for pregunta, respuesta in self.respuestas.items():
            datos = self.catalogo.obtener("preguntas", pregunta) or {}
            elegidas += [r for r in datos.get("respuestas", []) if r["id"] == respuesta]
        return elegidas

    def perfil(self) -> dict[str, int]:
        total: dict[str, int] = defaultdict(int)
        for respuesta in self._elegidas():
            for rasgo, valor in respuesta.get("perfil", {}).items():
                total[rasgo] += valor
        return dict(total)

    def pesos(self) -> dict[str, int]:
        total: dict[str, int] = defaultdict(int)
        for respuesta in self._elegidas():
            for referencia, valor in respuesta.get("pesos", {}).items():
                total[referencia] += valor
        return dict(total)

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
        if (not self.acepta_multiclase or nivel < NIVEL_MINIMO_MULTICLASE
                or not self.personaje.reglas_opcionales.get("multiclase", True)):
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
        a.personaje.clases = []
        a.establecer_nivel(sum(n for _, n in reparto))
        a.elegir_clase(reparto[0][0])
        for otra, niveles in reparto[1:]:
            a.anadir_clase(otra, niveles)
        for entrada in list(a.personaje.clases):
            if a.subclases(entrada.clase):
                a.elegir_subclase(self._mejor_subclase(entrada.clase), entrada.clase)
        a.elegir_trasfondo(trasfondo)
        self._caracteristicas()
        self._completar_elecciones()
        self._equipo()
        self._conjuros()
        self._ajustar_al_libro()
        self._detalles()
        self.personaje.extra.setdefault("cuestionario", {})["generado"] = True

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
            # Primero las más restringidas (Bendiciones del Conocimiento: 2 de 4), para que las amplias
            # (Versatilidad con Habilidades del semielfo: 2 de 18) no les quiten las opciones.
            pendientes.sort(key=lambda e: len(e.opciones) - e.faltan)
            for eleccion in pendientes:
                elegidas = self._elegir(eleccion, self._rng(f"{eleccion.clave}/{vuelta}"))
                if not elegidas:
                    continue
                self.asistente.elegir(eleccion.clave, eleccion.seleccion + elegidas)

    def _elegir(self, eleccion: EleccionPendiente, rng: random.Random) -> list[str]:
        n = eleccion.faltan
        ids = [o.id for o in eleccion.opciones]
        if "caracteristicas" in ids:  # mejora de característica o dote: lo sencillo es la característica
            return ["caracteristicas"]
        if set(ids) <= set(CARACTERISTICAS):
            return self._mejoras(eleccion, n)
        conocidas = self.asistente.conocidas(eleccion)
        libres = [i for i in ids if i not in conocidas and (eleccion.repetible or i not in eleccion.seleccion)]
        sin_competencia = self.asistente.sin_competencia(eleccion)  # pericia: solo donde ya hay competencia
        libres = [i for i in libres if i not in sin_competencia]
        if libres and set(libres) <= set(HABILIDADES):
            return self._habilidades(libres, n, rng)
        conjuros = [self.catalogo.obtener("conjuros", i) for i in libres]
        if libres and all(conjuros) and len({c["nivel"] for c in conjuros}) > 1:
            return self._conjuros_de_cualquier_nivel(eleccion, conjuros, n, rng)
        preferidas =self._recomendados("opciones") + self._recomendados("dotes") + self._recomendados("conjuros")
        elegidas = [i for i in dict.fromkeys(preferidas) if i in libres][:n]
        resto = [i for i in libres if i not in elegidas]
        # Sin recomendación: primero lo que no tiene prerrequisitos (no se comprueban todos) y, entre eso, al azar.
        rng.shuffle(resto)
        resto.sort(key=lambda i: self._tiene_prerrequisito(i))
        return elegidas + resto[: n - len(elegidas)]

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

    def _mejoras(self, eleccion: EleccionPendiente, n: int) -> list[str]:
        """Mejora de característica: lo más importante para la clase, sin pasar de 20."""
        puntuaciones = {c: v.puntuacion for c, v in self.asistente.ficha().caracteristicas.items()}
        validas = {o.id for o in eleccion.opciones} - (set() if eleccion.repetible else set(eleccion.seleccion))
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

    def _conjuros(self) -> None:
        a = self.asistente
        otras = a.conjuros_de_otras_fuentes()
        for plan in a.planes_conjuros():
            recomendados = self._recomendados("conjuros")
            rng = self._rng(f"conjuros/{plan.clase_id}")
            # Maestría sobre Conjuros y Conjuros Característicos ya están elegidos y tienen que ir al libro.
            fijos = self._exigidos_en_libro(plan.clase_id) if plan.modo == "libro" else set()

            def orden(nivel: int, plan=plan, recomendados=recomendados, rng=rng, fijos=fijos) -> list[str]:
                ids = [i for i, _ in plan.disponibles.get(nivel, []) if i not in otras or i in fijos]
                rng.shuffle(ids)
                return sorted(ids, key=lambda i: (i not in fijos,
                                                  recomendados.index(i) if i in recomendados else len(recomendados)))

            trucos = orden(0)[: plan.limite_trucos or 0]
            por_nivel = {nivel: orden(nivel) for nivel in plan.disponibles if nivel > 0}
            if plan.modo != "libro":
                a.elegir_conjuros(plan.clase_id, trucos + self._repartir(por_nivel, plan.limite_conjuros or 0))
                continue
            libro = self._libro(plan.clase_id, por_nivel)
            a.elegir_conjuros(plan.clase_id, trucos + libro)
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

    def _libro(self, clase_id: str, por_nivel: dict[int, list[str]]) -> list[str]:
        """Libro del mago: cada conjuro ganado al subir es del nivel más alto que permitía ese nivel de clase."""
        config = motor.configuracion_lanzamiento(self.personaje, self.catalogo, clase_id)
        nivel_clase = next(e.nivel for e in self.personaje.clases if e.clase == clase_id)
        huecos = [motor.nivel_maximo_conjuro(config, 1)] * config["libro"]["inicial"]
        for nivel in range(2, nivel_clase + 1):
            huecos += [motor.nivel_maximo_conjuro(config, nivel)] * config["libro"]["por_nivel"]
        libro: list[str] = []
        for tope in sorted(huecos, reverse=True):
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
