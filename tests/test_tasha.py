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
    assert {c["id"] for c in catalogo.listar("conjuros") if c["nivel"] == 0 and "artifice" in c["listas"]
            and catalogo.origen("conjuros", c["id"]) == "tasha-2020"} == {
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


def test_origenes_del_hechicero_de_tasha(entorno):
    sistema, catalogo = entorno
    q = _con_subclase(entorno, "mente_aberrante", 6)
    ficha = sistema.calcular(q.personaje, catalogo)
    assert "psíquico" in ficha.resistencias
    preparados = {n for lista in ficha.lanzadores[0].siempre_preparados.values() for n in lista}
    assert {catalogo.obtener("conjuros", i)["nombre"] for i in ("brazos_de_hadar", "recado")} <= preparados
    assert catalogo.obtener("conjuros", "astilla_mental")["nombre"] not in preparados  # así en el texto de Tasha
    # No cuentan para los conocidos: el hechicero 6 sigue eligiendo sus 7 conjuros y 5 trucos.
    plan = next(p for p in q.asistente.planes_conjuros() if p.clase_id == "hechicero")
    conocidos = q.personaje.conjuros["hechicero"]
    trucos = [i for i in conocidos if catalogo.obtener("conjuros", i)["nivel"] == 0]
    assert len(trucos) == plan.limite_trucos and len(conocidos) - len(trucos) == plan.limite_conjuros


def test_tradiciones_del_mago_de_tasha(entorno):
    sistema, catalogo = entorno
    q = _con_subclase(entorno, "canto_de_la_hoja", 6)
    pj = q.personaje
    arma = next(v for k, v in pj.elecciones.items() if k.endswith("arma_de_la_cancion"))[0]
    assert "a_dos_manos" not in catalogo.obtener("objetos", arma)["arma"].get("propiedades", [])
    ficha = sistema.calcular(pj, catalogo)
    assert "Interpretación" in [h.nombre for h in ficha.habilidades.values() if h.competente]
    # El Ataque Adicional del Canto de la Hoja no se acumula con otro (multiclase): aquí, uno.
    assert [r.nombre for r in ficha.rasgos].count("Ataque Adicional") == 1
    assert not sistema.calcular(_con_subclase(entorno, "orden_de_los_escribas", 14).personaje, catalogo).avisos


def test_tradiciones_del_monje_de_tasha(entorno):
    sistema, catalogo = entorno
    ficha = sistema.calcular(_con_subclase(entorno, "camino_de_la_misericordia", 5).personaje, catalogo)
    competentes = {h.nombre for h in ficha.habilidades.values() if h.competente}
    assert {"Perspicacia", "Medicina"} <= competentes
    rasgos = {r.nombre: r for r in ficha.rasgos}
    assert "1d6" in rasgos["Mano de Sanación"].resumen  # el dado de Artes Marciales a nivel 5
    astral = sistema.calcular(_con_subclase(entorno, "camino_del_yo_astral", 11).personaje, catalogo)
    assert "1d8" in {r.nombre: r for r in astral.rasgos}["Cuerpo del Yo Astral"].resumen
    brazos = next(a for a in astral.ataques if a.nombre == "Ataque sin armas (Brazos del Yo Astral)")
    mejor = max(astral.caracteristicas[c].modificador for c in ("fue", "des", "sab"))
    assert brazos.tipo_dano == "fuerza" and brazos.dano.startswith("1d8") and brazos.bonificador == mejor + 4


def test_juramentos_del_paladin_de_tasha(entorno):
    sistema, catalogo = entorno
    vigilante = sistema.calcular(_con_subclase(entorno, "juramento_de_los_vigilantes", 7).personaje, catalogo)
    # Aura del Centinela: la iniciativa suma el bonificador por competencia (+3 a nivel 7).
    assert vigilante.iniciativa == vigilante.caracteristicas["des"].modificador + 3
    gloria = _con_subclase(entorno, "juramento_de_gloria", 7)
    assert sistema.calcular(gloria.personaje, catalogo).velocidades["caminar"] == 40  # Aura de Presteza: 30 + 10


def test_arquetipos_del_picaro_de_tasha(entorno):
    sistema, catalogo = entorno
    fantasma = {r.nombre: r for r in sistema.calcular(_con_subclase(entorno, "fantasma", 9).personaje, catalogo).rasgos}
    assert "3d6" in fantasma["Lamentos de la Tumba"].resumen  # mitad de los 5d6 de Ataque Furtivo, hacia arriba
    cuchillo = {r.nombre: r for r in sistema.calcular(_con_subclase(entorno, "cuchillo_del_alma", 5).personaje,
                                                      catalogo).rasgos}
    assert cuchillo["Poder Psiónico"].usos == 6 and "(d8)" in cuchillo["Poder Psiónico"].resumen
    ataques = {a.nombre: a for a in sistema.calcular(_con_subclase(entorno, "cuchillo_del_alma", 5).personaje,
                                                      catalogo).ataques}
    assert ataques["Espada Psíquica"].tipo_dano == "psíquico" and ataques["Espada Psíquica"].dano.startswith("1d6")


def test_al_subir_cambia_la_competencia_que_la_subclase_repite(entorno):
    sistema, catalogo = entorno
    q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
    for pregunta in q.preguntas():
        q.responder(pregunta.id, pregunta.respuestas[0].id)
    q.generar(nivel=2, raza="humano", subraza="humano_estandar", clase="monje")
    clave = "clase:monje:inicial/habilidades"
    if "perspicacia" not in q.personaje.elecciones[clave]:  # el caso: eligió Perspicacia a nivel 1
        q.personaje.elecciones[clave] = q.personaje.elecciones[clave][:-1] + ["perspicacia"]
    q.responder_subida("c:subclase_de:monje", ["camino_de_la_misericordia"])
    q.subir_nivel(1)
    assert "perspicacia" not in q.personaje.elecciones[clave]
    assert not [a for a in sistema.calcular(q.personaje, catalogo).avisos if "repetida" in a]


def _con_rasgos_opcionales(entorno, clase, nivel, subclase=None, **desactivados):
    sistema, catalogo = entorno
    pj = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES)
    pj.reglas_opcionales["rasgos_opcionales"] = True
    pj.reglas_opcionales.update({f"opcional:{r}": False for r in desactivados})
    q = sistema.crear_cuestionario(pj, catalogo)
    for pregunta in q.preguntas():
        q.responder(pregunta.id, pregunta.respuestas[0].id)
    if subclase:
        q._mejor_subclase = lambda _clase=None: subclase
    q.generar(nivel=nivel, raza="humano", subraza="humano_estandar", clase=clase)
    return q


