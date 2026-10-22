import json

import pytest

from creador.nucleo.paquetes import ErrorPaquete, cargar_catalogo, descubrir_paquetes, fusionar
from creador.sistemas import obtener_sistema

SISTEMA = obtener_sistema("dnd5e-2014")
RAZA = {"id": "orco", "nombre": "Orco", "tamano": "mediano", "velocidad": 30, "efectos": []}


def crear_paquete(raiz, id_, contenido, depende_de=(), sistema="dnd5e-2014"):
    carpeta = raiz / id_
    carpeta.mkdir(parents=True)
    manifiesto = {"id": id_, "nombre": id_, "sistema": sistema, "version": "1",
                  "archivos": ["contenido.json"], "depende_de": list(depende_de)}
    (carpeta / "paquete.json").write_text(json.dumps(manifiesto), encoding="utf-8")
    texto = contenido if isinstance(contenido, str) else json.dumps(contenido)
    (carpeta / "contenido.json").write_text(texto, encoding="utf-8")


def cargar(raiz, *ids):
    disponibles, avisos = descubrir_paquetes([raiz])
    assert avisos == []
    return cargar_catalogo(SISTEMA, ids, disponibles)


def test_paquete_de_prueba_es_valido(entorno):
    _, catalogo = entorno
    assert catalogo.obtener("razas", "enano")["nombre"] == "Enano"
    assert catalogo.origen("clases", "guerrero") == "prueba"


def test_dependencias_se_cargan_primero_y_modifica_fusiona(tmp_path):
    crear_paquete(tmp_path, "base", {"razas": [RAZA]})
    crear_paquete(tmp_path, "expansion", {
        "razas": [{"id": "orco", "modifica": True, "efectos": [{"tipo": "caracteristica", "car": "fue", "valor": 2}]}],
        "subrazas": [{"id": "orco_gris", "nombre": "Orco gris", "raza": "orco"}],
    }, depende_de=["base"])
    catalogo, errores = cargar(tmp_path, "expansion")
    assert errores == []
    assert [p.id for p in catalogo.paquetes] == ["base", "expansion"]
    assert catalogo.obtener("razas", "orco")["efectos"] == [{"tipo": "caracteristica", "car": "fue", "valor": 2}]
    assert catalogo.origen("razas", "orco") == "base"


def test_id_duplicado_es_error_salvo_reemplaza(tmp_path):
    crear_paquete(tmp_path, "a", {"razas": [RAZA]})
    crear_paquete(tmp_path, "b", {"razas": [RAZA]}, depende_de=["a"])
    crear_paquete(tmp_path, "c", {"razas": [{**RAZA, "nombre": "Orco nuevo", "reemplaza": True}]}, depende_de=["a"])
    _, errores = cargar(tmp_path, "b")
    assert any("duplicado" in e for e in errores)
    catalogo, errores = cargar(tmp_path, "c")
    assert errores == []
    assert catalogo.obtener("razas", "orco")["nombre"] == "Orco nuevo"
    assert "reemplaza" not in catalogo.obtener("razas", "orco")


def test_modifica_sin_base_es_error(tmp_path):
    crear_paquete(tmp_path, "a", {"razas": [{"id": "orco", "modifica": True, "velocidad": 35}]})
    _, errores = cargar(tmp_path, "a")
    assert any("modifica" in e for e in errores)


def test_dependencia_ausente_y_circular(tmp_path):
    crear_paquete(tmp_path, "a", {}, depende_de=["no_existe"])
    crear_paquete(tmp_path, "x", {}, depende_de=["y"])
    crear_paquete(tmp_path, "y", {}, depende_de=["x"])
    with pytest.raises(ErrorPaquete, match="no está instalado"):
        cargar(tmp_path, "a")
    with pytest.raises(ErrorPaquete, match="circular"):
        cargar(tmp_path, "x")


def test_paquete_de_otro_sistema_es_rechazado(tmp_path):
    crear_paquete(tmp_path, "a", {}, sistema="dnd35")
    with pytest.raises(ErrorPaquete, match="sistema"):
        cargar(tmp_path, "a")


def test_errores_de_contenido_indican_donde(tmp_path):
    crear_paquete(tmp_path, "roto", '{"razas": [ {"id": "x",, } ]}')
    _, errores = cargar(tmp_path, "roto")
    assert len(errores) == 1 and "línea 1" in errores[0]

    crear_paquete(tmp_path, "malo", {
        "monstruos": [],
        "razas": [{"id": "sin_velocidad", "nombre": "X", "tamano": "mediano"},
                  {**RAZA, "efectos": [{"tipo": "volar_alto"},
                                       {"tipo": "competencia", "categoria": "habilidad", "id": "cocina"}]}],
        "subrazas": [{"id": "huerfana", "nombre": "Huérfana", "raza": "inexistente"}],
        "dotes": [{"id": "d", "nombre": "D", "efectos": [{"tipo": "eleccion", "id": "e", "opciones": {"desde": "pociones"}}]},
                  {"id": "f", "nombre": "F", "efectos": [{"tipo": "competencia", "categoria": "arma", "id": "espada_lser"},
                                                         {"tipo": "competencia", "categoria": "arma", "id": "armas_marciales"}]}],
    })
    _, errores = cargar(tmp_path, "malo")
    texto = "\n".join(errores)
    assert "categoría desconocida «monstruos»" in texto
    assert "razas/sin_velocidad: falta el campo «velocidad»" in texto
    assert "efectos[0]: tipo de efecto desconocido «volar_alto»" in texto
    assert "habilidad desconocida «cocina»" in texto
    assert "la raza «inexistente» no existe" in texto
    assert "fuente de opciones desconocida «pociones»" in texto
    assert "dotes/f: «espada_lser» no existe en objetos" in texto
    assert "armas_marciales" not in texto


def test_paquete_duplicado_en_varios_directorios(tmp_path):
    crear_paquete(tmp_path / "uno", "a", {})
    crear_paquete(tmp_path / "dos", "a", {})
    disponibles, avisos = descubrir_paquetes([tmp_path / "uno", tmp_path / "dos"])
    assert disponibles["a"].ruta == tmp_path / "uno" / "a"
    assert len(avisos) == 1


def test_fusionar():
    base = {"a": 1, "lista": [1, 2], "sub": {"x": 1, "y": [1]}}
    assert fusionar(base, {"a": 2, "lista": [2, 3], "sub": {"y": [2]}}) == {
        "a": 2, "lista": [1, 2, 3], "sub": {"x": 1, "y": [1, 2]}}
    assert base["lista"] == [1, 2]
