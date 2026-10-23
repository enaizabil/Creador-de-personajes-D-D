"""Asistente del modo normal sobre los paquetes reales (srd-5.1, phb-2014, dmg-2014)."""
import random

import pytest

from creador.entorno import abrir_catalogo
from creador.nucleo.personaje import Personaje
from creador.nucleo.rutas import directorio_datos_integrados
from creador.nucleo.personaje import EntradaClase
from creador.sistemas.dnd5e_2014.asistente import describir_eleccion, tirar_dados

PAQUETES = ["srd-5.1", "phb-2014", "dmg-2014"]


@pytest.fixture(scope="module")
def entorno_real():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", PAQUETES, [directorio_datos_integrados() / "paquetes"])
    if not catalogo.listar("clases"):
        pytest.skip("los paquetes reales aún no tienen clases")
    assert errores == []
    return sistema, catalogo


@pytest.fixture
def asistente(entorno_real):
    sistema, catalogo = entorno_real
    personaje = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES)
    return sistema.crear_asistente(personaje, catalogo, rng=random.Random(7))


def completar_elecciones(asistente, paso):
    for _ in range(10):
        pendientes = [e for e in asistente.elecciones(paso) if e.faltan > 0]
        if not pendientes:
            return
        for e in pendientes:
            libres = [o.id for o in e.opciones if o.id not in e.seleccion]
            asistente.elegir(e.clave, e.seleccion + libres[:e.faltan])


def completar_equipo(asistente):
    for bloque in asistente.bloques_equipo():
        if bloque.elegida is None:
            asistente.elegir_alternativa(bloque.origen, bloque.indice, 0)
    for bloque in asistente.bloques_equipo():
        for n, linea in enumerate(bloque.alternativas[bloque.elegida]):
            for hueco in range(linea.cantidad if linea.id is None else 0):
                asistente.elegir_objeto(bloque.origen, bloque.indice, bloque.elegida, n, hueco, linea.opciones[0][0])
    asistente.aplicar_equipo()


