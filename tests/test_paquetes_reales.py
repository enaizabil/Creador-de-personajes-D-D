"""Comprobaciones de integración sobre los paquetes reales srd-5.1 y phb-2014.

Construyen personajes de todas las clases, subclases y razas a niveles 1, 3 y 5,
eligiendo siempre las primeras opciones de cada elección, y exigen que el motor
no encuentre referencias rotas ni expresiones inválidas.
"""
import sys
from pathlib import Path

import pytest

from creador.entorno import abrir_catalogo
from creador.nucleo.personaje import EntradaClase, Personaje
from creador.nucleo.rutas import directorio_datos_integrados

RAIZ = Path(__file__).resolve().parents[1]
PAQUETES = ["srd-5.1", "phb-2014", "dmg-2014"]
BASE = {"fue": 15, "des": 14, "con": 13, "int": 12, "sab": 10, "car": 8}
# Avisos que indican datos rotos (no simples decisiones pendientes del jugador).
AVISOS_GRAVES = ("no existe", "desconocid", "no es una opción válida", "variable", "expresión", "operación",
                 "anidamiento", "sin «tipo»", "no tiene opciones", "no pertenece")


@pytest.fixture(scope="module")
def entorno_real():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    if not catalogo.listar("clases"):
        pytest.skip("los paquetes reales aún no tienen clases")
    return sistema, catalogo, errores


def resolver_todo(sistema, personaje, catalogo, rondas=12):
    """Rellena cada elección pendiente con sus primeras opciones disponibles."""
    for _ in range(rondas):
        pendientes = sistema.elecciones_pendientes(personaje, catalogo)
        if not pendientes:
            return
        for pendiente in pendientes:
            libres = [o.id for o in pendiente.opciones if pendiente.repetible or o.id not in pendiente.seleccion]
            personaje.elecciones[pendiente.clave] = pendiente.seleccion + libres[:pendiente.faltan]


def graves(ficha):
    return [a for a in ficha.avisos if any(marca in a for marca in AVISOS_GRAVES)]


def test_paquetes_sin_errores(entorno_real):
    _, _, errores = entorno_real
    assert errores == []


def casos_de_clase():
    sistema, catalogo, _ = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    casos = []
    for clase in catalogo.listar("clases"):
        subclases = [s["id"] for s in catalogo.listar("subclases", {"clase": clase["id"]})] or [None]
        for subclase in subclases:
            for nivel in (1, 3, 5):
                casos.append((clase["id"], subclase, nivel))
    return casos


@pytest.mark.parametrize("clase, subclase, nivel", casos_de_clase())
def test_cada_clase_y_subclase_genera_ficha(entorno_real, clase, subclase, nivel):
    sistema, catalogo, _ = entorno_real
    nivel_subclase = catalogo.obtener("clases", clase).get("nivel_subclase", 1)
    personaje = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, raza="humano", subraza="humano_estandar",
                          metodo_caracteristicas="manual", caracteristicas_base=dict(BASE),
                          clases=[EntradaClase(clase, nivel, subclase if nivel >= nivel_subclase else None)])
    resolver_todo(sistema, personaje, catalogo)
    ficha = sistema.calcular(personaje, catalogo)
    assert graves(ficha) == []
    assert sistema.elecciones_pendientes(personaje, catalogo) == []
    assert ficha.pg_maximos > 0 and ficha.ca >= 10
    assert all(r.nombre for r in ficha.rasgos)


def casos_de_raza():
    _, catalogo, _ = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    casos = []
    for raza in catalogo.listar("razas"):
        subrazas = [s["id"] for s in catalogo.listar("subrazas", {"raza": raza["id"]})] or [None]
        casos += [(raza["id"], subraza) for subraza in subrazas]
    return casos


@pytest.mark.parametrize("raza, subraza", casos_de_raza())
def test_cada_raza_genera_ficha(entorno_real, raza, subraza):
    sistema, catalogo, _ = entorno_real
    for nivel in (1, 5):
        personaje = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, raza=raza, subraza=subraza,
                              metodo_caracteristicas="manual", caracteristicas_base=dict(BASE),
                              clases=[EntradaClase("guerrero", nivel)])
        resolver_todo(sistema, personaje, catalogo)
        ficha = sistema.calcular(personaje, catalogo)
        assert graves(ficha) == []
        assert ficha.velocidades["caminar"] > 0


def test_contraste_con_el_srd_oficial(entorno_real):
    sys.path.insert(0, str(RAIZ / "herramientas"))
    import verificar_srd

    datos = verificar_srd.cargar_datos()
    problemas = (verificar_srd.verificar_conjuros(datos) + verificar_srd.verificar_armas(datos)
                 + verificar_srd.verificar_armaduras(datos))
    assert problemas == []
