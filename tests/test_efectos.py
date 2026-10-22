from ayudas import EntradaClase, nuevo_personaje


def claves_pendientes(sistema, personaje, catalogo):
    return {p.clave: p for p in sistema.elecciones_pendientes(personaje, catalogo)}


def test_elecciones_pendientes_con_sus_opciones(sistema, catalogo):
    personaje = nuevo_personaje(raza="elfo", subraza="elfo_alto", clases=[EntradaClase("guerrero")])
    pendientes = claves_pendientes(sistema, personaje, catalogo)
    assert set(pendientes) == {
        "subraza:elfo_alto/truco",
        "subraza:elfo_alto/idioma",
        "clase:guerrero:inicial/habilidades",
        "clase:guerrero:1/estilo",
    }
    truco = pendientes["subraza:elfo_alto/truco"]
    assert [o.id for o in truco.opciones] == ["luz", "mano_de_mago", "rayo_de_escarcha"]  # solo trucos de mago
    habilidades = pendientes["clase:guerrero:inicial/habilidades"]
    assert habilidades.elegir == 2
    assert {o.nombre for o in habilidades.opciones} >= {"Atletismo", "Percepción"}


def test_seleccion_invalida_repetida_o_sobrante(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero")], elecciones={
        "clase:guerrero:inicial/habilidades": ["conocimiento_arcano", "atletismo", "atletismo", "historia", "percepcion"],
    })
    resolucion = sistema.resolver(personaje, catalogo)
    texto = "\n".join(resolucion.errores)
    assert "«conocimiento_arcano» no es una opción válida" in texto
    assert "«atletismo» está repetido" in texto
    assert "sobran selecciones" in texto
    competencias = {a.efecto["id"] for a in resolucion.de_tipo("competencia") if a.efecto["categoria"] == "habilidad"}
    assert competencias == {"atletismo", "historia"}


def test_mejora_anidada_con_dote_que_tiene_su_propia_eleccion(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero", nivel=4)], elecciones={
        "clase:guerrero:4/mejora": ["dote"],
        "clase:guerrero:4/mejora=dote/dote": ["resiliente"],
    })
    pendientes = claves_pendientes(sistema, personaje, catalogo)
    clave_resiliente = "clase:guerrero:4/mejora=dote/dote=resiliente>dote:resiliente/car"
    assert clave_resiliente in pendientes

    personaje.elecciones[clave_resiliente] = ["sab"]
    ficha = sistema.calcular(personaje, catalogo)
    assert ficha.caracteristicas["sab"].puntuacion == 13
    assert ficha.salvaciones["sab"].competente
    assert "Dote: Resiliente" in [r.nombre for r in ficha.rasgos]


def test_eleccion_anidada_usa_la_opcion_exterior_en_su_filtro(sistema, catalogo):
    dote = "clase:guerrero:4/mejora=dote/dote=iniciado>dote:iniciado"
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero", nivel=4)], elecciones={
        "clase:guerrero:4/mejora": ["dote"],
        "clase:guerrero:4/mejora=dote/dote": ["iniciado"],
        f"{dote}/clase": ["bardo"],
    })
    truco = claves_pendientes(sistema, personaje, catalogo)[f"{dote}/clase=bardo/truco"]
    assert [o.id for o in truco.opciones] == ["luz", "mano_de_mago"]

    personaje.elecciones[f"{dote}/clase=bardo/truco"] = ["mano_de_mago"]
    assert sistema.calcular(personaje, catalogo).conjuros_innatos == ["Mano de mago"]


def test_sin_dotes_la_mejora_solo_ofrece_caracteristicas(sistema, catalogo):
    personaje = nuevo_personaje(clases=[EntradaClase("guerrero", nivel=4)], reglas_opcionales={"dotes": False})
    mejora = claves_pendientes(sistema, personaje, catalogo)["clase:guerrero:4/mejora"]
    assert [o.id for o in mejora.opciones] == ["caracteristicas"]


def test_limpiar_elecciones_huerfanas_al_cambiar_de_raza(sistema, catalogo):
    personaje = nuevo_personaje(raza="elfo", subraza="elfo_alto", elecciones={
        "subraza:elfo_alto/idioma": ["enano"],
        "subraza:elfo_alto/truco": ["luz"],
    })
    personaje.raza, personaje.subraza = "enano", "enano_colinas"
    vigentes = sistema.resolver(personaje, catalogo).claves_visitadas
    assert sorted(personaje.limpiar_elecciones(vigentes)) == ["subraza:elfo_alto/idioma", "subraza:elfo_alto/truco"]
    assert personaje.elecciones == {}
