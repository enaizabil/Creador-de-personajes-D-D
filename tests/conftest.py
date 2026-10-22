import pytest

from ayudas import DIRECTORIO_PAQUETES
from creador.entorno import abrir_catalogo


@pytest.fixture(scope="session")
def entorno():
    sistema, catalogo, errores = abrir_catalogo("dnd5e-2014", ["prueba"], [DIRECTORIO_PAQUETES])
    assert errores == []
    return sistema, catalogo


@pytest.fixture
def sistema(entorno):
    return entorno[0]


@pytest.fixture
def catalogo(entorno):
    return entorno[1]