def test_recorrido_completo_de_un_mago_alto_elfo(asistente):
    a = asistente
    assert [p.id for p in a.pasos()] == ["inicio", "raza", "clase", "caracteristicas", "trasfondo", "equipo",
                                         "detalles", "resumen"]
    a.establecer_nivel(3)

    a.elegir_raza("elfo")
    assert a.faltan("raza") == ["Elige una subraza"]
    a.elegir_subraza("alto_elfo")
    assert any("Truco" in f or "truco" in f for f in a.faltan("raza"))
    completar_elecciones(a, "raza")
    assert a.faltan("raza") == []

    a.elegir_clase("mago")
    assert a.faltan("clase")[0] == "Elige una subclase"
    a.elegir_subclase("escuela_de_evocacion")
    completar_elecciones(a, "clase")
    assert a.faltan("clase") == []
    assert "conjuros" in [p.id for p in a.pasos()]

    a.establecer_metodo("estandar")
    assert a.valores_disponibles() == [15, 14, 13, 12, 10, 8]
    a.sugerir_caracteristicas()
    assert a.personaje.caracteristicas_base["int"] == 15
    assert a.faltan("caracteristicas") == []
    assert a.bonos_raciales()["des"] == 2 and a.bonos_raciales()["int"] == 1

    a.elegir_trasfondo("sabio")
    completar_elecciones(a, "trasfondo")
    assert a.faltan("trasfondo") == []
    assert a.personalidad_sugerida()["ideales"]

    assert a.faltan("equipo")
    completar_equipo(a)
    assert a.faltan("equipo") == []
    ids = {o.id for o in a.personaje.equipo}
    assert "libro_de_conjuros" in ids and "paquete_de_erudito" not in ids  # los paquetes se abren
    assert a.personaje.monedas.get("po", 0) > 0

    (plan,) = a.planes_conjuros()
    assert (plan.clase_id, plan.nivel_maximo, plan.limite_trucos, plan.modo) == ("mago", 2, 3, "libro")
    assert plan.limite_conjuros == 3 + 3  # preparados: INT 16 (+3) + nivel 3
    assert plan.limite_libro == 6 + 2 * 2
    trucos = [i for i, _ in plan.disponibles[0][:3]]
    nivel_1 = [i for i, _ in plan.disponibles[1]]
    nivel_2 = [i for i, _ in plan.disponibles[2]]
    # A nivel 3 solo los 2 conjuros ganados al llegar a nivel 3 pueden ser de nivel 2.
    a.elegir_conjuros("mago", trucos + nivel_1[:7] + nivel_2[:3])
    assert any("nivel 2 o más" in f for f in a.faltan("conjuros"))
    libro = nivel_1[:8] + nivel_2[:2]
    a.elegir_conjuros("mago", trucos + libro)
    assert a.faltan("conjuros") == ["Mago: prepara 6 conjuro(s) más del libro"]
    a.elegir_preparados("mago", [nivel_2[0], "bola_de_fuego", *nivel_1[:5]])
    assert a.personaje.preparados["mago"] == [nivel_2[0], *nivel_1[:5]]  # fuera de libro: descartado
    assert a.faltan("conjuros") == []
    a.elegir_conjuros("mago", trucos + libro[1:])  # quitar del libro lo quita de preparados
    assert nivel_1[0] not in a.personaje.preparados["mago"]
    a.elegir_conjuros("mago", trucos + libro)
    a.elegir_preparados("mago", [nivel_2[0], *nivel_1[:5]])
    mago = a.ficha().lanzadores[0]
    assert sum(map(len, mago.libro.values())) == 10 and sum(map(len, mago.conjuros.values())) == 3 + 6

    assert a.faltan("detalles") == ["Ponle nombre al personaje"]
    a.establecer_detalle("nombre", "Ilmara")
    a.establecer_detalle("alineamiento", "Neutral bueno")
    assert a.faltan("resumen") == []

    ficha = a.ficha()
    assert ficha.clase_y_nivel == "Mago 3 (Escuela de Evocación)"
    assert ficha.lanzadores[0].cd == 8 + 2 + 3
    graves = [x for x in ficha.avisos if "no existe" in x or "desconocid" in x or "pendiente" in x.lower()]
    assert graves == []


def test_opciones_que_requieren_permiso_del_dm(asistente):
    asistente.elegir_raza("elfo")
    assert "eladrin" not in [o.id for o in asistente.subrazas()]
    assert "aasimar" not in [o.id for o in asistente.razas()]
    asistente.establecer_regla("opciones_dm", True)
    assert "eladrin" in [o.id for o in asistente.subrazas()]
    assert any(o.id == "aasimar" and o.permiso_dm for o in asistente.razas())


def test_humano_variante_solo_con_dotes(asistente):
    asistente.elegir_raza("humano")
    assert "humano_variante" in [o.id for o in asistente.subrazas()]
    asistente.establecer_regla("dotes", False)
    assert "humano_variante" not in [o.id for o in asistente.subrazas()]


def test_compra_por_puntos_y_tiradas(asistente):
    asistente.establecer_metodo("compra")
    assert asistente.puntos_restantes() == 27
    asistente.asignar("fue", 15)
    assert asistente.puntos_restantes() == 18
    with pytest.raises(ValueError):
        asistente.asignar("des", 16)

    asistente.establecer_metodo("tirada")
    assert asistente.faltan("caracteristicas")
    tiradas = asistente.tirar_caracteristicas()
    assert len(tiradas) == 6 and asistente.valores_disponibles() == sorted(tiradas, reverse=True)
    asistente.asignar("con", tiradas[0])
    assert len(asistente.valores_disponibles()) == 5


def test_oro_en_vez_de_equipo_de_clase(asistente):
    asistente.elegir_clase("guerrero")
    asistente.elegir_trasfondo("soldado")
    asistente.usar_oro_en_vez_de_equipo(True)
    assert all(b.origen == "trasfondo" for b in asistente.bloques_equipo())
    completar_equipo(asistente)
    oro = asistente.personaje.extra["equipo_inicial"]["oro_tirado"]
    assert 50 <= oro <= 200  # 5d4 × 10
    assert asistente.personaje.monedas["po"] == oro + 10  # + 10 po del soldado


