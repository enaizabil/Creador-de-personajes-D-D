"""Vista del asistente de creación de 5e (2014): un panel por paso."""
from __future__ import annotations

from collections.abc import Callable
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


class VistaAsistente5e(ctk.CTkFrame):
    def __init__(self, master, asistente: Asistente5e, al_volver: Callable[[], None]):
        super().__init__(master, fg_color="transparent")
        self.a = asistente
        self.al_volver = al_volver
        self.nombres_paquetes = {p.id: p.nombre for p in asistente.catalogo.paquetes}
        self.paso_actual = "inicio"
        self.archivo: str | None = None
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
        self.mostrar("inicio")

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
        self.paso_actual = paso
        for hijo in self.contenido.winfo_children():
            hijo.destroy()
        getattr(self, f"_paso_{paso}")(self.contenido)
        self._refrescar()

    def _redibujar(self) -> None:
        self.mostrar(self.paso_actual)

    def _refrescar(self) -> None:
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
            SelectorEleccion(master, eleccion, self._eleccion_cambiada).pack(fill="x", padx=10, pady=4)

    def _eleccion_cambiada(self, clave: str, valores: list[str]) -> None:
        self.a.elegir(clave, valores)
        self._redibujar()

    def _faltan(self, master, paso: str) -> None:
        ListaAvisos(master, self.a.faltan(paso)).pack(fill="x", padx=10, pady=(14, 6))

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

    # ── pasos ─────────────────────────────────────────────────────────────

    def _paso_inicio(self, master) -> None:
        self._cabecera_paso(master, "inicio")
        reglas = self.a.personaje.reglas_opcionales
        caja = ctk.CTkFrame(master)
        caja.pack(fill="x", padx=10, pady=4)
        fila = ctk.CTkFrame(caja, fg_color="transparent")
        fila.pack(anchor="w", padx=12, pady=12)
        ctk.CTkLabel(fila, text="Nivel inicial:", font=fuente(14, True)).pack(side="left", padx=(0, 10))
        menu = ctk.CTkOptionMenu(fila, values=[str(n) for n in range(1, 21)], width=80,
                                 command=lambda v: (self.a.establecer_nivel(int(v)), self._redibujar()))
        menu.set(str(self.a.nivel))
        menu.pack(side="left")
        ctk.CTkLabel(fila, text="(los datos de clase llegan, por ahora, hasta nivel 5)",
                     text_color="gray").pack(side="left", padx=10)

        interruptores = [("dotes", "Dotes (regla opcional del Manual del Jugador)", True),
                         ("multiclase", "Multiclase (regla opcional del Manual del Jugador)", True),
                         ("opciones_dm", "Opciones de la Guía del DM que requieren su permiso (aasimar, eladrín…)", False)]
        if any(p.id == "dmg-2014" for p in self.a.catalogo.paquetes):
            interruptores.append(("equipo_por_nivel", "Oro extra al empezar por encima de nivel 4 (Guía del DM)", False))
        for regla, texto, defecto in interruptores:
            variable = ctk.BooleanVar(value=reglas.get(regla, defecto))
            ctk.CTkSwitch(caja, text=texto, variable=variable,
                          command=lambda r=regla, v=variable: (self.a.establecer_regla(r, v.get()), self._refrescar())
                          ).pack(anchor="w", padx=12, pady=4)
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
        ListaOpciones(master, "Clase", self.a.clases(), actual, lambda i: (self.a.elegir_clase(i), self._redibujar()),
                      self.nombres_paquetes, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10)
        subclases = self.a.subclases()
        if subclases:
            ListaOpciones(master, "Subclase", subclases, p.clases[0].subclase,
                          lambda i: (self.a.elegir_subclase(i), self._redibujar()), self.nombres_paquetes,
                          alto=180, nombres_perfil=NOMBRES_PERFIL).pack(fill="x", padx=10, pady=(14, 0))
        self._elecciones(master, "clase")
        self._faltan(master, "clase")

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
        for plan in self.a.planes_conjuros():
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

            def actualizar(plan=plan, casillas=casillas, contador=contador):
                ids = [i for i, (v, _, _) in casillas.items() if v.get()]
                self.a.elegir_conjuros(plan.clase_id, ids)
                trucos = sum(1 for i in ids if casillas[i][2] == 0)
                otros = len(ids) - trucos
                texto = []
                if plan.limite_trucos is not None:
                    texto.append(f"Trucos {trucos}/{plan.limite_trucos}")
                if plan.limite_conjuros is not None:
                    palabra = "Conocidos" if plan.modo == "conocidos" else "Preparados"
                    texto.append(f"{palabra} {otros}/{plan.limite_conjuros}")
                contador.configure(text="  ·  ".join(texto))
                for _id, (variable, casilla, nivel) in casillas.items():
                    limite = plan.limite_trucos if nivel == 0 else plan.limite_conjuros
                    lleno = limite is not None and (trucos if nivel == 0 else otros) >= limite
                    casilla.configure(state="disabled" if lleno and not variable.get() else "normal")
                self._refrescar()

            for nivel, opciones in plan.disponibles.items():
                ctk.CTkLabel(master, text="Trucos" if nivel == 0 else f"Nivel {nivel}", font=fuente(14, True),
                             anchor="w").pack(anchor="w", padx=10, pady=(8, 2))
                rejilla = ctk.CTkFrame(master, fg_color="transparent")
                rejilla.pack(anchor="w", padx=16)
                for i, (id_, nombre) in enumerate(opciones):
                    variable = ctk.BooleanVar(value=id_ in elegidos)
                    casilla = ctk.CTkCheckBox(rejilla, text=nombre, variable=variable, width=240, command=actualizar)
                    casilla.grid(row=i // 3, column=i % 3, sticky="w", padx=4, pady=2)
                    casillas[id_] = (variable, casilla, nivel)
            actualizar()
        self._faltan(master, "conjuros")

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

    def _paso_resumen(self, master) -> None:
        self._cabecera_paso(master, "resumen")
        self._faltan(master, "resumen")
        ficha = self.a.ficha()
        if ficha.avisos:
            ListaAvisos(master, ficha.avisos, "Revisa antes de jugar").pack(fill="x", padx=10, pady=(0, 6))
        caja = ctk.CTkTextbox(master, height=520, wrap="word", font=ctk.CTkFont(family="DejaVu Sans Mono", size=13))
        caja.insert("1.0", resumen_ficha(ficha))
        caja.configure(state="disabled")
        caja.pack(fill="both", expand=True, padx=10, pady=8)
        texto_ajustado(master, "La ficha oficial, el PDF rellenable y la guía para Nivel20 llegan en el paso 5. "
                               "Por ahora puedes guardar el personaje en JSON y volver a abrirlo.", 760,
                       text_color="gray").pack(anchor="w", padx=10)
