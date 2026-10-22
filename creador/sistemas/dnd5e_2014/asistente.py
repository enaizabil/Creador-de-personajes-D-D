"""Asistente de creación del modo normal para 5e (2014), sin interfaz.

La interfaz gráfica solo pinta lo que ofrece esta clase y le pasa lo que elige el
jugador; así la lógica se prueba sin ventanas y otra edición puede tener su propio
asistente con otros pasos.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ...nucleo.efectos import EleccionPendiente
from ...nucleo.personaje import EntradaClase, ObjetoInventario
from ...nucleo.texto import clave_alfabetica
from . import motor
from .caracteristicas import asignar_por_prioridad, coste_compra, modificador, tirar_4d6, validar_base
from .constantes import ARRAY_ESTANDAR, CARACTERISTICAS, COSTE_COMPRA, NIVEL_MAXIMO, PUNTOS_COMPRA
from .ficha import Ficha, PlanConjuros

if TYPE_CHECKING:
    from ...nucleo.paquetes import Catalogo
    from ...nucleo.personaje import Personaje
    from ...nucleo.sistema import SistemaReglas

ALINEAMIENTOS = (
    "Legal bueno", "Neutral bueno", "Caótico bueno",
    "Legal neutral", "Neutral", "Caótico neutral",
    "Legal malvado", "Neutral malvado", "Caótico malvado",
)
METODOS_CARACTERISTICAS = {
    "estandar": "Array estándar (15, 14, 13, 12, 10, 8)",
    "compra": f"Compra por puntos ({PUNTOS_COMPRA} puntos)",
    "tirada": "Tirar 4d6 (descartando el menor)",
    "manual": "Introducir a mano",
}
CAMPOS_DETALLES = ("nombre", "jugador", "alineamiento", "rasgos_personalidad", "ideales", "vinculos", "defectos",
                   "edad", "altura", "peso", "ojos", "piel", "pelo", "apariencia", "historia")
# Guía del DM 2014, tabla «Equipo inicial» (p. 38), campaña estándar: oro extra por nivel inicial.
ORO_EXTRA_POR_NIVEL = ((5, 10, "500 + 1d10x25"), (11, 16, "5000 + 1d10x250"), (17, 20, "20000 + 1d10x250"))
# Nombres de las líneas de equipo «a elegir» (si el dato no trae su propio «nombre»).
NOMBRES_FOCO = {"arcano": "Canalizador arcano", "druidico": "Canalizador druídico", "sagrado": "Símbolo sagrado"}
NOMBRES_HERRAMIENTA = {"instrumento": "Instrumento musical", "artesano": "Herramientas de artesano"}
# Elecciones que se muestran en cada paso, según el origen de su clave.
PREFIJOS_PASO = {"raza": ("raza:", "subraza:"), "clase": ("clase:", "subclase:"), "trasfondo": ("trasfondo:",)}


@dataclass(frozen=True)
class Paso:
    id: str
    titulo: str
    ayuda: str


PASOS = (
    Paso("inicio", "Edición y reglas", "Nivel inicial y reglas opcionales de la mesa."),
    Paso("raza", "Raza", "Tu pueblo de origen y lo que te aporta."),
    Paso("clase", "Clase", "Tu profesión de aventurero."),
    Paso("caracteristicas", "Características", "Fuerza, Destreza, Constitución, Inteligencia, Sabiduría y Carisma."),
    Paso("trasfondo", "Trasfondo", "Qué hacías antes de ser aventurero."),
    Paso("equipo", "Equipo", "Lo que llevas al empezar."),
    Paso("conjuros", "Conjuros", "Trucos y conjuros que conoces o preparas."),
    Paso("detalles", "Detalles", "Nombre, alineamiento y personalidad."),
    Paso("resumen", "Resumen", "La ficha calculada y lo que falta."),
)


@dataclass(frozen=True)
class OpcionDetallada:
    id: str
    nombre: str
    descripcion: str = ""
    perfil: dict = field(default_factory=dict)
    paquete: str = ""
    permiso_dm: bool = False


@dataclass
class LineaEquipo:
    id: str | None  # objeto fijo; None si hay que elegirlo
    nombre: str
    cantidad: int
    opciones: list[tuple[str, str]] = field(default_factory=list)  # (id, nombre) si es «desde»


@dataclass
class BloqueEquipo:
    origen: str  # clase | trasfondo
    indice: int
    alternativas: list[list[LineaEquipo]]
    elegida: int | None


def tirar_dados(expresion: str, rng: random.Random) -> int:
    """«5d4x10», «2d4», «500 + 1d10x25»: suma de términos NdM con multiplicador opcional."""
    total = 0
    for termino in expresion.replace(" ", "").split("+"):
        m = re.fullmatch(r"(?:(\d+)d(\d+))?(?:x(\d+))?|(\d+)", termino)
        if not m or not termino:
            raise ValueError(f"Expresión de dados no válida: «{expresion}»")
        if m.group(4):
            total += int(m.group(4))
            continue
        tirada = sum(rng.randint(1, int(m.group(2))) for _ in range(int(m.group(1))))
        total += tirada * int(m.group(3) or 1)
    return total


def describir_eleccion(linea: dict) -> str:
    """«Arma marcial cuerpo a cuerpo a elegir», «Canalizador arcano a elegir»…"""
    filtro = linea.get("filtro") or {}
    if linea["desde"] == "armas":
        arma = filtro.get("arma", {})
        tipo = {"cuerpo_a_cuerpo": "cuerpo a cuerpo", "distancia": "a distancia"}.get(arma.get("tipo", ""), "")
        texto = " ".join(p for p in ("Arma", arma.get("categoria", ""), tipo) if p)
    elif filtro.get("categoria") == "foco":
        texto = NOMBRES_FOCO.get(filtro.get("subcategoria"), "Canalizador")
    elif filtro.get("subcategoria") in NOMBRES_HERRAMIENTA:
        texto = NOMBRES_HERRAMIENTA[filtro["subcategoria"]]
    else:
        texto = {"armas": "Arma", "herramientas": "Herramienta"}.get(linea["desde"], "Objeto")
    return f"{texto} a elegir"


class Asistente5e:
    def __init__(self, sistema: SistemaReglas, catalogo: Catalogo, personaje: Personaje, rng: random.Random | None = None):
        self.sistema = sistema
        self.catalogo = catalogo
        self.personaje = personaje
        self.rng = rng or random.Random()

    # ── utilidades ─────────────────────────────────────────────────────────

    def _visible(self, entrada: dict) -> bool:
        if entrada.get("permiso_dm") and not self.personaje.reglas_opcionales.get("opciones_dm", False):
            return False
        return all(self.personaje.reglas_opcionales.get(r, True) for r in entrada.get("requiere_reglas", []))

    def _opciones(self, categoria: str, filtro: dict | None = None) -> list[OpcionDetallada]:
        entradas = [e for e in self.catalogo.listar(categoria, filtro) if self._visible(e)]
        return sorted((OpcionDetallada(e["id"], e["nombre"], e.get("descripcion", ""), e.get("perfil", {}),
                                       self.catalogo.origen(categoria, e["id"]) or "", bool(e.get("permiso_dm")))
                       for e in entradas), key=lambda o: clave_alfabetica(o.nombre))

    def _limpiar(self) -> None:
        self.personaje.limpiar_elecciones(self.sistema.resolver(self.personaje, self.catalogo).claves_visitadas)

    @property
    def extra(self) -> dict:
        return self.personaje.extra

    # ── inicio: nivel y reglas ─────────────────────────────────────────────

    @property
    def nivel(self) -> int:
        if self.personaje.clases:
            return self.personaje.clases[0].nivel
        return self.extra.get("nivel_inicial", 1)

    def establecer_nivel(self, nivel: int) -> None:
        if not 1 <= nivel <= NIVEL_MAXIMO:
            raise ValueError(f"El nivel va de 1 a {NIVEL_MAXIMO}")
        self.extra["nivel_inicial"] = nivel
        if self.personaje.clases:
            entrada = self.personaje.clases[0]
            entrada.nivel = nivel
            clase = self.catalogo.obtener("clases", entrada.clase) or {}
            if nivel < clase.get("nivel_subclase", 1):
                entrada.subclase = None
            entrada.tiradas_pg = entrada.tiradas_pg[: max(0, nivel - 1)]
        self._limpiar()

    def establecer_regla(self, regla: str, activa: bool) -> None:
        """dotes, multiclase, opciones_dm (opciones de la Guía del DM que requieren permiso)."""
        self.personaje.reglas_opcionales[regla] = activa
        self._limpiar()

    # ── raza ───────────────────────────────────────────────────────────────

    def razas(self) -> list[OpcionDetallada]:
        return self._opciones("razas")

    def subrazas(self) -> list[OpcionDetallada]:
        return self._opciones("subrazas", {"raza": self.personaje.raza}) if self.personaje.raza else []

    def elegir_raza(self, id_: str) -> None:
        self.personaje.raza, self.personaje.subraza = id_, None
        self._limpiar()

    def elegir_subraza(self, id_: str | None) -> None:
        self.personaje.subraza = id_
        self._limpiar()

    # ── clase ──────────────────────────────────────────────────────────────

    def clases(self) -> list[OpcionDetallada]:
        return self._opciones("clases")

    def subclases(self) -> list[OpcionDetallada]:
        if not self.personaje.clases:
            return []
        clase = self.catalogo.obtener("clases", self.personaje.clases[0].clase) or {}
        if self.nivel < clase.get("nivel_subclase", 1):
            return []
        return self._opciones("subclases", {"clase": clase.get("id")})

    def elegir_clase(self, id_: str) -> None:
        self.personaje.clases = [EntradaClase(id_, self.nivel)]
        self.personaje.conjuros = {}
        self._limpiar()

    def elegir_subclase(self, id_: str | None) -> None:
        self.personaje.clases[0].subclase = id_
        self._limpiar()

    # ── características ────────────────────────────────────────────────────

    def establecer_metodo(self, metodo: str) -> None:
        if metodo not in METODOS_CARACTERISTICAS:
            raise ValueError(f"Método desconocido «{metodo}»")
        self.personaje.metodo_caracteristicas = metodo
        self.extra.pop("tiradas_caracteristicas", None)
        base = {"compra": 8, "manual": 10}.get(metodo)
        self.personaje.caracteristicas_base = {c: base for c in CARACTERISTICAS} if base else {}

    def tirar_caracteristicas(self) -> list[int]:
        tiradas = tirar_4d6(self.rng)
        self.extra["tiradas_caracteristicas"] = tiradas
        self.personaje.caracteristicas_base = {}
        return tiradas

    def valores_disponibles(self) -> list[int]:
        """Para array estándar y tiradas: los valores que quedan por asignar."""
        metodo = self.personaje.metodo_caracteristicas
        if metodo not in ("estandar", "tirada"):
            return []
        restantes = list(ARRAY_ESTANDAR) if metodo == "estandar" else list(self.extra.get("tiradas_caracteristicas", []))
        for valor in self.personaje.caracteristicas_base.values():
            if valor in restantes:
                restantes.remove(valor)
        return sorted(restantes, reverse=True)

    def asignar(self, car: str, valor: int | None) -> None:
        if car not in CARACTERISTICAS:
            raise ValueError(f"Característica desconocida «{car}»")
        if valor is None:
            self.personaje.caracteristicas_base.pop(car, None)
            return
        if self.personaje.metodo_caracteristicas == "compra" and valor not in COSTE_COMPRA:
            raise ValueError("Con compra por puntos las puntuaciones van de 8 a 15")
        self.personaje.caracteristicas_base[car] = valor

    def puntos_restantes(self) -> int | None:
        if self.personaje.metodo_caracteristicas != "compra":
            return None
        try:
            return PUNTOS_COMPRA - coste_compra(self.personaje.caracteristicas_base)
        except ValueError:
            return None

    def prioridad_de_clase(self) -> list[str]:
        """Orden recomendado de características para la clase elegida (deducido de sus datos)."""
        clase = self.catalogo.obtener("clases", self.personaje.clases[0].clase) if self.personaje.clases else None
        if not clase:
            return list(CARACTERISTICAS)
        prioridad = []
        lanzamiento = clase.get("lanzamiento") or {}
        if lanzamiento.get("caracteristica"):
            prioridad.append(lanzamiento["caracteristica"])
        requisitos = clase.get("requisitos_multiclase", {})
        prioridad += [*requisitos.get("caracteristicas", {}), *requisitos.get("alguna_caracteristica", {})]
        prioridad += ["con", *clase.get("salvaciones", [])]
        return list(dict.fromkeys([*prioridad, *CARACTERISTICAS]))

    def sugerir_caracteristicas(self) -> None:
        """Reparte el array (o las tiradas) según la prioridad de la clase."""
        metodo = self.personaje.metodo_caracteristicas
        valores = list(ARRAY_ESTANDAR) if metodo == "estandar" else self.extra.get("tiradas_caracteristicas")
        if metodo == "compra":
            valores = [15, 15, 15, 8, 8, 8]
        if not valores:
            raise ValueError("Primero hay que tirar los dados")
        self.personaje.caracteristicas_base = asignar_por_prioridad(list(valores), self.prioridad_de_clase())

    def bonos_raciales(self) -> dict[str, int]:
        ficha = self.ficha()
        return {c: ficha.caracteristicas[c].puntuacion - self.personaje.caracteristicas_base.get(c, 10)
                for c in CARACTERISTICAS}

    # ── trasfondo ──────────────────────────────────────────────────────────

    def trasfondos(self) -> list[OpcionDetallada]:
        return self._opciones("trasfondos")

    def elegir_trasfondo(self, id_: str) -> None:
        self.personaje.trasfondo = id_
        self._limpiar()

    def personalidad_sugerida(self) -> dict[str, list[str]]:
        trasfondo = self.catalogo.obtener("trasfondos", self.personaje.trasfondo) if self.personaje.trasfondo else None
        personalidad = (trasfondo or {}).get("personalidad", {})
        return {"rasgos_personalidad": personalidad.get("rasgos", []),
                "ideales": [i["texto"] for i in personalidad.get("ideales", [])],
                "vinculos": personalidad.get("vinculos", []), "defectos": personalidad.get("defectos", [])}

    # ── elecciones pendientes por paso ─────────────────────────────────────

    def elecciones(self, paso: str) -> list[EleccionPendiente]:
        """Todas las elecciones de un paso (hechas o no), en orden de aparición."""
        prefijos = PREFIJOS_PASO.get(paso, ())
        return [e for e in self.sistema.resolver(self.personaje, self.catalogo).elecciones if e.clave.startswith(prefijos)]

    def elegir(self, clave: str, valores: list[str]) -> None:
        if valores:
            self.personaje.elecciones[clave] = list(valores)
        else:
            self.personaje.elecciones.pop(clave, None)
        self._limpiar()

    # ── equipo ─────────────────────────────────────────────────────────────

    def _seleccion_equipo(self) -> dict:
        return self.extra.setdefault("equipo_inicial", {"clase": {}, "trasfondo": {}, "desde": {}, "oro": False})

    def _bloques_de(self, origen: str) -> list:
        if origen == "clase" and self.personaje.clases:
            return (self.catalogo.obtener("clases", self.personaje.clases[0].clase) or {}).get("equipo_inicial", [])
        if origen == "trasfondo" and self.personaje.trasfondo:
            return (self.catalogo.obtener("trasfondos", self.personaje.trasfondo) or {}).get("equipo", [])
        return []

    def bloques_equipo(self) -> list[BloqueEquipo]:
        seleccion = self._seleccion_equipo()
        bloques = []
        for origen in ("clase", "trasfondo"):
            if origen == "clase" and seleccion["oro"]:
                continue
            for i, bloque in enumerate(self._bloques_de(origen)):
                alternativas = [[self._linea(linea) for linea in alternativa] for alternativa in bloque]
                elegida = 0 if len(bloque) == 1 else seleccion[origen].get(str(i))
                bloques.append(BloqueEquipo(origen, i, alternativas, elegida))
        return bloques

    def _linea(self, linea: dict) -> LineaEquipo:
        cantidad = linea.get("cantidad", 1)
        if "id" in linea:
            objeto = self.catalogo.obtener("objetos", linea["id"]) or {}
            return LineaEquipo(linea["id"], objeto.get("nombre", linea["id"]), cantidad)
        opciones = [(o.id, o.nombre) for o in self.sistema.opciones_desde(linea["desde"], linea.get("filtro"), self.catalogo)]
        return LineaEquipo(None, linea.get("nombre") or describir_eleccion(linea), cantidad, opciones)

    def elegir_alternativa(self, origen: str, indice: int, alternativa: int) -> None:
        self._seleccion_equipo()[origen][str(indice)] = alternativa

    def elegir_objeto(self, origen: str, indice: int, alternativa: int, linea: int, hueco: int, objeto: str) -> None:
        """Para una línea «a elegir»; «hueco» distingue las armas de «dos armas marciales»."""
        self._seleccion_equipo()["desde"][f"{origen}.{indice}.{alternativa}.{linea}.{hueco}"] = objeto

    def objeto_elegido(self, origen: str, indice: int, alternativa: int, linea: int, hueco: int) -> str | None:
        return self._seleccion_equipo()["desde"].get(f"{origen}.{indice}.{alternativa}.{linea}.{hueco}")

    def oro_inicial(self) -> str | None:
        clase = self.catalogo.obtener("clases", self.personaje.clases[0].clase) if self.personaje.clases else None
        return (clase or {}).get("oro_inicial")

    def usar_oro_en_vez_de_equipo(self, usar: bool) -> None:
        self._seleccion_equipo()["oro"] = usar

    def oro_extra_por_nivel(self) -> str | None:
        if not self.personaje.reglas_opcionales.get("equipo_por_nivel", False):
            return None
        return next((oro for desde, hasta, oro in ORO_EXTRA_POR_NIVEL if desde <= self.nivel <= hasta), None)

    def equipo_pendiente(self) -> list[str]:
        faltan = []
        for bloque in self.bloques_equipo():
            if bloque.elegida is None:
                faltan.append(f"Equipo de {bloque.origen}: elige una de las opciones del bloque {bloque.indice + 1}")
                continue
            for n, linea in enumerate(bloque.alternativas[bloque.elegida]):
                for hueco in range(linea.cantidad if linea.id is None else 0):
                    if not self.objeto_elegido(bloque.origen, bloque.indice, bloque.elegida, n, hueco):
                        faltan.append(f"Equipo de {bloque.origen}: elige el objeto del bloque {bloque.indice + 1}")
        return list(dict.fromkeys(faltan))

    def aplicar_equipo(self) -> None:
        """Rehace el inventario y el dinero a partir de las elecciones de equipo inicial."""
        inventario: dict[str, int] = {}

        def anadir(id_: str, cantidad: int) -> None:
            objeto = self.catalogo.obtener("objetos", id_) or {}
            if objeto.get("contenido"):  # los paquetes de equipo se abren
                for linea in objeto["contenido"]:
                    anadir(linea["id"], linea.get("cantidad", 1) * cantidad)
            else:
                inventario[id_] = inventario.get(id_, 0) + cantidad

        for bloque in self.bloques_equipo():
            if bloque.elegida is None:
                continue
            for n, linea in enumerate(bloque.alternativas[bloque.elegida]):
                if linea.id:
                    anadir(linea.id, linea.cantidad)
                    continue
                for hueco in range(linea.cantidad):
                    elegido = self.objeto_elegido(bloque.origen, bloque.indice, bloque.elegida, n, hueco)
                    if elegido:
                        anadir(elegido, 1)

        seleccion = self._seleccion_equipo()
        monedas: dict[str, int] = {}
        trasfondo = self.catalogo.obtener("trasfondos", self.personaje.trasfondo) if self.personaje.trasfondo else None
        for moneda, valor in (trasfondo or {}).get("monedas", {}).items():
            monedas[moneda] = monedas.get(moneda, 0) + valor
        if seleccion["oro"] and self.oro_inicial():
            seleccion.setdefault("oro_tirado", tirar_dados(self.oro_inicial(), self.rng))
            monedas["po"] = monedas.get("po", 0) + seleccion["oro_tirado"]
        extra = self.oro_extra_por_nivel()
        if extra:
            seleccion.setdefault("oro_extra_tirado", tirar_dados(extra, self.rng))
            monedas["po"] = monedas.get("po", 0) + seleccion["oro_extra_tirado"]

        armadura_equipada = escudo_equipado = False
        equipo = []
        for id_, cantidad in inventario.items():
            categoria = (self.catalogo.obtener("objetos", id_) or {}).get("categoria")
            equipar = (categoria == "armadura" and not armadura_equipada) or (categoria == "escudo" and not escudo_equipado)
            armadura_equipada |= equipar and categoria == "armadura"
            escudo_equipado |= equipar and categoria == "escudo"
            equipo.append(ObjetoInventario(id_, cantidad=cantidad, equipado=equipar))
        self.personaje.equipo = equipo
        self.personaje.monedas = monedas

    # ── conjuros ───────────────────────────────────────────────────────────

    def planes_conjuros(self) -> list[PlanConjuros]:
        mods = {c: v.modificador for c, v in self.ficha().caracteristicas.items()}
        return motor.planes_de_conjuros(self.personaje, self.catalogo, mods)

    def elegir_conjuros(self, clase_id: str, ids: list[str]) -> None:
        self.personaje.conjuros[clase_id] = list(dict.fromkeys(ids))

    # ── detalles ───────────────────────────────────────────────────────────

    def establecer_detalle(self, campo: str, valor: str) -> None:
        if campo not in CAMPOS_DETALLES:
            raise ValueError(f"Detalle desconocido «{campo}»")
        if campo in ("nombre", "jugador"):
            setattr(self.personaje, campo, valor)
        else:
            self.personaje.detalles[campo] = valor

    # ── estado de cada paso ────────────────────────────────────────────────

    def pasos(self) -> list[Paso]:
        hay_magia = bool(self.planes_conjuros()) if self.personaje.clases else False
        return [p for p in PASOS if p.id != "conjuros" or hay_magia]

    def faltan(self, paso: str) -> list[str]:
        """Lo que impide dar por terminado un paso (vacío = completo)."""
        personaje = self.personaje
        faltan = [f"{e.etiqueta}: {e.nombre} (faltan {e.faltan})" for e in self.elecciones(paso) if e.faltan > 0]
        if paso == "raza":
            if not personaje.raza:
                faltan.insert(0, "Elige una raza")
            elif self.subrazas() and not personaje.subraza:
                faltan.insert(0, "Elige una subraza")
        elif paso == "clase":
            if not personaje.clases:
                faltan.insert(0, "Elige una clase")
            elif self.subclases() and not personaje.clases[0].subclase:
                faltan.insert(0, "Elige una subclase")
        elif paso == "caracteristicas":
            faltan += validar_base(personaje.metodo_caracteristicas, personaje.caracteristicas_base)
        elif paso == "trasfondo" and not personaje.trasfondo:
            faltan.insert(0, "Elige un trasfondo")
        elif paso == "equipo":
            if not personaje.clases:
                faltan.append("Elige antes una clase")
            if not personaje.trasfondo:
                faltan.append("Elige antes un trasfondo")
            faltan += self.equipo_pendiente()
        elif paso == "conjuros":
            for plan in self.planes_conjuros():
                elegidos = [self.catalogo.obtener("conjuros", i) for i in personaje.conjuros.get(plan.clase_id, [])]
                trucos = sum(1 for c in elegidos if c and c["nivel"] == 0)
                conjuros = sum(1 for c in elegidos if c and c["nivel"] > 0)
                if plan.limite_trucos and trucos < plan.limite_trucos:
                    faltan.append(f"{plan.clase}: elige {plan.limite_trucos - trucos} truco(s) más")
                if plan.limite_conjuros and conjuros < plan.limite_conjuros:
                    faltan.append(f"{plan.clase}: elige {plan.limite_conjuros - conjuros} conjuro(s) más")
        elif paso == "detalles" and not personaje.nombre.strip():
            faltan.append("Ponle nombre al personaje")
        elif paso == "resumen":
            faltan += [f for p in PASOS[:-1] if p.id != "resumen" for f in self.faltan(p.id)]
        return faltan

    def ficha(self) -> Ficha:
        return self.sistema.calcular(self.personaje, self.catalogo)

    def modificadores(self) -> dict[str, int]:
        return {c: modificador(v.puntuacion) for c, v in self.ficha().caracteristicas.items()}