def test_bajar_de_nivel_quita_la_subclase(asistente):
    asistente.establecer_nivel(3)
    asistente.elegir_clase("guerrero")
    asistente.elegir_subclase("campeon")
    asistente.establecer_nivel(2)
    assert asistente.personaje.clases[0].subclase is None
    assert asistente.subclases() == []


def test_tirar_dados():
    rng = random.Random(3)
    assert all(20 <= tirar_dados("2d4x10", rng) <= 80 for _ in range(50))
    assert all(5 <= tirar_dados("5d4", rng) <= 20 for _ in range(50))
    assert all(525 <= tirar_dados("500 + 1d10x25", rng) <= 750 for _ in range(50))
    with pytest.raises(ValueError):
        tirar_dados("dos dados", rng)


def test_equipo_pendiente_hasta_tener_clase_y_trasfondo(asistente):
    assert asistente.faltan("equipo") == ["Elige antes una clase", "Elige antes un trasfondo"]
    asistente.elegir_clase("guerrero")
    asistente.elegir_trasfondo("soldado")
    assert not any(f.startswith("Elige antes") for f in asistente.faltan("equipo"))


def test_nombre_de_las_lineas_de_equipo_a_elegir(asistente):
    assert describir_eleccion({"desde": "armas", "filtro": {"arma": {"categoria": "marcial", "tipo": "cuerpo_a_cuerpo"}}}) \
        == "Arma marcial cuerpo a cuerpo a elegir"
    assert describir_eleccion({"desde": "armas", "filtro": {"arma": {"categoria": "sencilla"}}}) == "Arma sencilla a elegir"
    assert describir_eleccion({"desde": "objetos", "filtro": {"categoria": "foco", "subcategoria": "druidico"}}) \
        == "Canalizador druídico a elegir"
    assert describir_eleccion({"desde": "herramientas", "filtro": {"subcategoria": "instrumento"}}) \
        == "Instrumento musical a elegir"
    asistente.elegir_clase("mago")
    nombres = [linea.nombre for b in asistente.bloques_equipo() for alt in b.alternativas for linea in alt]
    assert "Canalizador arcano a elegir" in nombres and "a elegir" not in nombres


def test_avisos_del_libro_de_conjuros(entorno_real):
    sistema, catalogo = entorno_real
    personaje = Personaje(sistema="dnd5e-2014", paquetes=PAQUETES, raza="humano", trasfondo="sabio",
                          clases=[EntradaClase("mago", 1)], caracteristicas_base={"int": 15},
                          conjuros={"mago": ["proyectil_magico", "escudo", "invisibilidad"]},
                          preparados={"mago": ["proyectil_magico", "dormir"]})
    avisos = sistema.calcular(personaje, catalogo).avisos
    assert "Mago: el libro tiene 1 conjuros de nivel 2 o más; a nivel 1 solo pueden ser 0" in avisos
    assert any("Dormir" in x and "no está en el libro" in x for x in avisos)
    mago = sistema.calcular(personaje, catalogo).lanzadores[0]
    assert mago.conjuros == {1: ["Proyectil mágico"]}
    assert mago.libro[1] == ["Escudo", "Proyectil mágico"]
    personaje.conjuros["mago"] = ["alarma", "dormir", "escudo", "grasa", "identificar", "salto", "proyectil_magico"]
    assert any("7 conjuros en el libro, máximo 6" in x for x in sistema.calcular(personaje, catalogo).avisos)


