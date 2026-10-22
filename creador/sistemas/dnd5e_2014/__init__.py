"""Sistema de reglas de D&D 5ª edición (2014)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...nucleo.sistema import ErrorReferencia, Opcion, SistemaReglas
from ...nucleo.texto import clave_alfabetica
from . import motor, validacion
from .constantes import CARACTERISTICAS, HABILIDADES

if TYPE_CHECKING:
    from ...nucleo.efectos import Resolucion
    from ...nucleo.paquetes import Catalogo
    from ...nucleo.personaje import Personaje
    from .ficha import Ficha

# Fuentes de opciones que son subconjuntos de «objetos».
_FUENTES_OBJETO = {"herramientas": "herramienta", "armas": "arma"}


class Sistema5e2014(SistemaReglas):
    id = "dnd5e-2014"
    nombre = "D&D 5ª edición (2014)"
    categorias = validacion.CATEGORIAS

    def validar_entrada(self, categoria: str, entrada: dict) -> list[str]:
        return validacion.validar_entrada(categoria, entrada)

    def validar_catalogo(self, catalogo: Catalogo) -> list[str]:
        return validacion.validar_catalogo(catalogo)

    def opciones_desde(self, fuente: str, filtro: dict | None, catalogo: Catalogo) -> list[Opcion]:
        if fuente == "caracteristicas":
            return [Opcion(c, n) for c, n in CARACTERISTICAS.items()]
        if fuente == "habilidades":
            permitidas = (filtro or {}).get("caracteristica")
            return [Opcion(h, n) for h, (n, car) in HABILIDADES.items() if permitidas in (None, car)]
        if fuente in _FUENTES_OBJETO:
            filtro = {**(filtro or {}), "categoria": _FUENTES_OBJETO[fuente]}
            fuente = "objetos"
        if fuente not in self.categorias:
            return []
        opciones = [Opcion(e["id"], e["nombre"]) for e in catalogo.listar(fuente, filtro)]
        return sorted(opciones, key=lambda o: clave_alfabetica(o.nombre))

    def expandir_efecto(self, efecto: dict, catalogo: Catalogo, personaje: Personaje) -> list[dict] | None:
        if efecto["tipo"] == "dote":
            dote = catalogo.obtener("dotes", efecto["id"])
            if dote is None:
                raise ErrorReferencia(f"la dote «{efecto['id']}» no existe en los paquetes activos")
            rasgo = {"tipo": "rasgo", "nombre": f"Dote: {dote['nombre']}", "descripcion": dote.get("descripcion", "")}
            return [rasgo, *dote.get("efectos", [])]
        if efecto["tipo"] == "mejora_caracteristica":
            return [self._eleccion_mejora(personaje)]
        return None

    @staticmethod
    def _eleccion_mejora(personaje: Personaje) -> dict:
        opciones = [{
            "id": "caracteristicas",
            "nombre": "Mejorar características (+2 a una o +1 a dos)",
            "efectos": [{
                "tipo": "eleccion",
                "id": "puntos",
                "nombre": "Características a mejorar",
                "elegir": 2,
                "repetible": True,
                "opciones": {"desde": "caracteristicas"},
                "aplicar": [{"tipo": "caracteristica", "car": "$opcion", "valor": 1}],
            }],
        }]
        if personaje.reglas_opcionales.get("dotes", True):
            opciones.append({
                "id": "dote",
                "nombre": "Dote",
                "efectos": [{
                    "tipo": "eleccion",
                    "id": "dote",
                    "nombre": "Dote",
                    "opciones": {"desde": "dotes"},
                    "aplicar": [{"tipo": "dote", "id": "$opcion"}],
                }],
            })
        return {"tipo": "eleccion", "id": "mejora", "nombre": "Mejora de característica", "opciones": opciones}

    def resolver(self, personaje: Personaje, catalogo: Catalogo) -> Resolucion:
        return motor.resolver(self, personaje, catalogo)

    def calcular(self, personaje: Personaje, catalogo: Catalogo) -> Ficha:
        return motor.calcular(self, personaje, catalogo)
