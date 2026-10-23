"""Rasgos de niveles altos (6-20) sobre los paquetes reales: auras, Secretos Mágicos, arcanum, usos ilimitados…"""
import pytest

from creador.entorno import abrir_catalogo
from creador.nucleo.personaje import EntradaClase, Personaje
from creador.nucleo.rutas import directorio_datos_integrados
from creador.sistemas.dnd5e_2014 import motor

PAQUETES = ["srd-5.1", "phb-2014", "dmg-2014"]


@pytest.fixture(scope="module")
def real():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    assert errores == []
    return sistema, catalogo


def personaje(clase, nivel, subclase=None, **base):
    caracteristicas = {"fue": 15, "des": 14, "con": 13, "int": 12, "sab": 10, "car": 8, **base}
    return Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, raza="humano", subraza="humano_estandar",
                     metodo_caracteristicas="manual", caracteristicas_base=caracteristicas,
                     clases=[EntradaClase(clase, nivel, subclase)])


def resolver_todo(sistema, pj, catalogo):
    for _ in range(12):
        pendientes = sistema.elecciones_pendientes(pj, catalogo)
        if not pendientes:
            return
        for p in pendientes:
            libres = [o.id for o in p.opciones if o.id not in p.seleccion]
            pj.elecciones[p.clave] = p.seleccion + libres[:p.faltan]


def ficha(real, pj):
    sistema, catalogo = real
    resolver_todo(sistema, pj, catalogo)
    return sistema.calcular(pj, catalogo)


def rasgo(f, nombre):
    return next(r for r in f.rasgos if r.nombre == nombre)


def test_aura_de_proteccion_suma_el_carisma_a_todas_las_salvaciones(real):
    pj = personaje("paladin", 5, "juramento_de_entrega", car=15)  # 16 con el humano: +3
    antes = ficha(real, pj).salvaciones
    pj.clases[0].nivel = 6
    despues = ficha(real, pj).salvaciones
    assert all(despues[c].valor == antes[c].valor + 3 for c in antes)


def test_aura_de_proteccion_minimo_mas_uno(real):
    pj = personaje("paladin", 6, "juramento_de_entrega", car=7)  # 8: −1, pero el aura da al menos +1
    f = ficha(real, pj)
    assert f.salvaciones["fue"].valor == f.caracteristicas["fue"].modificador + 1


def test_furia_ilimitada_y_campeon_primordial(real):
    pj = personaje("barbaro", 19, "senda_del_berserker")
    f19 = ficha(real, pj)
    assert rasgo(f19, "Furia").usos == 6
    pj.clases[0].nivel = 20
    f20 = ficha(real, pj)
    furia = rasgo(f20, "Furia")
    assert furia.usos is None and not furia.recarga
    for car in ("fue", "con"):
        assert f20.caracteristicas[car].puntuacion == min(24, f19.caracteristicas[car].puntuacion + 4)


def test_secretos_magicos_ocupan_plazas_de_conocidos(real):
    sistema, catalogo = real
    pj = personaje("bardo", 10, "colegio_del_valor", car=15)
    resolver_todo(sistema, pj, catalogo)
    secretos = pj.elecciones["clase:bardo:10/secretos_magicos_10"]
    assert len(secretos) == 2
    efectos = [a.efecto for a in sistema.resolver(pj, catalogo).aplicados if a.tipo == "conjuro"]
    assert motor.conocidos_por_efectos(efectos) == {"bardo": 2}
    mods = {c: v.modificador for c, v in sistema.calcular(pj, catalogo).caracteristicas.items()}
    plan = motor.planes_de_conjuros(pj, catalogo, mods, motor.conocidos_por_efectos(efectos))[0]
    assert plan.limite_conjuros == 14 - 2
    lanzador = sistema.calcular(pj, catalogo).lanzadores[0]
    nombres = {n for ns in lanzador.siempre_preparados.values() for n in ns}
    assert {catalogo.obtener("conjuros", i)["nombre"] for i in secretos} <= nombres
    # 13 conjuros de bardo elegidos a mano: uno de más.
    pj.conjuros["bardo"] = [c["id"] for c in catalogo.listar("conjuros", {"listas": "bardo", "nivel": 1})][:13]
    assert any("máximo 12" in a for a in sistema.calcular(pj, catalogo).avisos)


def test_secretos_magicos_adicionales_no_ocupan_plazas(real):
    sistema, catalogo = real
    pj = personaje("bardo", 6, "colegio_del_conocimiento")
    resolver_todo(sistema, pj, catalogo)
    efectos = [a.efecto for a in sistema.resolver(pj, catalogo).aplicados if a.tipo == "conjuro"]
    assert motor.conocidos_por_efectos(efectos) == {}


