"""Versión web: la sesión describe cada pantalla en JSON y ejecuta las acciones de la página."""
import base64
import json
import zipfile
from pathlib import Path

import pytest

import creador.entorno
import creador.gestor
from creador.nucleo.rutas import directorio_datos_integrados
from creador.web import sesion as modulo_sesion
from creador.web.sesion import Sesion

EJEMPLO = Path(__file__).resolve().parents[1] / "docs" / "ejemplos" / "homebrew-ejemplo"
INTERACTIVOS = {"boton", "interruptor", "menu", "segmentado", "entrada", "lista_opciones", "casillas", "respuestas",
                "archivo", "radios", "eleccion", "recomendaciones"}


@pytest.fixture
def usuario(tmp_path, monkeypatch):
    """Los paquetes del usuario van a una carpeta temporal, no a la personal."""
    carpeta = tmp_path / "paquetes"
    carpeta.mkdir()
    directorios = [directorio_datos_integrados() / "paquetes", carpeta]
    monkeypatch.setattr(creador.entorno, "directorios_paquetes", lambda: directorios)
    monkeypatch.setattr(creador.gestor, "directorios_paquetes", lambda: directorios)
    return carpeta


@pytest.fixture
def s(usuario):
    sesion = Sesion()
    llamar(sesion, "ir", pantalla="portada")
    return sesion


def llamar(sesion: Sesion, accion: str, **args) -> dict:
    """Como la página: la respuesta tiene que poder pasar por JSON y no traer errores."""
    respuesta = json.loads(sesion.llamar_json(accion, json.dumps(args)))
    assert "error" not in respuesta, respuesta["error"]
    return respuesta


def componentes(nodo):
    """Todos los componentes de una vista (o de una lista de ellos), en orden."""
    if isinstance(nodo, list):
        for hijo in nodo:
            yield from componentes(hijo)
    elif isinstance(nodo, dict):
        if "t" in nodo:
            yield nodo
        for clave in ("contenido", "pie", "hijos", "filas"):
            if clave in nodo:
                yield from componentes(nodo[clave])


def de_tipo(respuesta: dict, tipo: str) -> list[dict]:
    return [x for x in componentes(respuesta["vista"]) if x["t"] == tipo]


def textos(respuesta: dict) -> str:
    return "\n".join(x.get("texto", "") for x in componentes(respuesta["vista"]) if isinstance(x.get("texto"), str))


def boton(respuesta: dict, texto: str) -> dict:
    return next(x for x in de_tipo(respuesta, "boton") if x["texto"].startswith(texto))


def pulsar(sesion: Sesion, componente: dict, **extra) -> dict:
    return llamar(sesion, componente["accion"], **componente["args"], **extra)


def acciones_conocidas(respuesta: dict) -> None:
    for x in componentes(respuesta["vista"]):
        if x["t"] in INTERACTIVOS:
            assert hasattr(Sesion, f"accion_{x['accion']}"), x


def nuevo(s: Sesion, modo: str, *paquetes: str) -> dict:
    """Marca solo esos paquetes (con sus dependencias) y crea."""
    for id_ in list(s.marcados):
        s.marcados[id_] = False
    for id_ in paquetes:
        llamar(s, "marcar_paquete", id=id_, valor=True)
    return llamar(s, "crear", modo=modo)


def responder_todo(s: Sesion) -> dict:
    respuesta = llamar(s, "pregunta", indice=0)
    while respuesta["vista"]["pantalla"] == "pregunta":
        tarjetas = de_tipo(respuesta, "respuestas")[0]
        respuesta = pulsar(s, tarjetas, respuesta=tarjetas["opciones"][-1]["id"])
    return respuesta


def completar_pasos(s: Sesion) -> None:
    """Rellena cada elección con las primeras opciones que se pueden marcar."""
    for _ in range(4):
        for paso in [x["id"] for x in llamar(s, "paso", paso="inicio")["vista"]["lateral"]]:
            respuesta = llamar(s, "paso", paso=paso)
            for eleccion in de_tipo(respuesta, "eleccion"):
                if not eleccion["completa"]:
                    libres = [o["id"] for o in eleccion["opciones"] if not o["motivo"]]
                    pulsar(s, eleccion, valores=libres[:eleccion["elegir"]])


