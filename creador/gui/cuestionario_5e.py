"""Modo sencillo de 5e (2014): preguntas de situaciones, resultado y paso al asistente para retocar."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..sistemas.dnd5e_2014.cuestionario import MINIMO_RESPUESTAS, NIVEL_MINIMO_MULTICLASE, Cuestionario5e, Recomendacion
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
        self.reparto: list[tuple[str, int]] = []  # el que se usará al crear (propuesto o retocado)
        self.marco_reparto = None
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
                                 command=lambda v: (setattr(self, "nivel", int(v)), self.pantalla_inicio()))
        menu.set(str(self.nivel))
        menu.pack(side="left")
        ctk.CTkLabel(fila, text="(si no te lo han dicho, nivel 1)", text_color="gray").pack(side="left", padx=10)
        # La multiclase confunde a quien empieza: apagada de serie y solo cuando el nivel da para repartir.
        if self.nivel < NIVEL_MINIMO_MULTICLASE:
            if self.q.acepta_multiclase:
                self.q.aceptar_multiclase(False)
        else:
            variable = ctk.BooleanVar(value=self.q.acepta_multiclase)
            ctk.CTkSwitch(columna, text="Multiclase: repartir los niveles entre dos clases (para jugadores con experiencia)",
                          variable=variable, command=lambda: self.q.aceptar_multiclase(variable.get())
                          ).pack(anchor="w", pady=(0, 2))
            ctk.CTkLabel(columna, text="Si no sabes qué es, déjala apagada: tendrás una sola clase.",
                         text_color="gray").pack(anchor="w", padx=50, pady=(0, 6))
        botones = ctk.CTkFrame(columna, fg_color="transparent")
        botones.pack(anchor="w", pady=10)
        ctk.CTkButton(botones, text="Empezar", width=180, height=40, font=fuente(15, True),
                      command=lambda: self.pantalla_pregunta(0)).pack(side="left")
        ctk.CTkButton(botones, text="Volver al inicio", width=150, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.al_volver).pack(side="left", padx=12)

    def pantalla_pregunta(self, indice: int) -> None:
        if indice >= len(self.preguntas):
            # A nivel alto, antes del resultado: lo vivido hasta ahora decide mejoras, dotes, opciones y conjuros.
            if self.nivel > 1 and self.q.preguntas_subida():
                self.pantalla_historia()
            else:
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

    def pantalla_historia(self) -> None:
        """Preguntas de subida al crear por encima de nivel 1: la historia del personaje hasta hoy."""
        desplazamiento = self.cuerpo._parent_canvas.yview()[0]
        columna = self._limpiar()
        titulo(columna, f"Tu historia hasta el nivel {self.nivel}", 26).pack(anchor="w")
        texto_ajustado(columna, "Tu personaje ya ha vivido aventuras. Cuéntanos cómo le han cambiado y con eso decidimos "
                                "sus mejoras, dotes, opciones de clase y conjuros. Puedes dejar preguntas sin responder.",
                       ANCHO, font=fuente(15)).pack(anchor="w", pady=(10, 18))
        for pregunta in self.q.preguntas_subida({"mejora", "subclase", "opciones", "conjuros"}):
            ctk.CTkLabel(columna, text=pregunta.titulo, text_color="gray", anchor="w").pack(anchor="w", pady=(10, 0))
            texto_ajustado(columna, pregunta.texto, ANCHO, font=fuente(19, True)).pack(anchor="w", pady=(2, 10))
            actual = self.q.respuestas_subida.get(pregunta.id)
            for respuesta in pregunta.respuestas:
                TarjetaRespuesta(columna, respuesta.texto, respuesta.id == actual,
                                 lambda p=pregunta.id, r=respuesta.id, act=actual: (
                                     self.q.responder_subida(p, None if r == act else r), self.pantalla_historia())
                                 ).pack(fill="x", pady=4)
        pie = ctk.CTkFrame(columna, fg_color="transparent")
        pie.pack(fill="x", pady=(24, 0))
        ctk.CTkButton(pie, text="← Anterior", width=120,
                      command=lambda: self.pantalla_pregunta(len(self.preguntas) - 1)).pack(side="left")
        ctk.CTkButton(pie, text="Ver mi personaje →", width=180, command=self.pantalla_resultado).pack(side="right")
        self.update_idletasks()
        self.cuerpo._parent_canvas.yview_moveto(desplazamiento)

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
        if self.q.acepta_multiclase:
            self.marco_reparto = ctk.CTkFrame(columna)
            self.marco_reparto.pack(fill="x", pady=(14, 0))
            self.reparto = self.q.proponer_reparto(self.nivel, self.eleccion["clase"].id)
            self._pintar_reparto()

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
            if clave == "clase" and self.marco_reparto is not None:
                self.reparto = self.q.proponer_reparto(self.nivel, self.eleccion["clase"].id)
                self._pintar_reparto()

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

    def _pintar_reparto(self) -> None:
        """Multiclase: el reparto propuesto, con la segunda clase y sus niveles a elegir."""
        for hijo in self.marco_reparto.winfo_children():
            hijo.destroy()
        titulo(self.marco_reparto, "Reparto de clases", 16).pack(anchor="w", padx=12, pady=(10, 2))
        principal = self.eleccion["clase"]
        nombres = {r.id: r.nombre for r in self.q.recomendar_clases()}
        nivel_subclase = (self.q.catalogo.obtener("clases", principal.id) or {}).get("nivel_subclase", 1)
        libres = self.nivel - nivel_subclase  # niveles que puede ceder la principal sin quedarse sin subclase
        if self.nivel < NIVEL_MINIMO_MULTICLASE or libres < 1:
            texto_ajustado(self.marco_reparto, f"A nivel {self.nivel} te proponemos una sola clase: repartir dejaría a "
                                               f"{principal.nombre} sin lo que la define.", ANCHO,
                           text_color="gray").pack(anchor="w", padx=12, pady=(0, 12))
            return
        reparto = " / ".join(f"{nombres.get(c, c)} {n}" for c, n in self.reparto)
        texto_ajustado(self.marco_reparto, f"Propuesta: {reparto}. Puedes cambiar la segunda clase o sus niveles.",
                       ANCHO).pack(anchor="w", padx=12)
        fila = ctk.CTkFrame(self.marco_reparto, fg_color="transparent")
        fila.pack(anchor="w", padx=12, pady=(6, 12))
        ctk.CTkLabel(fila, text="Segunda clase:").pack(side="left", padx=(0, 6))
        candidatas = [r for r in self.q.recomendar_clases() if self.q.compatibles(principal.id, r.id)]
        por_nombre = {"Ninguna": None, **{r.nombre: r.id for r in candidatas}}
        actual = self.reparto[1] if len(self.reparto) > 1 else (None, min(libres, 1))
        menu = ctk.CTkOptionMenu(fila, values=list(por_nombre), width=170, dynamic_resizing=False)
        menu.set(nombres.get(actual[0], "Ninguna") if actual[0] else "Ninguna")
        menu.pack(side="left")
        ctk.CTkLabel(fila, text="niveles:").pack(side="left", padx=(12, 6))
        niveles = ctk.CTkOptionMenu(fila, values=[str(n) for n in range(1, libres + 1)], width=70)
        niveles.set(str(min(actual[1], libres)))
        niveles.pack(side="left")

        def cambiar(_valor=None):
            otra = por_nombre[menu.get()]
            n = int(niveles.get())
            self.reparto = [(principal.id, self.nivel - n), (otra, n)] if otra else [(principal.id, self.nivel)]
            self._pintar_reparto()

        menu.configure(command=cambiar)
        niveles.configure(command=cambiar)

    def _crear(self) -> None:
        raza, clase, trasfondo = (self.eleccion[c] for c in ("raza", "clase", "trasfondo"))
        reparto = self.reparto if self.q.acepta_multiclase and self.reparto and self.reparto[0][0] == clase.id else None
        self.q.generar(nivel=self.nivel, raza=raza.id, subraza=raza.subraza, clase=clase.id, trasfondo=trasfondo.id,
                       reparto=reparto)
        nombre = self.entrada_nombre.get().strip()
        if nombre:
            self.q.asistente.establecer_detalle("nombre", nombre)
        self.al_terminar()


NOMBRES_DECISION = {"mejora": "mejora de característica o dote", "subclase": "subclase",
                    "opciones": "opciones de clase", "conjuros": "conjuros nuevos"}


class VistaSubida5e(ctk.CTkFrame):
    """Subir de nivel con preguntas: lo vivido desde el último hito decide lo nuevo de esos niveles."""

    def __init__(self, master, cuestionario: Cuestionario5e, niveles: int, clase: str | None,
                 al_terminar: Callable[[list[str]], None], al_cancelar: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.q = cuestionario
        self.niveles = niveles
        self.clase = clase
        self.al_terminar = al_terminar
        self.al_cancelar = al_cancelar
        self.decisiones = cuestionario.decisiones_de_subida(niveles, clase)
        self.preguntas = cuestionario.preguntas_subida(self.decisiones)
        self.cuerpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True)
        self._pintar()

    def _pintar(self) -> None:
        desplazamiento = self.cuerpo._parent_canvas.yview()[0]
        for hijo in self.cuerpo.winfo_children():
            hijo.destroy()
        columna = ctk.CTkFrame(self.cuerpo, fg_color="transparent", width=ANCHO)
        columna.pack(pady=24, padx=20)
        a = self.q.asistente
        titulo(columna, f"Subir de nivel: de {a.nivel} a {a.nivel + self.niveles}", 26).pack(anchor="w")
        if self.decisiones:
            que = ", ".join(NOMBRES_DECISION[d] for d in ("mejora", "subclase", "opciones", "conjuros") if d in self.decisiones)
            texto = (f"Estos niveles traen decisiones: {que}. Cuéntanos qué ha vivido tu personaje desde el último hito "
                     "de la aventura y lo decidimos con eso. Puedes dejar preguntas sin responder.")
        else:
            texto = "Estos niveles no traen decisiones: solo rasgos y puntos de golpe, que se suman solos."
        texto_ajustado(columna, texto, ANCHO, font=fuente(15)).pack(anchor="w", pady=(10, 18))
        for pregunta in self.preguntas:
            ctk.CTkLabel(columna, text=pregunta.titulo, text_color="gray", anchor="w").pack(anchor="w", pady=(10, 0))
            texto_ajustado(columna, pregunta.texto, ANCHO, font=fuente(19, True)).pack(anchor="w", pady=(2, 10))
            actual = self.q.respuestas_subida.get(pregunta.id)
            for respuesta in pregunta.respuestas:
                TarjetaRespuesta(columna, respuesta.texto, respuesta.id == actual,
                                 lambda p=pregunta.id, r=respuesta.id, act=actual: self._responder(p, None if r == act else r)
                                 ).pack(fill="x", pady=4)
        pie = ctk.CTkFrame(columna, fg_color="transparent")
        pie.pack(fill="x", pady=(24, 0))
        ctk.CTkButton(pie, text="Subir de nivel →", width=180, height=40, font=fuente(15, True),
                      command=self._subir).pack(side="left")
        ctk.CTkButton(pie, text="Cancelar", width=120, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self._cancelar).pack(side="left", padx=12)
        self.update_idletasks()
        self.cuerpo._parent_canvas.yview_moveto(desplazamiento)

    def _responder(self, pregunta: str, respuesta: str | None) -> None:
        # Pulsar otra vez la respuesta elegida la quita.
        self.q.responder_subida(pregunta, respuesta)
        self._pintar()

    def _cancelar(self) -> None:
        self.q.respuestas_subida.clear()
        self.al_cancelar()

    def _subir(self) -> None:
        a = self.q.asistente
        antes = a.instantanea()
        self.q.subir_nivel(self.niveles, self.clase)
        self.al_terminar(a.novedades(antes))