def test_arcanum_mistico_de_nivel_6_a_9(real):
    pj = personaje("brujo", 17, "el_infernal")
    lanzador = ficha(real, pj).lanzadores[0]
    assert {6, 7, 8, 9} <= set(lanzador.siempre_preparados)
    assert lanzador.nivel_maximo == 5  # los espacios de pacto no pasan de nivel 5


def test_conjuros_caracteristicos_y_maestria_nombran_el_conjuro(real):
    sistema, catalogo = real
    pj = personaje("mago", 20, "escuela_de_evocacion")
    f = ficha(real, pj)
    caracteristicos = pj.elecciones["clase:mago:20/conjuros_caracteristicos"]
    nombres = [catalogo.obtener("conjuros", i)["nombre"] for i in caracteristicos]
    resumenes = [r.resumen for r in f.rasgos if r.nombre == "Conjuro Característico"]
    assert sorted(r.split(":")[0] for r in resumenes) == sorted(nombres)
    assert set(nombres) <= set(f.lanzadores[0].siempre_preparados[3])
    maestria = rasgo(f, "Maestría sobre Conjuros (nivel 1)")
    elegido = pj.elecciones["clase:mago:18/maestria_conjuros_1"][0]
    assert maestria.resumen.startswith(catalogo.obtener("conjuros", elegido)["nombre"])


def test_movimiento_sin_armadura_del_monje_hasta_30_pies(real):
    pj = personaje("monje", 18, "camino_de_la_mano_abierta")
    assert ficha(real, pj).velocidades["caminar"] == 30 + 30
    pj.clases[0].nivel = 14
    assert ficha(real, pj).velocidades["caminar"] == 30 + 25


def test_alma_diamantina_da_todas_las_salvaciones(real):
    f = ficha(real, personaje("monje", 14, "camino_de_la_mano_abierta"))
    assert all(t.competente for t in f.salvaciones.values())


def test_explorador_amplia_enemigos_y_terrenos(real):
    sistema, catalogo = real
    pj = personaje("explorador", 14, "cazador")
    resolver_todo(sistema, pj, catalogo)
    claves = set(pj.elecciones)
    for clave in ("clase:explorador:6/enemigo_predilecto_nivel_6", "clase:explorador:14/enemigo_predilecto_nivel_14",
                  "clase:explorador:6/terreno_predilecto_nivel_6", "clase:explorador:10/terreno_predilecto_nivel_10",
                  "subclase:cazador:7/tacticas_defensivas", "subclase:cazador:11/ataque_multiple"):
        assert clave in claves
    # Elegir tres veces el mismo enemigo se avisa; con enemigos distintos, no.
    assert any("Aberraciones está elegida más de una vez" in a for a in sistema.calcular(pj, catalogo).avisos)
    pj.elecciones["clase:explorador:6/enemigo_predilecto_nivel_6"] = ["enemigo_dragones"]
    pj.elecciones["clase:explorador:14/enemigo_predilecto_nivel_14"] = ["enemigo_gigantes"]
    pj.elecciones["clase:explorador:6/terreno_predilecto_nivel_6"] = ["terreno_bosque"]
    pj.elecciones["clase:explorador:10/terreno_predilecto_nivel_10"] = ["terreno_costa"]
    resolver_todo(sistema, pj, catalogo)
    assert not any("más de una vez" in a for a in sistema.calcular(pj, catalogo).avisos)


def test_forma_salvaje_ilimitada_a_nivel_20(real):
    f = ficha(real, personaje("druida", 20, "circulo_de_la_tierra"))
    assert rasgo(f, "Forma Salvaje").usos is None
    # Los conjuros de círculo de nivel 7 y 9 del terreno elegido (el primero: ártico).
    siempre = {n for ns in f.lanzadores[0].siempre_preparados.values() for n in ns}
    assert {"Tormenta de hielo", "Cono de frío"} <= siempre


def test_disciplinas_elementales_por_nivel(real):
    sistema, catalogo = real
    pj = personaje("monje", 17, "camino_de_los_cuatro_elementos")
    resolver_todo(sistema, pj, catalogo)
    eleccion = {e.clave: e for e in sistema.resolver(pj, catalogo).elecciones}
    a_6 = {o.id for o in eleccion["subclase:camino_de_los_cuatro_elementos:6/disciplina_elemental_6"].opciones}
    a_17 = {o.id for o in eleccion["subclase:camino_de_los_cuatro_elementos:17/disciplina_elemental_17"].opciones}
    assert "gong_de_la_cumbre" in a_6 and "llamas_del_fenix" not in a_6 and "aliento_del_invierno" not in a_6
    assert {"gong_de_la_cumbre", "llamas_del_fenix", "aliento_del_invierno"} <= a_17


