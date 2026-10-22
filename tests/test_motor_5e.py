import pytest

from ayudas import EntradaClase, ObjetoInventario, nuevo_personaje
from creador.sistemas.dnd5e_2014 import motor

BASE_BARBARO = {"fue": 15, "des": 14, "con": 16, "int": 8, "sab": 10, "car": 10}


def guerrero_enano():
    return nuevo_personaje(
        nombre="Thorin",
        raza="enano",
        subraza="enano_colinas",
        trasfondo="acolito",
        clases=[EntradaClase("guerrero")],
        elecciones={
            "clase:guerrero:inicial/habilidades": ["atletismo", "percepcion"],
            "clase:guerrero:1/estilo": ["defensa"],
            "trasfondo:acolito/idiomas": ["elfico", "draconico"],
        },
        equipo=[
            ObjetoInventario("cota_de_mallas", equipado=True),
            ObjetoInventario("escudo", equipado=True),
            ObjetoInventario("espada_larga"),
            ObjetoInventario("daga", cantidad=2),
        ],
    )


def test_guerrero_enano_nivel_1_completo(sistema, catalogo):
    ficha = sistema.calcular(guerrero_enano(), catalogo)

    assert ficha.avisos == []
    assert ficha.raza == "Enano de las colinas"
    assert ficha.clase_y_nivel == "Guerrero 1"
    assert {c: v.puntuacion for c, v in ficha.caracteristicas.items()} == {
        "fue": 15, "des": 13, "con": 16, "int": 8, "sab": 13, "car": 10}
    assert ficha.bonificador_competencia == 2
    assert ficha.pg_maximos == 14  # 10 + CON 3 + Dureza enana 1
    assert ficha.dados_golpe == {"d10": 1}
    assert ficha.ca == 19  # cota 16 + escudo 2 + Defensa 1
    assert ficha.iniciativa == 1
    assert ficha.velocidades == {"caminar": 25}
    assert ficha.tamano == "Mediano"

    assert {c: t.valor for c, t in ficha.salvaciones.items() if t.competente} == {"fue": 4, "con": 5}
    habilidades = ficha.habilidades
    assert (habilidades["atletismo"].valor, habilidades["percepcion"].valor) == (4, 3)
    assert (habilidades["perspicacia"].valor, habilidades["religion"].valor) == (3, 1)
    assert habilidades["sigilo"].valor == 1 and "Desventaja" in habilidades["sigilo"].notas
    assert ficha.percepcion_pasiva == 13

    assert ficha.competencias["idiomas"] == ["Común", "Dracónico", "Élfico", "Enano"]
    assert "Armas marciales" in ficha.competencias["armas"]
    ataques = {a.nombre: a for a in ficha.ataques}
    assert (ataques["Espada larga"].bonificador, ataques["Espada larga"].dano) == (4, "1d8+2")
    assert "1d10+2" in ataques["Espada larga"].notas
    assert (ataques["Daga"].bonificador, ataques["Daga"].dano) == (4, "1d4+2")
    assert "Daga (x2)" in ficha.equipo

    assert [r.nombre for r in ficha.rasgos] == [
        "Rasgo enano de prueba", "Estilo de combate: Defensa", "Rasgo de guerrero de prueba"]
    assert ficha.sentidos == {"Visión en la oscuridad": 60}
    assert ficha.resistencias == ["veneno"]


def test_defensa_no_se_aplica_sin_armadura(sistema, catalogo):
    personaje = guerrero_enano()
    personaje.equipo = [ObjetoInventario("escudo", equipado=True)]
    assert sistema.calcular(personaje, catalogo).ca == 13  # 10 + DES 1 + escudo 2


@pytest.mark.parametrize("raza, velocidad", [("elfo", 20), ("enano", 25)])
def test_armadura_pesada_sin_fuerza_reduce_velocidad_salvo_enano(sistema, catalogo, raza, velocidad):
    personaje = nuevo_personaje(raza=raza, metodo_caracteristicas="manual",
                                caracteristicas_base={"fue": 8, "des": 10, "con": 10, "int": 10, "sab": 10, "car": 10},
                                equipo=[ObjetoInventario("cota_de_mallas", equipado=True)])
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.velocidades["caminar"] == velocidad
    assert any("Sin competencia con Cota de mallas" in a for a in ficha.avisos)


def test_mejora_de_caracteristica_y_pg_por_media(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero", nivel=4)], elecciones={
        "clase:guerrero:4/mejora": ["caracteristicas"],
        "clase:guerrero:4/mejora=caracteristicas/puntos": ["fue", "fue"],
    })
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.caracteristicas["fue"].puntuacion == 17
    assert ficha.pg_maximos == 36  # 10+2 y tres niveles de 6+2
    assert ficha.bonificador_competencia == 2


def test_mejora_no_supera_20_salvo_maximo_explicito():
    personaje = nuevo_personaje(metodo_caracteristicas="manual",
                                caracteristicas_base={"fue": 19, "des": 10, "con": 20, "int": 10, "sab": 10, "car": 10})
    mejoras = [
        {"car": "fue", "valor": 2},
        {"car": "con", "valor": 4, "maximo": 24},
        {"car": "con", "valor": 1},
    ]
    valores = motor._puntuaciones(personaje, mejoras)
    assert (valores["fue"], valores["con"]) == (20, 24)