def test_rasgos_opcionales_sustituyen_y_se_desactivan_uno_a_uno(entorno):
    sistema, catalogo = entorno
    q = _con_rasgos_opcionales(entorno, "explorador", 6)
    elecciones = {e.clave.split("/")[-1] for e in sistema.resolver(q.personaje, catalogo).elecciones}
    assert not elecciones & {"terreno_predilecto", "enemigo_predilecto", "terreno_predilecto_nivel_6"}
    assert {"astuto_pericia", "astuto_idiomas"} <= elecciones
    ficha = sistema.calcular(q.personaje, catalogo)
    assert ficha.velocidades == {"caminar": 35, "trepar": 35, "nadar": 35}
    assert {"Enemigo Favorecido", "Explorador Hábil: Errante"} <= {r.nombre for r in ficha.rasgos}
    assert not ficha.avisos, ficha.avisos
    # Desactivado Explorador Hábil, vuelve Explorador Nato (y Enemigo Favorecido sigue).
    q = _con_rasgos_opcionales(entorno, "explorador", 6, explorador_habil=True)
    elecciones = {e.clave.split("/")[-1] for e in sistema.resolver(q.personaje, catalogo).elecciones}
    assert "terreno_predilecto" in elecciones and "enemigo_predilecto" not in elecciones
    # Golpes Bendecidos en lugar del Golpe Divino del dominio.
    q = _con_rasgos_opcionales(entorno, "clerigo", 8, "dominio_de_la_vida")
    nombres = {r.nombre for r in sistema.calcular(q.personaje, catalogo).rasgos}
    assert "Golpes Bendecidos" in nombres and "Golpe Divino" not in nombres