def test_piedra_del_transmutador_aplica_su_beneficio(real):
    sistema, catalogo = real
    pj = personaje("mago", 6, "escuela_de_transmutacion")
    resolver_todo(sistema, pj, catalogo)
    pj.elecciones["subclase:escuela_de_transmutacion:6/piedra_del_transmutador"] = ["constitucion"]
    assert sistema.calcular(pj, catalogo).salvaciones["con"].competente


def test_patrones_del_phb_amplian_la_lista_a_niveles_4_y_5(real):
    sistema, catalogo = real
    pj = personaje("brujo", 9, "el_archihada")
    resolver_todo(sistema, pj, catalogo)
    mods = {c: v.modificador for c, v in sistema.calcular(pj, catalogo).caracteristicas.items()}
    plan = motor.planes_de_conjuros(pj, catalogo, mods)[0]
    ids = {i for nivel in plan.disponibles.values() for i, _ in nivel}
    assert {"invisibilidad_mejorada", "apariencia", "dominar_persona"} <= ids


def test_dominio_del_phb_con_conjuros_de_nivel_alto(real):
    f = ficha(real, personaje("clerigo", 9, "dominio_de_la_tempestad"))
    siempre = {n for ns in f.lanzadores[0].siempre_preparados.values() for n in ns}
    assert {"Controlar agua", "Tormenta de hielo", "Ola destructora", "Plaga de insectos"} <= siempre
    assert rasgo(f, "Golpe Divino").resumen.endswith("1d8 de daño de trueno")


def test_conjuros_gratis_en_el_libro(real):
    sistema, catalogo = real
    pj = personaje("mago", 6, "escuela_de_nigromancia")
    resolver_todo(sistema, pj, catalogo)
    libro = [c["id"] for c in catalogo.listar("conjuros", {"listas": "mago", "nivel": 1})][:16]  # 6 + 2 × 5: lleno
    pj.conjuros["mago"] = libro
    pj.preparados["mago"] = ["animar_a_los_muertos", *libro[:3]]
    f = sistema.calcular(pj, catalogo)
    lanzador = f.lanzadores[0]
    assert "Animar a los muertos" in lanzador.libro[3]  # en el libro sin ocupar plaza
    assert "Animar a los muertos" in lanzador.conjuros[3]  # y se puede preparar
    assert not any("libro" in a for a in f.avisos), f.avisos
    assert "Animar a los muertos" not in {n for ns in lanzador.siempre_preparados.values() for n in ns}


def test_maestria_avisa_si_el_conjuro_no_esta_en_el_libro(real):
    sistema, catalogo = real
    pj = personaje("mago", 18, "escuela_de_evocacion")
    resolver_todo(sistema, pj, catalogo)
    elegido = pj.elecciones["clase:mago:18/maestria_conjuros_1"][0]
    pj.conjuros["mago"] = []
    assert any("Maestría sobre Conjuros (nivel 1)" in a and "no está en tu libro" in a
               for a in sistema.calcular(pj, catalogo).avisos)
    pj.conjuros["mago"] = [elegido]
    assert not any("Maestría sobre Conjuros (nivel 1)" in a for a in sistema.calcular(pj, catalogo).avisos)


def test_maestro_en_armaduras_medias_quita_la_desventaja_de_sigilo(real):
    sistema, catalogo = real
    from creador.nucleo.personaje import ObjetoInventario
    pj = personaje("guerrero", 4)
    pj.equipo = [ObjetoInventario("media_armadura", equipado=True)]
    resolver_todo(sistema, pj, catalogo)
    assert sistema.calcular(pj, catalogo).habilidades["sigilo"].notas.startswith("Desventaja")
    pj.elecciones["clase:guerrero:4/mejora"] = ["dote"]
    pj.elecciones["clase:guerrero:4/mejora=dote/dote"] = ["maestro_en_armaduras_medias"]
    f = sistema.calcular(pj, catalogo)
    assert not f.habilidades["sigilo"].notas, f.avisos


def test_criatura_pequena_con_arma_pesada(real):
    sistema, catalogo = real
    from creador.nucleo.personaje import ObjetoInventario
    pj = personaje("guerrero", 1)
    pj.raza, pj.subraza = "mediano", "mediano_piesligeros"
    pj.equipo = [ObjetoInventario("gran_hacha" if catalogo.obtener("objetos", "gran_hacha") else "hacha_a_dos_manos")]
    resolver_todo(sistema, pj, catalogo)
    ataque = sistema.calcular(pj, catalogo).ataques[0]
    assert "criatura Pequeña" in ataque.notas
