"""Modo sencillo: cuestionario de situaciones sobre los paquetes reales."""
import random
from collections import Counter

import pytest

from creador.entorno import abrir_catalogo
from creador.nucleo.personaje import Personaje
from creador.nucleo.rutas import directorio_datos_integrados
from creador.sistemas.dnd5e_2014 import motor
from creador.sistemas.dnd5e_2014.constantes import RASGOS_PERFIL
from creador.sistemas.dnd5e_2014.cuestionario import afinidad

PAQUETES = ["srd-5.1", "phb-2014", "dmg-2014", "cuestionario-basico"]


@pytest.fixture(scope="module")
def entorno():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    assert errores == []
    return sistema, catalogo


def nuevo(entorno, **campos):
    sistema, catalogo = entorno
    personaje = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, **campos)
    return sistema.crear_cuestionario(personaje, catalogo)


def responder_al_azar(cuestionario, semilla):
    rng = random.Random(semilla)
    for pregunta in cuestionario.preguntas():
        cuestionario.responder(pregunta.id, rng.choice(pregunta.respuestas).id)


def responder_hacia(cuestionario, catalogo, rasgo):
    """En cada pregunta, la respuesta que más puntúa ese rasgo (las que no lo tocan se dejan sin responder)."""
    for pregunta in catalogo.listar("preguntas"):
        mejor = max(pregunta["respuestas"], key=lambda r: r.get("perfil", {}).get(rasgo, 0))
        if mejor.get("perfil", {}).get(rasgo):
            cuestionario.responder(pregunta["id"], mejor["id"])


def test_banco_de_preguntas_equilibrado(entorno):
    _, catalogo = entorno
    preguntas = catalogo.listar("preguntas")
    assert len(preguntas) >= 12
    apariciones = Counter(r for p in preguntas for resp in p["respuestas"] for r in resp.get("perfil", {}))
    assert set(apariciones) == set(RASGOS_PERFIL)
    assert min(apariciones.values()) >= 4, apariciones
    lapiz = catalogo.obtener("preguntas", "lapiz")
    assert {r["id"] for r in lapiz["respuestas"]} >= {"clavar", "prestar", "todo"}


def test_referencias_de_recomendaciones_y_pesos_existen(entorno):
    _, catalogo = entorno
    for recomendacion in catalogo.listar("recomendaciones"):
        for id_ in recomendacion.get("conjuros", []):
            assert catalogo.obtener("conjuros", id_), (recomendacion["id"], id_)
        for id_ in recomendacion.get("opciones", []):
            assert catalogo.obtener("opciones", id_), (recomendacion["id"], id_)
        for id_ in recomendacion.get("dotes", []):
            assert catalogo.obtener("dotes", id_), (recomendacion["id"], id_)
        if recomendacion["id"] != "general":
            assert catalogo.obtener("clases", recomendacion["id"]), recomendacion["id"]
    for pregunta in catalogo.listar("preguntas"):
        for respuesta in pregunta["respuestas"]:
            for referencia in respuesta.get("pesos", {}):
                categoria, id_ = referencia.split(":")
                assert catalogo.obtener(categoria, id_), referencia


def test_respuestas_validas_y_borrables(entorno):
    q = nuevo(entorno)
    q.responder("lapiz", "clavar")
    assert q.perfil() == {"combate": 2, "astucia": 1}
    with pytest.raises(ValueError):
        q.responder("lapiz", "comerselo")
    q.responder("lapiz", None)
    assert q.perfil() == {} and q.respuestas == {}


def test_el_alineamiento_sale_de_las_respuestas(entorno):
    q = nuevo(entorno)
    assert q.alineamiento() == "Neutral"
    q.responder("lapiz", "clavar")  # moral -2, orden -1
    assert q.alineamiento() == "Neutral malvado"
    q.responder("cartera", "quedarse")  # moral -1, orden -1
    assert q.alineamiento() == "Caótico malvado"
    q.responder("lapiz", "todo")
    q.responder("cartera", "policia")
    assert q.alineamiento() == "Legal bueno"


