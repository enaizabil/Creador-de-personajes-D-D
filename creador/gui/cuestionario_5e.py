"""Modo sencillo de 5e (2014): preguntas de situaciones, resultado y paso al asistente para retocar."""
from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ..sistemas.dnd5e_2014.cuestionario import (MINIMO_RESPUESTAS, NIVEL_MINIMO_MULTICLASE, UMBRAL_ALINEAMIENTO, Cuestionario5e,
                                                Pregunta, Recomendacion)
from .asistente_5e import NOMBRES_PERFIL
from .componentes import fuente, texto_ajustado, titulo

ANCHO = 820
COLOR_TARJETA = ("gray86", "gray20")
COLOR_TARJETA_ENCIMA = ("gray78", "gray28")
COLOR_TARJETA_ELEGIDA = ("#bfdbfe", "#1e3a5f")
COLOR_NOTA = ("gray35", "gray68")
MARCA_PROPUESTA = "★ Propuesta."
RESPUESTAS_EN_UNA_COLUMNA = 6  # con más, en dos columnas para no hacer la lista eterna
AYUDA_SUBIDA = ("Cada pregunta concreta trae las opciones reales de tu personaje; «★ Propuesta» marca lo que se elegiría "
                "según su forma de ser si no respondes. Puedes dejar preguntas sin responder.")
CUANTAS_RECOMENDACIONES = 3


class TarjetaRespuesta(ctk.CTkFrame):
    """Respuesta pulsable con el texto ajustado (un CTkButton no parte líneas) y, debajo, su detalle en gris."""

    def __init__(self, master, texto: str, elegida: bool, al_pulsar: Callable[[], None], detalle: str = "",
                 propuesta: bool = False, ancho: int = ANCHO):
        super().__init__(master, fg_color=COLOR_TARJETA_ELEGIDA if elegida else COLOR_TARJETA, corner_radius=10,
                         cursor="hand2")
        self.color = COLOR_TARJETA_ELEGIDA if elegida else COLOR_TARJETA
        nota = ((MARCA_PROPUESTA + " ") if propuesta else "") + detalle
        self.etiqueta = ctk.CTkLabel(self, text=texto, font=fuente(15), wraplength=ancho - 60, justify="left",
                                     anchor="w", cursor="hand2")
        self.etiqueta.pack(fill="x", padx=18, pady=(14, 0 if nota else 14))
        widgets = [self, self.etiqueta]
        if nota:
            self.nota = ctk.CTkLabel(self, text=nota, font=fuente(12), text_color=COLOR_NOTA, wraplength=ancho - 60,
                                     justify="left", anchor="w", cursor="hand2")
            self.nota.pack(fill="x", padx=18, pady=(2, 12))
            widgets.append(self.nota)
        for widget in widgets:
            widget.bind("<Button-1>", lambda _e: al_pulsar())
            widget.bind("<Enter>", lambda _e: self.configure(fg_color=COLOR_TARJETA_ENCIMA))
            widget.bind("<Leave>", lambda _e: self.configure(fg_color=self.color))


