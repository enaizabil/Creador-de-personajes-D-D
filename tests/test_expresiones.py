import pytest

from creador.nucleo.expresiones import ErrorExpresion, comprobar, evaluar, rellenar

CONTEXTO = {"nivel": 5, "nivel_clase": 3, "mod_car": 2, "escala": "1d6"}


def test_evaluar_y_rellenar():
    assert evaluar("nivel_clase*5", CONTEXTO) == 15
    assert evaluar("max(1, mod_car - 4)", CONTEXTO) == 1
    assert evaluar("nivel // 2 + -1", CONTEXTO) == 1
    assert rellenar("Reserva de {nivel_clase*5} PG; dado {escala}", CONTEXTO) == "Reserva de 15 PG; dado 1d6"
    assert rellenar("Sin huecos", CONTEXTO) == "Sin huecos"


@pytest.mark.parametrize("expresion", ["nivel ** 2", "__import__('os')", "nivel.real", "otra + 1", "nivel /", "[1][0]"])
def test_expresiones_no_permitidas(expresion):
    with pytest.raises(ErrorExpresion):
        evaluar(expresion, CONTEXTO)


def test_comprobar_plantillas():
    assert comprobar("{nivel_clase*5} PG", {"nivel_clase"}) == []
    assert "desconocida" in comprobar("{nivel_cls}", {"nivel_clase"})[0]
    assert comprobar("1+mod_car", {"mod_car"}, es_expresion=True) == []
