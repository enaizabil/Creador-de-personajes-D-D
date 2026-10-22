"""Ficha calculada de 5e (2014): lo que consumen la interfaz y los exportadores."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ValorCaracteristica:
    puntuacion: int
    modificador: int
    base: int


@dataclass
class Tirada:
    nombre: str
    caracteristica: str
    valor: int
    competente: bool = False
    pericia: bool = False
    notas: str = ""


@dataclass
class Ataque:
    nombre: str
    bonificador: int
    dano: str
    tipo_dano: str
    notas: str = ""


@dataclass
class Rasgo:
    nombre: str
    descripcion: str
    origen: str
    resumen: str = ""  # línea corta para la ficha, con los valores ya calculados
    usos: int | None = None
    recarga: str = ""  # corto | largo


@dataclass
class Lanzador:
    clase_id: str
    clase: str
    caracteristica: str
    cd: int
    ataque: int
    nivel_maximo: int
    # nivel de conjuro (0 = truco) -> nombres
    conjuros: dict[int, list[str]] = field(default_factory=dict)
    # dominio, juramento, círculo…: no cuentan para el límite de preparados
    siempre_preparados: dict[int, list[str]] = field(default_factory=dict)


@dataclass
class Ficha:
    nombre: str
    jugador: str
    raza: str
    clase_y_nivel: str
    trasfondo: str
    nivel: int
    experiencia: int
    caracteristicas: dict[str, ValorCaracteristica]
    bonificador_competencia: int
    salvaciones: dict[str, Tirada]
    habilidades: dict[str, Tirada]
    percepcion_pasiva: int
    pasivas: dict[str, int]  # percepcion, perspicacia, investigacion
    ca: int
    iniciativa: int
    velocidades: dict[str, int]  # en pies
    pg_maximos: int
    dados_golpe: dict[str, int]
    tamano: str
    competencias: dict[str, list[str]]
    ataques: list[Ataque]
    rasgos: list[Rasgo]
    sentidos: dict[str, int]
    resistencias: list[str]
    inmunidades: list[str]
    espacios_conjuro: dict[int, int]
    magia_pacto: dict[str, int] | None
    lanzadores: list[Lanzador]
    conjuros_innatos: list[str]
    equipo: list[str]
    monedas: dict[str, int]
    detalles: dict[str, str]
    avisos: list[str]

    def a_dict(self) -> dict:
        return asdict(self)