def test_opciones_que_ya_se_tienen_por_otra_via(asistente):
    a = asistente
    a.elegir_raza("elfo")
    a.elegir_subraza("alto_elfo")
    a.elegir_clase("mago")
    a.elegir_trasfondo("sabio")
    idioma_elfo = next(e for e in a.elecciones("raza") if e.clave == "subraza:alto_elfo/idioma")
    assert {"comun", "elfico"} <= a.conocidas(idioma_elfo)
    a.elegir(idioma_elfo.clave, ["abisal"])
    idiomas_sabio = next(e for e in a.elecciones("trasfondo") if e.clave.startswith("trasfondo:sabio/"))
    assert "abisal" in a.conocidas(idiomas_sabio)
    idioma_elfo = next(e for e in a.elecciones("raza") if e.clave == idioma_elfo.clave)
    assert "abisal" not in a.conocidas(idioma_elfo)  # la propia selección no cuenta
    habilidades_mago = next(e for e in a.elecciones("clase") if e.clave == "clase:mago:inicial/habilidades")
    assert {"conocimiento_arcano", "historia"} <= a.conocidas(habilidades_mago)  # las da el trasfondo
    truco = next(e for e in a.elecciones("raza") if e.clave == "subraza:alto_elfo/truco")
    a.elegir(truco.clave, ["luz"])
    assert "luz" in a.conjuros_de_otras_fuentes()
    a.elegir_conjuros("mago", ["mano_de_mago"])
    truco = next(e for e in a.elecciones("raza") if e.clave == "subraza:alto_elfo/truco")
    assert a.conocidas(truco) == {"mano_de_mago"}


def test_nivel_limitado_a_los_datos(asistente, monkeypatch):
    a = asistente
    assert a.nivel_maximo() == 20
    for clase in a.catalogo.listar("clases"):  # como un paquete cuyos datos solo llegan a nivel 5
        monkeypatch.setitem(a.catalogo.obtener("clases", clase["id"]), "niveles_completos", 5)
    assert a.nivel_maximo() == 5
    with pytest.raises(ValueError):
        a.establecer_nivel(6)
    a.establecer_nivel(5)
    a.elegir_clase("guerrero")
    assert a.personaje.clases[0].nivel == 5
    a.personaje.clases[0].nivel = 7  # p. ej. un JSON editado a mano
    assert any("solo llegan a nivel 5" in x for x in a.ficha().avisos)


def test_subclase_con_datos_hasta_un_nivel_menor(asistente, monkeypatch):
    a = asistente
    # Como un paquete (homebrew, expansión) cuya subclase solo tiene datos hasta nivel 5.
    monkeypatch.setitem(a.catalogo.obtener("subclases", "maestro_de_batalla"), "niveles_completos", 5)
    a.establecer_nivel(10)
    a.elegir_clase("guerrero")
    nombres = {o.id: o.nombre for o in a.subclases()}
    assert nombres["campeon"] == "Campeón"  # SRD: completa hasta 20
    assert nombres["maestro_de_batalla"].endswith("(datos hasta nivel 5)")
    a.elegir_subclase("maestro_de_batalla")
    assert any("Maestro de Batalla solo llegan a nivel 5" in x for x in a.ficha().avisos)


def test_la_pericia_no_se_bloquea_por_ser_competente(asistente):
    a = asistente
    a.elegir_raza("humano")
    a.elegir_subraza("humano_estandar")
    a.elegir_clase("picaro")
    a.elegir_trasfondo("criminal")  # da Engaño y Sigilo
    habilidades = next(e for e in a.elecciones("clase") if e.clave == "clase:picaro:inicial/habilidades")
    assert {"engano", "sigilo"} <= a.conocidas(habilidades)
    a.elegir(habilidades.clave, ["acrobacias", "percepcion", "investigacion", "persuasion"])
    pericia = next(e for e in a.elecciones("clase") if e.clave == "clase:picaro:1/pericia")
    assert a.conocidas(pericia) == set()
    a.elegir(pericia.clave, ["sigilo", "engano"])
    a.establecer_nivel(5)  # a nivel 6 llegaría otra pericia; aquí basta con ver que no se repite
    assert a.conocidas(next(e for e in a.elecciones("clase") if e.clave == pericia.clave)) == set()