# ── portada y paquetes ───────────────────────────────────────────────────


def test_portada_con_los_paquetes_integrados(s):
    respuesta = llamar(s, "ir", pantalla="portada")
    assert respuesta["vista"]["pantalla"] == "portada" and respuesta["estado"] is None
    nombres = {x["args"]["id"]: x["activo"] for x in de_tipo(respuesta, "interruptor")}
    assert {"srd-5.1", "phb-2014", "dmg-2014", "tasha-2020", "cuestionario-basico"} <= set(nombres)
    assert all(nombres.values())  # oficiales y del programa, marcados de serie
    acciones_conocidas(respuesta)


def test_marcar_y_desmarcar_arrastra_las_dependencias(s):
    llamar(s, "marcar_paquete", id="srd-5.1", valor=False)
    assert not any(s.marcados[i] for i in ("srd-5.1", "phb-2014", "dmg-2014", "tasha-2020"))
    llamar(s, "marcar_paquete", id="tasha-2020", valor=True)
    assert s.marcados["tasha-2020"] and s.marcados["phb-2014"] and s.marcados["srd-5.1"]


def test_crear_sin_paquetes_da_error(s):
    for id_ in list(s.marcados):
        s.marcados[id_] = False
    respuesta = s.llamar("crear", {"modo": "normal"})
    assert "paquete" in respuesta["error"] and respuesta["vista"]["pantalla"] == "portada"


def test_preguntas_sin_cuestionario_da_error(s):
    llamar(s, "marcar_paquete", id="cuestionario-basico", valor=False)
    respuesta = s.llamar("crear", {"modo": "sencillo"})
    assert "Cuestionario" in respuesta["error"] and respuesta["vista"]["pantalla"] == "portada"


def test_accion_desconocida_y_errores_del_motor_no_rompen(s):
    assert "desconocida" in s.llamar("volar", {})["error"]
    nuevo(s, "normal", "srd-5.1")
    llamar(s, "paso", paso="caracteristicas")
    llamar(s, "metodo_caracteristicas", valor="manual")
    respuesta = s.llamar("asignar", {"car": "fue", "valor": "mucho"})
    assert "número" in respuesta["error"] and respuesta["vista"]["paso"] == "caracteristicas"


def zip_del_ejemplo(destino: Path) -> str:
    with zipfile.ZipFile(destino, "w") as archivo:
        for ruta in EJEMPLO.rglob("*"):
            if ruta.is_file():
                archivo.write(ruta, f"{EJEMPLO.name}/{ruta.relative_to(EJEMPLO)}")
    return base64.b64encode(destino.read_bytes()).decode("ascii")


def test_importar_y_quitar_paquete(s, usuario, tmp_path):
    respuesta = llamar(s, "ir", pantalla="paquetes")
    assert respuesta["vista"]["pantalla"] == "paquetes" and not de_tipo(respuesta, "boton")[2:]  # sin «Quitar»
    acciones_conocidas(respuesta)
    respuesta = llamar(s, "importar_paquete", nombre="ejemplo.zip", datos=zip_del_ejemplo(tmp_path / "ejemplo.zip"))
    assert "instalado" in respuesta["mensaje"] and (usuario / "homebrew-ejemplo").is_dir()
    quitar = boton(respuesta, "Quitar")
    assert quitar["args"] == {"id": "homebrew-ejemplo"} and quitar["confirmar"]
    respuesta = llamar(s, "importar_paquete", nombre="ejemplo.zip", datos=zip_del_ejemplo(tmp_path / "ejemplo.zip"))
    assert "actualizado" in respuesta["mensaje"]
    portada = llamar(s, "ir", pantalla="portada")
    assert "homebrew-ejemplo" in {x["args"]["id"] for x in de_tipo(portada, "interruptor")}
    assert s.marcados["homebrew-ejemplo"] is False  # el homebrew no se marca de serie
    llamar(s, "ir", pantalla="paquetes")
    assert "quitado" in pulsar(s, quitar)["mensaje"] and not (usuario / "homebrew-ejemplo").exists()


