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
        if recomendacion["id"] != "general" and "rasgo" not in recomendacion:  # rasgo_*: tabla rasgo → ids
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


@pytest.mark.parametrize("clase, subclase", [("bardo", None), ("brujo", None), ("clerigo", None), ("druida", None),
                                             ("explorador", None), ("guerrero", "caballero_arcano"), ("hechicero", None),
                                             ("mago", None), ("paladin", None), ("picaro", "embaucador_arcano")])
def test_conjuros_de_nivel_alto_salen_de_las_recomendaciones(entorno, clase, subclase):
    """Un conjuro de nivel 3 o más no recomendado solo entra si ya están todos los recomendados de su nivel."""
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, clase)
    if subclase:  # la única subclase lanzadora de la clase
        q._mejor_subclase = lambda _clase: subclase
    q.generar(nivel=20, raza="humano", subraza="humano_estandar", clase=clase)
    recomendados = catalogo.obtener("recomendaciones", clase)["conjuros"]
    plan = next(p for p in q.asistente.planes_conjuros() if p.clase_id == clase)
    elegidos = q.personaje.conjuros[clase]
    altos = 0
    for id_ in elegidos:
        nivel = catalogo.obtener("conjuros", id_)["nivel"]
        if nivel < 3:
            continue
        altos += 1
        if id_ not in recomendados:
            disponibles = {i for i, _ in plan.disponibles.get(nivel, [])}
            olvidados = [r for r in recomendados if r in disponibles and r not in elegidos]
            assert not olvidados, (id_, olvidados)
    assert altos, elegidos


def test_maestria_y_caracteristicos_entran_en_el_libro_sin_desplazar_recomendados(entorno):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, "mago")
    q.generar(nivel=20, raza="humano", subraza="humano_estandar", clase="mago")
    libro, preparados = q.personaje.conjuros["mago"], q.personaje.preparados["mago"]
    caracteristicos = q.personaje.elecciones["clase:mago:20/conjuros_caracteristicos"]
    for clave in ("clase:mago:18/maestria_conjuros_1", "clase:mago:18/maestria_conjuros_2"):
        assert set(q.personaje.elecciones[clave]) <= set(libro)
    assert set(caracteristicos) <= set(libro)
    assert not set(caracteristicos) & set(preparados)  # siempre preparados: no gastan preparación
    recomendados = catalogo.obtener("recomendaciones", "mago")["conjuros"]
    assert {"bola_de_fuego", "contrahechizo"} <= set(libro) & set(recomendados)
    assert not [a for a in sistema.calcular(q.personaje, catalogo).avisos if "libro" in a]


def test_sin_aceptar_multiclase_siempre_una_clase(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "una")
    assert not q.acepta_multiclase
    assert len(q.proponer_reparto(10)) == 1
    q.aceptar_multiclase(True)
    assert q.personaje.reglas_opcionales["multiclase"] is True
    assert len(q.proponer_reparto(10)) == 2
    q.aceptar_multiclase(False)
    assert len(q.proponer_reparto(10)) == 1


@pytest.mark.parametrize("clase", ["bardo", "brujo", "clerigo", "guerrero", "mago", "paladin", "picaro"])
def test_subir_de_nivel_conserva_lo_elegido_y_completa_lo_nuevo(entorno, clase):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, f"subir-{clase}")
    q.generar(nivel=3, raza="humano", subraza="humano_estandar", clase=clase)
    antes_elecciones = dict(q.personaje.elecciones)
    antes_conjuros = {c: list(ids) for c, ids in q.personaje.conjuros.items()}
    subclase = q.personaje.clases[0].subclase
    q.subir_nivel(5)
    assert q.personaje.nivel_total == 8
    assert q.personaje.clases[0].subclase == subclase or subclase is None
    for clave, valor in antes_elecciones.items():
        assert q.personaje.elecciones.get(clave) == valor, clave
    for clase_id, ids in antes_conjuros.items():
        assert set(ids) <= set(q.personaje.conjuros[clase_id]), clase_id
    ficha = sistema.calcular(q.personaje, catalogo)
    assert not [a for a in ficha.avisos if "pendiente" in a or "faltan" in a or "sobran" in a.lower()], ficha.avisos
    if clase == "mago":  # 6 + 2 por nivel: 20 conjuros en el libro a nivel 8
        libro = [i for i in q.personaje.conjuros["mago"] if catalogo.obtener("conjuros", i)["nivel"] > 0]
        assert len(libro) == 6 + 2 * 7


