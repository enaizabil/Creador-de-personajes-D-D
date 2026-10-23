"""Salidas: nota para Obsidian con la guía de Nivel20 y réplica de la ficha oficial en PDF."""
import random
import re

import pytest

from creador.entorno import abrir_catalogo
from creador.nucleo.personaje import Personaje
from creador.nucleo.rutas import directorio_datos_integrados
from creador.sistemas.dnd5e_2014.salidas.nota import nota_obsidian

PAQUETES = ["srd-5.1", "phb-2014", "dmg-2014", "cuestionario-basico"]
CLASES = ["barbaro", "bardo", "brujo", "clerigo", "druida", "explorador", "guerrero", "hechicero", "mago", "monje",
          "paladin", "picaro"]


@pytest.fixture(scope="module")
def entorno():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    assert errores == []
    return sistema, catalogo


def personaje(entorno, clase, nivel=5, raza="semielfo", subraza=None):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    rng = random.Random(clase)
    for pregunta in q.preguntas():
        q.responder(pregunta.id, rng.choice(pregunta.respuestas).id)
    q.generar(nivel=nivel, raza=raza, subraza=subraza, clase=clase)
    q.asistente.establecer_detalle("nombre", f"Prueba {clase}")
    q.asistente.establecer_detalle("jugador", "Jugadora")
    return q.asistente


def propiedades(nota: str) -> dict[str, str]:
    bloque = nota.split("---")[1]
    return dict(linea.split(":", 1) for linea in bloque.strip().splitlines())


@pytest.mark.parametrize("clase", CLASES)
def test_nota_con_propiedades_de_la_plantilla(entorno, clase):
    a = personaje(entorno, clase)
    ficha = a.ficha()
    nota = nota_obsidian(a)
    datos = {k: v.strip() for k, v in propiedades(nota).items()}
    assert datos["tipo"] == "pj" and datos["tags"] == "[pj]"
    assert int(datos["hp"]) == ficha.pg_maximos and int(datos["ac"]) == ficha.ca
    assert int(datos["modifier"]) == ficha.iniciativa and int(datos["nivel"]) == 5
    assert int(datos["pasiva_percepcion"]) == ficha.pasivas["percepcion"]
    for seccion in ("## Disparadores de inspiración", "## Ficha de Nivel20", "## Equipo", "## Cómo pasarlo a Nivel20",
                    "## Historial"):
        assert seccion in nota
    assert f"**{ficha.raza} · {ficha.clase_y_nivel}** · PG {ficha.pg_maximos}" in nota
    assert "| Puntuación |" in nota and "| Salvación |" in nota
    if ficha.lanzadores:
        assert "- **Magia (" in nota and "Conjuros de" in nota


def test_nota_marca_salvaciones_y_diferencias_de_nivel20(entorno):
    a = personaje(entorno, "guerrero")
    a.elegir(next(e.clave for e in a.elecciones("raza") if "dioma" in e.nombre), ["abisal"])
    nota = nota_obsidian(a)
    fila = next(linea for linea in nota.splitlines() if linea.startswith("| Salvación |"))
    assert fila.count("**") == 4  # dos salvaciones con competencia en negrita
    assert re.search(r"Abisal \(en Nivel20, «Demoníaco»\)", nota)
    assert "−" in fila or "+" in fila  # signo menos tipográfico en negativos


def test_nota_del_mago_con_libro_y_preparados(entorno):
    nota = nota_obsidian(personaje(entorno, "mago", nivel=3, raza="gnomo", subraza="gnomo_de_las_rocas"))
    assert "  - Libro de conjuros: " in nota
    assert "**marca como preparados**" in nota
    assert "vision: oscuridad 60 pies" in nota


@pytest.mark.parametrize("clase", ["monje", "mago", "brujo", "clerigo"])
def test_ficha_pdf(entorno, clase, tmp_path):
    pytest.importorskip("reportlab")
    from creador.sistemas.dnd5e_2014.salidas.ficha_pdf import generar_ficha_pdf

    a = personaje(entorno, clase)
    ruta = tmp_path / f"{clase}.pdf"
    generar_ficha_pdf(a, ruta)
    contenido = ruta.read_bytes()
    assert contenido.startswith(b"%PDF")
    paginas = len(re.findall(rb"/Type /Page\b", contenido))
    assert paginas == (3 if a.ficha().lanzadores else 2)


def test_texto_apto_para_el_pdf():
    pytest.importorskip("reportlab")
    from creador.sistemas.dnd5e_2014.salidas.ficha_pdf import _t

    assert _t("−1 · «Ñandú» — áéíóú") == "-1 · «Ñandú» — áéíóú"
    _t("ŁŒ→≥ x").encode("cp1252")  # todo lo que queda se puede escribir con las fuentes estándar
