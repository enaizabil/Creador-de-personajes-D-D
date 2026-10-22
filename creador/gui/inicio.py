"""Pantalla de inicio: edición, paquetes de contenido y crear o abrir un personaje."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..entorno import paquetes_instalados
from ..sistemas import listar_sistemas
from .componentes import fuente, texto_ajustado, titulo


class PantallaInicio(ctk.CTkFrame):
    def __init__(self, master, al_crear: Callable[[str, list[str], str], None], al_abrir: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.al_crear = al_crear
        self.disponibles, self.avisos = paquetes_instalados()
        self.sistemas = {s.nombre: s.id for s in listar_sistemas()}
        self.casillas: dict[str, ctk.BooleanVar] = {}

        titulo(self, "Creador de personajes de rol", 26).pack(anchor="w", padx=30, pady=(30, 4))
        texto_ajustado(self, "Elige la edición y los libros o homebrew que se usan en tu mesa. "
                             "Solo aparecerá lo que aporten los paquetes marcados. «Crear con preguntas» decide el "
                             "personaje por ti a partir de situaciones cotidianas; «paso a paso» te deja elegirlo todo.",
                       760, text_color="gray").pack(anchor="w", padx=30)

        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(anchor="w", padx=30, pady=(20, 6))
        ctk.CTkLabel(fila, text="Edición:", font=fuente(14, True)).pack(side="left", padx=(0, 10))
        self.menu_sistema = ctk.CTkOptionMenu(fila, values=list(self.sistemas), width=280, command=self._mostrar_paquetes)
        self.menu_sistema.pack(side="left")

        titulo(self, "Paquetes de contenido", 15).pack(anchor="w", padx=30, pady=(16, 4))
        self.lista = ctk.CTkScrollableFrame(self, height=300)
        self.lista.pack(fill="x", padx=30)

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(anchor="w", padx=30, pady=20)
        ctk.CTkButton(botones, text="Crear con preguntas", width=200, height=40, font=fuente(15, True),
                      command=lambda: self._crear("sencillo")).pack(side="left", padx=(0, 12))
        ctk.CTkButton(botones, text="Crear paso a paso", width=170, height=40,
                      command=lambda: self._crear("normal")).pack(side="left", padx=(0, 12))
        ctk.CTkButton(botones, text="Abrir personaje…", width=160, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=al_abrir).pack(side="left")
        if self.avisos:
            texto_ajustado(self, "Avisos al buscar paquetes: " + "; ".join(self.avisos), 760,
                           text_color=("#b45309", "#fbbf24")).pack(anchor="w", padx=30)
        if self.sistemas:
            self._mostrar_paquetes(next(iter(self.sistemas)))

    @property
    def sistema_id(self) -> str:
        return self.sistemas[self.menu_sistema.get()]

    def _mostrar_paquetes(self, _nombre_sistema: str) -> None:
        for hijo in self.lista.winfo_children():
            hijo.destroy()
        self.casillas = {}
        paquetes = sorted((i for i in self.disponibles.values() if i.sistema == self.sistema_id),
                          key=lambda i: (len(i.depende_de), i.nombre))
        for info in paquetes:
            variable = ctk.BooleanVar(value=info.tipo in ("oficial", "propio"))
            self.casillas[info.id] = variable
            fila = ctk.CTkFrame(self.lista, fg_color="transparent")
            fila.pack(fill="x", pady=4, padx=4)
            ctk.CTkCheckBox(fila, text=info.nombre, variable=variable, font=fuente(14, True),
                            command=lambda i=info.id: self._dependencias(i)).pack(anchor="w")
            detalle = info.descripcion
            if info.depende_de:
                necesita = ", ".join(self.disponibles[d].nombre for d in info.depende_de if d in self.disponibles)
                detalle += f"  (necesita: {necesita})"
            etiqueta = {"oficial": "Oficial", "propio": "Del programa"}.get(info.tipo, "Homebrew")
            texto_ajustado(fila, f"{etiqueta} · {detalle}", 700, text_color="gray").pack(anchor="w", padx=32)

    def _dependencias(self, id_: str) -> None:
        """Marcar un paquete marca sus dependencias; desmarcarlo desmarca los que dependen de él."""
        if self.casillas[id_].get():
            pendientes = list(self.disponibles[id_].depende_de)
            while pendientes:
                dep = pendientes.pop()
                if dep in self.casillas and not self.casillas[dep].get():
                    self.casillas[dep].set(True)
                    pendientes += self.disponibles[dep].depende_de
        else:
            for otro, info in self.disponibles.items():
                if id_ in info.depende_de and otro in self.casillas and self.casillas[otro].get():
                    self.casillas[otro].set(False)
                    self._dependencias(otro)

    def _crear(self, modo: str) -> None:
        elegidos = [id_ for id_, variable in self.casillas.items() if variable.get()]
        self.al_crear(self.sistema_id, elegidos, modo)
