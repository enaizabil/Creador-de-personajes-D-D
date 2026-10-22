"""Modo sencillo de 5e (2014): preguntas de situaciones, resultado y paso al asistente para retocar."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..sistemas.dnd5e_2014.cuestionario import MINIMO_RESPUESTAS, Cuestionario5e, Recomendacion
from .asistente_5e import NOMBRES_PERFIL
from .componentes import fuente, texto_ajustado, titulo

ANCHO = 820
COLOR_TARJETA = ("gray86", "gray20")
COLOR_TARJETA_ENCIMA = ("gray78", "gray28")
COLOR_TARJETA_ELEGIDA = ("#bfdbfe", "#1e3a5f")
CUANTAS_RECOMENDACIONES = 3


class TarjetaRespuesta(ctk.CTkFrame):
    """Respuesta pulsable con el texto ajustado (un CTkButton no parte líneas)."""

    def __init__(self, master, texto: str, elegida: bool, al_pulsar: Callable[[], None]):
        super().__init__(master, fg_color=COLOR_TARJETA_ELEGIDA if elegida else COLOR_TARJETA, corner_radius=10,
                         cursor="hand2")
        self.color = COLOR_TARJETA_ELEGIDA if elegida else COLOR_TARJETA
        self.etiqueta = ctk.CTkLabel(self, text=texto, font=fuente(15), wraplength=ANCHO - 60, justify="left",
                                     anchor="w", cursor="hand2")
        self.etiqueta.pack(fill="x", padx=18, pady=14)
        for widget in (self, self.etiqueta):
            widget.bind("<Button-1>", lambda _e: al_pulsar())
            widget.bind("<Enter>", lambda _e: self.configure(fg_color=COLOR_TARJETA_ENCIMA))
            widget.bind("<Leave>", lambda _e: self.configure(fg_color=self.color))


class VistaCuestionario5e(ctk.CTkFrame):
    def __init__(self, master, cuestionario: Cuestionario5e, al_terminar: Callable[[], None], al_volver: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.q = cuestionario
        self.al_terminar = al_terminar
        self.al_volver = al_volver
        self.preguntas = cuestionario.preguntas()
        self.indice = 0
        self.nivel = 1
        self.eleccion: dict[str, Recomendacion] = {}
        self.cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True)
        self.pantalla_inicio()

    def _limpiar(self) -> ctk.CTkFrame:
        for hijo in self.cuerpo.winfo_children():
            hijo.destroy()
        self.cuerpo._parent_canvas.yview_moveto(0)
        columna = ctk.CTkFrame(self.cuerpo, fg_color="transparent", width=ANCHO)
        columna.pack(pady=24, padx=20)
        return columna

    # ── pantallas ─────────────────────────────────────────────────────────

    def pantalla_inicio(self) -> None:
        columna = self._limpiar()
        titulo(columna, "Crea tu personaje respondiendo preguntas", 26).pack(anchor="w")
        texto_ajustado(columna, "No hace falta saber nada de reglas. Te contaremos situaciones de la vida cotidiana y "
                                "tú dices qué haría tu personaje. Con eso proponemos raza, clase, trasfondo, características "
                                "y todo lo demás. Al final podrás cambiar lo que quieras.", ANCHO,
                       font=fuente(15)).pack(anchor="w", pady=(10, 18))
        texto_ajustado(columna, f"Son {len(self.preguntas)} preguntas; con {MINIMO_RESPUESTAS} ya hay un resultado. "
                                "Puedes saltarte las que no te convenzan.", ANCHO, text_color="gray").pack(anchor="w")
        fila = ctk.CTkFrame(columna, fg_color="transparent")
        fila.pack(anchor="w", pady=18)
        ctk.CTkLabel(fila, text="Nivel del personaje:", font=fuente(14, True)).pack(side="left", padx=(0, 10))
        maximo = self.q.asistente.nivel_maximo()
        menu = ctk.CTkOptionMenu(fila, values=[str(n) for n in range(1, maximo + 1)], width=80,
                                 command=lambda v: setattr(self, "nivel", int(v)))
        menu.set(str(self.nivel))
        menu.pack(side="left")
        ctk.CTkLabel(fila, text="(si no te lo han dicho, nivel 1)", text_color="gray").pack(side="left", padx=10)
        botones = ctk.CTkFrame(columna, fg_color="transparent")
        botones.pack(anchor="w", pady=10)
        ctk.CTkButton(botones, text="Empezar", width=180, height=40, font=fuente(15, True),
                      command=lambda: self.pantalla_pregunta(0)).pack(side="left")
        ctk.CTkButton(botones, text="Volver al inicio", width=150, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.al_volver).pack(side="left", padx=12)

    def pantalla_pregunta(self, indice: int) -> None:
        if indice >= len(self.preguntas):
            self.pantalla_resultado()
            return
        self.indice = indice
        pregunta = self.preguntas[indice]
        columna = self._limpiar()
        ctk.CTkLabel(columna, text=f"Pregunta {indice + 1} de {len(self.preguntas)}  ·  {pregunta.titulo}",
                     text_color="gray", anchor="w").pack(anchor="w")
        barra = ctk.CTkProgressBar(columna, width=ANCHO)
        barra.set(indice / len(self.preguntas))
        barra.pack(anchor="w", pady=(6, 22))
        texto_ajustado(columna, pregunta.texto, ANCHO, font=fuente(22, True)).pack(anchor="w", pady=(0, 18))
        actual = self.q.respuestas.get(pregunta.id)
        for respuesta in pregunta.respuestas:
            TarjetaRespuesta(columna, respuesta.texto, respuesta.id == actual,
                             lambda r=respuesta.id: self._responder(pregunta.id, r)).pack(fill="x", pady=5)

        pie = ctk.CTkFrame(columna, fg_color="transparent")
        pie.pack(fill="x", pady=(22, 0))
        ctk.CTkButton(pie, text="← Anterior", width=120,
                      command=lambda: self.pantalla_pregunta(indice - 1) if indice else self.pantalla_inicio()).pack(side="left")
        ctk.CTkButton(pie, text="Saltar", width=100, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"),
                      command=lambda: self._saltar(pregunta.id)).pack(side="left", padx=10)
        respondidas = len(self.q.respuestas)
        if respondidas >= MINIMO_RESPUESTAS:
            ctk.CTkButton(pie, text="Ver mi personaje ya →", width=180,
                          command=self.pantalla_resultado).pack(side="right")
        else:
            ctk.CTkLabel(pie, text=f"{respondidas} respondidas", text_color="gray").pack(side="right")

    def _responder(self, pregunta: str, respuesta: str) -> None:
        self.q.responder(pregunta, respuesta)
        self.pantalla_pregunta(self.indice + 1)

    def _saltar(self, pregunta: str) -> None:
        self.q.responder(pregunta, None)
        self.pantalla_pregunta(self.indice + 1)

    def pantalla_resultado(self) -> None:
        columna = self._limpiar()
        if len(self.q.respuestas) < MINIMO_RESPUESTAS:
            titulo(columna, "Faltan respuestas", 22).pack(anchor="w")
            texto_ajustado(columna, f"Responde al menos {MINIMO_RESPUESTAS} preguntas para tener un resultado fiable "
                                    f"(llevas {len(self.q.respuestas)}).", ANCHO).pack(anchor="w", pady=10)
            ctk.CTkButton(columna, text="Volver a las preguntas",
                          command=lambda: self.pantalla_pregunta(0)).pack(anchor="w")
            return
        titulo(columna, "Así es tu personaje", 26).pack(anchor="w")
        perfil = sorted(self.q.perfil().items(), key=lambda x: -x[1])[:3]
        rasgos = ", ".join(NOMBRES_PERFIL.get(r, r).lower() for r, _ in perfil)
        texto_ajustado(columna, f"Lo que más le define: {rasgos}. Alineamiento: {self.q.alineamiento()}. "
                                "Te proponemos lo que mejor encaja; puedes elegir otra opción de cada lista.", ANCHO,
                       font=fuente(15)).pack(anchor="w", pady=(8, 16))

        rejilla = ctk.CTkFrame(columna, fg_color="transparent")
        rejilla.pack(fill="x")
        for col, (clave, nombre, recomendaciones) in enumerate((
                ("raza", "Raza", self.q.recomendar_razas()),
                ("clase", "Clase", self.q.recomendar_clases()),
                ("trasfondo", "Trasfondo", self.q.recomendar_trasfondos()))):
            rejilla.grid_columnconfigure(col, weight=1, uniform="col")
            self._columna_recomendaciones(rejilla, col, clave, nombre, recomendaciones[:CUANTAS_RECOMENDACIONES])

        fila = ctk.CTkFrame(columna, fg_color="transparent")
        fila.pack(anchor="w", pady=(20, 6))
        ctk.CTkLabel(fila, text="Nombre:", font=fuente(14, True)).pack(side="left", padx=(0, 10))
        self.entrada_nombre = ctk.CTkEntry(fila, width=300, placeholder_text="Cómo se llama tu personaje")
        self.entrada_nombre.insert(0, self.q.personaje.nombre)
        self.entrada_nombre.pack(side="left")
        botones = ctk.CTkFrame(columna, fg_color="transparent")
        botones.pack(anchor="w", pady=14)
        ctk.CTkButton(botones, text="Crear personaje", width=200, height=40, font=fuente(15, True),
                      command=self._crear).pack(side="left")
        ctk.CTkButton(botones, text="Repasar las preguntas", width=180, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=lambda: self.pantalla_pregunta(0)).pack(side="left", padx=12)

    def _columna_recomendaciones(self, rejilla, col: int, clave: str, nombre: str,
                                 recomendaciones: list[Recomendacion]) -> None:
        caja = ctk.CTkFrame(rejilla)
        caja.grid(row=0, column=col, sticky="nsew", padx=6)
        titulo(caja, nombre, 16).pack(anchor="w", padx=12, pady=(10, 4))
        actual = self.eleccion.get(clave)
        if actual not in recomendaciones:
            actual = recomendaciones[0]
        self.eleccion[clave] = actual
        variable = ctk.IntVar(value=recomendaciones.index(actual))
        descripcion = texto_ajustado(caja, actual.descripcion, 230, text_color="gray")

        def elegir(i=None):
            self.eleccion[clave] = recomendaciones[variable.get()]
            descripcion.configure(text=self.eleccion[clave].descripcion)

        for i, recomendacion in enumerate(recomendaciones):
            fila = ctk.CTkFrame(caja, fg_color="transparent")
            fila.pack(fill="x", padx=12, pady=3)
            ctk.CTkRadioButton(fila, text=recomendacion.nombre_completo, value=i, variable=variable,
                               command=elegir).pack(anchor="w")
            barra = ctk.CTkProgressBar(fila, height=8)
            barra.set(recomendacion.afinidad / 100)
            barra.pack(fill="x", padx=(28, 0), pady=(2, 0))
            ctk.CTkLabel(fila, text=f"afinidad {recomendacion.afinidad}%", text_color="gray",
                         font=fuente(11)).pack(anchor="e")
        descripcion.pack(anchor="w", padx=12, pady=(6, 12))

    def _crear(self) -> None:
        raza, clase, trasfondo = (self.eleccion[c] for c in ("raza", "clase", "trasfondo"))
        self.q.generar(nivel=self.nivel, raza=raza.id, subraza=raza.subraza, clase=clase.id, trasfondo=trasfondo.id)
        nombre = self.entrada_nombre.get().strip()
        if nombre:
            self.q.asistente.establecer_detalle("nombre", nombre)
        self.al_terminar()
