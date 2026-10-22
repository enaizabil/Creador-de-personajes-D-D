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