@pytest.mark.parametrize(("rasgo", "esperadas"), [
    ("combate", {"guerrero", "barbaro"}),
    ("arcano", {"mago", "hechicero", "brujo"}),
    ("fe", {"clerigo", "paladin"}),
    ("sigilo", {"picaro"}),
    ("naturaleza", {"druida", "explorador"}),
])
def test_respuestas_coherentes_dan_clases_coherentes(entorno, rasgo, esperadas):
    _, catalogo = entorno
    q = nuevo(entorno)
    responder_hacia(q, catalogo, rasgo)
    q.responder("experiencia", "alguna_vez")
    assert q.recomendar_clases()[0].id in esperadas, [(r.id, r.afinidad) for r in q.recomendar_clases()[:4]]


def test_los_novatos_tiran_a_clases_sencillas(entorno):
    q = nuevo(entorno)
    q.responder("experiencia", "nunca")
    assert {r.id for r in q.recomendar_clases()[:2]} == {"guerrero", "barbaro"}


def test_mismas_respuestas_mismo_personaje(entorno):
    personajes = []
    for _ in range(2):
        q = nuevo(entorno)
        responder_al_azar(q, 42)
        q.generar(nivel=3)
        personajes.append(q.personaje.a_dict())
    assert personajes[0] == personajes[1]


def test_recomendaciones_ordenadas_y_una_por_raza(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, 1)
    razas = q.recomendar_razas()
    assert len({r.id for r in razas}) == len(razas)
    assert [r.afinidad for r in razas] == sorted((r.afinidad for r in razas), reverse=True)
    assert all(0 <= r.afinidad <= 100 for r in razas)
    assert not any(r.id == "aasimar" for r in razas)  # requiere permiso del DM


@pytest.mark.parametrize("clase", ["barbaro", "bardo", "brujo", "clerigo", "druida", "explorador", "guerrero",
                                   "hechicero", "mago", "monje", "paladin", "picaro"])
def test_genera_personajes_completos_y_sin_avisos(entorno, clase):
    combinaciones = ((1, "mediano", "mediano_piesligeros"), (3, "semielfo", None), (5, "enano", "enano_de_las_colinas"),
                     (11, "humano", "humano_estandar"), (17, "elfo", "alto_elfo"), (20, "semiorco", None))
    for nivel, raza, subraza in combinaciones:
        q = nuevo(entorno)
        responder_al_azar(q, f"{clase}{nivel}")
        q.generar(nivel=nivel, raza=raza, subraza=subraza, clase=clase)
        a = q.asistente
        faltan = {p.id: a.faltan(p.id) for p in a.pasos() if a.faltan(p.id)}
        assert faltan == {"detalles": ["Ponle nombre al personaje"], "resumen": ["Ponle nombre al personaje"]}, faltan
        ficha = a.ficha()
        assert ficha.avisos == [], (nivel, ficha.avisos)
        assert ficha.detalles["alineamiento"] and ficha.detalles["ideales"]
        assert ficha.equipo


def test_el_mago_generado_tiene_libro_valido(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, 3)
    q.generar(nivel=5, raza="gnomo", subraza="gnomo_de_las_rocas", clase="mago")
    personaje = q.personaje
    _, catalogo = entorno
    libro = [catalogo.obtener("conjuros", i) for i in personaje.conjuros["mago"]]
    niveles = [c["nivel"] for c in libro if c["nivel"] > 0]
    assert len(niveles) == 6 + 2 * 4 and 3 in niveles
    config = motor.configuracion_lanzamiento(personaje, catalogo, "mago")
    assert motor.avisos_libro(config, 5, niveles, "Mago") == []
    assert set(personaje.preparados["mago"]) <= set(personaje.conjuros["mago"])
    assert "proyectil_magico" in personaje.conjuros["mago"]  # recomendado


def test_caracteristicas_segun_clase_y_respuestas(entorno):
    _, catalogo = entorno
    q = nuevo(entorno)
    responder_hacia(q, catalogo, "agilidad")
    q.generar(nivel=1, raza="humano", subraza="humano_estandar", clase="guerrero")
    base = q.personaje.caracteristicas_base
    assert base["des"] == 15 and base["fue"] < 15  # guerrero ágil: «fue o des» lo deciden las respuestas
    q = nuevo(entorno)
    responder_hacia(q, catalogo, "combate")
    q.generar(nivel=1, raza="humano", subraza="humano_estandar", clase="guerrero")
    assert q.personaje.caracteristicas_base["fue"] == 15
    q = nuevo(entorno)
    responder_hacia(q, catalogo, "combate")
    q.generar(nivel=1, raza="humano", subraza="humano_estandar", clase="mago")
    assert q.personaje.caracteristicas_base["int"] == 15  # la clase manda en su característica clave


