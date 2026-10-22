"""Funciones del motor que necesita el contenido real del PHB."""
from ayudas import EntradaClase, ObjetoInventario, nuevo_personaje

BASE_PALADIN = {"fue": 15, "des": 10, "con": 13, "int": 8, "sab": 12, "car": 16}
BASE_MONJE = {"fue": 10, "des": 16, "con": 13, "int": 8, "sab": 16, "car": 10}


def manual(base, **campos):
    return nuevo_personaje(metodo_caracteristicas="manual", caracteristicas_base=dict(base), **campos)


def rasgo(ficha, nombre):
    return next(r for r in ficha.rasgos if r.nombre == nombre)


def test_rasgos_con_valores_calculados_y_usos(sistema, catalogo):
    ficha = sistema.calcular(manual(BASE_PALADIN, clases=[EntradaClase("paladin", 3)]), catalogo)
    assert rasgo(ficha, "Imponer las Manos").resumen == "Reserva de 15 PG"
    sentido = rasgo(ficha, "Sentido Divino")
    assert (sentido.usos, sentido.recarga) == (4, "largo")


def test_opciones_de_clase_filtradas_y_aplicadas(sistema, catalogo):
    personaje = manual(BASE_PALADIN, clases=[EntradaClase("paladin", 2)],
                       equipo=[ObjetoInventario("cota_de_mallas", equipado=True)])
    (estilo,) = [p for p in sistema.elecciones_pendientes(personaje, catalogo) if p.nombre == "Estilo de Combate"]
    assert [o.id for o in estilo.opciones] == ["defensa"]  # «arqueria» no es de paladín

    personaje.elecciones[estilo.clave] = ["defensa"]
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.ca == 17
    assert "Estilo de Combate: Defensa" in [r.nombre for r in ficha.rasgos]


def test_conjuros_siempre_preparados_no_cuentan(sistema, catalogo):
    personaje = manual(BASE_PALADIN, clases=[EntradaClase("paladin", 3, subclase="venganza")])
    (paladin,) = sistema.calcular(personaje, catalogo).lanzadores
    assert paladin.siempre_preparados == {1: ["Marca del Cazador", "Perdición"]}
    assert paladin.conjuros == {}


def test_conjuros_adicionales_de_subclase(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("brujo", 1, subclase="infernal")],
                                conjuros={"brujo": ["manos_ardientes", "proyectil_magico"]})
    texto = "\n".join(sistema.calcular(personaje, catalogo).avisos)
    assert "Manos Ardientes no está" not in texto
    assert "Proyectil mágico no está en la lista de conjuros de Brujo" in texto


def test_conjuros_raciales_por_nivel(sistema, catalogo):
    tiflin = nuevo_personaje(raza="tiflin", clases=[EntradaClase("guerrero", 2)])
    assert sistema.calcular(tiflin, catalogo).conjuros_innatos == ["Taumaturgia (Carisma)"]
    tiflin.clases[0].nivel = 3
    assert sistema.calcular(tiflin, catalogo).conjuros_innatos == ["Taumaturgia (Carisma)", "Reprensión Infernal (Carisma)"]


def test_monje_defensa_artes_marciales_y_ataque_sin_armas(sistema, catalogo):
    personaje = manual(BASE_MONJE, clases=[EntradaClase("monje", 1)],
                       equipo=[ObjetoInventario("espada_corta"), ObjetoInventario("baston"), ObjetoInventario("espada_larga")])
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.ca == 16  # 10 + DES 3 + SAB 3
    ataques = {a.nombre: (a.bonificador, a.dano) for a in ficha.ataques}
    assert ataques["Bastón"] == (5, "1d6+3")  # arma de monje: usa DES
    assert ataques["Espada corta"] == (5, "1d6+3")
    assert ataques["Espada larga"] == (0, "1d8")  # ni arma de monje ni competencia
    assert ataques["Ataque sin armas"] == (5, "1d4+3")
    assert rasgo(ficha, "Artes Marciales").resumen == "Dado de artes marciales 1d4"

    personaje.clases[0].nivel = 5
    ficha = sistema.calcular(personaje, catalogo)
    assert {a.nombre: a.dano for a in ficha.ataques}["Ataque sin armas"] == "1d6+3"
    assert rasgo(ficha, "Artes Marciales").resumen == "Dado de artes marciales 1d6"

    personaje.equipo.append(ObjetoInventario("escudo", equipado=True))
    assert sistema.calcular(personaje, catalogo).ca == 15  # sin Defensa sin Armadura: 10 + DES 3 + escudo 2


def dote_en_nivel_4(clase, dote, base, **campos):
    clave = f"clase:{clase}:4/mejora"
    return manual(base, clases=[EntradaClase(clase, 4)], elecciones={
        clave: ["dote"], f"{clave}=dote/dote": [dote]}, **campos)


def test_prerrequisitos_de_dotes(sistema, catalogo):
    texto = "\n".join(sistema.calcular(dote_en_nivel_4("mago", "maestro_armadura_media", BASE_MONJE), catalogo).avisos)
    assert "Dote Maestro en armaduras medias: no cumple el prerrequisito (competencia con Armaduras medias)" in texto
    texto = "\n".join(sistema.calcular(dote_en_nivel_4("mago", "apresador", BASE_MONJE), catalogo).avisos)
    assert "Dote Apresador: no cumple el prerrequisito (FUE 13)" in texto
    texto = "\n".join(sistema.calcular(dote_en_nivel_4("guerrero", "apresador", BASE_PALADIN), catalogo).avisos)
    assert "Apresador" not in texto


def test_maestro_en_armaduras_medias(sistema, catalogo):
    equipo = [ObjetoInventario("cota_de_escamas", equipado=True)]
    sin_dote = manual(BASE_MONJE, clases=[EntradaClase("guerrero", 4)], equipo=equipo)
    assert sistema.calcular(sin_dote, catalogo).ca == 16  # 14 + DES (máx. 2)
    con_dote = dote_en_nivel_4("guerrero", "maestro_armadura_media", BASE_MONJE, equipo=equipo)
    assert sistema.calcular(con_dote, catalogo).ca == 17  # 14 + DES (máx. 3)


def test_pasivas(sistema, catalogo):
    ficha = sistema.calcular(dote_en_nivel_4("guerrero", "observador", BASE_PALADIN), catalogo)
    assert ficha.pasivas == {"percepcion": 16, "perspicacia": 11, "investigacion": 14}
    assert ficha.percepcion_pasiva == 16


def test_requisitos_de_multiclase(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero", 1), EntradaClase("monje", 1)])
    texto = "\n".join(sistema.calcular(personaje, catalogo).avisos)
    assert "Multiclase: Monje requiere DES 13 y SAB 13" in texto
    assert "Multiclase: Guerrero" not in texto