def test_importar_un_paquete_roto_explica_por_que(s, tmp_path):
    roto = tmp_path / "roto.zip"
    with zipfile.ZipFile(roto, "w") as archivo:
        archivo.writestr("roto/paquete.json", "{ no es json")
    llamar(s, "ir", pantalla="paquetes")
    respuesta = s.llamar("importar_paquete", {"nombre": "roto.zip",
                                              "datos": base64.b64encode(roto.read_bytes()).decode("ascii")})
    assert respuesta["error"].startswith("roto/paquete.json: no se puede leer") and respuesta["vista"]["pantalla"] == "paquetes"


def test_quitar_un_integrado_no_se_puede(s):
    respuesta = s.llamar("quitar_paquete", {"id": "srd-5.1"})
    assert "viene con el programa" in respuesta["error"]


# ── cuestionario ─────────────────────────────────────────────────────────


def test_cuestionario_a_nivel_1(s):
    respuesta = nuevo(s, "sencillo", "srd-5.1", "cuestionario-basico")
    assert respuesta["vista"]["pantalla"] == "cuestionario"
    acciones_conocidas(respuesta)
    assert not [x for x in de_tipo(respuesta, "interruptor") if "Tasha" in x["texto"]]  # sin Tasha, sin sus reglas
    llamar(s, "configurar", campo="cantidad", valor="rapido")
    assert s.q.configuracion["cantidad"] == "rapido"
    respuestas = next(x for x in de_tipo(llamar(s, "pregunta", indice=-1), "segmentado") if x["args"] == {"campo": "respuestas"})
    assert respuestas["actual"] == "4" and [v for v, _ in respuestas["valores"]] == ["4", "6"]
    pulsar(s, respuestas, valor="6")
    assert s.q.configuracion["respuestas"] == 6
    pulsar(s, respuestas, valor="4")
    primera = llamar(s, "pregunta", indice=0)
    acciones_conocidas(primera)
    assert textos(primera).count("Pregunta 1 de") == 1 and not [x for x in de_tipo(primera, "boton")
                                                                  if x["texto"].startswith("Ver mi personaje")]
    saltar = boton(primera, "Saltar")
    assert pulsar(s, saltar)["vista"]["contenido"][0]["texto"].startswith("Pregunta 2 de")
    resultado = responder_todo(s)
    assert resultado["vista"]["pantalla"] == "resultado"
    acciones_conocidas(resultado)
    columnas = de_tipo(resultado, "recomendaciones")
    assert [x["titulo"] for x in columnas] == ["Raza", "Clase", "Trasfondo"]
    assert "¿Por qué este resultado?" in textos(resultado)
    assert not [x for x in componentes(resultado["vista"]) if x.get("texto") == "Reparto de clases"]
    otra_clase = columnas[1]["opciones"][1]
    pulsar(s, columnas[1], valor=otra_clase["id"])
    llamar(s, "nombre_cuestionario", valor="  Brenna ")
    assert boton(llamar(s, "volver_resultado"), "Crear personaje")
    final = llamar(s, "siguiente_resultado")
    assert final["vista"]["pantalla"] == "asistente" and final["vista"]["paso"] == "resumen"
    assert final["vista"]["cabecera"]["texto"].startswith("Brenna  ·")
    assert otra_clase["nombre"] in final["vista"]["cabecera"]["texto"]
    assert final["estado"]["titulo"].startswith("Brenna")


