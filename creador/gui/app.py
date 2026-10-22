"""Ventana principal: pantalla de inicio y asistente de creación."""
from __future__ import annotations

import json
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import __version__
from ..entorno import abrir_catalogo
from ..nucleo.paquetes import ErrorPaquete
from ..nucleo.personaje import Personaje
from .asistente_5e import VistaAsistente5e
from .inicio import PantallaInicio

# Vista del asistente de cada sistema de reglas.
VISTAS = {"dnd5e-2014": VistaAsistente5e}


class Aplicacion(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.title(f"Creador de personajes de rol {__version__}")
        self.geometry("1200x780")
        self.minsize(980, 640)
        self.vista = None
        self.mostrar_inicio()

    def _cambiar(self, vista) -> None:
        if self.vista is not None:
            self.vista.destroy()
        self.vista = vista
        vista.pack(fill="both", expand=True)

    def mostrar_inicio(self) -> None:
        self._cambiar(PantallaInicio(self, self.crear, self.abrir))

    def _cargar(self, personaje: Personaje) -> None:
        try:
            sistema, catalogo, errores = abrir_catalogo(personaje.sistema, personaje.paquetes)
        except (ErrorPaquete, KeyError) as exc:
            messagebox.showerror("No se pueden cargar los paquetes", str(exc))
            return
        if errores:
            resumen = "\n".join(errores[:12]) + (f"\n… y {len(errores) - 12} más" if len(errores) > 12 else "")
            if not messagebox.askyesno("Errores en los paquetes", f"{resumen}\n\n¿Continuar de todos modos?"):
                return
        vista = VISTAS.get(sistema.id)
        if vista is None:
            messagebox.showerror("Sin asistente", f"El sistema «{sistema.nombre}» aún no tiene asistente de creación.")
            return
        self._cambiar(vista(self, sistema.crear_asistente(personaje, catalogo), self.mostrar_inicio))

    def crear(self, sistema_id: str, paquetes: list[str]) -> None:
        if not paquetes:
            messagebox.showwarning("Sin paquetes", "Marca al menos un paquete de contenido.")
            return
        self._cargar(Personaje(sistema=sistema_id, paquetes=paquetes))

    def abrir(self) -> None:
        ruta = filedialog.askopenfilename(filetypes=[("Personaje", "*.json")])
        if not ruta:
            return
        try:
            personaje = Personaje.cargar(ruta)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror("No se puede abrir", f"{ruta}\n\n{exc}")
            return
        self._cargar(personaje)


def ejecutar() -> None:
    Aplicacion().mainloop()