def test_subir_de_nivel_con_tiradas_de_pg(entorno):
    q = nuevo(entorno, metodo_pg="tiradas")
    responder_al_azar(q, "tiradas")
    q.generar(nivel=1, raza="humano", subraza="humano_estandar", clase="guerrero")
    q.subir_nivel(3)
    entrada = q.personaje.clases[0]
    assert entrada.nivel == 4 and len(entrada.tiradas_pg) == 3
    assert all(1 <= t <= 10 for t in entrada.tiradas_pg)


def subida(entorno, clase, nivel, semilla="concretas"):
    q = nuevo(entorno)
    responder_al_azar(q, semilla)
    q.generar(nivel=nivel, raza="humano", subraza="humano_estandar", clase=clase)
    return q


def concretas(preguntas):
    return {p.id: p for p in preguntas if p.concreta}


def test_preguntas_de_subida_segun_lo_que_traen_los_niveles(entorno):
    q = nuevo(entorno)
    assert not any(p.id.startswith("subida_") for p in q.preguntas())
    q = subida(entorno, "guerrero", 3, semilla="decisiones")
    assert q.decisiones_de_subida(1) == {"mejora"}
    preguntas = q.preguntas_de_subida(1)
    assert q.personaje.nivel_total == 3  # se prueba sobre una copia
    hitos = [p for p in preguntas if not p.concreta]
    # Un hito (no el de entrenar: la mejora ya se pregunta en concreto) y la mejora, con más de 4 respuestas.
    assert len(hitos) == 1 and hitos[0].id != "subida_entrenamiento"
    mejora = concretas(preguntas)["c:clase:guerrero:4/mejora"]
    assert len(mejora.respuestas) > 4 and sum(r.propuesta for r in mejora.respuestas) == 1
    puntuaciones = {c: v.puntuacion for c, v in q.asistente.ficha().caracteristicas.items()}
    reparto = next(r for r in mejora.respuestas if r.id.startswith("car:"))
    car = reparto.id.removeprefix("car:").split("+")[0]
    assert f"{puntuaciones[car]} → " in reparto.texto  # con las puntuaciones de ahora
    assert any(r.id.startswith("dote:") for r in mejora.respuestas)
    # Sin decisiones (guerrero 5: Ataque Extra), ninguna pregunta.
    q.subir_nivel(1)
    assert q.preguntas_de_subida(1) == []
    # Mago 1 → 2: la escuela de magia (8 subclases) y los conjuros nuevos, con ejemplos de su lista.
    q2 = subida(entorno, "mago", 1)
    preguntas = concretas(q2.preguntas_de_subida(1))
    assert set(preguntas) == {"c:subclase_de:mago", "c:escuela:mago"}
    assert len(preguntas["c:subclase_de:mago"].respuestas) >= 8
    assert all("(" in r.detalle for r in preguntas["c:escuela:mago"].respuestas)