def test_preguntas_que_dependen_de_lo_cargado(entorno):
    sistema, catalogo = entorno
    catalogo.agregar("preguntas", {"id": "solo_tasha", "nombre": "x", "texto": "x", "requiere": ["clases:artifice"],
                                   "respuestas": [{"id": "a", "texto": "a", "perfil": {"saber": 1}},
                                                  {"id": "b", "texto": "b", "perfil": {"arcano": 1}}]}, "prueba")
    try:
        assert "solo_tasha" not in [p.id for p in nuevo(entorno).preguntas()]
    finally:
        catalogo._entradas["preguntas"].pop("solo_tasha")


def test_afinidad():
    assert afinidad({"combate": 3}, {"combate": 5}) == pytest.approx(1)
    assert afinidad({"combate": 3}, {"saber": 5}) == 0
    assert afinidad({}, {"saber": 5}) == 0


def test_secretos_magicos_de_nivel_alto_y_de_otras_listas(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "bardo20")
    q.generar(nivel=20, raza="semielfo", clase="bardo")
    catalogo = q.catalogo
    for nivel, maximo in ((10, 5), (14, 7), (18, 9)):
        ids = q.personaje.elecciones[f"clase:bardo:{nivel}/secretos_magicos_{nivel}"]
        elegidos = [catalogo.obtener("conjuros", i) for i in ids]
        assert [c["nivel"] for c in elegidos] == [maximo, maximo]
        assert not any("bardo" in c["listas"] for c in elegidos)


# ── multiclase ─────────────────────────────────────────────────────────────

def test_una_sola_clase_si_no_se_acepta_multiclase(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "solo")
    assert not q.acepta_multiclase
    assert len(q.proponer_reparto(12)) == 1


def test_reparto_propuesto_con_multiclase(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "mixto")
    q.aceptar_multiclase(True)
    principal = q.recomendar_clases()[0].id
    for nivel in (1, 2, 3):
        assert q.proponer_reparto(nivel) == [(principal, nivel)]  # por debajo de 4, una sola clase
    for nivel, secundaria in ((4, 1), (9, 3), (20, 5)):
        reparto = q.proponer_reparto(nivel)
        assert reparto[0][0] == principal and sum(n for _, n in reparto) == nivel
        assert reparto[1][1] == secundaria and q.compatibles(principal, reparto[1][0])
        nivel_subclase = q.catalogo.obtener("clases", principal)["nivel_subclase"]
        assert reparto[0][1] >= nivel_subclase


def test_compatibles_como_mucho_tres_caracteristicas_clave(entorno):
    q = nuevo(entorno)
    assert q.compatibles("paladin", "brujo")  # FUE y CAR
    assert q.compatibles("guerrero", "picaro")  # FUE (o DES) y DES
    assert not q.compatibles("monje", "paladin")  # DES, SAB, FUE y CAR
    assert not q.compatibles("mago", "mago")


@pytest.mark.parametrize("semilla", ["a", "b", "c", "d", "e", "f"])
def test_genera_multiclase_completo_y_sin_avisos(entorno, semilla):
    q = nuevo(entorno)
    responder_al_azar(q, semilla)
    q.aceptar_multiclase(True)
    for nivel in (5, 12, 20):
        q.generar(nivel=nivel)
        a = q.asistente
        assert len(a.personaje.clases) == 2 and a.nivel == nivel
        faltan = {p.id: a.faltan(p.id) for p in a.pasos() if a.faltan(p.id)}
        assert faltan == {"detalles": ["Ponle nombre al personaje"], "resumen": ["Ponle nombre al personaje"]}, faltan
        assert a.ficha().avisos == [], (nivel, a.personaje.clases, a.ficha().avisos)


def test_generar_con_reparto_elegido(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "reparto")
    q.aceptar_multiclase(True)
    q.generar(nivel=10, raza="humano", subraza="humano_estandar", reparto=[("paladin", 7), ("brujo", 3)])
    assert [(e.clase, e.nivel) for e in q.personaje.clases] == [("paladin", 7), ("brujo", 3)]
    assert all(e.subclase for e in q.personaje.clases)
    assert q.asistente.ficha().avisos == []