def test_la_pericia_solo_donde_hay_competencia(asistente):
    a = asistente
    a.elegir_raza("humano")
    a.elegir_subraza("humano_estandar")
    a.elegir_clase("picaro")
    a.elegir_trasfondo("criminal")  # Engaño, Sigilo y herramientas de ladrón (también de clase)
    pericia = next(e for e in a.elecciones("clase") if e.clave == "clase:picaro:1/pericia")
    bloqueadas = a.sin_competencia(pericia)
    assert "acrobacias" in bloqueadas and "medicina" in bloqueadas
    assert not {"engano", "sigilo", "herramientas_de_ladron"} & bloqueadas
    assert a.bloqueadas(pericia)["acrobacias"] == "sin competencia"
    habilidades = next(e for e in a.elecciones("clase") if e.clave == "clase:picaro:inicial/habilidades")
    a.elegir(habilidades.clave, ["acrobacias", "percepcion", "investigacion", "persuasion"])
    pericia = next(e for e in a.elecciones("clase") if e.clave == pericia.clave)
    assert "acrobacias" not in a.sin_competencia(pericia) and "medicina" in a.sin_competencia(pericia)


def test_competencia_y_pericia_a_la_vez_no_se_bloquea(asistente):
    a = asistente
    a.elegir_raza("humano")
    a.elegir_subraza("humano_estandar")
    a.elegir_clase("clerigo")
    a.elegir_subclase("dominio_del_conocimiento")
    a.elegir_trasfondo("soldado")
    bendiciones = next(e for e in a.elecciones("clase") if "Bendiciones" in e.nombre)
    assert a.sin_competencia(bendiciones) == set()


# ── multiclase ─────────────────────────────────────────────────────────────

def test_multiclase_reparte_el_nivel_total(asistente):
    a = asistente
    a.establecer_nivel(8)
    a.elegir_clase("guerrero")
    a.anadir_clase("picaro", 3)
    assert [(e.clase, e.nivel) for e in a.personaje.clases] == [("guerrero", 5), ("picaro", 3)]
    assert a.nivel == 8
    a.establecer_niveles_clase("picaro", 2)
    assert [(e.clase, e.nivel) for e in a.personaje.clases] == [("guerrero", 6), ("picaro", 2)]
    a.establecer_nivel(10)  # el nivel total sube la principal
    assert [(e.clase, e.nivel) for e in a.personaje.clases] == [("guerrero", 8), ("picaro", 2)]
    with pytest.raises(ValueError):
        a.establecer_nivel(2)  # con 2 niveles de pícaro, el total no puede bajar de 3
    with pytest.raises(ValueError):
        a.establecer_niveles_clase("picaro", 10)  # la principal se quedaría sin niveles
    with pytest.raises(ValueError):
        a.anadir_clase("picaro")  # ya la tiene
    a.quitar_clase("picaro")
    assert [(e.clase, e.nivel) for e in a.personaje.clases] == [("guerrero", 10)]


def test_multiclase_subclase_por_clase_y_lo_que_falta(asistente):
    a = asistente
    a.establecer_nivel(6)
    a.elegir_clase("guerrero")
    a.anadir_clase("clerigo", 1)  # el clérigo elige dominio a nivel 1
    assert a.subclases("clerigo") and a.subclases("guerrero")
    faltan = a.faltan("clase")
    assert "Elige una subclase de Guerrero" in faltan and "Elige una subclase de Clérigo" in faltan
    a.elegir_subclase("dominio_de_la_vida", "clerigo")
    a.elegir_subclase("campeon")
    assert not any("subclase" in f for f in a.faltan("clase"))
    a.establecer_niveles_clase("clerigo", 4)  # guerrero 2: aún no tiene arquetipo
    assert a.personaje.clases[0].subclase is None and a.subclases("guerrero") == []


def test_multiclase_requisitos_avisan_sin_bloquear(asistente):
    a = asistente
    a.elegir_raza("humano")
    a.elegir_subraza("humano_estandar")
    a.establecer_nivel(4)
    a.elegir_clase("guerrero")
    a.establecer_metodo("estandar")
    a.personaje.caracteristicas_base = {"fue": 15, "des": 14, "con": 13, "int": 8, "sab": 12, "car": 10}
    a.anadir_clase("mago", 1)  # INT 9 con el humano: no llega a 13
    assert a.requisito_multiclase("mago") == ("INT 13", False)
    assert any("Multiclase: Mago requiere INT 13" in x for x in a.ficha().avisos)
    a.sugerir_caracteristicas()  # reparte pensando también en el mago
    assert a.requisito_multiclase("mago")[1]


