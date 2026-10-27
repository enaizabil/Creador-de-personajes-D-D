"""Componentes reutilizables de la interfaz (CustomTkinter)."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..nucleo.efectos import EleccionPendiente
from ..nucleo.texto import clave_alfabetica
from .estilo import fuente_titulo

NINGUNA = "— elige —"
MAX_CASILLAS = 10  # con más opciones se usan desplegables
MAX_DESPLEGABLE = 40  # con más aún (Secretos Mágicos: cualquier conjuro), un buscador
MAX_RESULTADOS = 20  # casillas que muestra el buscador a la vez (cada una cuesta ~5 ms de dibujo)
ESPERA_BUSQUEDA = 250  # ms sin teclear antes de repintar los resultados
_BUSQUEDAS: dict[str, str] = {}  # texto buscado por elección: el paso se redibuja tras cada clic


def fuente(tamano: int = 13, negrita: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(size=tamano, weight="bold" if negrita else "normal")


def titulo(master, texto: str, tamano: int = 18, imagen: ctk.CTkImage | None = None) -> ctk.CTkLabel:
    """Título en Cinzel; con «imagen», el icono a su izquierda."""
    return ctk.CTkLabel(master, text=f"  {texto}" if imagen else texto, font=fuente_titulo(tamano), anchor="w",
                        image=imagen, compound="left")


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
                 nombres_perfil: dict[str, str] | None = None,
                 icono: Callable[[str], ctk.CTkImage | None] | None = None):
        super().__init__(master, fg_color="transparent")
        self.opciones = {o.id: o for o in opciones}
        self.icono = icono  # id de la opción -> icono grande junto a su nombre en el panel de detalle
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
        titulo(self.detalle, opcion.nombre, 18, self.icono(opcion.id) if self.icono else None).pack(
            padx=12, pady=(12, 2), anchor="w")
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
    """Una elección del motor: casillas si hay pocas opciones, desplegables si hay muchas o se repiten y un
    buscador si hay tantas que un desplegable no cabría en pantalla."""

    def __init__(self, master, eleccion: EleccionPendiente, al_cambiar: Callable[[str, list[str]], None],
                 bloqueadas: dict[str, str] | None = None):
        super().__init__(master)
        self.eleccion = eleccion
        self.al_cambiar = al_cambiar
        # Opción -> motivo («ya la tienes», «sin competencia»): no se ofrece, o se marca si ya está elegida.
        self.bloqueadas = bloqueadas or {}
        completa = eleccion.faltan <= 0
        cabecera = f"{'✓' if completa else '•'} {eleccion.nombre}  ·  elige {eleccion.elegir}"
        ctk.CTkLabel(self, text=cabecera, font=fuente(14, True), anchor="w",
                     text_color=None if completa else ("#b45309", "#fbbf24")).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(self, text=eleccion.etiqueta, text_color="gray", anchor="w").pack(anchor="w", padx=10)
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="x", padx=10, pady=(4, 10))
        if not eleccion.repetible and len(eleccion.opciones) > MAX_DESPLEGABLE:
            self._buscador(cuerpo)
        elif eleccion.repetible or len(eleccion.opciones) > MAX_CASILLAS:
            self._desplegables(cuerpo)
        else:
            self._casillas(cuerpo)

    def _texto(self, opcion) -> str:
        motivo = self.bloqueadas.get(opcion.id)
        return f"{opcion.nombre} ({motivo})" if motivo else opcion.nombre

    def _casillas(self, cuerpo) -> None:
        self.variables = {}
        for i, opcion in enumerate(self.eleccion.opciones):
            variable = ctk.BooleanVar(value=opcion.id in self.eleccion.seleccion)
            texto = self._texto(opcion)
            casilla = ctk.CTkCheckBox(cuerpo, text=texto, variable=variable, command=self._casilla_cambiada)
            casilla.grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=3)
            self.variables[opcion.id] = (variable, casilla)
        self._limitar()

    def _casilla_cambiada(self) -> None:
        elegidas = [id_ for id_, (variable, _) in self.variables.items() if variable.get()]
        self._limitar()
        self.al_cambiar(self.eleccion.clave, elegidas)

    def _limitar(self) -> None:
        llenas = sum(v.get() for v, _ in self.variables.values()) >= self.eleccion.elegir
        for id_, (variable, casilla) in self.variables.items():
            bloqueada = (llenas or id_ in self.bloqueadas) and not variable.get()
            casilla.configure(state="disabled" if bloqueada else "normal")

    def _buscador(self, cuerpo) -> None:
        self.elegidas = list(self.eleccion.seleccion)
        # Sin textvariable: con ella CustomTkinter no muestra el texto de ayuda del campo vacío.
        self.busqueda = ctk.CTkEntry(cuerpo, width=320,
                                     placeholder_text=f"Buscar entre {len(self.eleccion.opciones)} opciones…")
        if _BUSQUEDAS.get(self.eleccion.clave):
            self.busqueda.insert(0, _BUSQUEDAS[self.eleccion.clave])
        self.busqueda.pack(anchor="w", pady=(0, 4))
        self.resumen_elegidas = ctk.CTkLabel(cuerpo, text="", anchor="w", justify="left", wraplength=640)
        self.resumen_elegidas.pack(anchor="w")
        self.resultados = ctk.CTkScrollableFrame(cuerpo, height=180)
        self.resultados.pack(fill="x", pady=(4, 0))
        self._pendiente = None
        self.busqueda.bind("<KeyRelease>", lambda _evento: self._programar_busqueda())
        self._pintar_resultados()

    def _programar_busqueda(self) -> None:
        # Se repinta cuando deja de teclear, no en cada pulsación: así escribir no se vuelve lento.
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(ESPERA_BUSQUEDA, self._busqueda_cambiada)

    def _busqueda_cambiada(self) -> None:
        self._pendiente = None
        _BUSQUEDAS[self.eleccion.clave] = self.busqueda.get()
        self._pintar_resultados()

    def destroy(self) -> None:
        if getattr(self, "_pendiente", None):
            self.after_cancel(self._pendiente)
        super().destroy()

    def _pintar_resultados(self) -> None:
        for hijo in self.resultados.winfo_children():
            hijo.destroy()
        nombres = {o.id: o.nombre for o in self.eleccion.opciones}
        self.resumen_elegidas.configure(
            text="Elegidas: " + (", ".join(nombres.get(i, i) for i in self.elegidas) or "ninguna"))
        buscado = clave_alfabetica(self.busqueda.get().strip())
        coinciden = [o for o in self.eleccion.opciones if buscado in clave_alfabetica(o.nombre)]
        # Las elegidas primero, para poder quitarlas sin buscarlas.
        coinciden.sort(key=lambda o: o.id not in self.elegidas)
        llenas = len(self.elegidas) >= self.eleccion.elegir
        for opcion in coinciden[:MAX_RESULTADOS]:
            marcada = opcion.id in self.elegidas
            variable = ctk.BooleanVar(value=marcada)
            casilla = ctk.CTkCheckBox(self.resultados, text=self._texto(opcion), variable=variable,
                                      command=lambda i=opcion.id, v=variable: self._buscador_cambiado(i, v.get()))
            if not marcada and (llenas or opcion.id in self.bloqueadas):
                casilla.configure(state="disabled")
            casilla.pack(anchor="w", padx=4, pady=2)
        if len(coinciden) > MAX_RESULTADOS:
            ctk.CTkLabel(self.resultados, text=f"… y {len(coinciden) - MAX_RESULTADOS} más: escribe para afinar",
                         text_color="gray").pack(anchor="w", padx=4)
        elif not coinciden:
            ctk.CTkLabel(self.resultados, text="Nada coincide con la búsqueda", text_color="gray").pack(anchor="w")

    def _buscador_cambiado(self, id_: str, marcada: bool) -> None:
        if marcada and id_ not in self.elegidas:
            self.elegidas.append(id_)
        elif not marcada and id_ in self.elegidas:
            self.elegidas.remove(id_)
        self._pintar_resultados()
        self.al_cambiar(self.eleccion.clave, list(self.elegidas))

    def _desplegables(self, cuerpo) -> None:
        nombres = {o.id: self._texto(o) for o in self.eleccion.opciones}
        self.ids_por_nombre = {nombre: id_ for id_, nombre in nombres.items()}
        libres = [nombre for id_, nombre in nombres.items() if id_ not in self.bloqueadas]
        self.menus = []
        for i in range(self.eleccion.elegir):
            actual = self.eleccion.seleccion[i] if i < len(self.eleccion.seleccion) else None
            valores = [NINGUNA, *libres, *([nombres[actual]] if actual in self.bloqueadas else [])]
            menu = ctk.CTkOptionMenu(cuerpo, values=valores, width=260,
                                     command=lambda _valor: self._desplegable_cambiado(), dynamic_resizing=False)
            menu.set(nombres.get(actual, NINGUNA))
            menu.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=3)
            self.menus.append(menu)

    def _desplegable_cambiado(self) -> None:
        elegidas = [self.ids_por_nombre[m.get()] for m in self.menus if m.get() in self.ids_por_nombre]
        self.al_cambiar(self.eleccion.clave, elegidas)


class ListaAvisos(ctk.CTkFrame):
    """Lo que falta para terminar un paso."""

    def __init__(self, master, mensajes: list[str], titulo_lista: str = "Falta por decidir", completo: bool = False):
        # «completo»: los mensajes son buenas noticias (novedades de una subida), en verde.
        verde = ("#dde8cc", "#1f2e1a")
        super().__init__(master, fg_color=verde if completo or not mensajes else ("#f3e0b0", "#3b2f12"))
        if not mensajes:
            ctk.CTkLabel(self, text="✓ Paso completo", anchor="w").pack(anchor="w", padx=10, pady=6)
            return
        ctk.CTkLabel(self, text=titulo_lista, font=fuente(13, True), anchor="w").pack(anchor="w", padx=10, pady=(6, 0))
        for mensaje in mensajes:
            texto_ajustado(self, f"• {mensaje}", 760).pack(anchor="w", padx=14)
        ctk.CTkFrame(self, height=6, fg_color="transparent").pack()