def test_las_respuestas_concretas_deciden_la_subida(entorno):
    sistema, catalogo = entorno
    q = subida(entorno, "guerrero", 3)
    mejora = concretas(q.preguntas_de_subida(1))["c:clase:guerrero:4/mejora"]
    dote = next(r.id for r in mejora.respuestas if r.id.startswith("dote:") and not r.propuesta)
    q.responder_subida(mejora.id, [dote])
    q.subir_nivel(1)
    assert q.personaje.elecciones["clase:guerrero:4/mejora"] == ["dote"]
    assert q.personaje.elecciones["clase:guerrero:4/mejora=dote/dote"] == [dote.removeprefix("dote:")]
    assert q.subidas_anteriores[-1]["respuestas"] == {mejora.id: [dote]}

    q = subida(entorno, "guerrero", 3)
    q.responder_subida("c:clase:guerrero:4/mejora", ["car:con+con"])
    q.subir_nivel(1)
    assert q.personaje.elecciones["clase:guerrero:4/mejora=caracteristicas/puntos"] == ["con", "con"]

    q = subida(entorno, "mago", 1)
    subclase = next(r.id for r in concretas(q.preguntas_de_subida(1))["c:subclase_de:mago"].respuestas if not r.propuesta)
    q.responder_subida("c:subclase_de:mago", subclase)
    q.subir_nivel(1)
    assert q.personaje.clases[0].subclase == subclase

    # Una respuesta que ya no vale (de otra versión de los datos, p. ej.) se ignora: decide el perfil.
    q = subida(entorno, "guerrero", 3)
    q.responder_subida("c:clase:guerrero:4/mejora", ["dote:no_existe"])
    q.subir_nivel(1)
    assert q.personaje.elecciones["clase:guerrero:4/mejora"]
    assert not [a for a in sistema.calcular(q.personaje, catalogo).avisos if "pendiente" in a or "faltan" in a]


def test_huecos_iguales_de_varios_niveles_en_una_pregunta(entorno):
    sistema, catalogo = entorno
    q = subida(entorno, "brujo", 1)
    q.responder_subida("c:clase:brujo:3/beneficio_pacto", ["pacto_del_filo"])
    preguntas = concretas(q.preguntas_de_subida(4))
    invocaciones = preguntas["c:clase:brujo:2/invocaciones"]
    assert invocaciones.elegir == 3  # 2 a nivel 2 y 1 a nivel 5
    ofrecidas = {r.id for r in invocaciones.respuestas}
    # Prerrequisitos leídos: Filo Sediento (nivel 5 y Pacto del Filo) sí; los de nivel 12 o de otro pacto, no.
    assert "filo_sediento" in ofrecidas
    assert not ofrecidas & {"devorador_de_vida", "cadenas_de_carceri", "voz_del_amo_de_la_cadena"}
    elegidas = [r.id for r in invocaciones.respuestas if not r.propuesta][:3]
    q.responder_subida(invocaciones.id, elegidas)
    q.subir_nivel(4)
    pj = q.personaje.elecciones
    assert pj["clase:brujo:3/beneficio_pacto"] == ["pacto_del_filo"]
    assert sorted(pj["clase:brujo:2/invocaciones"] + pj["clase:brujo:5/invocacion_nivel_5"]) == sorted(elegidas)
    assert not [a for a in sistema.calcular(q.personaje, catalogo).avisos if "pendiente" in a or "faltan" in a]


def test_la_escuela_concreta_ordena_los_conjuros_nuevos(entorno):
    q = subida(entorno, "mago", 6, semilla="escuela concreta")
    antes = set(q.personaje.conjuros["mago"])
    escuelas = concretas(q.preguntas_de_subida(1))["c:escuela:mago"]
    assert len(escuelas.respuestas) > 4
    q.responder_subida(escuelas.id, ["nigromancia"])
    plan = next(p for p in q.asistente.planes_conjuros() if p.clase_id == "mago")
    q.subir_nivel(1)
    nuevos = set(q.personaje.conjuros["mago"]) - antes
    # Van primero los de nigromancia del nivel nuevo (aunque la clase recomiende otros); si no llegan, el resto.
    nigromancia = [i for i, _ in plan.disponibles.get(4, []) + q.asistente.planes_conjuros()[0].disponibles.get(4, [])
                   if q.catalogo.obtener("conjuros", i)["escuela"] == "nigromancia" and i not in antes]
    assert nigromancia and set(nigromancia[:len(nuevos)]) <= nuevos, (nigromancia, nuevos)


