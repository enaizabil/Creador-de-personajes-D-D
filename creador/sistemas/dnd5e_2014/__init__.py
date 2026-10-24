"""Sistema de reglas de D&D 5ª edición (2014)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...nucleo.sistema import ErrorReferencia, Opcion, SistemaReglas
from ...nucleo.texto import clave_alfabetica
from . import motor, validacion
from .constantes import CARACTERISTICAS, HABILIDADES

if TYPE_CHECKING:
    from ...nucleo.efectos import Resolucion
    from .asistente import Asistente5e
    from .cuestionario import Cuestionario5e
    from ...nucleo.paquetes import Catalogo
    from ...nucleo.personaje import Personaje
    from .ficha import Ficha

# Fuentes de opciones que son subconjuntos de «objetos».
_FUENTES_OBJETO = {"herramientas": "herramienta", "armas": "arma"}
# Campos de una dote u opción de clase que pasan a su rasgo en la ficha.
_CAMPOS_RASGO = ("descripcion", "resumen", "usos", "recarga", "escala", "clase")


class Sistema5e2014(SistemaReglas):
    id = "dnd5e-2014"
    nombre = "D&D 5ª edición (2014)"
    categorias = validacion.CATEGORIAS

    def validar_entrada(self, categoria: str, entrada: dict) -> list[str]:
        return validacion.validar_entrada(categoria, entrada)

    def validar_catalogo(self, catalogo: Catalogo) -> list[str]:
        return validacion.validar_catalogo(catalogo)

    def opciones_desde(self, fuente: str, filtro: dict | None, catalogo: Catalogo,
                       personaje: Personaje | None = None) -> list[Opcion]:
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
        entradas = catalogo.listar(fuente, filtro)
        if fuente == "opciones":
            # Las de un rasgo de clase opcional (estilos, invocaciones y maniobras de Tasha), solo con él activo.
            activos = {r["id"] for r in motor.rasgos_opcionales_activos(personaje, catalogo)} if personaje else set()
            entradas = [e for e in entradas if not e.get("rasgo_opcional") or activos & set(
                [e["rasgo_opcional"]] if isinstance(e["rasgo_opcional"], str) else e["rasgo_opcional"])]
        opciones = [Opcion(e["id"], e["nombre"]) for e in entradas]
        return sorted(opciones, key=lambda o: clave_alfabetica(o.nombre))

    def efecto_activo(self, efecto: dict, personaje: Personaje) -> bool:
        if efecto.get("nivel_minimo", 1) > max(1, personaje.nivel_total):
            return False
        if "nivel_clase_minimo" in efecto:
            nivel_clase = next((e.nivel for e in personaje.clases if e.clase == efecto.get("clase")), 0)
            return nivel_clase >= efecto["nivel_clase_minimo"]
        return True

    def expandir_efecto(self, efecto: dict, catalogo: Catalogo, personaje: Personaje) -> list[dict] | None:
        if efecto["tipo"] in ("dote", "opcion"):
            categoria = "dotes" if efecto["tipo"] == "dote" else "opciones"
            entrada = catalogo.obtener(categoria, efecto["id"])
            if entrada is None:
                raise ErrorReferencia(f"«{efecto['id']}» no existe en {categoria} de los paquetes activos")
            rasgo = {"tipo": "rasgo", "nombre": entrada["nombre"], **{c: entrada[c] for c in _CAMPOS_RASGO if c in entrada}}
            if efecto["tipo"] == "dote":
                rasgo.update(nombre=f"Dote: {entrada['nombre']}", dote=entrada["id"])
            else:
                rasgo["opcion"] = entrada["id"]
            return [rasgo, *entrada.get("efectos", [])]
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

    def crear_asistente(self, personaje: Personaje, catalogo: Catalogo, **opciones) -> Asistente5e:
        from .asistente import Asistente5e

        return Asistente5e(self, catalogo, personaje, **opciones)

    def crear_cuestionario(self, personaje: Personaje, catalogo: Catalogo) -> Cuestionario5e:
        from .cuestionario import Cuestionario5e

        return Cuestionario5e(self, catalogo, personaje)