def test_cuestionario_con_historia_y_multiclase(s):
    respuesta = nuevo(s, "sencillo", "tasha-2020", "cuestionario-basico")
    assert [x for x in de_tipo(respuesta, "interruptor") if "Tasha" in x["texto"]]
    respuesta = llamar(s, "nivel_cuestionario", valor="8")
    multiclase = next(x for x in de_tipo(respuesta, "interruptor") if x["accion"] == "multiclase_cuestionario")
    pulsar(s, multiclase, valor=True)
    llamar(s, "configurar", campo="cantidad", valor="rapido")
    resultado = responder_todo(s)
    reparto = [x for x in de_tipo(resultado, "menu") if x["accion"] == "cambiar_reparto"]
    assert len(reparto) == 2 and s.reparto[0][0] == s.eleccion["clase"][0]
    segunda = next(v for v, _ in reparto[0]["valores"] if v)
    pulsar(s, reparto[0], valor=segunda)
    pulsar(s, reparto[1], valor="2")
    assert s.reparto == [[s.eleccion["clase"][0], 6], [segunda, 2]]
    historia = llamar(s, "siguiente_resultado")
    assert historia["vista"]["pantalla"] == "historia"
    acciones_conocidas(historia)
    for tarjetas in de_tipo(historia, "respuestas"):
        eleccion = tarjetas["opciones"][0]["id"]
        historia = pulsar(s, tarjetas, respuesta=eleccion)
        pregunta = tarjetas["args"]["pregunta"]
        guardada = s.q.respuestas_subida.get(pregunta)
        assert guardada == eleccion or eleccion in guardada or pregunta not in s.q.respuestas_subida
    # Volver a pulsar una elegida la quita.
    hito = de_tipo(historia, "respuestas")[0]
    elegida = next(o["id"] for o in hito["opciones"] if o["elegida"])
    pulsar(s, hito, respuesta=elegida)
    assert hito["args"]["pregunta"] not in s.q.respuestas_subida
    final = llamar(s, "crear_personaje")
    clases = s.personaje.clases
    assert final["vista"]["pantalla"] == "asistente" and s.personaje.nivel_total == 8
    assert [(e.clase, e.nivel) for e in clases] == [(s.eleccion["clase"][0], 6), (segunda, 2)]


def test_las_respuestas_concretas_de_varias_se_alternan(s):
    nuevo(s, "sencillo", "srd-5.1", "cuestionario-basico")
    llamar(s, "nivel_cuestionario", valor="3")
    llamar(s, "configurar", campo="cantidad", valor="rapido")
    responder_todo(s)
    for indice in range(3):  # la primera clase con preguntas de varias respuestas (conjuros, p. ej.)
        columnas = de_tipo(llamar(s, "volver_resultado"), "recomendaciones")
        pulsar(s, columnas[1], valor=indice)
        historia = llamar(s, "siguiente_resultado")
        varias = [x for x in de_tipo(historia, "respuestas") if x["args"]["pregunta"].startswith("c:")]
        if historia["vista"]["pantalla"] == "historia" and varias:
            break
    else:
        pytest.skip("Ninguna de las clases propuestas trae preguntas concretas")
    tarjetas = varias[0]
    pregunta = tarjetas["args"]["pregunta"]
    for opcion in tarjetas["opciones"]:
        pulsar(s, tarjetas, respuesta=opcion["id"])
    elegir = next(p.elegir for p in s._preguntas_vigentes() if p.id == pregunta)
    marcadas = s.q.respuestas_subida[pregunta]
    assert len(marcadas) == min(elegir, len(tarjetas["opciones"])) and marcadas[-1] == tarjetas["opciones"][-1]["id"]
    pulsar(s, tarjetas, respuesta=marcadas[-1])
    assert marcadas[-1] not in s.q.respuestas_subida.get(pregunta, [])


# ── asistente ────────────────────────────────────────────────────────────


