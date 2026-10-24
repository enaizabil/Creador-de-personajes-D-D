"""Vista del asistente de creación de 5e (2014): un panel por paso."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..sistemas.dnd5e_2014.asistente import ALINEAMIENTOS, METODOS_CARACTERISTICAS, Asistente5e
from ..sistemas.dnd5e_2014.constantes import CARACTERISTICAS, COSTE_COMPRA, RASGOS_PERFIL
from ..sistemas.dnd5e_2014.texto import resumen_ficha
from .componentes import NINGUNA, ListaAvisos, ListaOpciones, SelectorEleccion, fuente, texto_ajustado, titulo

PERSONALIDAD = (("rasgos_personalidad", "Rasgos de personalidad"), ("ideales", "Ideales"),
                ("vinculos", "Vínculos"), ("defectos", "Defectos"))
FISICO = (("edad", "Edad"), ("altura", "Altura"), ("peso", "Peso"), ("ojos", "Ojos"), ("piel", "Piel"), ("pelo", "Pelo"))
NOMBRES_PERFIL = {r: r.capitalize() for r in RASGOS_PERFIL} | {"proteccion": "Protección", "curacion": "Curación"}
LARGO_DESCRIPCION_OPCIONAL = 95


class VistaAsistente5e(ctk.CTkFrame):
    def __init__(self, master, asistente: Asistente5e, al_volver: Callable[[], None], paso_inicial: str = "inicio",
                 novedades: list[str] | None = None):
        super().__init__(master, fg_color="transparent")
        self.a = asistente
        self.al_volver = al_volver
        self.novedades = novedades or []  # de la última subida de nivel, para enseñarlas en el resumen
        self.nombres_paquetes = {p.id: p.nombre for p in asistente.catalogo.paquetes}
        self.paso_actual = "inicio"
        self.archivo: str | None = None
        self.marco_avisos: ctk.CTkFrame | None = None
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.lateral = ctk.CTkFrame(self, width=210, corner_radius=0)
        self.lateral.grid(row=0, column=0, rowspan=3, sticky="nsw")
        self.cabecera = ctk.CTkLabel(self, text="", font=fuente(15, True), anchor="w")
        self.cabecera.grid(row=0, column=1, sticky="ew", padx=20, pady=(14, 4))
        self.contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.contenido.grid(row=1, column=1, sticky="nsew", padx=10)
        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=2, column=1, sticky="ew", padx=20, pady=12)
        self.boton_anterior = ctk.CTkButton(pie, text="← Anterior", width=120, command=lambda: self._mover(-1))
        self.boton_anterior.pack(side="left")
        self.boton_siguiente = ctk.CTkButton(pie, text="Siguiente →", width=120, command=lambda: self._mover(1))
        self.boton_siguiente.pack(side="left", padx=10)
        ctk.CTkButton(pie, text="Guardar…", width=110, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.guardar).pack(side="right")
        ctk.CTkButton(pie, text="Inicio", width=90, fg_color="transparent", text_color=("gray10", "gray90"),
                      command=self._volver).pack(side="right", padx=10)
        self.mostrar(paso_inicial)

    # ── navegación y estado ───────────────────────────────────────────────

    def _ids_pasos(self) -> list[str]:
        return [p.id for p in self.a.pasos()]

    def _mover(self, delta: int) -> None:
        ids = self._ids_pasos()
        posicion = ids.index(self.paso_actual) if self.paso_actual in ids else 0
        self.mostrar(ids[max(0, min(len(ids) - 1, posicion + delta))])

    def mostrar(self, paso: str) -> None:
        if paso == "equipo" or self.paso_actual == "equipo":
            self.a.aplicar_equipo()
        nuevo = paso != self.paso_actual
        self.paso_actual = paso
        self.marco_avisos = None
        for hijo in self.contenido.winfo_children():
            hijo.destroy()
        getattr(self, f"_paso_{paso}")(self.contenido)
        if nuevo:
            # Otro paso empieza arriba; si no, conserva el desplazamiento del anterior y puede verse en blanco.
            self.contenido._parent_canvas.yview_moveto(0)
        self._refrescar()

    def _redibujar(self) -> None:
        self.mostrar(self.paso_actual)

    def _refrescar(self) -> None:
        self._pintar_avisos()
        for hijo in self.lateral.winfo_children():
            hijo.destroy()
        ctk.CTkLabel(self.lateral, text="Creación", font=fuente(16, True)).pack(anchor="w", padx=16, pady=(18, 10))
        for paso in self.a.pasos():
            completo = not self.a.faltan(paso.id)
            marca = "✓" if completo else "•"
            actual = paso.id == self.paso_actual
            ctk.CTkButton(self.lateral, text=f"{marca}  {paso.titulo}", anchor="w", width=180,
                          fg_color=None if actual else "transparent",
                          text_color=None if actual else (("gray10", "gray90") if completo else ("#b45309", "#fbbf24")),
                          command=lambda p=paso.id: self.mostrar(p)).pack(padx=12, pady=2)
        ficha = self.a.ficha()
        partes = [ficha.nombre or "Personaje sin nombre", ficha.raza, ficha.clase_y_nivel]
        if self.a.personaje.clases:
            partes.append(f"PG {ficha.pg_maximos} · CA {ficha.ca}")
        self.cabecera.configure(text="  ·  ".join(p for p in partes if p))
        ids = self._ids_pasos()
        self.boton_anterior.configure(state="normal" if self.paso_actual != ids[0] else "disabled")
        self.boton_siguiente.configure(state="normal" if self.paso_actual != ids[-1] else "disabled")

    def _cabecera_paso(self, master, paso: str) -> None:
        datos = next(p for p in self.a.pasos() if p.id == paso)
        titulo(master, datos.titulo, 22).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(master, text=datos.ayuda, text_color="gray", anchor="w").pack(anchor="w", padx=10, pady=(0, 10))

    def _elecciones(self, master, paso: str) -> None:
        elecciones = self.a.elecciones(paso)
        if elecciones:
            titulo(master, "Elecciones", 15).pack(anchor="w", padx=10, pady=(14, 4))
        for eleccion in elecciones:
            SelectorEleccion(master, eleccion, self._eleccion_cambiada,
                             self.a.bloqueadas(eleccion)).pack(fill="x", padx=10, pady=4)

    def _eleccion_cambiada(self, clave: str, valores: list[str]) -> None:
        self.a.elegir(clave, valores)
        self._redibujar()

    def _faltan(self, master, paso: str) -> None:
        """Recuadro de lo que falta; _refrescar lo repinta tras cada cambio que no redibuja el paso."""
        self.marco_avisos = ctk.CTkFrame(master, fg_color="transparent")
        self.marco_avisos.pack(fill="x", padx=10, pady=(14, 6))
        self._pintar_avisos()

    def _pintar_avisos(self) -> None:
        if self.marco_avisos is None or not self.marco_avisos.winfo_exists():
            return
        for hijo in self.marco_avisos.winfo_children():
            hijo.destroy()
        ListaAvisos(self.marco_avisos, self.a.faltan(self.paso_actual)).pack(fill="x")

    def _volver(self) -> None:
        if messagebox.askyesno("Volver al inicio", "¿Volver al inicio? Lo que no hayas guardado se perderá."):
            self.al_volver()

    def guardar(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Personaje", "*.json")],
                                            initialfile=f"{self.a.personaje.nombre or 'personaje'}.json")
        if ruta:
            self.a.aplicar_equipo()
            self.a.personaje.guardar(ruta)
            self.archivo = ruta
            messagebox.showinfo("Guardado", f"Personaje guardado en:\n{ruta}")

    def exportar(self, formato: str) -> None:
        """Guarda la ficha en PDF (réplica de la oficial) o la nota para Obsidian con la guía de Nivel20."""
        extension, tipo = {"pdf": (".pdf", "Ficha en PDF"), "oficial": (".pdf", "Hoja oficial rellenable"),
                           "nota": (".md", "Nota de Obsidian")}[formato]
        ruta = filedialog.asksaveasfilename(defaultextension=extension, filetypes=[(tipo, f"*{extension}")],
                                            initialfile=f"{self.a.personaje.nombre or 'personaje'}{extension}")
        if not ruta:
            return
        self.a.aplicar_equipo()
        try:
            if formato == "pdf":
                from ..sistemas.dnd5e_2014.salidas.ficha_pdf import generar_ficha_pdf
                generar_ficha_pdf(self.a, ruta)
            elif formato == "oficial":
                from ..sistemas.dnd5e_2014.salidas.pdf_oficial import rellenar_hoja_oficial
                rellenar_hoja_oficial(self.a, ruta)
            else:
                from ..sistemas.dnd5e_2014.salidas.nota import nota_obsidian
                Path(ruta).write_text(nota_obsidian(self.a), encoding="utf-8")
        except ImportError as exc:
            messagebox.showerror("Falta una dependencia",
                                 f"No se puede generar el PDF: {exc}\n(pip install -r requirements.txt)")
            return
        except OSError as exc:
            messagebox.showerror("No se puede guardar", f"{ruta}\n\n{exc}")
            return
        messagebox.showinfo("Guardado", f"{tipo} guardada en:\n{ruta}")

    # ── pasos ─────────────────────────────────────────────────────────────

    def _paso_inicio(self, master) -> None:
        self._cabecera_paso(master, "inicio")
        reglas = self.a.personaje.reglas_opcionales
        caja = ctk.CTkFrame(master)
        caja.pack(fill="x", padx=10, pady=4)
        fila = ctk.CTkFrame(caja, fg_color="transparent")
        fila.pack(anchor="w", padx=12, pady=12)
        ctk.CTkLabel(fila, text="Nivel inicial:", font=fuente(14, True)).pack(side="left", padx=(0, 10))
        maximo = self.a.nivel_maximo()
        # Con varias clases, el total no puede bajar de lo repartido en las secundarias (+1 de la principal).
        minimo = 1 + sum(e.nivel for e in self.a.personaje.clases[1:])
        menu = ctk.CTkOptionMenu(fila, values=[str(n) for n in range(minimo, maximo + 1)], width=80,
                                 command=lambda v: (self.a.establecer_nivel(int(v)), self._redibujar()))
        menu.set(str(self.a.nivel))
        menu.pack(side="left")
        if minimo > 1:
            ctk.CTkLabel(fila, text="(total de todas las clases; el reparto se hace en el paso «Clase»)",
                         text_color="gray").pack(side="left", padx=10)
        if maximo < 20:
            ctk.CTkLabel(fila, text=f"(los datos de clase llegan, por ahora, hasta nivel {maximo})",
                         text_color="gray").pack(side="left", padx=10)

        interruptores = [("dotes", "Dotes (regla opcional del Manual del Jugador)", True),
                         ("multiclase", "Multiclase (regla opcional del Manual del Jugador)", False),
                         ("opciones_dm", "Opciones de la Guía del DM que requieren su permiso (aasimar, eladrín…)", False)]
        if any(p.id == "tasha-2020" for p in self.a.catalogo.paquetes):
            interruptores.append(("origen_personalizado", "Personalizar tu origen: mover las mejoras de raza a otras "
                                                          "características (Tasha)", False))
            interruptores.append(("rasgos_opcionales", "Rasgos de clase opcionales (Tasha): listas de conjuros ampliadas, "
                                                       "estilos, invocaciones… y rasgos que sustituyen a otros", False))
        if any(p.id == "dmg-2014" for p in self.a.catalogo.paquetes):
            interruptores.append(("equipo_por_nivel", "Oro extra al empezar por encima de nivel 4 (Guía del DM)", False))
            interruptores.append(("entrenamiento", "Entrenarse para subir de nivel: días y coste por nivel (Guía del DM)",
                                  False))
        for regla, texto, defecto in interruptores:
            activa = self.a.multiclase_activa() if regla == "multiclase" else reglas.get(regla, defecto)
            variable = ctk.BooleanVar(value=activa)
            ctk.CTkSwitch(caja, text=texto, variable=variable,
                          command=lambda r=regla, v=variable: (self.a.establecer_regla(r, v.get()), self._refrescar())
                          ).pack(anchor="w", padx=12, pady=4)
            if regla == "multiclase":
                texto_ajustado(caja, "Reparte los niveles entre varias clases (desde nivel 2, en el paso «Clase»). Es para "
                                     "jugadores con experiencia: si no sabes qué es, déjala apagada.", 700,
                               text_color="gray").pack(anchor="w", padx=60, pady=(0, 4))
        fila_pg = ctk.CTkFrame(caja, fg_color="transparent")
        fila_pg.pack(anchor="w", padx=12, pady=(8, 12))
        ctk.CTkLabel(fila_pg, text="Puntos de golpe al subir de nivel:").pack(side="left", padx=(0, 10))
        selector = ctk.CTkSegmentedButton(
            fila_pg, values=["Media", "Tiradas"],
            command=lambda v: setattr(self.a.personaje, "metodo_pg", "media" if v == "Media" else "tiradas"))
        selector.set("Media" if self.a.personaje.metodo_pg == "media" else "Tiradas")
        selector.pack(side="left")
        paquetes = ", ".join(p.nombre for p in self.a.catalogo.paquetes)
        texto_ajustado(master, f"Paquetes cargados: {paquetes}", 760, text_color="gray").pack(anchor="w", padx=10, pady=8)

    def _paso_raza(self, master) -> None:
        self._cabecera_paso(master, "raza")
        p = self.a.personaje
        ListaOpciones(master, "Raza", self.a.razas(), p.raza, lambda i: (self.a.elegir_raza(i), self._redibujar()),
                      self.nombres_paquetes, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10)
        subrazas = self.a.subrazas()
        if subrazas:
            ListaOpciones(master, "Subraza", subrazas, p.subraza, lambda i: (self.a.elegir_subraza(i), self._redibujar()),
                          self.nombres_paquetes, alto=140, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10, pady=(14, 0))
        self._elecciones(master, "raza")
        self._faltan(master, "raza")

    def _paso_clase(self, master) -> None:
        self._cabecera_paso(master, "clase")
        p = self.a.personaje
        actual = p.clases[0].clase if p.clases else None
        varias = len(p.clases) > 1
        ListaOpciones(master, "Clase principal" if varias else "Clase", self.a.clases(), actual,
                      lambda i: (self.a.elegir_clase(i), self._redibujar()),
                      self.nombres_paquetes, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10)
        subclases = self.a.subclases()
        if subclases:
            ListaOpciones(master, "Subclase", subclases, p.clases[0].subclase,
                          lambda i: (self.a.elegir_subclase(i), self._redibujar()), self.nombres_paquetes,
                          alto=180, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10, pady=(14, 0))
        # Solo desde nivel 2 con la regla activa; si ya hay secundarias, siempre, para poder quitarlas.
        if p.clases and (self.a.puede_anadir_clase() or len(p.clases) > 1):
            self._multiclase(master)
        if self.a.rasgos_opcionales():
            self._rasgos_opcionales(master)
        self._elecciones(master, "clase")
        self._faltan(master, "clase")

    def _rasgos_opcionales(self, master) -> None:
        """Rasgos de clase opcionales de Tasha: de serie todos; cada uno se puede dejar (con el DM)."""
        caja = ctk.CTkFrame(master)
        caja.pack(fill="x", padx=10, pady=(14, 0))
        titulo(caja, "Rasgos de clase opcionales (Tasha)", 15).pack(anchor="w", padx=12, pady=(10, 0))
        texto_ajustado(caja, "Cada uno se toma o se deja por separado, de acuerdo con el DM. Los que dicen «sustituye» "
                             "quitan el rasgo del Manual que nombran.", 760, text_color="gray").pack(anchor="w", padx=12,
                                                                                                 pady=(2, 6))
        nombres = {o.id: o.nombre for o in self.a.clases()}
        for rasgo, activo in self.a.rasgos_opcionales():
            variable = ctk.BooleanVar(value=activo)
            descripcion = rasgo.get("descripcion", "")
            if len(descripcion) > LARGO_DESCRIPCION_OPCIONAL:  # una casilla no parte líneas
                descripcion = descripcion[:LARGO_DESCRIPCION_OPCIONAL].rsplit(" ", 1)[0] + "…"
            texto = f"{nombres.get(rasgo['clase'], rasgo['clase'])}: {rasgo['nombre']}. {descripcion}"
            ctk.CTkCheckBox(caja, text=texto, variable=variable,
                            command=lambda r=rasgo["id"], v=variable: (self.a.usar_rasgo_opcional(r, v.get()),
                                                                        self._redibujar())
                            ).pack(anchor="w", padx=12, pady=2)
        ctk.CTkFrame(caja, height=8, fg_color="transparent").pack()

    def _multiclase(self, master) -> None:
        """Clases secundarias: niveles (los quitan a la principal), requisito, subclase y añadir otra."""
        p = self.a.personaje
        caja = ctk.CTkFrame(master)
        caja.pack(fill="x", padx=10, pady=(14, 0))
        titulo(caja, "Multiclase", 15).pack(anchor="w", padx=12, pady=(10, 0))
        nombres = {o.id: o.nombre for o in self.a.clases()}
        reparto = " · ".join(f"{nombres.get(e.clase, e.clase)} {e.nivel}" for e in p.clases)
        texto_ajustado(caja, f"Nivel total {self.a.nivel}: {reparto}. Los niveles de las otras clases se le quitan a la "
                             "principal; el equipo inicial y las salvaciones son solo los de la principal.", 760,
                       text_color="gray").pack(anchor="w", padx=12, pady=(2, 6))
        principal = p.clases[0]
        for entrada in p.clases[1:]:
            self._fila_multiclase(caja, entrada, nombres, principal.nivel + entrada.nivel - 1)
        if not self.a.multiclase_activa():
            texto_ajustado(caja, "La regla de multiclase está desactivada: quita las clases secundarias o actívala en "
                                 "«Edición y reglas».", 760, text_color=("#b45309", "#fbbf24")).pack(anchor="w", padx=12,
                                                                                                 pady=(4, 12))
            return
        candidatas = self.a.clases_para_multiclase()
        if not candidatas or not self.a.puede_anadir_clase():
            return
        fila = ctk.CTkFrame(caja, fg_color="transparent")
        fila.pack(anchor="w", padx=12, pady=(6, 12))
        menu = ctk.CTkOptionMenu(fila, values=[o.nombre for o in candidatas], width=200, dynamic_resizing=False)
        menu.set(candidatas[0].nombre)
        menu.pack(side="left")
        por_nombre = {o.nombre: o.id for o in candidatas}
        boton = ctk.CTkButton(fila, text="Añadir otra clase", width=150,
                              command=lambda: (self.a.anadir_clase(por_nombre[menu.get()]), self._redibujar()))
        boton.pack(side="left", padx=10)
        if principal.nivel <= 1:
            boton.configure(state="disabled")
            ctk.CTkLabel(fila, text="Sube el nivel total (paso «Edición y reglas») para tener niveles que repartir",
                         text_color="gray").pack(side="left")

    def _fila_multiclase(self, caja, entrada, nombres: dict[str, str], maximo: int) -> None:
        marco = ctk.CTkFrame(caja, fg_color="transparent")
        marco.pack(fill="x", padx=12, pady=4)
        fila = ctk.CTkFrame(marco, fg_color="transparent")
        fila.pack(anchor="w")
        ctk.CTkLabel(fila, text=nombres.get(entrada.clase, entrada.clase), font=fuente(14, True), width=120,
                     anchor="w").pack(side="left")
        ctk.CTkLabel(fila, text="Niveles:").pack(side="left", padx=(6, 4))
        niveles = ctk.CTkOptionMenu(fila, values=[str(n) for n in range(1, max(1, maximo) + 1)], width=70,
                                    command=lambda v, c=entrada.clase: (self.a.establecer_niveles_clase(c, int(v)),
                                                                        self._redibujar()))
        niveles.set(str(entrada.nivel))
        niveles.pack(side="left")
        requisito = self.a.requisito_multiclase(entrada.clase)
        if requisito:
            texto, cumple = requisito
            ctk.CTkLabel(fila, text=f"{'✓' if cumple else '✗'} requisito: {texto}",
                         text_color=("#15803d", "#4ade80") if cumple else ("#b45309", "#fbbf24")).pack(side="left", padx=12)
        ctk.CTkButton(fila, text="Quitar", width=70, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"),
                      command=lambda c=entrada.clase: (self.a.quitar_clase(c), self._redibujar())).pack(side="left", padx=6)
        subclases = self.a.subclases(entrada.clase)
        if subclases:
            ListaOpciones(marco, f"Subclase de {nombres.get(entrada.clase, entrada.clase)}", subclases, entrada.subclase,
                          lambda i, c=entrada.clase: (self.a.elegir_subclase(i, c), self._redibujar()),
                          self.nombres_paquetes, alto=140, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", pady=(6, 0))

    def _paso_caracteristicas(self, master) -> None:
        self._cabecera_paso(master, "caracteristicas")
        p = self.a.personaje
        nombres_metodo = {v: k for k, v in METODOS_CARACTERISTICAS.items()}
        fila = ctk.CTkFrame(master, fg_color="transparent")
        fila.pack(anchor="w", padx=10, pady=4)
        menu = ctk.CTkOptionMenu(fila, values=list(METODOS_CARACTERISTICAS.values()), width=320,
                                 command=lambda v: (self.a.establecer_metodo(nombres_metodo[v]), self._redibujar()))
        menu.set(METODOS_CARACTERISTICAS[p.metodo_caracteristicas])
        menu.pack(side="left")
        if p.metodo_caracteristicas == "tirada":
            ctk.CTkButton(fila, text="Tirar 4d6 × 6", width=130,
                          command=lambda: (self.a.tirar_caracteristicas(), self._redibujar())).pack(side="left", padx=10)
        if p.clases and (p.metodo_caracteristicas != "tirada" or self.a.extra.get("tiradas_caracteristicas")) \
                and p.metodo_caracteristicas != "manual":
            ctk.CTkButton(fila, text="Repartir según mi clase", width=180,
                          command=lambda: (self.a.sugerir_caracteristicas(), self._redibujar())).pack(side="left", padx=10)

        if p.metodo_caracteristicas == "tirada" and self.a.extra.get("tiradas_caracteristicas"):
            ctk.CTkLabel(master, text="Tiradas: " + ", ".join(map(str, self.a.extra["tiradas_caracteristicas"])),
                         anchor="w").pack(anchor="w", padx=10, pady=4)
        restantes = self.a.puntos_restantes()
        if restantes is not None:
            ctk.CTkLabel(master, text=f"Puntos restantes: {restantes} de 27", font=fuente(14, True),
                         anchor="w").pack(anchor="w", padx=10, pady=4)

        tabla = ctk.CTkFrame(master)
        tabla.pack(anchor="w", padx=10, pady=8)
        for col, texto in enumerate(("Característica", "Base", "Raza", "Total", "Mod.")):
            ctk.CTkLabel(tabla, text=texto, font=fuente(13, True)).grid(row=0, column=col, padx=12, pady=6)
        bonos = self.a.bonos_raciales()
        ficha = self.a.ficha()
        disponibles = self.a.valores_disponibles()
        for fila_n, (car, nombre) in enumerate(CARACTERISTICAS.items(), start=1):
            ctk.CTkLabel(tabla, text=nombre, anchor="w").grid(row=fila_n, column=0, sticky="w", padx=12, pady=3)
            self._celda_base(tabla, fila_n, car, disponibles)
            bono = bonos.get(car, 0)
            ctk.CTkLabel(tabla, text=f"{bono:+d}" if bono else "—").grid(row=fila_n, column=2, padx=12)
            valor = ficha.caracteristicas[car]
            asignada = car in p.caracteristicas_base
            ctk.CTkLabel(tabla, text=str(valor.puntuacion) if asignada else "—",
                         font=fuente(14, True)).grid(row=fila_n, column=3, padx=12)
            ctk.CTkLabel(tabla, text=f"{valor.modificador:+d}" if asignada else "—").grid(row=fila_n, column=4, padx=12)
        if p.clases:
            prioridad = ", ".join(CARACTERISTICAS[c] for c in self.a.prioridad_de_clase()[:3])
            ctk.CTkLabel(master, text=f"Más importantes para tu clase: {prioridad}", text_color="gray",
                         anchor="w").pack(anchor="w", padx=10)
        self._faltan(master, "caracteristicas")

    def _celda_base(self, tabla, fila_n: int, car: str, disponibles: list[int]) -> None:
        p = self.a.personaje
        actual = p.caracteristicas_base.get(car)
        metodo = p.metodo_caracteristicas
        if metodo in ("estandar", "tirada"):
            valores = sorted({*disponibles, *([actual] if actual else [])}, reverse=True)
            menu = ctk.CTkOptionMenu(
                tabla, values=["—", *map(str, valores)], width=80,
                command=lambda v, c=car: (self.a.asignar(c, None if v == "—" else int(v)), self._redibujar()))
            menu.set(str(actual) if actual else "—")
            menu.grid(row=fila_n, column=1, padx=12)
        elif metodo == "compra":
            celda = ctk.CTkFrame(tabla, fg_color="transparent")
            celda.grid(row=fila_n, column=1, padx=12)
            valor = actual or 8
            ctk.CTkButton(celda, text="−", width=28, state="normal" if valor > 8 else "disabled",
                          command=lambda c=car, v=valor: (self.a.asignar(c, v - 1), self._redibujar())).pack(side="left")
            ctk.CTkLabel(celda, text=str(valor), width=32).pack(side="left")
            sube = valor < 15 and (self.a.puntos_restantes() or 0) >= COSTE_COMPRA.get(valor + 1, 99) - COSTE_COMPRA[valor]
            ctk.CTkButton(celda, text="+", width=28, state="normal" if sube else "disabled",
                          command=lambda c=car, v=valor: (self.a.asignar(c, v + 1), self._redibujar())).pack(side="left")
        else:
            entrada = ctk.CTkEntry(tabla, width=60)
            entrada.insert(0, str(actual or ""))
            entrada.grid(row=fila_n, column=1, padx=12)

            def confirmar(_evento=None, c=car, e=entrada):
                texto = e.get().strip()
                if texto.isdigit() and 1 <= int(texto) <= 30:
                    self.a.asignar(c, int(texto))
                    self._redibujar()
            entrada.bind("<Return>", confirmar)
            entrada.bind("<FocusOut>", confirmar)

    def _paso_trasfondo(self, master) -> None:
        self._cabecera_paso(master, "trasfondo")
        ListaOpciones(master, "Trasfondo", self.a.trasfondos(), self.a.personaje.trasfondo,
                      lambda i: (self.a.elegir_trasfondo(i), self._redibujar()), self.nombres_paquetes,
                      nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10)
        self._elecciones(master, "trasfondo")
        self._faltan(master, "trasfondo")

    def _paso_equipo(self, master) -> None:
        self._cabecera_paso(master, "equipo")
        oro = self.a.oro_inicial()
        if oro:
            variable = ctk.BooleanVar(value=self.a._seleccion_equipo()["oro"])
            ctk.CTkSwitch(master, text=f"Usar oro en vez del equipo de clase ({oro.replace('x', ' × ')} po)", variable=variable,
                          command=lambda: (self.a.usar_oro_en_vez_de_equipo(variable.get()), self._redibujar())
                          ).pack(anchor="w", padx=10, pady=(0, 8))
        for bloque in self.a.bloques_equipo():
            caja = ctk.CTkFrame(master)
            caja.pack(fill="x", padx=10, pady=4)
            origen = "De tu clase" if bloque.origen == "clase" else "De tu trasfondo"
            ctk.CTkLabel(caja, text=f"{origen} · {bloque.indice + 1}", font=fuente(13, True),
                         anchor="w").pack(anchor="w", padx=10, pady=(6, 2))
            variable = ctk.IntVar(value=-1 if bloque.elegida is None else bloque.elegida)
            for n, alternativa in enumerate(bloque.alternativas):
                texto = " + ".join(f"{linea.cantidad} × {linea.nombre}" if linea.cantidad > 1 else linea.nombre
                                   for linea in alternativa)
                if len(bloque.alternativas) > 1:
                    ctk.CTkRadioButton(
                        caja, text=texto, value=n, variable=variable,
                        command=lambda b=bloque, v=variable: (self.a.elegir_alternativa(b.origen, b.indice, v.get()),
                                                              self._redibujar())).pack(anchor="w", padx=16, pady=2)
                else:
                    ctk.CTkLabel(caja, text=texto, anchor="w").pack(anchor="w", padx=16, pady=2)
                if n == bloque.elegida:
                    self._huecos(caja, bloque, n, alternativa)
            ctk.CTkFrame(caja, height=4, fg_color="transparent").pack()
        self.a.aplicar_equipo()
        ficha = self.a.ficha()
        if ficha.equipo or ficha.monedas:
            titulo(master, "Inventario resultante", 15).pack(anchor="w", padx=10, pady=(12, 2))
            texto_ajustado(master, ", ".join(ficha.equipo), 760).pack(anchor="w", padx=10)
            dinero = ", ".join(f"{v} {m}" for m, v in ficha.monedas.items() if v)
            if dinero:
                ctk.CTkLabel(master, text=f"Dinero: {dinero}", anchor="w").pack(anchor="w", padx=10, pady=4)
        self._faltan(master, "equipo")

    def _huecos(self, caja, bloque, alternativa: int, lineas) -> None:
        for n, linea in enumerate(lineas):
            if linea.id is not None:
                continue
            nombres = {i: nombre for i, nombre in linea.opciones}
            ids = {nombre: i for i, nombre in linea.opciones}
            for hueco in range(linea.cantidad):
                actual = self.a.objeto_elegido(bloque.origen, bloque.indice, alternativa, n, hueco)
                menu = ctk.CTkOptionMenu(
                    caja, values=[NINGUNA, *nombres.values()], width=260, dynamic_resizing=False,
                    command=lambda v, b=bloque, ln=n, h=hueco, ids=ids: (
                        self.a.elegir_objeto(b.origen, b.indice, alternativa, ln, h, ids[v]) if v in ids else None,
                        self._redibujar()))
                menu.set(nombres.get(actual, NINGUNA))
                menu.pack(anchor="w", padx=40, pady=2)

    def _paso_conjuros(self, master) -> None:
        self._cabecera_paso(master, "conjuros")
        ficha = self.a.ficha()
        lanzadores = {lanzador.clase_id: lanzador for lanzador in ficha.lanzadores}
        otras_fuentes = self.a.conjuros_de_otras_fuentes()
        for plan in self.a.planes_conjuros():
            nombres = {id_: nombre for opciones in plan.disponibles.values() for id_, nombre in opciones}
            lanzador = lanzadores.get(plan.clase_id)
            cabecera = f"{plan.clase}: CD {lanzador.cd}, ataque {lanzador.ataque:+d}" if lanzador else plan.clase
            titulo(master, cabecera, 16).pack(anchor="w", padx=10, pady=(4, 0))
            if lanzador and lanzador.siempre_preparados:
                siempre = ", ".join(n for nivel in sorted(lanzador.siempre_preparados)
                                    for n in lanzador.siempre_preparados[nivel])
                texto_ajustado(master, f"Siempre preparados (no cuentan): {siempre}", 760,
                               text_color="gray").pack(anchor="w", padx=10)
            contador = ctk.CTkLabel(master, text="", font=fuente(13, True), anchor="w")
            contador.pack(anchor="w", padx=10, pady=4)
            elegidos = set(self.a.personaje.conjuros.get(plan.clase_id, []))
            casillas: dict[str, tuple[ctk.BooleanVar, ctk.CTkCheckBox, int]] = {}
            libro = plan.modo == "libro"
            # En modo libro las casillas eligen el libro y los preparados se eligen de él, más abajo.
            limite_otros = plan.limite_libro if libro else plan.limite_conjuros
            marco_preparados = ctk.CTkFrame(master, fg_color="transparent") if libro else None

            def actualizar(plan=plan, casillas=casillas, contador=contador, limite_otros=limite_otros,
                           marco_preparados=marco_preparados, nombres=nombres):
                ids = [i for i, (v, _, _) in casillas.items() if v.get()]
                self.a.elegir_conjuros(plan.clase_id, ids)
                trucos = sum(1 for i in ids if casillas[i][2] == 0)
                otros = len(ids) - trucos
                texto = []
                if plan.limite_trucos is not None:
                    texto.append(f"Trucos {trucos}/{plan.limite_trucos}")
                if limite_otros is not None:
                    palabra = {"conocidos": "Conocidos", "preparados": "Preparados", "libro": "Libro"}[plan.modo]
                    texto.append(f"{palabra} {otros}/{limite_otros}")
                contador.configure(text="  ·  ".join(texto))
                for id_, (variable, casilla, nivel) in casillas.items():
                    limite = plan.limite_trucos if nivel == 0 else limite_otros
                    lleno = limite is not None and (trucos if nivel == 0 else otros) >= limite
                    bloqueada = (lleno or id_ in otras_fuentes) and not variable.get()
                    casilla.configure(state="disabled" if bloqueada else "normal")
                if marco_preparados is not None:
                    extra = [(i, nombres[i]) for i in self.a.libro_extra(plan.clase_id) if i in nombres and i not in ids]
                    self._preparados_del_libro(marco_preparados, plan,
                                               [(i, nombres[i]) for i in ids if casillas[i][2] > 0] + extra)
                self._refrescar()

            for nivel, opciones in plan.disponibles.items():
                ctk.CTkLabel(master, text="Trucos" if nivel == 0 else f"Nivel {nivel}", font=fuente(14, True),
                             anchor="w").pack(anchor="w", padx=10, pady=(8, 2))
                rejilla = ctk.CTkFrame(master, fg_color="transparent")
                rejilla.pack(anchor="w", padx=16)
                for i, (id_, nombre) in enumerate(opciones):
                    variable = ctk.BooleanVar(value=id_ in elegidos)
                    texto = nombre + (" (ya lo tienes)" if id_ in otras_fuentes else "")
                    casilla = ctk.CTkCheckBox(rejilla, text=texto, variable=variable, width=240, command=actualizar)
                    casilla.grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=2)
                    casillas[id_] = (variable, casilla, nivel)
            if marco_preparados is not None:
                marco_preparados.pack(fill="x", padx=10, pady=(12, 0))
            actualizar()
        self._faltan(master, "conjuros")

    def _preparados_del_libro(self, marco, plan, libro: list[tuple[str, str]]) -> None:
        """Casillas de preparados (modo libro), rehechas cada vez que cambia el libro."""
        for hijo in marco.winfo_children():
            hijo.destroy()
        preparados = set(self.a.personaje.preparados.get(plan.clase_id, []))
        contador = ctk.CTkLabel(marco, text="", font=fuente(14, True), anchor="w")
        contador.pack(anchor="w")
        texto_ajustado(marco, "Los que puedes lanzar hoy; se cambian tras un descanso largo.", 760,
                       text_color="gray").pack(anchor="w")
        if not libro:
            ctk.CTkLabel(marco, text="Primero elige conjuros para el libro.", anchor="w").pack(anchor="w", pady=4)
        rejilla = ctk.CTkFrame(marco, fg_color="transparent")
        rejilla.pack(anchor="w", padx=6)
        casillas: dict[str, tuple[ctk.BooleanVar, ctk.CTkCheckBox]] = {}

        def actualizar():
            ids = [i for i, (v, _) in casillas.items() if v.get()]
            self.a.elegir_preparados(plan.clase_id, ids)
            contador.configure(text=f"Preparados {len(ids)}/{plan.limite_conjuros}")
            lleno = len(ids) >= (plan.limite_conjuros or 0)
            for variable, casilla in casillas.values():
                casilla.configure(state="disabled" if lleno and not variable.get() else "normal")
            self._refrescar()

        for i, (id_, nombre) in enumerate(libro):
            variable = ctk.BooleanVar(value=id_ in preparados)
            casilla = ctk.CTkCheckBox(rejilla, text=nombre, variable=variable, width=240, command=actualizar)
            casilla.grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=2)
            casillas[id_] = (variable, casilla)
        actualizar()

    def _paso_detalles(self, master) -> None:
        self._cabecera_paso(master, "detalles")
        p = self.a.personaje
        rejilla = ctk.CTkFrame(master, fg_color="transparent")
        rejilla.pack(anchor="w", padx=10)
        for col, (campo, texto, valor) in enumerate((("nombre", "Nombre", p.nombre), ("jugador", "Jugador", p.jugador))):
            ctk.CTkLabel(rejilla, text=texto, anchor="w").grid(row=0, column=col, sticky="w", padx=6)
            entrada = ctk.CTkEntry(rejilla, width=260)
            entrada.insert(0, valor)
            entrada.grid(row=1, column=col, padx=6, pady=(0, 8))
            entrada.bind("<KeyRelease>",
                         lambda _e, c=campo, w=entrada: (self.a.establecer_detalle(c, w.get()), self._refrescar()))
        ctk.CTkLabel(rejilla, text="Alineamiento", anchor="w").grid(row=0, column=2, sticky="w", padx=6)
        menu = ctk.CTkOptionMenu(rejilla, values=["—", *ALINEAMIENTOS], width=180,
                                 command=lambda v: self.a.establecer_detalle("alineamiento", "" if v == "—" else v))
        menu.set(p.detalles.get("alineamiento") or "—")
        menu.grid(row=1, column=2, padx=6, pady=(0, 8))

        sugerencias = self.a.personalidad_sugerida()
        titulo(master, "Personalidad", 15).pack(anchor="w", padx=10, pady=(10, 0))
        texto_ajustado(master, "Sirve también para los disparadores de inspiración. Puedes escribir lo tuyo o partir de "
                               "las sugerencias de tu trasfondo.", 760, text_color="gray").pack(anchor="w", padx=10)
        for campo, nombre in PERSONALIDAD:
            fila = ctk.CTkFrame(master, fg_color="transparent")
            fila.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(fila, text=nombre, width=170, anchor="w").pack(side="left", anchor="n")
            caja = ctk.CTkTextbox(fila, height=54, wrap="word")
            caja.insert("1.0", p.detalles.get(campo, ""))
            caja.pack(side="left", fill="x", expand=True)
            caja.bind("<KeyRelease>", lambda _e, c=campo, w=caja: self.a.establecer_detalle(c, w.get("1.0", "end").strip()))
            if sugerencias.get(campo):
                cortas = {(s[:60] + "…") if len(s) > 60 else s: s for s in sugerencias[campo]}

                def usar(valor, c=campo, w=caja, cortas=cortas):
                    w.delete("1.0", "end")
                    w.insert("1.0", cortas[valor])
                    self.a.establecer_detalle(c, cortas[valor])
                menu = ctk.CTkOptionMenu(fila, values=list(cortas), width=200, dynamic_resizing=False, command=usar)
                menu.set("Sugerencias")
                menu.pack(side="left", padx=6, anchor="n")

        titulo(master, "Aspecto e historia", 15).pack(anchor="w", padx=10, pady=(10, 4))
        fisico = ctk.CTkFrame(master, fg_color="transparent")
        fisico.pack(anchor="w", padx=10)
        for i, (campo, nombre) in enumerate(FISICO):
            ctk.CTkLabel(fisico, text=nombre).grid(row=(i // 3) * 2, column=i % 3, sticky="w", padx=6)
            entrada = ctk.CTkEntry(fisico, width=160)
            entrada.insert(0, p.detalles.get(campo, ""))
            entrada.grid(row=(i // 3) * 2 + 1, column=i % 3, padx=6, pady=(0, 6))
            entrada.bind("<KeyRelease>", lambda _e, c=campo, w=entrada: self.a.establecer_detalle(c, w.get()))
        for campo, nombre in (("apariencia", "Apariencia"), ("historia", "Historia")):
            ctk.CTkLabel(master, text=nombre, anchor="w").pack(anchor="w", padx=16, pady=(6, 0))
            caja = ctk.CTkTextbox(master, height=80, wrap="word")
            caja.insert("1.0", p.detalles.get(campo, ""))
            caja.pack(fill="x", padx=16)
            caja.bind("<KeyRelease>", lambda _e, c=campo, w=caja: self.a.establecer_detalle(c, w.get("1.0", "end").strip()))
        self._faltan(master, "detalles")

    def _subir_nivel(self, master) -> None:
        """Subir de nivel un personaje ya hecho: con preguntas (modo sencillo) o eligiendo uno mismo."""
        a = self.a
        p = a.personaje
        if not p.clases:
            return
        caja = ctk.CTkFrame(master)
        caja.pack(fill="x", padx=10, pady=(0, 8))
        fila = ctk.CTkFrame(caja, fg_color="transparent")
        fila.pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(fila, text=f"Subir de nivel (ahora, nivel {a.nivel}):", font=fuente(14, True)).pack(side="left")
        quedan = a.nivel_maximo() - a.nivel
        if quedan < 1:
            ctk.CTkLabel(fila, text="ya está en el nivel máximo con datos", text_color="gray").pack(side="left", padx=10)
            ctk.CTkFrame(caja, height=6, fg_color="transparent").pack()
            return
        niveles = ctk.CTkOptionMenu(fila, values=[f"+{n}" for n in range(1, quedan + 1)], width=70)
        niveles.pack(side="left", padx=10)
        nombres = {o.id: o.nombre for o in a.clases()}
        por_nombre = {nombres.get(e.clase, e.clase): e.clase for e in p.clases}
        clase = None
        if len(p.clases) > 1:
            clase = ctk.CTkOptionMenu(fila, values=list(por_nombre), width=170)
            clase.pack(side="left")

        def subir(con_preguntas: bool) -> None:
            n = int(niveles.get().lstrip("+"))
            clase_id = por_nombre[clase.get()] if clase is not None else None
            try:
                if con_preguntas:
                    self._subir_con_preguntas(n, clase_id)
                else:
                    a.subir_nivel(n, clase_id)
                    pendientes = [x.id for x in a.pasos() if x.id not in ("resumen", "detalles") and a.faltan(x.id)]
                    self.novedades = []
                    self.mostrar(pendientes[0] if pendientes else "resumen")
            except ValueError as exc:
                messagebox.showerror("No se puede subir de nivel", str(exc))

        hay_preguntas = any(x.get("momento") == "subida" for x in a.catalogo.listar("preguntas"))
        ctk.CTkButton(fila, text="Con preguntas…", width=140, state="normal" if hay_preguntas else "disabled",
                      command=lambda: subir(True)).pack(side="left", padx=(10, 0))
        ctk.CTkButton(fila, text="Elijo yo", width=100, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=lambda: subir(False)).pack(side="left", padx=10)
        ayuda = ("Con preguntas: un hito de la aventura (Guía del DM) y una pregunta por cada decisión de esos niveles, con "
                 "las opciones reales de tu personaje (subclases, mejoras con sus puntuaciones, dotes, opciones de clase, "
                 "conjuros). Elijo yo: sube el nivel y te lleva a lo que hay que decidir.")
        if not hay_preguntas:
            ayuda += " (Para las preguntas, carga el paquete «Cuestionario de situaciones».)"
        texto_ajustado(caja, ayuda, 760, text_color="gray").pack(anchor="w", padx=12, pady=(0, 10))

    def _subir_con_preguntas(self, niveles: int, clase_id: str | None) -> None:
        from .cuestionario_5e import VistaSubida5e  # aquí: cuestionario_5e importa este módulo

        app = self.master
        cuestionario = self.a.sistema.crear_cuestionario(self.a.personaje, self.a.catalogo)
        archivo = self.archivo

        def volver(novedades: list[str] | None = None) -> None:
            vista = VistaAsistente5e(app, self.a, self.al_volver, "resumen", novedades=novedades)
            vista.archivo = archivo
            app._cambiar(vista)

        app._cambiar(VistaSubida5e(app, cuestionario, niveles, clase_id, volver, volver))

    def _paso_resumen(self, master) -> None:
        self._cabecera_paso(master, "resumen")
        if self.novedades:
            ListaAvisos(master, self.novedades, "Novedades de la subida de nivel", completo=True).pack(fill="x", padx=10,
                                                                                                    pady=(0, 6))
        self._faltan(master, "resumen")
        pendiente = self.a.entrenamiento_pendiente()
        if pendiente:
            caja = ctk.CTkFrame(master)
            caja.pack(fill="x", padx=10, pady=(0, 8))
            texto = "; ".join(f"nivel {e['nivel']}: {e['dias']} días y {e['coste_po']} po" for e in pendiente)
            texto_ajustado(caja, f"Entrenamiento pendiente (Guía del DM, p. 131): {texto}. Los rasgos nuevos llegan al "
                                 "terminarlo.", 620).pack(side="left", padx=12, pady=10)
            ctk.CTkButton(caja, text="Hecho", width=90, command=lambda: (self.a.entrenamiento_hecho(), self._redibujar())
                          ).pack(side="right", padx=12)
        self._subir_nivel(master)
        ficha = self.a.ficha()
        if ficha.avisos:
            ListaAvisos(master, ficha.avisos, "Revisa antes de jugar").pack(fill="x", padx=10, pady=(0, 6))
        # Las exportaciones arriba, a la vista; el resumen debajo.
        botones = ctk.CTkFrame(master, fg_color="transparent")
        botones.pack(anchor="w", padx=10, pady=(4, 2))
        from ..sistemas.dnd5e_2014.salidas import hay_hoja_oficial
        ctk.CTkButton(botones, text="Hoja oficial (PDF editable)…", width=210,
                      state="normal" if hay_hoja_oficial() else "disabled",
                      command=lambda: self.exportar("oficial")).pack(side="left")
        ctk.CTkButton(botones, text="Ficha en PDF…", width=140,
                      command=lambda: self.exportar("pdf")).pack(side="left", padx=(10, 0))
        ctk.CTkButton(botones, text="Nota y guía para Nivel20…", width=210,
                      command=lambda: self.exportar("nota")).pack(side="left", padx=10)
        ctk.CTkButton(botones, text="Personaje (JSON)…", width=160, fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"), command=self.guardar).pack(side="left")
        texto_ajustado(master, "La hoja oficial es la editable en español, rellena (se puede seguir editando). La ficha en "
                               "PDF es una réplica en A4 que no depende de la plantilla. La nota es para Obsidian: "
                               "propiedades de la plantilla de PJ, ficha resumida y los pasos para crearlo en Nivel20. "
                               "El JSON sirve para volver a abrirlo aquí.", 760,
                       text_color="gray").pack(anchor="w", padx=10, pady=(4, 0))
        caja = ctk.CTkTextbox(master, height=480, wrap="word", font=ctk.CTkFont(family="Courier", size=13))
        caja.insert("1.0", resumen_ficha(ficha))
        caja.configure(state="disabled")
        caja.pack(fill="both", expand=True, padx=10, pady=8)