def test_opciones_de_tasha_solo_con_su_rasgo_opcional(entorno):
    sistema, catalogo = entorno
    sin = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES)
    con = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, reglas_opcionales={"rasgos_opcionales": True})
    for clase, esperado in (("guerrero", "lucha_a_ciegas"), ("brujo", "pacto_del_talisman")):
        sin.clases = [EntradaClase(clase, 5)]
        con.clases = [EntradaClase(clase, 5)]
        filtro = {"grupo": "estilo_combate" if clase == "guerrero" else "pacto", "clases": clase}
        assert esperado not in {o.id for o in sistema.opciones_desde("opciones", filtro, catalogo, sin)}
        assert esperado in {o.id for o in sistema.opciones_desde("opciones", filtro, catalogo, con)}


def test_lista_de_conjuros_del_artifice(entorno):
    sistema, catalogo = entorno
    lista = [c for c in catalogo.listar("conjuros") if "artifice" in c["listas"]]
    assert {n: sum(1 for c in lista if c["nivel"] == n) for n in range(6)} == {0: 19, 1: 15, 2: 19, 3: 12, 4: 10, 5: 5}
    assert all(c["listas"].count("artifice") == 1 for c in lista)  # «modifica» no repite la lista que ya traía
    # Iniciado Artífice elige ya entre toda la lista.
    trucos = sistema.opciones_desde("conjuros", {"listas": "artifice", "nivel": 0}, catalogo)
    assert len(trucos) == 19


def test_espacios_del_artifice_redondean_hacia_arriba(entorno):
    sistema, catalogo = entorno

    def espacios(*clases):
        pj = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, metodo_caracteristicas="manual",
                       caracteristicas_base={"fue": 10, "des": 14, "con": 14, "int": 15, "sab": 10, "car": 13},
                       clases=[EntradaClase(c, n) for c, n in clases])
        return sistema.calcular(pj, catalogo).espacios_conjuro

    assert espacios(("artifice", 1)) == {1: 2}
    assert espacios(("artifice", 5)) == {1: 4, 2: 2}
    assert espacios(("artifice", 20)) == {1: 4, 2: 3, 3: 3, 4: 3, 5: 2}
    # En multiclase suma la mitad de sus niveles redondeando hacia arriba (el paladín, hacia abajo).
    assert espacios(("artifice", 1), ("mago", 1)) == {1: 3}
    assert espacios(("artifice", 3), ("paladin", 3)) == {1: 4, 2: 2}


def test_infusiones_del_artifice(entorno):
    sistema, catalogo = entorno
    de_nivel = {o["id"]: int(o["prerrequisito"]["texto"].split()[1]) for o in catalogo.listar("opciones")
                if o["grupo"] == "infusion" and "prerrequisito" in o}
    assert de_nivel == {"anillo_de_recarga_de_conjuros": 6, "arma_radiante": 6, "armadura_resistente": 6,
                        "botas_del_camino_serpenteante": 6, "escudo_de_repulsion": 6, "yelmo_de_la_alerta": 10,
                        "armadura_de_propulsion_arcana": 14}
    for nivel, total in ((2, 4), (6, 6), (10, 8), (14, 10), (18, 12)):
        for semilla in ("a", "b"):
            q = _con_subclase(entorno, "artillero", nivel, semilla)
            infusiones = [v for c, vs in q.personaje.elecciones.items() if "/infusiones" in c for v in vs]
            assert len(infusiones) == total, (nivel, infusiones)
            assert len(set(infusiones)) == total or "replicar_objeto_magico" in infusiones
            # El cuestionario respeta el nivel que pide cada una (el asistente lo muestra en la descripción).
            assert all(de_nivel.get(i, 0) <= nivel for i in infusiones), (nivel, infusiones)
            assert q._prerrequisito("armadura_de_propulsion_arcana") is (nivel >= 14)