def test_asistente_paso_a_paso(s):
    respuesta = nuevo(s, "normal", "srd-5.1")
    vista = respuesta["vista"]
    assert vista["pantalla"] == "asistente" and vista["paso"] == "inicio" and vista["lateral"][0]["actual"]
    assert respuesta["estado"]["pantalla"] == "asistente"
    for paso in [x["id"] for x in vista["lateral"]]:
        acciones_conocidas(llamar(s, "paso", paso=paso))
    raza = de_tipo(llamar(s, "paso", paso="raza"), "lista_opciones")[0]
    respuesta = pulsar(s, raza, valor="enano")
    listas = de_tipo(respuesta, "lista_opciones")
    assert listas[0]["detalle"]["nombre"] == "Enano" and listas[0]["detalle"]["icono"] == "dwarf-face"
    pulsar(s, listas[1], valor=listas[1]["opciones"][0]["id"])
    clase = de_tipo(llamar(s, "paso", paso="clase"), "lista_opciones")[0]
    respuesta = pulsar(s, clase, valor="mago")
    assert respuesta["vista"]["cabecera"]["icono"] == "pointy-hat"
    eleccion = next(x for x in de_tipo(respuesta, "eleccion") if not x["completa"])
    assert eleccion["modo"] in ("casillas", "desplegables", "buscador") and eleccion["args"] == {"clave": eleccion["clave"]}
    trasfondo = de_tipo(llamar(s, "paso", paso="trasfondo"), "lista_opciones")[0]
    pulsar(s, trasfondo, valor=trasfondo["opciones"][0]["id"])
    completar_pasos(s)
    # Características: compra de puntos.
    respuesta = llamar(s, "paso", paso="caracteristicas")
    pulsar(s, de_tipo(respuesta, "menu")[0], valor="compra")
    respuesta = llamar(s, "asignar", car="int", valor=15)
    assert "Puntos restantes: 18 de 27" in textos(respuesta)
    menos = next(x for x in de_tipo(respuesta, "boton") if x["texto"] == "−" and x["args"]["car"] == "int")
    assert "Puntos restantes: 20 de 27" in textos(pulsar(s, menos))  # 15 cuesta 9 y 14, 7
    pulsar(s, boton(llamar(s, "paso", paso="caracteristicas"), "Repartir"))
    assert len(s.personaje.caracteristicas_base) == 6
    # Equipo: alternativas y objetos por elegir.
    respuesta = llamar(s, "paso", paso="equipo")
    for radios in de_tipo(respuesta, "radios"):
        respuesta = pulsar(s, radios, valor=radios["opciones"][-1][0])
    for menu in [x for x in de_tipo(respuesta, "menu") if x["accion"] == "objeto_equipo"]:
        pulsar(s, menu, valor=menu["valores"][0][0])
    respuesta = llamar(s, "paso", paso="equipo")
    assert "Inventario resultante" in textos(respuesta)
    assert not [x for x in de_tipo(respuesta, "menu") if x["accion"] == "objeto_equipo" and not x["actual"]]
    # Conjuros: trucos y libro, con el límite bloqueando el resto.
    respuesta = llamar(s, "paso", paso="conjuros")
    trucos = de_tipo(respuesta, "casillas")[0]
    for opcion in trucos["opciones"][:3]:
        respuesta = pulsar(s, trucos, id=opcion["id"], marcada=True)
    trucos = de_tipo(respuesta, "casillas")[0]
    assert all(o["bloqueada"] for o in trucos["opciones"] if not o["marcada"])
    libro = de_tipo(respuesta, "casillas")[1]
    for opcion in libro["opciones"][:6]:
        respuesta = pulsar(s, libro, id=opcion["id"], marcada=True)
    preparados = de_tipo(respuesta, "casillas")[-1]
    assert preparados["accion"] == "alternar_preparado" and len(preparados["opciones"]) == 6
    respuesta = pulsar(s, preparados, id=preparados["opciones"][0]["id"], marcada=True)
    assert s.personaje.preparados["mago"] == [preparados["opciones"][0]["id"]]
    pulsar(s, de_tipo(respuesta, "casillas")[1], id=libro["opciones"][0]["id"], marcada=False)
    assert libro["opciones"][0]["id"] not in s.personaje.conjuros["mago"]
    # Detalles.
    respuesta = llamar(s, "paso", paso="detalles")
    nombre = next(x for x in de_tipo(respuesta, "entrada") if x["args"] == {"campo": "nombre"})
    pulsar(s, nombre, valor="  Tobias ")
    rasgos = next(x for x in de_tipo(respuesta, "entrada") if x["args"] == {"campo": "rasgos_personalidad"})
    assert rasgos["multilinea"] and rasgos["sugerencias"]
    pulsar(s, rasgos, valor=rasgos["sugerencias"][0])
    respuesta = llamar(s, "paso", paso="resumen")
    assert s.personaje.nombre == "Tobias" and respuesta["vista"]["cabecera"]["texto"].startswith("Tobias")
    assert de_tipo(respuesta, "preformateado")[0]["texto"]
    incompletos = {x["id"] for x in respuesta["vista"]["lateral"] if not x["completo"]}
    assert incompletos == {"conjuros", "resumen"}  # se ha quitado un conjuro del libro y solo hay uno preparado
    assert s.a.faltan("conjuros") == ["Mago: añade 1 conjuro(s) más al libro", "Mago: prepara 3 conjuro(s) más del libro"]


