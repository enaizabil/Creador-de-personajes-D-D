import pytest

from ayudas import EntradaClase, ObjetoInventario, nuevo_personaje
from creador.nucleo.personaje import VERSION_FORMATO, Personaje


def test_guardar_y_cargar_conserva_todo(tmp_path):
    personaje = nuevo_personaje(
        nombre="Ánika", raza="elfo", clases=[EntradaClase("mago", 3, tiradas_pg=[4, 2])],
        elecciones={"subraza:elfo_alto/truco": ["luz"]}, equipo=[ObjetoInventario("daga", cantidad=2)],
        detalles={"alineamiento": "Neutral bueno"},
    )
    ruta = tmp_path / "anika.json"
    personaje.guardar(ruta)
    assert "Ánika" in ruta.read_text(encoding="utf-8")
    assert Personaje.cargar(ruta) == personaje
    assert personaje.nivel_total == 3


def test_formato_desconocido_o_mas_nuevo_es_rechazado():
    datos = nuevo_personaje().a_dict()
    with pytest.raises(ValueError, match="Campos desconocidos"):
        Personaje.desde_dict({**datos, "poderes": []})
    with pytest.raises(ValueError, match="más nuevo"):
        Personaje.desde_dict({**datos, "version_formato": VERSION_FORMATO + 1})
