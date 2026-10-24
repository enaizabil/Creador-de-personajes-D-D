"""Guía de Tasha (paquete tasha-2020), fase 1: dotes, conjuros, Linaje personalizado, Personalizar tu origen y preguntas."""
import random

import pytest

from creador.entorno import abrir_catalogo
from creador.nucleo.personaje import EntradaClase, Personaje
from creador.nucleo.rutas import directorio_datos_integrados

PAQUETES = ["srd-5.1", "phb-2014", "dmg-2014", "tasha-2020", "cuestionario-basico"]


@pytest.fixture(scope="module")
def entorno():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    assert errores == []
    return sistema, catalogo


def test_contenido_de_la_primera_fase(entorno):
    _, catalogo = entorno
    tasha = [e for cat in ("dotes", "conjuros", "razas") for e in catalogo.listar(cat)
             if catalogo.origen(cat, e["id"]) == "tasha-2020"]
    assert len([e for e in tasha if "prerrequisito" in e or "resumen" in e and "nivel" not in e]) >= 15
    assert len([e for e in tasha if "nivel" in e]) == 21
    assert {c["id"] for c in catalogo.listar("conjuros") if c["nivel"] == 0 and "artifice" in c["listas"]} == {
        "atraccion_del_relampago", "estallido_de_espadas", "filo_atronador", "filo_de_llamas_verdes"}


def test_tocado_por_las_hadas_lanza_con_la_caracteristica_que_sube(entorno):
    sistema, catalogo = entorno
    pj = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, raza="humano", subraza="humano_variante",
                   metodo_caracteristicas="manual",
                   caracteristicas_base={"fue": 10, "des": 12, "con": 12, "int": 15, "sab": 14, "car": 8},
                   clases=[EntradaClase("guerrero", 1)])
    pj.elecciones["subraza:humano_variante/dote"] = ["tocado_por_las_hadas"]
    dote = "subraza:humano_variante/dote=tocado_por_las_hadas>dote:tocado_por_las_hadas"
    pj.elecciones[f"{dote}/caracteristica"] = ["sab"]
    pj.elecciones[f"{dote}/caracteristica=sab/conjuro"] = ["dormir"]
    ficha = sistema.calcular(pj, catalogo)
    resolucion = sistema.resolver(pj, catalogo)
    conjuros = {a.efecto["id"]: a.efecto.get("caracteristica") for a in resolucion.aplicados if a.tipo == "conjuro"}
    assert conjuros == {"paso_brumoso": "sab", "dormir": "sab"}
    assert ficha.caracteristicas["sab"].puntuacion == 15


def test_linaje_personalizado(entorno):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    rng = random.Random("linaje")
    for pregunta in q.preguntas():
        q.responder(pregunta.id, rng.choice(pregunta.respuestas).id)
    q.generar(nivel=1, raza="linaje_personalizado", clase="mago")
    ficha = q.asistente.ficha()
    assert ficha.caracteristicas["int"].puntuacion >= 17  # el +2 va a la característica de la clase
    assert any(clave.endswith("/dote") for clave in q.personaje.elecciones)
    assert not ficha.avisos


def test_personalizar_tu_origen_mueve_las_mejoras_de_raza(entorno):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES,
                                             reglas_opcionales={"origen_personalizado": True}), catalogo)
    rng = random.Random("origen")
    for pregunta in q.preguntas():
        q.responder(pregunta.id, rng.choice(pregunta.respuestas).id)
    q.generar(nivel=1, raza="enano", subraza="enano_de_las_colinas", clase="mago")  # enano: +2 CON, colinas: +1 SAB
    elegidas = [v for clave, valores in q.personaje.elecciones.items() if "/origen_" in clave for v in valores]
    assert len(elegidas) == 2 and len(set(elegidas)) == 2 and "int" in elegidas
    assert not q.asistente.ficha().avisos
    # Dos mejoras en la misma característica: aviso.
    claves = [c for c in q.personaje.elecciones if "/origen_" in c]
    q.personaje.elecciones[claves[1]] = list(q.personaje.elecciones[claves[0]])
    assert any("Personalizar tu origen" in a for a in sistema.calcular(q.personaje, catalogo).avisos)


def test_las_preguntas_de_tasha_sustituyen_a_otras_sin_cambiar_el_total(entorno):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    sin_tasha_sistema, sin_tasha, _ = abrir_catalogo(
        "dnd5e-2014", [p for p in PAQUETES if p != "tasha-2020"], [directorio_datos_integrados() / "paquetes"])
    q_sin = sin_tasha_sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), sin_tasha)
    for estilo, nueva, vieja in (("cotidiana", "t_familia", "lluvia"), ("fantasia", "t_espejo", "f_trol")):
        con = [p.id for p in q.preguntas(estilo=estilo)]
        sin = [p.id for p in q_sin.preguntas(estilo=estilo)]
        assert len(con) == len(sin) and nueva in con and vieja not in con and vieja in sin
        assert con.index(nueva) == sin.index(vieja)  # en el mismo sitio
        assert nueva not in [p.id for p in q.preguntas(estilo=estilo, cantidad="rapido")]  # es de detalle 2


def test_la_tabla_de_rasgos_de_tasha_apunta_a_contenido_que_existe(entorno):
    _, catalogo = entorno
    filas = [r for r in catalogo.listar("recomendaciones") if r["id"].endswith("_tasha")]
    assert {r["rasgo"] for r in filas} >= {"combate", "arcano", "saber", "astucia"}
    for fila in filas:
        for categoria in ("dotes", "conjuros"):
            for id_ in fila.get(categoria, []):
                assert catalogo.origen(categoria, id_) == "tasha-2020", id_


def test_al_subir_de_nivel_puede_salir_una_dote_de_tasha(entorno):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    rng = random.Random("tasha-dote")
    for pregunta in q.preguntas():
        q.responder(pregunta.id, rng.choice(pregunta.respuestas).id)
    q.generar(nivel=3, raza="humano", subraza="humano_estandar", clase="hechicero")
    q.responder_subida("subida_entrenamiento", "maestro")
    q.responder_subida("subida_cicatriz", "magia")
    q.subir_nivel(1)
    dote = next(v[0] for c, v in q.personaje.elecciones.items() if c.endswith("mejora=dote/dote"))
    assert catalogo.origen("dotes", dote) == "tasha-2020", dote
    assert not q.asistente.ficha().avisos