def test_anterior_y_siguiente(s):
    respuesta = nuevo(s, "normal", "srd-5.1")
    anterior, siguiente = respuesta["vista"]["pie"][:2]
    assert anterior["desactivado"] and siguiente["args"] == {"paso": "raza"}
    respuesta = pulsar(s, siguiente)
    assert respuesta["vista"]["paso"] == "raza" and respuesta["estado"]["paso"] == "raza"


def test_reglas_y_nivel_en_inicio(s):
    respuesta = nuevo(s, "normal", "tasha-2020", "dmg-2014")
    reglas = {x["args"]["regla"] for x in de_tipo(respuesta, "interruptor")}
    assert {"dotes", "multiclase", "opciones_dm", "origen_personalizado", "rasgos_opcionales", "equipo_por_nivel",
            "entrenamiento"} == reglas
    llamar(s, "regla", regla="multiclase", valor=True)
    llamar(s, "regla", regla="rasgos_opcionales", valor=True)
    pulsar(s, de_tipo(respuesta, "menu")[0], valor="5")
    llamar(s, "clase", valor="guerrero")
    respuesta = llamar(s, "paso", paso="clase")
    assert "Rasgos de clase opcionales (Tasha)" in textos(respuesta)
    opcional = next(x for x in de_tipo(respuesta, "interruptor") if x["accion"] == "rasgo_opcional")
    pulsar(s, opcional, valor=True)
    anadir = next(x for x in de_tipo(respuesta, "menu") if x["accion"] == "anadir_clase")
    respuesta = pulsar(s, anadir, valor="picaro")
    assert [(e.clase, e.nivel) for e in s.personaje.clases] == [("guerrero", 4), ("picaro", 1)]
    niveles = next(x for x in de_tipo(respuesta, "menu") if x["accion"] == "niveles_clase")
    pulsar(s, niveles, valor="2")
    assert [(e.clase, e.nivel) for e in s.personaje.clases] == [("guerrero", 3), ("picaro", 2)]
    pulsar(s, boton(llamar(s, "paso", paso="clase"), "Quitar"))
    assert [(e.clase, e.nivel) for e in s.personaje.clases] == [("guerrero", 5)]