def test_pg_por_tiradas(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero", nivel=3, tiradas_pg=[7, 3])], metodo_pg="tiradas")
    assert sistema.calcular(personaje, catalogo).pg_maximos == 26  # 12 + 9 + 5

    personaje.clases[0].tiradas_pg = [7]
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.pg_maximos == 29 and any("falta la tirada" in a for a in ficha.avisos)

    personaje.clases[0].tiradas_pg = [11, 1]
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.pg_maximos == 27 and any("fuera de 1–10" in a for a in ficha.avisos)


@pytest.mark.parametrize("equipo, ca", [
    ([], 15),  # 10 + DES 2 + CON 3
    ([ObjetoInventario("escudo", equipado=True)], 17),
    ([ObjetoInventario("cuero", equipado=True)], 13),
    ([ObjetoInventario("cuero", equipado=False)], 15),
])
def test_defensa_sin_armadura_del_barbaro(sistema, catalogo, equipo, ca):
    personaje = nuevo_personaje(clases=[EntradaClase("barbaro")], metodo_caracteristicas="manual",
                                caracteristicas_base=dict(BASE_BARBARO), equipo=equipo)
    assert sistema.calcular(personaje, catalogo).ca == ca


@pytest.mark.parametrize("clases, espacios, pacto", [
    ([EntradaClase("mago", 5)], {1: 4, 2: 3, 3: 2}, None),
    ([EntradaClase("paladin", 5)], {1: 4, 2: 2}, None),
    ([EntradaClase("paladin", 1)], {}, None),
    ([EntradaClase("mago", 3), EntradaClase("paladin", 4)], {1: 4, 2: 3, 3: 2}, None),
    ([EntradaClase("brujo", 5)], {}, {"espacios": 2, "nivel": 3}),
    ([EntradaClase("guerrero", 5), EntradaClase("brujo", 2)], {}, {"espacios": 2, "nivel": 1}),
])
def test_espacios_de_conjuro(sistema, catalogo, clases, espacios, pacto):
    ficha = sistema.calcular(nuevo_personaje(clases=clases), catalogo)
    assert ficha.espacios_conjuro == espacios
    assert ficha.magia_pacto == pacto


def test_lanzador_cd_ataque_y_avisos_de_conjuros(sistema, catalogo):
    personaje = nuevo_personaje(
        clases=[EntradaClase("mago", 3)], metodo_caracteristicas="manual",
        caracteristicas_base={"fue": 8, "des": 14, "con": 14, "int": 16, "sab": 12, "car": 10},
        conjuros={"mago": ["luz", "rayo_de_escarcha", "taumaturgia", "proyectil_magico", "bola_de_fuego"]},
    )
    ficha = sistema.calcular(personaje, catalogo)
    (mago,) = ficha.lanzadores
    assert (mago.cd, mago.ataque, mago.nivel_maximo) == (13, 5, 2)
    assert mago.conjuros == {0: ["Luz", "Rayo de escarcha", "Taumaturgia"], 1: ["Proyectil mágico"], 3: ["Bola de fuego"]}
    texto = "\n".join(ficha.avisos)
    assert "Taumaturgia no está en la lista de conjuros de Mago" in texto
    assert "Bola de fuego es de nivel 3" in texto


def test_limites_y_repeticiones_de_conjuros(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("mago", 1)],
                                conjuros={"mago": ["luz", "rayo_de_escarcha", "mano_de_mago", "luz", "x"]})
    texto = "\n".join(sistema.calcular(personaje, catalogo).avisos)
    assert "Conjuro desconocido «x»" in texto
    assert "«luz» está repetido" in texto
    assert "trucos elegidos" not in texto

    personaje.conjuros["mago"] = ["luz", "rayo_de_escarcha", "mano_de_mago", "taumaturgia"]
    texto = "\n".join(sistema.calcular(personaje, catalogo).avisos)
    assert "Mago: 4 trucos elegidos, máximo 3" in texto


def test_medio_competencia(sistema, catalogo):
    bardo = nuevo_personaje(clases=[EntradaClase("bardo", 2)])
    ficha = sistema.calcular(bardo, catalogo)
    assert ficha.habilidades["arcanos"].valor == 0  # INT -1 + 1
    assert ficha.iniciativa == 2  # DES 1 + 1

    campeon = nuevo_personaje(clases=[EntradaClase("guerrero", 7, subclase="campeon")], elecciones={
        "clase:guerrero:inicial/habilidades": ["historia", "intimidacion"]})
    ficha = sistema.calcular(campeon, catalogo)
    assert ficha.habilidades["atletismo"].valor == 4  # FUE 2 + mitad de 3 redondeando arriba
    assert ficha.habilidades["arcanos"].valor == -1
    assert ficha.clase_y_nivel == "Guerrero 7 (Campeón)"


def test_truco_racial(sistema, catalogo):
    personaje = nuevo_personaje(raza="elfo", subraza="elfo_alto", elecciones={
        "subraza:elfo_alto/truco": ["luz"], "subraza:elfo_alto/idioma": ["enano"]})
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.conjuros_innatos == ["Luz (Inteligencia)"]
    assert ficha.competencias["idiomas"] == ["Común", "Élfico", "Enano"]
    assert ficha.habilidades["percepcion"].competente


def test_referencias_incoherentes_generan_avisos(sistema, catalogo):
    personaje = nuevo_personaje(raza="elfo", subraza="enano_colinas",
                                clases=[EntradaClase("guerrero", 2, subclase="campeon"), EntradaClase("ninja")])
    texto = "\n".join(sistema.calcular(personaje, catalogo).avisos)
    assert "no pertenece a Elfo" in texto
    assert "la subclase se elige a nivel 3" in texto
    assert "No existe la clase «ninja»" in texto

    personaje = nuevo_personaje(subraza="elfo_alto")
    assert "Hay subraza elegida pero no raza" in sistema.calcular(personaje, catalogo).avisos


def test_personaje_vacio_no_falla(sistema, catalogo):
    ficha = sistema.calcular(nuevo_personaje(), catalogo)
    assert ficha.nivel == 0 and ficha.pg_maximos == 0 and ficha.ca == 11
