"""Componentes reutilizables de la interfaz (CustomTkinter)."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..nucleo.efectos import EleccionPendiente

NINGUNA = "— elige —"
MAX_CASILLAS = 10  # con más opciones se usan desplegables


def fuente(tamano: int = 13, negrita: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(size=tamano, weight="bold" if negrita else "normal")


def titulo(master, texto: str, tamano: int = 18) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto, font=fuente(tamano, True), anchor="w")


def texto_ajustado(master, texto: str, ancho: int = 520, **opciones) -> ctk.CTkLabel:
    return ctk.CTkLabel(master, text=texto, wraplength=ancho, justify="left", anchor="w", **opciones)


def perfil_en_puntos(perfil: dict, nombres: dict[str, str] | None = None) -> str:
    """{"sigilo": 3, "astucia": 2} -> «Sigilo ●●● · Astucia ●●○»."""
    partes = []
    for rasgo, valor in sorted(perfil.items(), key=lambda x: -x[1]):
        if valor:
            nombre = (nombres or {}).get(rasgo, rasgo.capitalize())
            partes.append(f"{nombre} {'●' * valor}{'○' * (3 - valor)}")
    return " · ".join(partes)


class ListaOpciones(ctk.CTkFrame):
    """Lista de opciones excluyentes con un panel que describe la seleccionada."""

    def __init__(self, master, titulo_lista: str, opciones: list, seleccion: str | None,
                 al_elegir: Callable[[str], None], nombres_paquetes: dict[str, str] | None = None, alto: int = 300,
                 nombres_perfil: dict[str, str] | None = None):
        super().__init__(master, fg_color="transparent")
        self.opciones = {o.id: o for o in opciones}
        self.nombres_paquetes = nombres_paquetes or {}
        self.nombres_perfil = nombres_perfil
        self.variable = ctk.StringVar(value=seleccion or "")
        self.al_elegir = al_elegir
        self.grid_columnconfigure(1, weight=1)

        titulo(self, titulo_lista, 15).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        lista = ctk.CTkScrollableFrame(self, width=230, height=alto)
        lista.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        for opcion in opciones:
            etiqueta = opcion.nombre + ("  (DM)" if opcion.permiso_dm else "")
            ctk.CTkRadioButton(lista, text=etiqueta, value=opcion.id, variable=self.variable,
                               command=self._elegido).pack(anchor="w", pady=3, padx=4)

        self.detalle = ctk.CTkFrame(self)
        self.detalle.grid(row=1, column=1, sticky="nsew")
        self._mostrar_detalle(seleccion)

    def _elegido(self) -> None:
        self._mostrar_detalle(self.variable.get())
        self.al_elegir(self.variable.get())

    def _mostrar_detalle(self, id_: str | None) -> None:
        for hijo in self.detalle.winfo_children():
            hijo.destroy()
        opcion = self.opciones.get(id_ or "")
        if opcion is None:
            texto_ajustado(self.detalle, "Elige una opción de la lista para ver su descripción.",
                           text_color="gray").pack(padx=12, pady=12, anchor="w")
            return
        titulo(self.detalle, opcion.nombre, 16).pack(padx=12, pady=(12, 2), anchor="w")
        origen = self.nombres_paquetes.get(opcion.paquete, opcion.paquete)
        if opcion.permiso_dm:
            origen += " · requiere permiso del DM"
        ctk.CTkLabel(self.detalle, text=origen, text_color="gray", anchor="w").pack(padx=12, anchor="w")
        if opcion.perfil:
            ctk.CTkLabel(self.detalle, text=perfil_en_puntos(opcion.perfil, self.nombres_perfil),
                         anchor="w").pack(padx=12, pady=(6, 0), anchor="w")
        if opcion.descripcion:
            texto_ajustado(self.detalle, opcion.descripcion, 620).pack(padx=12, pady=(8, 12), anchor="w")


class SelectorEleccion(ctk.CTkFrame):
    """Una elección del motor: casillas si hay pocas opciones, desplegables si hay muchas o se repiten."""

    def __init__(self, master, eleccion: EleccionPendiente, al_cambiar: Callable[[str, list[str]], None]):
        super().__init__(master)
        self.eleccion = eleccion
        self.al_cambiar = al_cambiar
        completa = eleccion.faltan <= 0
        cabecera = f"{'✓' if completa else '•'} {eleccion.nombre}  ·  elige {eleccion.elegir}"
        ctk.CTkLabel(self, text=cabecera, font=fuente(14, True), anchor="w",
                     text_color=None if completa else ("#b45309", "#fbbf24")).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(self, text=eleccion.etiqueta, text_color="gray", anchor="w").pack(anchor="w", padx=10)
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="x", padx=10, pady=(4, 10))
        if eleccion.repetible or len(eleccion.opciones) > MAX_CASILLAS:
            self._desplegables(cuerpo)
        else:
            self._casillas(cuerpo)

    def _casillas(self, cuerpo) -> None:
        self.variables = {}
        for i, opcion in enumerate(self.eleccion.opciones):
            variable = ctk.BooleanVar(value=opcion.id in self.eleccion.seleccion)
            casilla = ctk.CTkCheckBox(cuerpo, text=opcion.nombre, variable=variable, command=self._casilla_cambiada)
            casilla.grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=3)
            self.variables[opcion.id] = (variable, casilla)
        self._limitar()

    def _casilla_cambiada(self) -> None:
        elegidas = [id_ for id_, (variable, _) in self.variables.items() if variable.get()]
        self._limitar()
        self.al_cambiar(self.eleccion.clave, elegidas)

    def _limitar(self) -> None:
        llenas = sum(v.get() for v, _ in self.variables.values()) >= self.eleccion.elegir
        for variable, casilla in self.variables.values():
            casilla.configure(state="disabled" if llenas and not variable.get() else "normal")

    def _desplegables(self, cuerpo) -> None:
        nombres = {o.id: o.nombre for o in self.eleccion.opciones}
        self.ids_por_nombre = {o.nombre: o.id for o in self.eleccion.opciones}
        self.menus = []
        for i in range(self.eleccion.elegir):
            actual = self.eleccion.seleccion[i] if i < len(self.eleccion.seleccion) else None
            menu = ctk.CTkOptionMenu(cuerpo, values=[NINGUNA, *nombres.values()], width=260,
                                     command=lambda _valor: self._desplegable_cambiado(), dynamic_resizing=False)
            menu.set(nombres.get(actual, NINGUNA))
            menu.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=3)
            self.menus.append(menu)

    def _desplegable_cambiado(self) -> None:
        elegidas = [self.ids_por_nombre[m.get()] for m in self.menus if m.get() in self.ids_por_nombre]
        self.al_cambiar(self.eleccion.clave, elegidas)


class ListaAvisos(ctk.CTkFrame):
    """Lo que falta para terminar un paso."""

    def __init__(self, master, mensajes: list[str], titulo_lista: str = "Falta por decidir"):
        super().__init__(master, fg_color=("#fef3c7", "#3b2f12") if mensajes else ("#dcfce7", "#14321f"))
        if not mensajes:
            ctk.CTkLabel(self, text="✓ Paso completo", anchor="w").pack(anchor="w", padx=10, pady=6)
            return
        ctk.CTkLabel(self, text=titulo_lista, font=fuente(13, True), anchor="w").pack(anchor="w", padx=10, pady=(6, 0))
        for mensaje in mensajes:
            texto_ajustado(self, f"• {mensaje}", 760).pack(anchor="w", padx=14)
        ctk.CTkFrame(self, height=6, fg_color="transparent").pack()
