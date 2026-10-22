import random

import pytest

from creador.sistemas.dnd5e_2014.caracteristicas import (
    asignar_por_prioridad,
    bonificador_competencia,
    coste_compra,
    modificador,
    tirar_4d6,
    validar_base,
)


def base(*valores):
    return dict(zip(("fue", "des", "con", "int", "sab", "car"), valores, strict=True))


@pytest.mark.parametrize("puntuacion, mod", [(1, -5), (8, -1), (9, -1), (10, 0), (11, 0), (15, 2), (20, 5), (30, 10)])
def test_modificador(puntuacion, mod):
    assert modificador(puntuacion) == mod


@pytest.mark.parametrize("nivel, bono", [(1, 2), (4, 2), (5, 3), (9, 4), (13, 5), (17, 6), (20, 6)])
def test_bonificador_competencia(nivel, bono):
    assert bonificador_competencia(nivel) == bono


def test_compra_por_puntos():
    assert coste_compra(base(15, 15, 15, 8, 8, 8)) == 27
    assert validar_base("compra", base(15, 15, 15, 8, 8, 8)) == []
    assert "gasta 36" in validar_base("compra", base(15, 15, 15, 15, 8, 8))[0]
    assert "Quedan 27" in validar_base("compra", base(8, 8, 8, 8, 8, 8))[0]
    assert "de 8 a 15" in validar_base("compra", base(16, 8, 8, 8, 8, 8))[0]


def test_array_estandar_y_otros_metodos():
    assert validar_base("estandar", base(8, 10, 12, 13, 14, 15)) == []
    assert validar_base("estandar", base(15, 15, 13, 12, 10, 8)) != []
    assert validar_base("tirada", base(18, 3, 10, 10, 10, 10)) == []
    assert validar_base("tirada", base(19, 3, 10, 10, 10, 10)) != []
    assert "Faltan" in validar_base("manual", {"fue": 10})[0]
    assert "desconocido" in validar_base("magia", base(10, 10, 10, 10, 10, 10))[0]


def test_tirada_4d6_reproducible():
    tiradas = tirar_4d6(random.Random(42))
    assert tiradas == tirar_4d6(random.Random(42))
    assert len(tiradas) == 6 and all(3 <= t <= 18 for t in tiradas)


def test_asignar_por_prioridad():
    assert asignar_por_prioridad([8, 10, 12, 13, 14, 15], ["int", "des", "con"]) == {
        "int": 15, "des": 14, "con": 13, "fue": 12, "sab": 10, "car": 8}
    with pytest.raises(ValueError):
        asignar_por_prioridad([15, 14], ["int"])
