"""Resolución genérica de efectos y elecciones declarados en los paquetes.

Un efecto es un dict con ``tipo``. El núcleo solo interpreta ``eleccion``; el
resto lo interpreta el sistema de reglas, que además puede expandir efectos que
referencian otras entradas (p. ej. ``{"tipo": "dote", "id": "alerta"}``).

Cada elección tiene una clave estable derivada de su ruta de origen
(``"clase:guerrero:4/mejora"``), de modo que las selecciones guardadas en
``Personaje.elecciones`` no se mezclan entre razas, clases o niveles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .sistema import ErrorReferencia, Opcion

if TYPE_CHECKING:
    from .paquetes import Catalogo
    from .personaje import Personaje
    from .sistema import SistemaReglas

PROFUNDIDAD_MAXIMA = 16
MARCADOR_OPCION = "$opcion"


@dataclass
class EfectoAplicado:
    efecto: dict
    origen: str
    etiqueta: str

    @property
    def tipo(self) -> str:
        return self.efecto["tipo"]


@dataclass
class EleccionPendiente:
    clave: str
    nombre: str
    elegir: int
    opciones: list[Opcion]
    seleccion: list[str]
    repetible: bool
    etiqueta: str
    # Lo que concede cada opción: «aplicar» con $opcion, o los «efectos» propios de la opción.
    aplicar: list = field(default_factory=list)
    efectos_por_opcion: dict[str, list] = field(default_factory=dict)

    @property
    def faltan(self) -> int:
        return self.elegir - len(self.seleccion)

    def efectos_de(self, opcion: str) -> list:
        return sustituir_opcion(self.efectos_por_opcion.get(opcion, self.aplicar), opcion)


@dataclass
class Resolucion:
    aplicados: list[EfectoAplicado] = field(default_factory=list)
    # Todas las elecciones alcanzables (hechas o no); «pendientes» son las que aún faltan.
    elecciones: list[EleccionPendiente] = field(default_factory=list)
    pendientes: list[EleccionPendiente] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    claves_visitadas: set[str] = field(default_factory=set)

    def de_tipo(self, *tipos: str) -> list[EfectoAplicado]:
        return [a for a in self.aplicados if a.tipo in tipos]


def sustituir_opcion(plantilla, valor: str):
    """Copia la plantilla cambiando ``$opcion`` por el valor elegido.

    No entra en lo que se aplica dentro de una elección anidada: allí ``$opcion``
    se refiere a la selección de esa elección interior. Sí sustituye en el resto
    de sus campos, lo que permite filtros como ``{"listas": "$opcion"}``.
    """
    if isinstance(plantilla, str):
        return plantilla.replace(MARCADOR_OPCION, valor)
    if isinstance(plantilla, list):
        return [sustituir_opcion(x, valor) for x in plantilla]
    if isinstance(plantilla, dict):
        if plantilla.get("tipo") == "eleccion":
            return _sustituir_en_eleccion(plantilla, valor)
        return {k: sustituir_opcion(v, valor) for k, v in plantilla.items()}
    return plantilla


def _sustituir_en_eleccion(eleccion: dict, valor: str) -> dict:
    resultado = {}
    for clave, contenido in eleccion.items():
        if clave == "aplicar":
            resultado[clave] = contenido
        elif clave == "opciones" and isinstance(contenido, list):
            resultado[clave] = [
                {k: (v if k == "efectos" else sustituir_opcion(v, valor)) for k, v in o.items()}
                if isinstance(o, dict) else sustituir_opcion(o, valor)
                for o in contenido
            ]
        else:
            resultado[clave] = sustituir_opcion(contenido, valor)
    return resultado


class ResolutorEfectos:
    def __init__(self, sistema: SistemaReglas, catalogo: Catalogo, personaje: Personaje):
        self.sistema = sistema
        self.catalogo = catalogo
        self.personaje = personaje
        self.resolucion = Resolucion()

    def resolver(self, efectos: list, origen: str, etiqueta: str, profundidad: int = 0) -> None:
        if profundidad > PROFUNDIDAD_MAXIMA:
            self.resolucion.errores.append(
                f"{etiqueta}: anidamiento de efectos demasiado profundo (¿referencia circular?)"
            )
            return
        for efecto in efectos or []:
            if not isinstance(efecto, dict) or "tipo" not in efecto:
                self.resolucion.errores.append(f"{etiqueta}: efecto sin «tipo»: {efecto!r}")
                continue
            if not self.sistema.efecto_activo(efecto, self.personaje):
                continue
            if efecto["tipo"] == "eleccion":
                self._resolver_eleccion(efecto, origen, etiqueta, profundidad)
                continue
            try:
                expansion = self.sistema.expandir_efecto(efecto, self.catalogo, self.personaje)
            except ErrorReferencia as exc:
                self.resolucion.errores.append(f"{etiqueta}: {exc}")
                continue
            if expansion is None:
                self.resolucion.aplicados.append(EfectoAplicado(efecto, origen, etiqueta))
            else:
                # Sin «id» (p. ej. mejora_caracteristica) la expansión comparte el origen del nivel.
                sub_origen = f"{origen}>{efecto['tipo']}:{efecto['id']}" if "id" in efecto else origen
                self.resolver(expansion, sub_origen, etiqueta, profundidad + 1)

    def _resolver_eleccion(self, efecto: dict, origen: str, etiqueta: str, profundidad: int) -> None:
        errores = self.resolucion.errores
        id_eleccion = efecto.get("id")
        if not id_eleccion:
            errores.append(f"{etiqueta}: elección sin «id»")
            return
        nombre = efecto.get("nombre", id_eleccion)
        clave = f"{origen}/{id_eleccion}"
        self.resolucion.claves_visitadas.add(clave)
        elegir = int(efecto.get("elegir", 1))
        repetible = bool(efecto.get("repetible", False))
        opciones, efectos_por_opcion = self._opciones(efecto, etiqueta)
        validas = {o.id for o in opciones}

        seleccion: list[str] = []
        for valor in self.personaje.elecciones.get(clave, []):
            if valor not in validas:
                errores.append(f"{etiqueta} – {nombre}: «{valor}» no es una opción válida")
            elif valor in seleccion and not repetible:
                errores.append(f"{etiqueta} – {nombre}: «{valor}» está repetido")
            elif len(seleccion) >= elegir:
                errores.append(f"{etiqueta} – {nombre}: sobran selecciones (máximo {elegir})")
                break
            else:
                seleccion.append(valor)

        eleccion = EleccionPendiente(clave, nombre, elegir, opciones, list(seleccion), repetible, etiqueta,
                                     efecto.get("aplicar", []), efectos_por_opcion)
        self.resolucion.elecciones.append(eleccion)
        if len(seleccion) < elegir:
            if not opciones:
                errores.append(f"{etiqueta} – {nombre}: la elección no tiene opciones disponibles")
            self.resolucion.pendientes.append(eleccion)

        repeticiones: dict[str, int] = {}
        for valor in seleccion:
            repeticiones[valor] = repeticiones.get(valor, 0) + 1
            sub_origen = f"{clave}={valor}"
            if repeticiones[valor] > 1:
                sub_origen += f"#{repeticiones[valor]}"
            plantilla = efectos_por_opcion.get(valor, efecto.get("aplicar", []))
            self.resolver(sustituir_opcion(plantilla, valor), sub_origen, etiqueta, profundidad + 1)

    def _opciones(self, efecto: dict, etiqueta: str) -> tuple[list[Opcion], dict[str, list]]:
        crudas = efecto.get("opciones", [])
        if isinstance(crudas, dict):
            return self.sistema.opciones_desde(crudas.get("desde", ""), crudas.get("filtro"), self.catalogo,
                                               self.personaje), {}

        fuente = efecto.get("fuente")
        conocidas = {o.id: o for o in self.sistema.opciones_desde(fuente, None, self.catalogo)} if fuente else {}
        opciones: list[Opcion] = []
        efectos_por_opcion: dict[str, list] = {}
        for item in crudas:
            if isinstance(item, str):
                opcion = conocidas.get(item)
                if opcion is None:
                    if fuente:
                        self.resolucion.errores.append(f"{etiqueta}: «{item}» no existe en «{fuente}»")
                        continue
                    opcion = Opcion(item, item)
                opciones.append(opcion)
            elif isinstance(item, dict) and "id" in item:
                opciones.append(Opcion(item["id"], item.get("nombre", item["id"])))
                if "efectos" in item:
                    efectos_por_opcion[item["id"]] = item["efectos"]
            else:
                self.resolucion.errores.append(f"{etiqueta}: opción mal formada {item!r}")
        return opciones, efectos_por_opcion