def test_historia_al_crear_a_nivel_alto(entorno):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, "historia")
    eleccion = {"raza": "humano", "subraza": "humano_estandar", "clase": "guerrero", "trasfondo": "soldado"}
    assert q.preguntas_de_historia(1, **eleccion) == []
    preguntas = q.preguntas_de_historia(12, **eleccion)
    hitos = [p for p in preguntas if not p.concreta]
    assert len(hitos) == 3  # 11 niveles de historia: tres hitos
    ids = list(concretas(preguntas))
    mejoras = [i for i in ids if i.endswith("/mejora")]
    assert ids[0] == "c:subclase_de:guerrero" and mejoras == [f"c:clase:guerrero:{n}/mejora" for n in (4, 6, 8, 12)]
    assert not any(":1/" in i for i in ids)  # lo de nivel 1 sale del perfil, como siempre
    subclase = next(r.id for r in concretas(preguntas)["c:subclase_de:guerrero"].respuestas if not r.propuesta)
    q.responder_subida("c:subclase_de:guerrero", [subclase])
    q.responder_subida("c:clase:guerrero:8/mejora", ["car:con+con"])
    q.generar(nivel=12, **eleccion)
    assert q.personaje.clases[0].subclase == subclase
    assert q.personaje.elecciones["clase:guerrero:8/mejora=caracteristicas/puntos"] == ["con", "con"]
    assert q.respuestas_subida == {} and q.subidas_anteriores[-1]["hasta"] == 12
    assert not [a for a in sistema.calcular(q.personaje, catalogo).avisos if "pendiente" in a or "faltan" in a]


def test_conservar_solo_las_respuestas_vigentes(entorno):
    q = nuevo(entorno)
    q.responder_subida("c:subclase_de:mago", ["escuela_de_evocacion"])
    q.responder_subida("subida_objetivo", "plan")
    q.conservar_respuestas_subida({"subida_objetivo"})
    assert q.respuestas_subida == {"subida_objetivo": "plan"}
    with pytest.raises(ValueError):
        q.responder_subida("c:clase:guerrero:4/mejora", [""])


@pytest.mark.parametrize("entreno, esperado", [("maestro", "dote"), ("pulir", "caracteristicas")])
def test_entrenar_decide_entre_mejora_y_dote(entorno, entreno, esperado):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, "dote")
    q.generar(nivel=3, raza="humano", subraza="humano_estandar", clase="guerrero")
    q.responder_subida("subida_entrenamiento", entreno)
    q.responder_subida("subida_objetivo", "primera_linea")
    q.subir_nivel(1)
    assert q.personaje.elecciones["clase:guerrero:4/mejora"] == [esperado]
    if esperado == "dote":
        dote = q.personaje.elecciones["clase:guerrero:4/mejora=dote/dote"][0]
        assert dote in catalogo.obtener("recomendaciones", "rasgo_combate")["dotes"] + \
            catalogo.obtener("recomendaciones", "rasgo_aguante")["dotes"]
    assert not [a for a in sistema.calcular(q.personaje, catalogo).avisos if "prerrequisito" in a or "pendiente" in a]
    assert q.respuestas_subida == {}
    assert q.subidas_anteriores[-1] == {"desde": 3, "hasta": 4, "respuestas": {"subida_entrenamiento": entreno,
                                                                               "subida_objetivo": "primera_linea"}}


def test_la_escuela_de_magia_elegida_al_subir_ordena_los_conjuros_nuevos(entorno):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, "escuelas")
    q.generar(nivel=6, raza="humano", subraza="humano_estandar", clase="mago")
    antes = set(q.personaje.conjuros["mago"])
    q.responder_subida("subida_poder", "destruccion")
    q.subir_nivel(1)
    nuevos = set(q.personaje.conjuros["mago"]) - antes
    assert nuevos and all(catalogo.obtener("conjuros", i)["escuela"] == "evocacion" for i in nuevos), nuevos


