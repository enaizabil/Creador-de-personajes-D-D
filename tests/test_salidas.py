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


def _leer_formulario(ruta):
    from pypdf import PdfReader

    lector = PdfReader(str(ruta))
    return lector, {nombre: campo.get("/V") for nombre, campo in lector.get_fields().items()}


def test_plantilla_vacia_con_los_campos_esperados():
    pypdf = pytest.importorskip("pypdf")
    from creador.sistemas.dnd5e_2014.salidas.pdf_oficial import PLANTILLA, RENGLONES_CONJURO

    lector = pypdf.PdfReader(str(PLANTILLA))
    campos = lector.get_fields()
    assert len(lector.pages) == 5
    assert all(c.get("/V") in (None, "", "/Off") for c in campos.values())  # sin datos de nadie
    necesarios = {"CharacterName", "ClassLevel", "STRscore", "Stealth", "stealthPROF", "FeaturesTraits", "Feat+Traits",
                  "Backstory", "Backstory 3", "SpellSaveDC", "Spells 1", "Spells 3"}
    necesarios |= {f"Spells{n}" for renglones in RENGLONES_CONJURO.values() for n in renglones}
    assert necesarios <= set(campos)


@pytest.mark.parametrize("clase", ["picaro", "mago", "brujo", "monje"])
def test_hoja_oficial_rellena(entorno, clase, tmp_path):
    pytest.importorskip("pypdf")
    from creador.sistemas.dnd5e_2014.salidas.pdf_oficial import rellenar_hoja_oficial

    # El monje 20 tiene rasgos de sobra para desbordar la página 1, sean cuales sean las respuestas al azar.
    a = personaje(entorno, clase, nivel=20 if clase == "monje" else 5)
    a.establecer_detalle("historia", "Primer párrafo de una historia muy larga. " * 60 + "\n\nY otro más.")
    ficha = a.ficha()
    ruta = tmp_path / "oficial.pdf"
    rellenar_hoja_oficial(a, ruta)
    lector, valores = _leer_formulario(ruta)
    assert valores["CharacterName"] == valores["CharacterName 2"] == f"Prueba {clase}"
    assert valores["ClassLevel"] == ficha.clase_y_nivel and valores["Race"] == ficha.raza
    assert valores["DEXscore"] == str(ficha.caracteristicas["des"].puntuacion)
    assert valores["HPMax"] == str(ficha.pg_maximos) and valores["AC"] == str(ficha.ca)
    sigilo = ficha.habilidades["sigilo"]
    assert valores["Stealth"] == f"{sigilo.valor:+d}"  # con la pericia ya sumada
    assert (valores["stealthPROF"] == "/Yes") == sigilo.competente
    assert "/CO" not in lector.trailer["/Root"]["/AcroForm"]
    for campo in lector.get_fields().values():
        acciones = campo.get("/AA")
        assert acciones is None or "/C" not in acciones.get_object()  # sin cálculos que pisen los valores
    assert valores.get("Backstory 1")  # la historia larga sigue en la página 5
    if ficha.lanzadores:
        assert valores["SpellSaveDC"] == str(ficha.lanzadores[0].cd)
        assert valores["Spells 1"]  # descripción de conjuros en la página 4
    if clase == "mago":
        libro = sum(map(len, ficha.lanzadores[0].libro.values()))
        preparados = [n for n, v in valores.items() if n.startswith("Check") and v == "/Yes"]
        assert len(preparados) == sum(len(v) for nivel, v in ficha.lanzadores[0].conjuros.items() if nivel > 0) < libro
    if clase == "monje":
        assert valores.get("Feat+Traits")  # los rasgos que no caben siguen en la página 2


def test_partir_respeta_el_ancho():
    pytest.importorskip("reportlab")
    from reportlab.pdfbase.pdfmetrics import stringWidth

    from creador.sistemas.dnd5e_2014.salidas.pdf_oficial import _partir

    renglones = _partir("Ventaja en las salvaciones para evitar que te hechicen; la magia no puede dormirte.\nOtra.", 80, 7)
    assert renglones[-1] == "Otra." and len(renglones) > 2
    assert all(stringWidth(r, "Helvetica", 7) <= 80 for r in renglones)


def personaje_multiclase(entorno, reparto, raza="semielfo"):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    rng = random.Random("multiclase")
    for pregunta in q.preguntas():
        q.responder(pregunta.id, rng.choice(pregunta.respuestas).id)
    q.aceptar_multiclase(True)
    q.generar(nivel=sum(n for _, n in reparto), raza=raza, reparto=reparto)
    q.asistente.establecer_detalle("nombre", "Prueba multiclase")
    return q.asistente


def test_salidas_de_un_brujo_multiclase(entorno, tmp_path):
    from creador.sistemas.dnd5e_2014.salidas.pdf_oficial import texto_espacios

    a = personaje_multiclase(entorno, [("paladin", 8), ("brujo", 4)])
    ficha = a.ficha()
    assert ficha.espacios_conjuro == {1: 4, 2: 3} and ficha.magia_pacto == {"espacios": 2, "nivel": 2}
    assert texto_espacios(ficha) == {1: "4", 2: "3 + 2 (pacto)"}  # antes, el pacto tapaba los normales
    nota = nota_obsidian(a)
    datos = propiedades(nota)
    assert datos["clase"].strip() == "Paladín / Brujo" and datos["nivel"].strip() == "12"
    assert "/" in datos["subclase"]
    assert "4 de nivel 1, 3 de nivel 2 y 2 de pacto de nivel 2" in nota
    assert "3. **Clase inicial:** Paladín" in nota and "elige también **Brujo** (4 niveles" in nota


def test_hoja_oficial_con_dos_aptitudes(entorno, tmp_path):
    pytest.importorskip("pypdf")
    from creador.sistemas.dnd5e_2014.salidas.pdf_oficial import rellenar_hoja_oficial

    a = personaje_multiclase(entorno, [("clerigo", 6), ("mago", 3)], raza="humano")
    ficha = a.ficha()
    ruta = tmp_path / "oficial.pdf"
    rellenar_hoja_oficial(a, ruta)
    _, valores = _leer_formulario(ruta)
    assert valores["ClassLevel"] == ficha.clase_y_nivel
    cds = [str(lz.cd) for lz in ficha.lanzadores]
    assert valores["SpellSaveDC"] == " / ".join(dict.fromkeys(cds))
