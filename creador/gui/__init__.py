"""Interfaz gráfica (CustomTkinter). Se importa solo al abrirla, para que el resto funcione sin Tk."""


def ejecutar() -> None:
    from .app import ejecutar as _ejecutar

    _ejecutar()