def test_especialistas_del_artifice(entorno):
    sistema, catalogo = entorno
    alquimista = _con_subclase(entorno, "alquimista", 15)
    ficha = sistema.calcular(alquimista.personaje, catalogo)
    assert {"ácido", "veneno"} <= set(ficha.resistencias) and "envenenado" in ficha.inmunidades
    siempre = {n for ns in ficha.lanzadores[0].siempre_preparados.values() for n in ns}
    assert {"Palabra de curación", "Guarda contra la muerte"} <= siempre and "Nube aniquiladora" not in siempre
    armero = _con_subclase(entorno, "armero", 3)
    clave = next(c for c in armero.personaje.elecciones if c.endswith("modelo_de_armadura"))
    armero.personaje.elecciones[clave] = ["infiltrador"]
    ficha = sistema.calcular(armero.personaje, catalogo)
    assert ficha.velocidades["caminar"] == 35
    assert "Modelo de Armadura: Infiltrador" in {r.nombre for r in ficha.rasgos}
    # El arma del modelo sale en los ataques con Inteligencia (si es la mejor) y competencia.
    lanzarrayos = next(a for a in ficha.ataques if a.nombre == "Lanzarrayos")
    mejor = max(ficha.caracteristicas[c].modificador for c in ("des", "int"))
    assert lanzarrayos.bonificador == mejor + 2 and lanzarrayos.tipo_dano == "relámpago"
    assert "Guanteletes de Trueno" not in {a.nombre for a in ficha.ataques}
    herrero = sistema.resolver(_con_subclase(entorno, "herrero_de_batalla", 3).personaje, catalogo)
    assert ("arma", "armas_marciales") in {(a.efecto["categoria"], a.efecto["id"]) for a in herrero.aplicados
                                            if a.tipo == "competencia"}


def test_el_artifice_no_quita_el_mago_a_quien_busca_saber(entorno, monkeypatch):
    """Cada partida saca otras preguntas y respuestas: se mide en varias y cuenta lo que pasa en la mayoría."""
    from collections import Counter

    from creador.sistemas.dnd5e_2014 import cuestionario
    sistema, catalogo = entorno

    def recomendada(*rasgos):
        resultados = Counter()
        for n in range(9):
            monkeypatch.setattr(cuestionario, "nueva_semilla", lambda n=n: f"saber{n}")
            resultados[recomendada_en_una(*rasgos)] += 1
        return resultados.most_common(1)[0][0]

    def recomendada_en_una(*rasgos):
        q = sistema.crear_cuestionario(Personaje(sistema="dnd5e-2014", paquetes=PAQUETES), catalogo)
        for i, pregunta in enumerate(q.preguntas()):
            rasgo = rasgos[i % len(rasgos)]
            vistas = {r.id for r in pregunta.respuestas}  # entre las que ve el jugador
            respuestas = [r for r in catalogo.obtener("preguntas", pregunta.id)["respuestas"] if r["id"] in vistas]
            mejor = max(respuestas, key=lambda r: r.get("perfil", {}).get(rasgo, 0))
            if mejor.get("perfil", {}).get(rasgo):
                q.responder(pregunta.id, mejor["id"])
        return q.recomendar_clases()[0].id

    assert recomendada("saber") == "mago"
    assert recomendada("saber", "arcano") == "mago"
    assert recomendada("saber", "astucia") == "artifice"