def test_sin_bastantes_opciones_nuevas_repite_antes_que_dejarla_a_medias(entorno):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, "rituales")
    q.generar(nivel=4, raza="humano", subraza="humano_estandar", clase="brujo")
    pj = q.personaje
    for clave in [c for c in pj.elecciones if c.startswith("clase:brujo:4/mejora")]:
        del pj.elecciones[clave]
    # Conoce dos de los tres rituales de nivel 1 de su lista: solo queda uno nuevo.
    resto = [i for i in pj.conjuros["brujo"] if i not in ("entender_idiomas", "texto_ilusorio", "sirviente_invisible")]
    pj.conjuros["brujo"] = resto[:-2] + ["entender_idiomas", "texto_ilusorio"]
    pj.elecciones["clase:brujo:4/mejora"] = ["dote"]
    pj.elecciones["clase:brujo:4/mejora=dote/dote"] = ["lanzador_ritual"]
    pj.elecciones["clase:brujo:4/mejora=dote/dote=lanzador_ritual>dote:lanzador_ritual/clase"] = ["brujo"]
    q._completar_elecciones()
    rituales = next(v for k, v in pj.elecciones.items() if k.endswith("/rituales"))
    assert len(rituales) == 2  # los dos rituales de nivel 1 del brujo, aunque ya conozca uno
    assert not [a for a in sistema.calcular(pj, catalogo).avisos if "pendiente" in a or "faltan" in a]


def test_resiliente_no_repite_una_salvacion_que_ya_tiene(entorno):
    sistema, catalogo = entorno
    q = nuevo(entorno)
    responder_al_azar(q, "resiliente")
    q.generar(nivel=4, raza="humano", subraza="humano_estandar", clase="guerrero")
    pj = q.personaje
    for clave in [c for c in pj.elecciones if c.startswith("clase:guerrero:4/mejora")]:
        del pj.elecciones[clave]
    pj.elecciones["clase:guerrero:4/mejora"] = ["dote"]
    pj.elecciones["clase:guerrero:4/mejora=dote/dote"] = ["resiliente"]
    q._completar_elecciones()
    elegida = next(v for c, v in pj.elecciones.items() if "resiliente" in c and c.count("/") > 1)
    assert not set(elegida) & {"fue", "con"}  # las salvaciones del guerrero
    assert not [a for a in sistema.calcular(pj, catalogo).avisos if "repetida" in a]


def test_novedades_de_una_subida(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "novedades")
    q.generar(nivel=4, raza="humano", subraza="humano_estandar", clase="guerrero")
    antes = q.asistente.instantanea()
    q.subir_nivel(1)
    novedades = q.asistente.novedades(antes)
    assert novedades[0].startswith("Guerrero 4") and "→ Guerrero 5" in novedades[0]
    assert any(n.startswith("Puntos de golpe máximos:") for n in novedades)
    assert any("Ataque Adicional" in n for n in novedades)


def test_entrenamiento_de_la_guia_del_dm_al_subir(entorno):
    from creador.sistemas.dnd5e_2014.salidas.nota import nota_obsidian
    from creador.sistemas.dnd5e_2014.texto import resumen_ficha
    sistema, catalogo = entorno
    q = nuevo(entorno, reglas_opcionales={"entrenamiento": True})
    responder_al_azar(q, "entrenar")
    q.generar(nivel=4, raza="humano", subraza="humano_estandar", clase="guerrero")
    q.subir_nivel(2)
    ficha = sistema.calcular(q.personaje, catalogo)
    assert [(e["nivel"], e["dias"], e["coste_po"]) for e in ficha.entrenamiento] == [(5, 20, 40), (6, 20, 40)]
    assert "ENTRENAMIENTO PENDIENTE" in resumen_ficha(ficha)
    assert "Entrenamiento pendiente" in nota_obsidian(q.asistente)
    q.asistente.entrenamiento_hecho()
    assert sistema.calcular(q.personaje, catalogo).entrenamiento == []


def test_hitos_sin_respuestas_concretas_al_crear_a_nivel_alto(entorno):
    q = nuevo(entorno)
    responder_al_azar(q, "historia")
    q.responder_subida("subida_entrenamiento", "maestro")
    q.responder_subida("subida_objetivo", "primera_linea")
    q.generar(nivel=8, raza="humano", subraza="humano_estandar", clase="guerrero")
    assert q.personaje.elecciones["clase:guerrero:4/mejora"] == ["dote"]
    assert q.subidas_anteriores[-1]["desde"] == 1 and q.subidas_anteriores[-1]["hasta"] == 8
    assert q.respuestas_subida == {}