def test_objetos_magicos_e_infusiones(s):
    nuevo(s, "normal", "tasha-2020")
    llamar(s, "regla", regla="multiclase", valor=False)
    llamar(s, "nivel", valor="3")
    llamar(s, "raza", valor="humano")
    llamar(s, "clase", valor="artifice")
    completar_pasos(s)
    respuesta = llamar(s, "paso", paso="equipo")
    for radios in de_tipo(respuesta, "radios"):
        pulsar(s, radios, valor=radios["opciones"][0][0])
    respuesta = llamar(s, "paso", paso="equipo")
    nuevo_objeto = next(x for x in de_tipo(respuesta, "menu") if x["accion"] == "nuevo_magico" and x["args"]["campo"] == "id")
    assert boton(respuesta, "Añadir")["desactivado"]
    pulsar(s, nuevo_objeto, valor=nuevo_objeto["valores"][0][0])
    respuesta = llamar(s, "nuevo_magico", campo="bonificador", valor="2")
    respuesta = pulsar(s, boton(respuesta, "Añadir"))
    assert s.a.objetos_magicos()[0]["bonificador"] == 2
    bonificador = next(x for x in de_tipo(respuesta, "menu") if x["accion"] == "bonificador_magico")
    pulsar(s, bonificador, valor="3")
    assert s.a.objetos_magicos()[0]["bonificador"] == 3
    infusiones = [x for x in de_tipo(respuesta, "interruptor") if x["accion"] == "llevar_infusion"]
    assert infusiones, "el artífice de nivel 3 conoce infusiones"
    respuesta = pulsar(s, infusiones[0], valor=True)
    assert s.a.infusiones_propias()[0].llevada or "ningún objeto" in infusiones[0]["ayuda"]
    pulsar(s, boton(respuesta, "Quitar"))
    assert s.a.objetos_magicos() == []


def test_subir_de_nivel_eligiendo_yo(s):
    nuevo(s, "normal", "srd-5.1")
    llamar(s, "raza", valor="humano")
    llamar(s, "clase", valor="guerrero")
    completar_pasos(s)
    respuesta = llamar(s, "paso", paso="resumen")
    niveles = next(x for x in de_tipo(respuesta, "menu") if x["accion"] == "config_subida")
    pulsar(s, niveles, valor="3")
    respuesta = pulsar(s, boton(respuesta, "Elijo yo"))
    assert s.personaje.nivel_total == 4 and respuesta["vista"]["paso"] != "resumen"  # hay subclase que elegir


def test_subir_de_nivel_con_preguntas(s):
    nuevo(s, "normal", "srd-5.1", "cuestionario-basico")
    llamar(s, "raza", valor="humano")
    llamar(s, "clase", valor="mago")
    completar_pasos(s)
    respuesta = llamar(s, "paso", paso="resumen")
    llamar(s, "config_subida", campo="niveles", valor="1")
    subida = pulsar(s, boton(respuesta, "Con preguntas"))
    assert subida["vista"]["pantalla"] == "subida" and subida["estado"]["pantalla"] == "subida"
    acciones_conocidas(subida)
    assert "de 1 a 2" in textos(subida)
    for tarjetas in de_tipo(subida, "respuestas"):
        pulsar(s, tarjetas, respuesta=tarjetas["opciones"][0]["id"])
    final = llamar(s, "aplicar_subida")
    assert final["vista"]["paso"] == "resumen" and s.personaje.nivel_total == 2
    assert s.novedades and de_tipo(final, "avisos")[0]["titulo"] == "Novedades de la subida de nivel"
    assert final["estado"]["novedades"] == s.novedades


def test_cancelar_la_subida(s):
    nuevo(s, "normal", "srd-5.1", "cuestionario-basico")
    llamar(s, "raza", valor="humano")
    llamar(s, "clase", valor="guerrero")
    llamar(s, "paso", paso="resumen")
    llamar(s, "subir", con_preguntas=True)
    respuesta = llamar(s, "cancelar_subida")
    assert respuesta["vista"]["pantalla"] == "asistente" and s.personaje.nivel_total == 1


# ── archivos y estado ───────────────────────────────────────────────────


@pytest.fixture
def mago(s):
    nuevo(s, "normal", "srd-5.1")
    llamar(s, "raza", valor="elfo")
    llamar(s, "clase", valor="mago")
    llamar(s, "detalle", campo="nombre", valor="Ilúvatar/Ñ?")
    completar_pasos(s)
    return s


@pytest.mark.parametrize("formato, inicio, nombre", [
    ("pdf", b"%PDF", "Ilúvatar.pdf"), ("oficial", b"%PDF", "Ilúvatar (hoja oficial).pdf"),
    ("nota", b"---", "Ilúvatar (nota).md"), ("json", b"{", "Ilúvatar.json")])
