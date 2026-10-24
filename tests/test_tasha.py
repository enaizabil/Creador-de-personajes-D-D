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


def _con_subclase(entorno, subclase, nivel, semilla="sub"):
    sistema, catalogo = entorno
    clase = catalogo.obtener("subclases", subclase)["clase"]
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    rng = random.Random(f"{semilla}{subclase}")
    for pregunta in q.preguntas():
        q.responder(pregunta.id, rng.choice(pregunta.respuestas).id)
    q._mejor_subclase = lambda _clase=None: subclase
    q.generar(nivel=nivel, raza="humano", subraza="humano_estandar", clase=clase)
    return q


def test_subclases_de_tasha_sin_avisos_a_cualquier_nivel(entorno):
    _, catalogo = entorno
    subclases = [s["id"] for s in catalogo.listar("subclases") if catalogo.origen("subclases", s["id"]) == "tasha-2020"]
    assert subclases
    for subclase in subclases:
        for nivel in (3, 6, 10, 14, 20):
            q = _con_subclase(entorno, subclase, nivel)
            a = q.asistente
            assert a.personaje.clases[0].subclase == subclase
            faltan = [f for p in a.pasos() if p.id not in ("resumen", "detalles") for f in a.faltan(p.id)]
            assert not faltan and not a.ficha().avisos, (subclase, nivel, faltan, a.ficha().avisos)


def test_el_genio_amplia_la_lista_segun_su_tipo(entorno):
    sistema, catalogo = entorno
    q = _con_subclase(entorno, "el_genio", 6)
    pj = q.personaje
    clave = next(c for c in pj.elecciones if c.endswith("tipo_de_genio"))
    pj.elecciones[clave] = ["dao"]
    plan = next(p for p in q.asistente.planes_conjuros() if p.clase_id == "brujo")
    disponibles = {i for ids in plan.disponibles.values() for i, _ in ids}
    assert {"santuario", "detectar_el_bien_y_el_mal", "crecimiento_espinoso"} <= disponibles
    assert "manos_ardientes" not in disponibles  # es del ifrit, y no está en la lista del brujo
    assert "contundente" in sistema.calcular(pj, catalogo).resistencias


def test_dominios_de_tasha(entorno):
    sistema, catalogo = entorno
    crepusculo = sistema.calcular(_con_subclase(entorno, "dominio_del_crepusculo", 3).personaje, catalogo)
    assert crepusculo.sentidos["Visión en la Oscuridad"] == 300
    # Los conjuros de dominio van siempre preparados, aunque no sean de la lista del clérigo (Heroísmo).
    paz = _con_subclase(entorno, "dominio_de_la_paz", 5)
    plan = next(p for p in paz.asistente.planes_conjuros() if p.clase_id == "clerigo")
    assert "heroismo" not in {i for ids in plan.disponibles.values() for i, _ in ids}
    preparados = sistema.calcular(paz.personaje, catalogo).lanzadores[0].siempre_preparados
    nombres = {catalogo.obtener("conjuros", i)["nombre"] for i in ("heroismo", "santuario", "recado", "senal_de_esperanza")}
    assert nombres <= {n for lista in preparados.values() for n in lista}


def test_circulos_del_druida_de_tasha(entorno):
    sistema, catalogo = entorno
    esporas = sistema.calcular(_con_subclase(entorno, "circulo_de_esporas", 14).personaje, catalogo)
    assert {"cegado", "ensordecido", "asustado", "envenenado"} <= set(esporas.inmunidades)
    estrellas = sistema.calcular(_con_subclase(entorno, "circulo_de_las_estrellas", 2).personaje, catalogo)
    preparados = {n for lista in estrellas.lanzadores[0].siempre_preparados.values() for n in lista}
    assert {catalogo.obtener("conjuros", i)["nombre"] for i in ("guia", "saeta_guia")} <= preparados
    assert not estrellas.avisos


def test_arquetipos_del_explorador_de_tasha(entorno):
    sistema, catalogo = entorno
    q = _con_subclase(entorno, "guardian_del_enjambre", 5)
    ficha = sistema.calcular(q.personaje, catalogo)
    preparados = {n for lista in ficha.lanzadores[0].siempre_preparados.values() for n in lista}
    assert {catalogo.obtener("conjuros", i)["nombre"] for i in ("mano_de_mago", "fuego_feerico", "telarana")} <= preparados
    # Los del arquetipo no cuentan para los conocidos: el explorador 5 sigue eligiendo sus 4.
    plan = next(p for p in q.asistente.planes_conjuros() if p.clase_id == "explorador")
    assert plan.limite_conjuros == 4 and len(q.personaje.conjuros["explorador"]) == 4
    vagabundo = _con_subclase(entorno, "vagabundo_feerico", 3).personaje
    assert next(v for k, v in vagabundo.elecciones.items() if k.endswith("encanto_sobrenatural"))[0] in (
        "engano", "interpretacion", "persuasion")


def test_arquetipos_del_guerrero_de_tasha(entorno):
    sistema, catalogo = entorno
    for semilla in ("a", "b", "c", "d"):  # a nivel 3, nunca las runas de nivel 7 (Colina, Tormenta)
        pj = _con_subclase(entorno, "caballero_runico", 3, semilla).personaje
        runas = pj.elecciones["subclase:caballero_runico:3/runas"]
        assert len(runas) == 2 and not set(runas) & {"runa_de_colina", "runa_de_tormenta"}, runas
    q = _con_subclase(entorno, "caballero_runico", 15)
    conocidas = [r for k, v in q.personaje.elecciones.items() if "caballero_runico" in k for r in v if r.startswith("runa_")]
    assert len(set(conocidas)) == 5
    rasgos = {r.nombre: r for r in sistema.calcular(q.personaje, catalogo).rasgos}
    assert all(rasgos[catalogo.obtener("opciones", r)["nombre"]].usos == 2 for r in conocidas)  # Maestro de las Runas
    # Las runas van juntas en una sola pregunta concreta al crear a nivel alto.
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    q.responder_subida("c:subclase_de:guerrero", ["caballero_runico"])
    preguntas = {p.id: p for p in q.preguntas_de_historia(15, raza="humano", subraza="humano_estandar", clase="guerrero")}
    assert preguntas["c:subclase:caballero_runico:3/runas"].elegir == 5
    psionico = sistema.calcular(_con_subclase(entorno, "guerrero_psionico", 10).personaje, catalogo)
    assert "psíquico" in psionico.resistencias