def pintar_preguntas_subida(columna, cuestionario: Cuestionario5e, preguntas: list[Pregunta],
                            al_cambiar: Callable[[], None]) -> None:
    """Hitos y preguntas concretas de subida. Pulsar una respuesta elegida la quita; en las que piden varias se
    marcan hasta las que tocan (al pasarse, sale la primera marcada). Con muchas respuestas, en dos columnas."""

    def alternar(pregunta: Pregunta, respuesta: str) -> None:
        actual = cuestionario.respuestas_subida.get(pregunta.id)
        if not pregunta.concreta:
            cuestionario.responder_subida(pregunta.id, None if respuesta == actual else respuesta)
        else:
            lista = list(actual or [])
            lista = [v for v in lista if v != respuesta] if respuesta in lista else (lista + [respuesta])[-pregunta.elegir:]
            cuestionario.responder_subida(pregunta.id, lista)
        al_cambiar()

    for pregunta in preguntas:
        ctk.CTkLabel(columna, text=pregunta.titulo, text_color="gray", anchor="w").pack(anchor="w", pady=(16, 0))
        texto_ajustado(columna, pregunta.texto, ANCHO, font=fuente(19, True)).pack(anchor="w", pady=(2, 8))
        actual = cuestionario.respuestas_subida.get(pregunta.id)
        elegidas = set(actual) if isinstance(actual, list) else {actual}
        if pregunta.elegir > 1:
            marcadas = len(elegidas & {r.id for r in pregunta.respuestas})
            ctk.CTkLabel(columna, text=f"Llevas {marcadas} de {pregunta.elegir}; las que falten se eligen solas.",
                         text_color="gray").pack(anchor="w", pady=(0, 4))
        dos_columnas = len(pregunta.respuestas) > RESPUESTAS_EN_UNA_COLUMNA
        rejilla = ctk.CTkFrame(columna, fg_color="transparent")
        rejilla.pack(fill="x")
        if dos_columnas:
            rejilla.grid_columnconfigure((0, 1), weight=1, uniform="respuestas")
        for i, respuesta in enumerate(pregunta.respuestas):
            tarjeta = TarjetaRespuesta(rejilla, respuesta.texto, respuesta.id in elegidas,
                                       lambda p=pregunta, r=respuesta.id: alternar(p, r), respuesta.detalle,
                                       respuesta.propuesta, (ANCHO - 12) // 2 if dos_columnas else ANCHO)
            if dos_columnas:
                tarjeta.grid(row=i // 2, column=i % 2, sticky="nsew", padx=3, pady=3)
            else:
                tarjeta.pack(fill="x", pady=4)


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
        self.nombre = ""  # se guarda al pasar del resultado a la historia
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
        texto_ajustado(columna, "No hace falta saber nada de reglas. Te contaremos situaciones (de la vida cotidiana o de "
                                "fantasía) y tú dices qué haría tu personaje. Con eso proponemos raza, clase, trasfondo, "
                                "características y todo lo demás. Al final podrás cambiar lo que quieras.", ANCHO,
                       font=fuente(15)).pack(anchor="w", pady=(10, 18))
        self._opciones_preguntas(columna)
        texto_ajustado(columna, f"Son {len(self.preguntas)} preguntas; con {MINIMO_RESPUESTAS} ya hay un resultado. "
                                "Puedes saltarte las que no te convenzan.", ANCHO,
                       text_color="gray").pack(anchor="w", pady=(8, 0))
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

    def _opciones_preguntas(self, columna) -> None:
        """Cuántas preguntas, de qué estilo y si entran las de contenido sensible o bizarro."""
        conf = self.q.configuracion

        def cambiar(**cambio) -> None:
            self.q.configurar(**cambio)
            self.preguntas = self.q.preguntas()
            self.pantalla_inicio()

        fila = ctk.CTkFrame(columna, fg_color="transparent")
        fila.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(fila, text="Preguntas:", font=fuente(14, True), width=90, anchor="w").pack(side="left")
        cantidades = {f"{nombre} ({len(self.q.preguntas(cantidad=clave))})": clave for clave, nombre in
                      (("rapido", "Rápido"), ("recomendado", "Recomendado"), ("preciso", "Preciso"))}
        selector = ctk.CTkSegmentedButton(fila, values=list(cantidades), command=lambda v: cambiar(cantidad=cantidades[v]))
        selector.set(next(n for n, c in cantidades.items() if c == conf["cantidad"]))
        selector.pack(side="left")
        ctk.CTkLabel(fila, text="(más preguntas, más precisión)", text_color="gray").pack(side="left", padx=10)
        fila = ctk.CTkFrame(columna, fg_color="transparent")
        fila.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(fila, text="Estilo:", font=fuente(14, True), width=90, anchor="w").pack(side="left")
        estilos = {"Vida cotidiana": "cotidiana", "Fantasía": "fantasia", "Mezcla": "mezcla"}
        selector = ctk.CTkSegmentedButton(fila, values=list(estilos), command=lambda v: cambiar(estilo=estilos[v]))
        selector.set(next(n for n, e in estilos.items() if e == conf["estilo"]))
        selector.pack(side="left")
        variable = ctk.BooleanVar(value=conf["sensible"])
        ctk.CTkSwitch(columna, text="Incluir preguntas de contenido sensible o bizarro (muerte, crueldad, situaciones absurdas)",
                      variable=variable, command=lambda: cambiar(sensible=variable.get())).pack(anchor="w", pady=(2, 0))
        if any(p.id == "tasha-2020" for p in self.q.catalogo.paquetes):
            reglas = self.q.personaje.reglas_opcionales
            origen = ctk.BooleanVar(value=reglas.get("origen_personalizado", False))
            ctk.CTkSwitch(columna, variable=origen,
                          text="Personalizar tu origen (Tasha): las mejoras de raza van donde más le sirven a tu clase",
                          command=lambda: reglas.__setitem__("origen_personalizado", origen.get())).pack(anchor="w", pady=(6, 0))
            opcionales = ctk.BooleanVar(value=reglas.get("rasgos_opcionales", False))
            ctk.CTkSwitch(columna, variable=opcionales,
                          text="Rasgos de clase opcionales (Tasha): más conjuros, estilos e invocaciones, y versiones nuevas "
                               "de algunos rasgos",
                          command=lambda: reglas.__setitem__("rasgos_opcionales", opcionales.get())).pack(anchor="w",
                                                                                                          pady=(6, 0))

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

    def pantalla_historia(self, repintar: bool = False) -> None:
        """Al crear por encima de nivel 1, tras elegir raza y clase: su historia hasta hoy, con un hito o varios y una
        pregunta concreta por cada elección de los niveles 2 en adelante. Al repintar tras una respuesta se queda
        donde estaba; al entrar, arriba."""
        desplazamiento = self.cuerpo._parent_canvas.yview()[0] if repintar else 0.0
        columna = self._limpiar()
        clase = self.eleccion["clase"].nombre
        titulo(columna, f"Su historia hasta el nivel {self.nivel}", 26).pack(anchor="w")
        texto_ajustado(columna, f"Tu {clase.lower()} ya ha vivido aventuras. Cuéntanos cómo le han cambiado y con eso "
                                f"decidimos su subclase, mejoras, dotes, opciones de clase y conjuros. {AYUDA_SUBIDA}",
                       ANCHO, font=fuente(15)).pack(anchor="w", pady=(10, 8))
        preguntas = self.q.preguntas_de_historia(self.nivel, **self._eleccion_generar())
        pintar_preguntas_subida(columna, self.q, preguntas, lambda: self.pantalla_historia(repintar=True))
        pie = ctk.CTkFrame(columna, fg_color="transparent")
        pie.pack(fill="x", pady=(24, 0))
        ctk.CTkButton(pie, text="← Volver al resultado", width=170, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.pantalla_resultado).pack(side="left")
        ctk.CTkButton(pie, text="Crear personaje", width=200, height=40, font=fuente(15, True),
                      command=self._crear).pack(side="right")
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
        self.marco_porque = ctk.CTkFrame(columna)
        self.marco_porque.pack(fill="x", pady=(14, 0))
        self._pintar_porque()
        if self.q.acepta_multiclase:
            self.marco_reparto = ctk.CTkFrame(columna)
            self.marco_reparto.pack(fill="x", pady=(14, 0))
            self.reparto = self.q.proponer_reparto(self.nivel, self.eleccion["clase"].id)
            self._pintar_reparto()

        fila = ctk.CTkFrame(columna, fg_color="transparent")
        fila.pack(anchor="w", pady=(20, 6))
        ctk.CTkLabel(fila, text="Nombre:", font=fuente(14, True)).pack(side="left", padx=(0, 10))
        self.entrada_nombre = ctk.CTkEntry(fila, width=300, placeholder_text="Cómo se llama tu personaje")
        self.entrada_nombre.insert(0, self.nombre or self.q.personaje.nombre)
        self.entrada_nombre.pack(side="left")
        botones = ctk.CTkFrame(columna, fg_color="transparent")
        botones.pack(anchor="w", pady=14)
        siguiente = "Crear personaje" if self.nivel == 1 else f"Su historia hasta nivel {self.nivel} →"
        ctk.CTkButton(botones, text=siguiente, width=230, height=40, font=fuente(15, True),
                      command=self._siguiente).pack(side="left")
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
            if getattr(self, "marco_porque", None) is not None and self.marco_porque.winfo_exists():
                self._pintar_porque()
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

    def _pintar_porque(self) -> None:
        """Por qué esa raza, esa clase y ese alineamiento: las respuestas que más han pesado y cuánto."""
        for hijo in self.marco_porque.winfo_children():
            hijo.destroy()
        titulo(self.marco_porque, "¿Por qué este resultado?", 16).pack(anchor="w", padx=12, pady=(10, 2))
        texto_ajustado(self.marco_porque, "Puntos: cuánto bajaría la afinidad si no hubieras respondido esa pregunta "
                                          "(negativos: cuánto la ha bajado).", ANCHO - 40,
                       text_color="gray").pack(anchor="w", padx=12)
        raza, clase = self.eleccion.get("raza"), self.eleccion.get("clase")
        bloques = []
        if raza is not None:
            bloques.append((f"Raza: {raza.nombre_completo} ({raza.afinidad}%)", self.q.explicar("razas", raza.id, raza.subraza)))
        if clase is not None:
            bloques.append((f"Clase: {clase.nombre} ({clase.afinidad}%)", self.q.explicar("clases", clase.id)))
        totales = self.q.totales_alineamiento()
        ejes = f"orden {totales.get('orden', 0):+d}, moral {totales.get('moral', 0):+d}; desde ±{UMBRAL_ALINEAMIENTO} se inclina"
        bloques.append((f"Alineamiento: {self.q.alineamiento()} ({ejes})", self.q.explicar_alineamiento()))
        for cabecera, motivos in bloques:
            ctk.CTkLabel(self.marco_porque, text=cabecera, font=fuente(13, True), anchor="w").pack(anchor="w", padx=12,
                                                                                                  pady=(8, 0))
            if not motivos:
                ctk.CTkLabel(self.marco_porque, text="Ninguna respuesta ha influido.", text_color="gray").pack(anchor="w",
                                                                                                             padx=24)
            for motivo in motivos[:5]:
                puntos = f"{motivo.puntos:+.0f}" if cabecera.startswith(("Raza", "Clase")) else motivo.detalle
                detalle = f" ({motivo.detalle})" if motivo.detalle and cabecera.startswith(("Raza", "Clase")) else ""
                texto_ajustado(self.marco_porque, f"• «{motivo.pregunta}»: {motivo.respuesta} → {puntos}{detalle}",
                               ANCHO - 60).pack(anchor="w", padx=24)
        ctk.CTkFrame(self.marco_porque, height=8, fg_color="transparent").pack()

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

    def _eleccion_generar(self) -> dict:
        """Lo elegido en el resultado, como lo recibe «generar» (y las preguntas de su historia)."""
        raza, clase, trasfondo = (self.eleccion[c] for c in ("raza", "clase", "trasfondo"))
        reparto = self.reparto if self.q.acepta_multiclase and self.reparto and self.reparto[0][0] == clase.id else None
        return {"raza": raza.id, "subraza": raza.subraza, "clase": clase.id, "trasfondo": trasfondo.id, "reparto": reparto}

    def _siguiente(self) -> None:
        self.nombre = self.entrada_nombre.get().strip()
        if self.nivel > 1 and self.q.preguntas_de_historia(self.nivel, **self._eleccion_generar()):
            self.pantalla_historia()
        else:
            self._crear()

    def _crear(self) -> None:
        eleccion = self._eleccion_generar()
        # Fuera las respuestas a preguntas que ya no se plantean (de otra clase elegida antes, p. ej.).
        self.q.conservar_respuestas_subida({p.id for p in self.q.preguntas_de_historia(self.nivel, **eleccion)})
        self.q.generar(nivel=self.nivel, **eleccion)
        if self.nombre:
            self.q.asistente.establecer_detalle("nombre", self.nombre)
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
        # Se rehacen en cada respuesta: lo respondido cambia lo siguiente (la subclase trae sus opciones; una
        # mejora, las puntuaciones de la próxima).
        self.preguntas = self.q.preguntas_de_subida(self.niveles, self.clase)
        que = ", ".join(NOMBRES_DECISION[d] for d in ("mejora", "subclase", "opciones", "conjuros") if d in self.decisiones)
        if self.preguntas:
            texto = (f"Estos niveles traen decisiones: {que}. Cuéntanos qué ha vivido tu personaje desde el último hito "
                     f"de la aventura y lo decidimos con eso. {AYUDA_SUBIDA}")
        elif self.decisiones:
            texto = (f"Estos niveles solo traen elecciones menores ({que}), que se deciden con su forma de ser: no hace "
                     "falta preguntar nada.")
        else:
            texto = "Estos niveles no traen decisiones: solo rasgos y puntos de golpe, que se suman solos."
        texto_ajustado(columna, texto, ANCHO, font=fuente(15)).pack(anchor="w", pady=(10, 8))
        pintar_preguntas_subida(columna, self.q, self.preguntas, self._pintar)
        pie = ctk.CTkFrame(columna, fg_color="transparent")
        pie.pack(fill="x", pady=(24, 0))
        ctk.CTkButton(pie, text="Subir de nivel →", width=180, height=40, font=fuente(15, True),
                      command=self._subir).pack(side="left")
        ctk.CTkButton(pie, text="Cancelar", width=120, height=40, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self._cancelar).pack(side="left", padx=12)
        self.update_idletasks()
        self.cuerpo._parent_canvas.yview_moveto(desplazamiento)

    def _cancelar(self) -> None:
        self.q.respuestas_subida.clear()
        self.al_cancelar()

    def _subir(self) -> None:
        a = self.q.asistente
        antes = a.instantanea()
        self.q.conservar_respuestas_subida({p.id for p in self.q.preguntas_de_subida(self.niveles, self.clase)})
        self.q.subir_nivel(self.niveles, self.clase)
        self.al_terminar(a.novedades(antes))