@pytest.mark.parametrize("estilo", ["cotidiana", "fantasia", "mezcla"])
def test_cantidad_estilo_y_contenido_sensible(entorno, estilo):
    _, catalogo = entorno
    q = nuevo(entorno)
    tamanos = []
    for cantidad in ("rapido", "recomendado", "preciso"):
        normales = q.preguntas(cantidad=cantidad, estilo=estilo, sensible=False)
        con_sensibles = q.preguntas(cantidad=cantidad, estilo=estilo, sensible=True)
        assert len(con_sensibles) > len(normales)
        assert not any(catalogo.obtener("preguntas", p.id).get("sensible") for p in normales)
        assert normales[0].id == "experiencia"  # la común va siempre la primera
        estilos = {catalogo.obtener("preguntas", p.id)["estilo"] for p in normales[1:]}
        assert estilos == ({"cotidiana", "fantasia"} if estilo == "mezcla" else {estilo})
        # Cada nivel cubre todos los rasgos del perfil al menos dos veces.
        apariciones = Counter(r for p in normales for resp in catalogo.obtener("preguntas", p.id)["respuestas"]
                              for r in resp.get("perfil", {}))
        assert set(apariciones) == set(RASGOS_PERFIL) and min(apariciones.values()) >= 2, (cantidad, apariciones)
        tamanos.append(len(normales))
    assert tamanos == [10, 20, 32]


def test_la_configuracion_se_guarda_en_el_personaje(entorno):
    q = nuevo(entorno)
    assert q.configuracion == {"cantidad": "recomendado", "estilo": "cotidiana", "sensible": False}
    q.configurar(cantidad="rapido", estilo="fantasia", sensible=True)
    assert q.personaje.extra["cuestionario"]["configuracion"] == {"cantidad": "rapido", "estilo": "fantasia",
                                                                  "sensible": True}
    assert len(q.preguntas()) == 12
    with pytest.raises(ValueError):
        q.configurar(estilo="terror")


@pytest.mark.parametrize("estilo", ["cotidiana", "fantasia", "mezcla"])
@pytest.mark.parametrize("cantidad", ["rapido", "recomendado", "preciso"])
def test_respuestas_coherentes_recomiendan_su_clase(entorno, estilo, cantidad):
    """Quien responde siempre lo más afín a una clase la tiene entre las dos primeras recomendaciones."""
    _, catalogo = entorno
    for clase in catalogo.listar("clases"):
        perfil = clase.get("perfil", {})
        q = nuevo(entorno)
        q.configurar(cantidad=cantidad, estilo=estilo)
        for pregunta in q.preguntas():
            respuestas = catalogo.obtener("preguntas", pregunta.id)["respuestas"]
            mejor = max(respuestas, key=lambda r, p=perfil, c=clase["id"]: sum(p.get(k, 0) * v for k, v in
                                                                               r.get("perfil", {}).items())
                        + 3 * r.get("pesos", {}).get(f"clases:{c}", 0))
            q.responder(pregunta.id, mejor["id"])
        assert clase["id"] in [r.id for r in q.recomendar_clases()[:2]], clase["id"]


def test_explicar_la_raza_la_clase_y_el_alineamiento(entorno):
    _, catalogo = entorno
    q = nuevo(entorno)
    q.responder("experiencia", "nunca")  # +3 directo al guerrero
    q.responder("pelea_bar", "unirse")  # combate 3, orden −1
    q.responder("lapiz", "clavar")  # combate 2, astucia 1; moral −2, orden −1
    q.responder("templo", "vela")  # fe 3
    motivos = q.explicar("clases", "guerrero")
    assert motivos[0].pregunta in ("Antes de empezar", "Pelea en el bar")
    assert all(m.puntos != 0 for m in motivos)
    directo = next(m for m in motivos if m.pregunta == "Antes de empezar")
    assert directo.puntos == pytest.approx(15) and "+3 directo" in directo.detalle
    fe = next(m for m in q.explicar("clases", "guerrero") if m.pregunta == "El templo")
    assert fe.puntos < 0  # la fe no le pega a un guerrero: baja la afinidad
    assert {m.pregunta for m in q.explicar_alineamiento()} == {"Pelea en el bar", "El lápiz"}
    assert q.totales_alineamiento() == {"orden": -2, "moral": -2}
    assert q.alineamiento() == "Caótico malvado"