def test_multiclase_cambiar_la_principal_conserva_las_demas(asistente):
    a = asistente
    a.establecer_nivel(5)
    a.elegir_clase("mago")
    a.anadir_clase("guerrero", 2)
    a.elegir_conjuros("mago", ["mano_de_mago"])
    a.elegir_clase("guerrero")  # la secundaria pasa a principal y se queda con todos los niveles
    assert [(e.clase, e.nivel) for e in a.personaje.clases] == [("guerrero", 5)]
    assert "mago" not in a.personaje.conjuros


def test_rasgos_que_no_se_acumulan(asistente):
    a = asistente
    a.establecer_nivel(16)
    a.elegir_clase("guerrero")
    a.anadir_clase("monje", 5)  # guerrero 11 (3 ataques) y monje 5 (2 ataques)
    completar_elecciones(a, "clase")
    rasgos = [r for r in a.ficha().rasgos if r.nombre == "Ataque Adicional"]
    assert len(rasgos) == 1 and rasgos[0].resumen.startswith("3 ataques")


def test_multiclase_desactivada(asistente):
    a = asistente
    a.establecer_regla("multiclase", False)
    a.establecer_nivel(4)
    a.elegir_clase("guerrero")
    with pytest.raises(ValueError):
        a.anadir_clase("picaro")


def test_canalizar_divinidad_de_dos_clases_no_suma_usos(asistente):
    a = asistente
    a.establecer_nivel(9)
    a.elegir_clase("clerigo")
    a.anadir_clase("paladin", 3)  # clérigo 6 (2 usos) y paladín 3 (1 uso)
    completar_elecciones(a, "clase")
    rasgos = [r for r in a.ficha().rasgos if r.nombre == "Canalizar Divinidad"]
    assert sorted(r.usos or 0 for r in rasgos) == [0, 2]
    assert any(r.resumen.startswith("usos: los de Clérigo 2 (no se suman)") for r in rasgos)


def test_defensa_sin_armadura_solo_de_la_primera_clase(asistente):
    a = asistente
    a.elegir_raza("humano")
    a.elegir_subraza("humano_estandar")
    a.establecer_nivel(4)
    a.elegir_clase("barbaro")
    a.anadir_clase("monje", 1)
    a.establecer_metodo("manual")
    a.personaje.caracteristicas_base = {"fue": 14, "des": 14, "con": 10, "int": 8, "sab": 16, "car": 8}
    a.personaje.equipo = []
    ficha = a.ficha()
    # Bárbaro: 10 + DES 2 + CON 0 = 12, aunque la del monje (10 + 2 + 3 = 15) sería mejor.
    assert ficha.ca == 10 + ficha.caracteristicas["des"].modificador + ficha.caracteristicas["con"].modificador


def test_la_resolucion_se_reutiliza_mientras_el_personaje_no_cambia(asistente, monkeypatch):
    a = asistente
    a.elegir_raza("humano")
    a.elegir_subraza("humano_estandar")
    a.elegir_clase("picaro")
    llamadas = []
    original = a.sistema.resolver
    monkeypatch.setattr(a.sistema, "resolver", lambda *x: llamadas.append(1) or original(*x))
    for eleccion in a.elecciones("clase"):
        a.bloqueadas(eleccion)
    assert llamadas == []  # la dejó calculada elegir_clase y nada ha cambiado desde entonces
    # Cualquier cambio en el personaje, aunque se haga sin pasar por el asistente, invalida la caché.
    a.personaje.elecciones["clase:picaro:inicial/habilidades"] = ["acrobacias"]
    assert a.elecciones("clase")[0].seleccion == ["acrobacias"]
    a.bloqueadas(a.elecciones("clase")[0])
    assert len(llamadas) == 1