def test_perfiles_de_criaturas_calculados_en_el_rasgo(entorno):
    sistema, catalogo = entorno

    def resumen(subclase, nivel, rasgo):
        ficha = sistema.calcular(_con_subclase(entorno, subclase, nivel).personaje, catalogo)
        mod_int = ficha.caracteristicas["int"].modificador
        return {r.nombre: r.resumen for r in ficha.rasgos}[rasgo], mod_int

    texto, mod_int = resumen("herrero_de_batalla", 3, "Defensor de Acero")
    assert f"CA 15, {2 + mod_int + 15} PG" in texto and f"Desgarro con Fuerza +{2 + mod_int}, 1d8+2" in texto
    texto, mod_int = resumen("herrero_de_batalla", 15, "Defensor de Acero")
    assert "CA 17" in texto and f"+{5 + mod_int}, 1d8+5" in texto
    texto, _ = resumen("artillero", 9, "Cañón Sobrenatural")
    assert "45 PG" in texto and "3d8 de fuego" in texto  # Cañón Explosivo


def test_listo_para_la_batalla_ataca_con_inteligencia_con_armas_magicas(entorno):
    sistema, catalogo = entorno
    q = _con_subclase(entorno, "herrero_de_batalla", 3)
    a = q.asistente
    ficha = a.ficha()
    mods = {c: v.modificador for c, v in ficha.caracteristicas.items()}
    assert mods["int"] > max(mods["fue"], mods["des"])  # el modo sencillo sube la INT del artífice
    arma = next(o.id for o in a.personaje.equipo if catalogo.obtener("objetos", o.id)["categoria"] == "arma")
    nombre = catalogo.obtener("objetos", arma)["nombre"]
    normal = next(at for at in ficha.ataques if at.nombre == nombre)
    a.anadir_objeto_magico(arma, 0)
    a.aplicar_equipo()
    magica = next(at for at in a.ficha().ataques if at.nombre == f"{nombre} (mágica)")
    assert magica.bonificador == normal.bonificador - max(mods["fue"], mods["des"]) + mods["int"]


def test_infusiones_que_lleva_el_propio_artifice(entorno):
    sistema, catalogo = entorno
    q = _con_subclase(entorno, "artillero", 10)
    a = q.asistente
    deseadas = ["defensa_mejorada", "armadura_resistente", "canalizador_arcano_mejorado", "arma_mejorada",
                "sirviente_homunculo", "afilador_mental", "arma_retornante", "yelmo_de_la_alerta"]
    for clave in sorted(c for c in a.personaje.elecciones if "/infusiones" in c):
        n = len(a.personaje.elecciones[clave])
        a.personaje.elecciones[clave], deseadas = deseadas[:n], deseadas[n:]
    a.aplicar_equipo()
    antes = a.ficha()
    propias = {i.id: i for i in a.infusiones_propias()}
    assert "sirviente_homunculo" not in propias  # no cambia la ficha
    armadura = propias["defensa_mejorada"].objetos[0][0]
    a.llevar_infusion("defensa_mejorada", True, armadura)
    a.llevar_infusion("canalizador_arcano_mejorado", True)
    ficha = a.ficha()
    assert ficha.ca == antes.ca + 2  # +2 desde nivel 10
    assert ficha.lanzadores[0].ataque == antes.lanzadores[0].ataque + 2
    assert any(o.endswith("+2 (Defensa Mejorada)") for o in ficha.equipo)
    # La misma armadura no admite otra infusión: avisa y la segunda no se aplica.
    a.llevar_infusion("armadura_resistente", True, armadura, "fuego")
    ficha = a.ficha()
    assert "fuego" not in ficha.resistencias and any("Armadura Resistente" in av for av in ficha.avisos)
    a.llevar_infusion("defensa_mejorada", False)
    ficha = a.ficha()
    assert "fuego" in ficha.resistencias and ficha.ca == antes.ca and not ficha.avisos