def test_exportar(mago, formato, inicio, nombre):
    if formato == "oficial":
        from creador.sistemas.dnd5e_2014.salidas import hay_hoja_oficial
        if not hay_hoja_oficial():
            pytest.skip("Sin la plantilla de la hoja oficial")
    archivo = llamar(mago, "exportar", formato=formato)["archivo"]
    datos = base64.b64decode(archivo["datos"])
    assert datos.startswith(inicio) and archivo["nombre"] == nombre.replace("Ilúvatar", "IlúvatarÑ")
    assert archivo["tipo"] in ("application/pdf", "text/markdown", "application/json")


def test_abrir_lo_exportado(mago, usuario):
    datos = llamar(mago, "exportar", formato="json")["archivo"]["datos"]
    otra = Sesion()
    respuesta = llamar(otra, "abrir_personaje", nombre="mago.json", datos=datos)
    assert respuesta["vista"]["paso"] == "resumen" and otra.personaje.a_dict() == mago.personaje.a_dict()
    assert respuesta["estado"]["id"] and respuesta["estado"]["id"] != mago.id
    assert "No se puede abrir" in otra.llamar("abrir_personaje", {"nombre": "x.json", "datos": "bm8gZXMganNvbg=="})["error"]


def test_estado_de_ida_y_vuelta_en_el_asistente(mago, usuario):
    llamar(mago, "paso", paso="equipo")
    estado = json.loads(json.dumps(mago.estado()))
    otra = Sesion()
    respuesta = llamar(otra, "restaurar", estado=estado)
    assert respuesta["vista"] == mago.vista() and otra.id == mago.id
    assert respuesta["estado"]["titulo"] == estado["titulo"]


def test_estado_de_ida_y_vuelta_en_el_cuestionario(s, usuario):
    nuevo(s, "sencillo", "srd-5.1", "cuestionario-basico")
    llamar(s, "nivel_cuestionario", valor="4")
    llamar(s, "configurar", campo="cantidad", valor="rapido")
    llamar(s, "pregunta", indice=0)
    tarjetas = de_tipo(llamar(s, "pregunta", indice=2), "respuestas")[0]
    pulsar(s, tarjetas, respuesta=tarjetas["opciones"][0]["id"])
    estado = s.estado()
    otra = Sesion()
    respuesta = llamar(otra, "restaurar", estado=json.loads(json.dumps(estado)))
    assert respuesta["vista"] == s.vista() and otra.nivel == 4 and otra.q.respuestas == s.q.respuestas
    responder_todo(otra)
    assert llamar(otra, "siguiente_resultado")["vista"]["pantalla"] in ("historia", "asistente")


def test_restaurar_otra_version_da_error(usuario):
    respuesta = Sesion().llamar("restaurar", {"estado": {"version": 99}})
    assert "otra versión" in respuesta["error"] and respuesta["vista"]["pantalla"] == "portada"


def test_volver_al_inicio_olvida_el_personaje(mago):
    respuesta = pulsar(mago, mago.vista()["pie"][-1])
    assert respuesta["vista"]["pantalla"] == "portada" and respuesta["estado"] is None


def test_en_el_navegador_los_paquetes_van_a_la_carpeta_personal(monkeypatch):
    from creador.nucleo import rutas
    monkeypatch.setattr(rutas.sys, "platform", "emscripten")
    assert rutas.directorios_paquetes() == [directorio_datos_integrados() / "paquetes",
                                            Path.home() / ".creador-personajes" / "paquetes"]


def test_portada_deja_sitio_a_los_recientes(s):
    assert [x for x in llamar(s, "ir", pantalla="portada")["vista"]["contenido"] if x["t"] == "recientes"]


def test_sin_tkinter():
    """La web no puede depender de la interfaz de escritorio."""
    fuente = Path(modulo_sesion.__file__).read_text(encoding="utf-8")
    assert "customtkinter" not in fuente and "..gui" not in fuente
