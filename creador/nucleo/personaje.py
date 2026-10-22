"""Modelo del personaje: guarda las decisiones del jugador, no los valores derivados.

Los valores de la ficha (CA, bonificadores, PG…) se recalculan siempre desde
aquí, así que subir de nivel o cambiar de raza no deja datos incoherentes.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

VERSION_FORMATO = 1


@dataclass
class EntradaClase:
    clase: str
    nivel: int = 1
    subclase: str | None = None
    # Una tirada por nivel, sin contar el primer nivel de la clase inicial.
    tiradas_pg: list[int] = field(default_factory=list)


@dataclass
class ObjetoInventario:
    id: str | None = None  # referencia al catálogo; None para objetos libres
    nombre: str = ""
    cantidad: int = 1
    equipado: bool = False


@dataclass
class Personaje:
    sistema: str
    paquetes: list[str] = field(default_factory=list)
    nombre: str = ""
    jugador: str = ""
    raza: str | None = None
    subraza: str | None = None
    trasfondo: str | None = None
    clases: list[EntradaClase] = field(default_factory=list)
    metodo_caracteristicas: str = "estandar"  # estandar | compra | tirada | manual
    caracteristicas_base: dict[str, int] = field(default_factory=dict)
    metodo_pg: str = "media"  # media | tiradas
    elecciones: dict[str, list[str]] = field(default_factory=dict)
    equipo: list[ObjetoInventario] = field(default_factory=list)
    monedas: dict[str, int] = field(default_factory=dict)
    # Conjuros conocidos o preparados, por id de clase.
    conjuros: dict[str, list[str]] = field(default_factory=dict)
    reglas_opcionales: dict[str, bool] = field(default_factory=dict)
    experiencia: int = 0
    detalles: dict[str, str] = field(default_factory=dict)
    # Datos propios de un sistema que no encajan en los campos comunes.
    extra: dict = field(default_factory=dict)

    @property
    def nivel_total(self) -> int:
        return sum(c.nivel for c in self.clases)

    def a_dict(self) -> dict:
        return {"version_formato": VERSION_FORMATO, **asdict(self)}

    @classmethod
    def desde_dict(cls, datos: dict) -> Personaje:
        datos = dict(datos)
        version = datos.pop("version_formato", VERSION_FORMATO)
        if version > VERSION_FORMATO:
            raise ValueError(
                f"El personaje usa el formato {version}, más nuevo que el que entiende este programa ({VERSION_FORMATO})"
            )
        desconocidos = set(datos) - {f.name for f in fields(cls)}
        if desconocidos:
            raise ValueError(f"Campos desconocidos en el personaje: {', '.join(sorted(desconocidos))}")
        clases = [EntradaClase(**c) for c in datos.pop("clases", [])]
        equipo = [ObjetoInventario(**o) for o in datos.pop("equipo", [])]
        return cls(clases=clases, equipo=equipo, **datos)

    def guardar(self, ruta: str | Path) -> None:
        Path(ruta).write_text(json.dumps(self.a_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls, ruta: str | Path) -> Personaje:
        return cls.desde_dict(json.loads(Path(ruta).read_text(encoding="utf-8")))

    def limpiar_elecciones(self, claves_vigentes: set[str]) -> list[str]:
        """Borra selecciones de elecciones que ya no existen (p. ej. tras cambiar de raza)."""
        huerfanas = [clave for clave in self.elecciones if clave not in claves_vigentes]
        for clave in huerfanas:
            del self.elecciones[clave]
        return huerfanas
