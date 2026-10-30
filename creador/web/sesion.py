"""Sesión de la versión web: el estado de la creación, cada pantalla descrita en JSON y las acciones de la página.

La página llama a ``Sesion.llamar(accion, args)`` y recibe ``{"vista", "estado", "archivo", "mensaje", "error"}``:
la vista que pintar, el estado para guardarlo en el navegador (``Sesion.restaurar`` lo recupera), un archivo que
descargar o un mensaje que enseñar. Las pantallas copian las de escritorio (``creador/gui``).
"""
from __future__ import annotations

import base64
import json
import re
import tempfile
import uuid
from pathlib import Path

from .. import __version__
from ..entorno import abrir_catalogo, paquetes_instalados
from ..gestor import ErrorInstalacion, es_integrado, instalar, quitar
from ..nucleo.personaje import Personaje
from ..sistemas.dnd5e_2014.asistente import ALINEAMIENTOS, METODOS_CARACTERISTICAS
from ..sistemas.dnd5e_2014.constantes import CARACTERISTICAS, COSTE_COMPRA, TIPOS_DANO
from ..sistemas.dnd5e_2014.cuestionario import MINIMO_RESPUESTAS, NIVEL_MINIMO_MULTICLASE, UMBRAL_ALINEAMIENTO
from ..sistemas.dnd5e_2014.interfaz import (AYUDA_SUBIDA, CUANTAS_RECOMENDACIONES, FISICO, ICONO_GENERICO,
                                            LARGO_DESCRIPCION_OPCIONAL, MARCA_PROPUESTA, MAX_CASILLAS, MAX_DESPLEGABLE,
                                            NOMBRES_DECISION, NOMBRES_PERFIL, PERSONALIDAD, RESPUESTAS_EN_UNA_COLUMNA,
                                            interruptores_reglas, nombre_icono, perfil_en_puntos)
from ..sistemas.dnd5e_2014.texto import resumen_ficha
from . import componentes as c

SISTEMA = "dnd5e-2014"
VERSION_ESTADO = 1
ETIQUETAS_TIPO = {"oficial": "Oficial", "propio": "Del programa", "homebrew": "Homebrew"}
FORMATOS = {"pdf": (".pdf", "application/pdf"), "oficial": (".pdf", "application/pdf"),
            "nota": (".md", "text/markdown"), "json": (".json", "application/json")}
DANOS_ELEGIBLES = [(i, n) for i, n in TIPOS_DANO.items() if i not in ("contundente", "cortante", "perforante")]
TEMPORAL = re.compile(r"(?:/[^/\s]+)*/tmp[\w-]+/")
PANTALLAS_CUESTIONARIO = ("cuestionario", "pregunta", "resultado", "historia", "subida")


class Sesion:
    def __init__(self) -> None:
        self.pantalla = "portada"
        self.id = ""
        self.paquetes: list[str] = []
        self.marcados: dict[str, bool] | None = None  # casillas de la portada
        self.sistema = self.catalogo = self.personaje = self.a = self.q = None
        self.paso = "inicio"
        self.indice = 0  # pregunta del cuestionario
        self.nivel = 1  # nivel pedido en el cuestionario
        self.eleccion: dict[str, list] = {}  # resultado: raza [id, subraza], clase [id], trasfondo [id]
        self.reparto: list[list] = []
        self.nombre = ""
        self.novedades: list[str] = []
        self.subida = {"niveles": 1, "clase": None}
        self.nuevo_magico = {"id": None, "bonificador": 1}

    # ── entrada única ──────────────────────────────────────────────────────

    def llamar(self, accion: str, args: dict | None = None) -> dict:
        respuesta: dict = {}
        metodo = getattr(self, f"accion_{accion}", None)
        if metodo is None:
            respuesta["error"] = f"Acción desconocida «{accion}»"
        else:
            try:
                extra = metodo(**(args or {}))
                if isinstance(extra, dict):
                    respuesta.update(extra)
            except (ValueError, ErrorInstalacion, KeyError) as exc:
                respuesta["error"] = str(exc).strip("'\"")
        respuesta["vista"] = self.vista()
        respuesta["estado"] = self.estado()
        return respuesta

    def llamar_json(self, accion: str, args_json: str = "{}") -> str:
        """Para la página: argumentos y respuesta en texto JSON."""
        return json.dumps(self.llamar(accion, json.loads(args_json or "{}")), ensure_ascii=False)

    # ── estado (para guardarlo en el navegador) ──────────────────────────

    def estado(self) -> dict | None:
        if self.personaje is None:
            return None
        return {"version": VERSION_ESTADO, "id": self.id, "pantalla": self.pantalla, "paso": self.paso,
                "indice": self.indice, "nivel": self.nivel, "eleccion": self.eleccion, "reparto": self.reparto,
                "nombre": self.nombre, "novedades": self.novedades, "subida": self.subida,
                "paquetes": self.paquetes, "personaje": self.personaje.a_dict(),
                "titulo": self._titulo_personaje()}

    def accion_restaurar(self, estado: dict) -> None:
        if not estado or estado.get("version") != VERSION_ESTADO:
            raise ValueError("No se puede recuperar ese personaje (guardado con otra versión)")
        personaje = Personaje.desde_dict(estado["personaje"])
        self._abrir(personaje, estado["pantalla"] in PANTALLAS_CUESTIONARIO)
        self.id = estado.get("id") or uuid.uuid4().hex
        for campo in ("pantalla", "paso", "indice", "nivel", "eleccion", "reparto", "nombre", "novedades", "subida"):
            setattr(self, campo, estado.get(campo, getattr(self, campo)))

    def _abrir(self, personaje: Personaje, con_cuestionario: bool) -> None:
        sistema, catalogo, errores = abrir_catalogo(personaje.sistema, personaje.paquetes)
        self.sistema, self.catalogo, self.personaje = sistema, catalogo, personaje
        self.paquetes = list(personaje.paquetes)
        self.q = sistema.crear_cuestionario(personaje, catalogo) if con_cuestionario else None
        self.a = self.q.asistente if self.q else sistema.crear_asistente(personaje, catalogo)
        self.id = uuid.uuid4().hex
        self.novedades = []
        return errores

    def _titulo_personaje(self) -> str:
        if self.a is None or not self.personaje.clases:
            return self.personaje.nombre or "Personaje sin nombre"
        ficha = self.a.ficha()
        return " · ".join(p for p in (ficha.nombre or "Sin nombre", ficha.raza, ficha.clase_y_nivel) if p)

    # ── vistas ─────────────────────────────────────────────────────────────

    def vista(self) -> dict:
        contenido = getattr(self, f"_vista_{self.pantalla}")()
        vista = contenido if self.pantalla == "asistente" else {"pantalla": self.pantalla, "contenido": contenido}
        vista["contenido"] = [x for x in vista["contenido"] if x]
        return vista

    # ── portada ────────────────────────────────────────────────────────────

    def _disponibles(self) -> dict:
        return self._buscar_paquetes()[0]

    @staticmethod
    def _buscar_paquetes() -> tuple[dict, list[str]]:
        disponibles, avisos = paquetes_instalados()
        return {i: info for i, info in disponibles.items() if info.sistema == SISTEMA}, avisos

    def _vista_portada(self) -> list[dict]:
        disponibles, avisos = self._buscar_paquetes()
        if self.marcados is None or set(self.marcados) != set(disponibles):
            self.marcados = {i: info.tipo in ("oficial", "propio") for i, info in disponibles.items()}
        paquetes = []
        for info in sorted(disponibles.values(), key=lambda i: (len(i.depende_de), i.nombre)):
            detalle = info.descripcion
            if info.depende_de:
                necesita = ", ".join(disponibles[d].nombre for d in info.depende_de if d in disponibles)
                detalle += f"  (necesita: {necesita})"
            paquetes.append(c.interruptor(info.nombre, self.marcados[info.id], "marcar_paquete", {"id": info.id},
                                          f"{ETIQUETAS_TIPO.get(info.tipo, 'Homebrew')} · {detalle}"))
        return [
            c.titulo("Creador de personajes de rol", 1, ICONO_GENERICO),
            c.texto("Elige los libros o el homebrew que se usan en tu mesa: solo aparecerá lo que aporten los paquetes "
                    "marcados. «Crear con preguntas» decide el personaje por ti a partir de situaciones cotidianas; «Paso a "
                    "paso» te deja elegirlo todo.", "gris"),
            c.titulo("Paquetes de contenido", 3),
            c.caja(*paquetes),
            c.fila(c.boton("Crear con preguntas", "crear", {"modo": "sencillo"}),
                   c.boton("Crear paso a paso", "crear", {"modo": "normal"}),
                   c.archivo("Abrir personaje (.json)…", "abrir_personaje", ".json"),
                   c.boton("Paquetes…", "ir", {"pantalla": "paquetes"}, "secundario")),
            c.texto("Avisos al buscar paquetes: " + "; ".join(avisos), "aviso") if avisos else None,
            c.texto(f"Versión {__version__}. Iconos: game-icons.net (Lorc, Delapouite, Cathelineau), CC BY 3.0 · "
                    "Tipografía: Cinzel, SIL Open Font License 1.1.", "pequeno"),
        ]

    def accion_marcar_paquete(self, id: str, valor: bool) -> None:  # noqa: A002 - nombre que manda la página
        """Marcar un paquete marca sus dependencias; desmarcarlo desmarca los que dependen de él."""
        disponibles = self._disponibles()
        self.marcados[id] = valor
        if valor:
            pendientes = list(disponibles[id].depende_de)
            while pendientes:
                dep = pendientes.pop()
                if dep in self.marcados and not self.marcados[dep]:
                    self.marcados[dep] = True
                    pendientes += disponibles[dep].depende_de
        else:
            for otro, info in disponibles.items():
                if id in info.depende_de and self.marcados.get(otro):
                    self.accion_marcar_paquete(otro, False)

    def accion_crear(self, modo: str) -> dict | None:
        elegidos = [i for i, marcado in (self.marcados or {}).items() if marcado]
        if not elegidos:
            raise ValueError("Marca al menos un paquete de contenido")
        errores = self._abrir(Personaje(sistema=SISTEMA, paquetes=elegidos), modo == "sencillo")
        self.paso, self.indice, self.nivel, self.eleccion, self.reparto, self.nombre = "inicio", 0, 1, {}, [], ""
        if modo == "sencillo" and not self.q.preguntas():
            self.q = None
            self.pantalla = "portada"
            raise ValueError("Ningún paquete marcado trae preguntas: marca «Cuestionario de situaciones» o crea el "
                             "personaje paso a paso")
        self.pantalla = "cuestionario" if modo == "sencillo" else "asistente"
        return {"mensaje": "Errores en los paquetes: " + "; ".join(errores[:5])} if errores else None

    def accion_ir(self, pantalla: str) -> None:
        if pantalla not in ("portada", "paquetes"):
            raise ValueError(f"Pantalla desconocida «{pantalla}»")
        if pantalla == "portada":
            self.personaje = self.a = self.q = None
        self.pantalla = pantalla

    def accion_abrir_personaje(self, nombre: str, datos: str) -> None:
        try:
            personaje = Personaje.desde_dict(json.loads(base64.b64decode(datos).decode("utf-8")))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"No se puede abrir «{nombre}»: {exc}") from None
        self._abrir(personaje, False)
        self.pantalla, self.paso = "asistente", "resumen"

    # ── paquetes ───────────────────────────────────────────────────────────

    def _vista_paquetes(self) -> list[dict]:
        disponibles, avisos = paquetes_instalados()
        tarjetas = []
        for info in sorted(disponibles.values(), key=lambda i: (not es_integrado(i), i.nombre)):
            integrado = es_integrado(info)
            partes = [info.id, f"versión {info.version}", ETIQUETAS_TIPO.get(info.tipo, info.tipo),
                      "Integrado" if integrado else "Instalado por ti"]
            detalle = info.descripcion
            if info.depende_de:
                nombres = [disponibles[d].nombre if d in disponibles else f"{d} (¡no instalado!)" for d in info.depende_de]
                detalle += f"  Necesita: {', '.join(nombres)}."
            tarjetas.append(c.caja(
                c.fila(c.texto(info.nombre, "negrita"),
                       None if integrado else c.boton("Quitar", "quitar_paquete", {"id": info.id}, "peligro",
                                                      confirmar=f"¿Quitar «{info.nombre}»?")),
                c.texto("  ·  ".join(partes), "gris"), c.texto(detalle)))
        return [
            c.titulo("Paquetes de contenido", 1),
            c.texto("Los integrados vienen con el programa. Los tuyos (homebrew o expansiones) se importan desde un .zip y "
                    "se validan antes de instalarse; se guardan en este navegador. Para usarlos, márcalos en la portada.",
                    "gris"),
            c.fila(c.archivo("Importar .zip…", "importar_paquete", ".zip", estilo="primario"),
                   c.boton("← Volver", "ir", {"pantalla": "portada"}, "secundario")),
            *[c.texto(f"Aviso: {aviso}", "aviso") for aviso in avisos],
            *tarjetas,
        ]

    def accion_importar_paquete(self, nombre: str, datos: str) -> dict:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / (Path(nombre).name or "paquete.zip")
            ruta.write_bytes(base64.b64decode(datos))
            try:
                instalado = instalar(ruta, reemplazar=True)
            except ErrorInstalacion as exc:  # sin las carpetas temporales, que en el navegador no dicen nada
                raise ErrorInstalacion(TEMPORAL.sub("", str(exc))) from None
        accion = "actualizado" if instalado.reemplazado else "instalado"
        self.marcados = None
        return {"mensaje": f"«{instalado.info.nombre}» {accion}. Márcalo en la portada para usarlo."}

    def accion_quitar_paquete(self, id: str) -> dict:  # noqa: A002
        info = quitar(id)
        self.marcados = None
        return {"mensaje": f"«{info.nombre}» quitado."}

    # ── cuestionario ───────────────────────────────────────────────────────

    def _vista_cuestionario(self) -> list[dict]:
        q = self.q
        conf = q.configuracion
        cantidades = [(clave, f"{nombre} ({len(q.preguntas(cantidad=clave))})") for clave, nombre in
                      (("rapido", "Rápido"), ("recomendado", "Recomendado"), ("preciso", "Preciso"))]
        bloques = [
            c.titulo("Crea tu personaje respondiendo preguntas", 1, ICONO_GENERICO),
            c.texto("No hace falta saber nada de reglas. Te contaremos situaciones (de la vida cotidiana o de fantasía) y tú "
                    "dices qué haría tu personaje. Con eso proponemos raza, clase, trasfondo, características y todo lo "
                    "demás. Al final podrás cambiar lo que quieras.", "grande"),
            c.segmentado(cantidades, conf["cantidad"], "configurar", {"campo": "cantidad"}, "Preguntas"),
            c.segmentado([("cotidiana", "Vida cotidiana"), ("fantasia", "Fantasía"), ("mezcla", "Mezcla")], conf["estilo"],
                         "configurar", {"campo": "estilo"}, "Estilo"),
            c.interruptor("Incluir preguntas de contenido sensible o bizarro (muerte, crueldad, situaciones absurdas)",
                          conf["sensible"], "configurar", {"campo": "sensible"}),
        ]
        if "tasha-2020" in self.paquetes:
            reglas = self.personaje.reglas_opcionales
            bloques += [
                c.interruptor("Personalizar tu origen (Tasha): las mejoras de raza van donde más le sirven a tu clase",
                              reglas.get("origen_personalizado", False), "regla", {"regla": "origen_personalizado"}),
                c.interruptor("Rasgos de clase opcionales (Tasha): más conjuros, estilos e invocaciones, y versiones nuevas "
                              "de algunos rasgos", reglas.get("rasgos_opcionales", False), "regla",
                              {"regla": "rasgos_opcionales"})]
        maximo = self.a.nivel_maximo()
        bloques += [
            c.texto(f"Son {len(q.preguntas())} preguntas; con {MINIMO_RESPUESTAS} ya hay un resultado. Puedes saltarte las "
                    "que no te convenzan.", "gris"),
            c.menu([(str(n), str(n)) for n in range(1, maximo + 1)], str(self.nivel), "nivel_cuestionario",
                   etiqueta="Nivel del personaje (si no te lo han dicho, 1)")]
        if self.nivel >= NIVEL_MINIMO_MULTICLASE:
            bloques.append(c.interruptor("Multiclase: repartir los niveles entre dos clases (para jugadores con experiencia)",
                                         q.acepta_multiclase, "multiclase_cuestionario",
                                         ayuda="Si no sabes qué es, déjala apagada: tendrás una sola clase."))
        bloques.append(c.fila(c.boton("Empezar", "pregunta", {"indice": 0}),
                              c.boton("Volver al inicio", "ir", {"pantalla": "portada"}, "secundario")))
        return bloques

    def accion_configurar(self, campo: str, valor) -> None:
        self.q.configurar(**{campo: valor})
        self.indice = 0

    def accion_regla(self, regla: str, valor: bool) -> None:
        self.a.establecer_regla(regla, valor)

    def accion_nivel_cuestionario(self, valor: str) -> None:
        self.nivel = int(valor)
        if self.nivel < NIVEL_MINIMO_MULTICLASE and self.q.acepta_multiclase:
            self.q.aceptar_multiclase(False)

    def accion_multiclase_cuestionario(self, valor: bool) -> None:
        self.q.aceptar_multiclase(valor)

    def accion_pregunta(self, indice: int) -> None:
        preguntas = self.q.preguntas()
        if indice < 0:
            self.pantalla = "cuestionario"
        elif indice >= len(preguntas):
            self.pantalla = "resultado"
        else:
            self.pantalla, self.indice = "pregunta", indice

    def _vista_pregunta(self) -> list[dict]:
        preguntas = self.q.preguntas()
        self.indice = min(self.indice, len(preguntas) - 1)
        pregunta = preguntas[self.indice]
        actual = self.q.respuestas.get(pregunta.id)
        respondidas = len(self.q.respuestas)
        return [
            c.texto(f"Pregunta {self.indice + 1} de {len(preguntas)}  ·  {pregunta.titulo}", "gris"),
            c.barra(self.indice / len(preguntas)),
            c.titulo(pregunta.texto, 2),
            c.respuestas([{"id": r.id, "texto": r.texto, "detalle": "", "propuesta": False, "elegida": r.id == actual}
                          for r in pregunta.respuestas], "responder", {"pregunta": pregunta.id}),
            c.fila(c.boton("← Anterior", "pregunta", {"indice": self.indice - 1}, "secundario"),
                   c.boton("Saltar", "responder", {"pregunta": pregunta.id, "respuesta": None}, "secundario"),
                   c.boton("Ver mi personaje ya →", "pregunta", {"indice": len(preguntas)})
                   if respondidas >= MINIMO_RESPUESTAS else c.texto(f"{respondidas} respondidas", "gris")),
        ]

    def accion_responder(self, pregunta: str, respuesta: str | None) -> None:
        self.q.responder(pregunta, respuesta)
        self.accion_pregunta(self.indice + 1)

    # resultado

    def _recomendaciones(self) -> dict[str, tuple[list, object]]:
        """Por raza, clase y trasfondo: las propuestas y la elegida (la primera si no hay otra)."""
        resultado = {}
        for clave, lista in (("raza", self.q.recomendar_razas()), ("clase", self.q.recomendar_clases()),
                             ("trasfondo", self.q.recomendar_trasfondos())):
            lista = lista[:CUANTAS_RECOMENDACIONES]
            guardada = self.eleccion.get(clave)
            actual = next((r for r in lista if guardada and [r.id, r.subraza][:len(guardada)] == guardada), lista[0])
            self.eleccion[clave] = [actual.id, actual.subraza] if clave == "raza" else [actual.id]
            resultado[clave] = (lista, actual)
        return resultado

    def _vista_resultado(self) -> list[dict]:
        q = self.q
        if len(q.respuestas) < MINIMO_RESPUESTAS:
            return [c.titulo("Faltan respuestas", 1),
                    c.texto(f"Responde al menos {MINIMO_RESPUESTAS} preguntas para tener un resultado fiable (llevas "
                            f"{len(q.respuestas)})."),
                    c.boton("Volver a las preguntas", "pregunta", {"indice": 0})]
        recomendaciones = self._recomendaciones()
        perfil = sorted(q.perfil().items(), key=lambda x: -x[1])[:3]
        rasgos = ", ".join(NOMBRES_PERFIL.get(r, r).lower() for r, _ in perfil)
        bloques = [
            c.titulo("Así es tu personaje", 1, ICONO_GENERICO),
            c.texto(f"Lo que más le define: {rasgos}. Alineamiento: {q.alineamiento()}. Te proponemos lo que mejor encaja; "
                    "puedes elegir otra opción de cada lista.", "grande"),
            c.columnas(*[self._columna_recomendaciones(clave, nombre, *recomendaciones[clave]) for clave, nombre in
                         (("raza", "Raza"), ("clase", "Clase"), ("trasfondo", "Trasfondo"))]),
            self._porque(recomendaciones),
        ]
        if q.acepta_multiclase:
            bloques.append(self._reparto(recomendaciones["clase"][1]))
        siguiente = "Crear personaje" if self.nivel == 1 else f"Su historia hasta nivel {self.nivel} →"
        bloques += [
            c.entrada(self.nombre or self.personaje.nombre, "nombre_cuestionario", etiqueta="Nombre",
                      marcador="Cómo se llama tu personaje"),
            c.fila(c.boton(siguiente, "siguiente_resultado"),
                   c.boton("Repasar las preguntas", "pregunta", {"indice": 0}, "secundario")),
        ]
        return bloques

    def _columna_recomendaciones(self, clave: str, nombre: str, lista: list, actual) -> dict:
        categoria = {"raza": "razas", "clase": "clases", "trasfondo": "trasfondos"}[clave]
        return {"t": "recomendaciones", "titulo": nombre, "icono": nombre_icono(categoria, actual.id),
                "opciones": [{"id": i, "nombre": r.nombre_completo, "afinidad": r.afinidad} for i, r in enumerate(lista)],
                "seleccion": lista.index(actual), "descripcion": actual.descripcion, "accion": "elegir_recomendacion",
                "args": {"clave": clave}}

    def accion_elegir_recomendacion(self, clave: str, valor: int) -> None:
        lista = {"raza": self.q.recomendar_razas, "clase": self.q.recomendar_clases,
                 "trasfondo": self.q.recomendar_trasfondos}[clave]()[:CUANTAS_RECOMENDACIONES]
        elegida = lista[int(valor)]
        self.eleccion[clave] = [elegida.id, elegida.subraza] if clave == "raza" else [elegida.id]
        if clave == "clase":
            self.reparto = []

    def _porque(self, recomendaciones: dict) -> dict:
        q = self.q
        raza, clase = recomendaciones["raza"][1], recomendaciones["clase"][1]
        totales = q.totales_alineamiento()
        ejes = f"orden {totales.get('orden', 0):+d}, moral {totales.get('moral', 0):+d}; desde ±{UMBRAL_ALINEAMIENTO} se inclina"
        bloques = [(f"Raza: {raza.nombre_completo} ({raza.afinidad}%)", q.explicar("razas", raza.id, raza.subraza), True),
                   (f"Clase: {clase.nombre} ({clase.afinidad}%)", q.explicar("clases", clase.id), True),
                   (f"Alineamiento: {q.alineamiento()} ({ejes})", q.explicar_alineamiento(), False)]
        hijos = [c.titulo("¿Por qué este resultado?", 3),
                 c.texto("Puntos: cuánto bajaría la afinidad si no hubieras respondido esa pregunta (negativos: cuánto la "
                         "ha bajado).", "gris")]
        for cabecera, motivos, con_puntos in bloques:
            hijos.append(c.texto(cabecera, "negrita"))
            if not motivos:
                hijos.append(c.texto("Ninguna respuesta ha influido.", "gris"))
            for motivo in motivos[:5]:
                puntos = f"{motivo.puntos:+.0f}" if con_puntos else motivo.detalle
                detalle = f" ({motivo.detalle})" if motivo.detalle and con_puntos else ""
                hijos.append(c.texto(f"• «{motivo.pregunta}»: {motivo.respuesta} → {puntos}{detalle}"))
        return c.caja(*hijos)

    def _reparto(self, principal) -> dict:
        nombres = {r.id: r.nombre for r in self.q.recomendar_clases()}
        nivel_subclase = (self.catalogo.obtener("clases", principal.id) or {}).get("nivel_subclase", 1)
        libres = self.nivel - nivel_subclase
        if self.nivel < NIVEL_MINIMO_MULTICLASE or libres < 1:
            return c.caja(c.titulo("Reparto de clases", 3),
                          c.texto(f"A nivel {self.nivel} te proponemos una sola clase: repartir dejaría a {principal.nombre} "
                                  "sin lo que la define.", "gris"))
        if not self.reparto or self.reparto[0][0] != principal.id:
            self.reparto = [list(r) for r in self.q.proponer_reparto(self.nivel, principal.id)]
        reparto = " / ".join(f"{nombres.get(cl, cl)} {n}" for cl, n in self.reparto)
        candidatas = [r for r in self.q.recomendar_clases() if self.q.compatibles(principal.id, r.id)]
        actual = self.reparto[1] if len(self.reparto) > 1 else [None, 1]
        return c.caja(
            c.titulo("Reparto de clases", 3),
            c.texto(f"Propuesta: {reparto}. Puedes cambiar la segunda clase o sus niveles."),
            c.fila(c.menu([("", "Ninguna"), *[(r.id, r.nombre) for r in candidatas]], actual[0] or "", "cambiar_reparto",
                          {"campo": "clase"}, "Segunda clase"),
                   c.menu([(str(n), str(n)) for n in range(1, libres + 1)], str(min(actual[1], libres)), "cambiar_reparto",
                          {"campo": "niveles"}, "Niveles")))

    def accion_cambiar_reparto(self, campo: str, valor: str) -> None:
        principal = self.eleccion["clase"][0]
        otra, niveles = (self.reparto[1] if len(self.reparto) > 1 else [None, 1])
        if campo == "clase":
            otra = valor or None
        else:
            niveles = int(valor)
        self.reparto = [[principal, self.nivel - niveles], [otra, niveles]] if otra else [[principal, self.nivel]]

    def accion_nombre_cuestionario(self, valor: str) -> None:
        self.nombre = valor.strip()

    def _eleccion_generar(self) -> dict:
        raza, clase, trasfondo = self.eleccion["raza"], self.eleccion["clase"][0], self.eleccion["trasfondo"][0]
        reparto = ([tuple(r) for r in self.reparto] if self.q.acepta_multiclase and self.reparto
                   and self.reparto[0][0] == clase else None)
        return {"raza": raza[0], "subraza": raza[1], "clase": clase, "trasfondo": trasfondo, "reparto": reparto}

    def accion_siguiente_resultado(self) -> None:
        self._recomendaciones()
        if self.nivel > 1 and self.q.preguntas_de_historia(self.nivel, **self._eleccion_generar()):
            self.pantalla = "historia"
        else:
            self.accion_crear_personaje()

    def _vista_historia(self) -> list[dict]:
        clase = self.catalogo.obtener("clases", self.eleccion["clase"][0])["nombre"]
        preguntas = self.q.preguntas_de_historia(self.nivel, **self._eleccion_generar())
        return [
            c.titulo(f"Su historia hasta el nivel {self.nivel}", 1),
            c.texto(f"Tu {clase.lower()} ya ha vivido aventuras. Cuéntanos cómo le han cambiado y con eso decidimos su "
                    f"subclase, mejoras, dotes, opciones de clase y conjuros. {AYUDA_SUBIDA}", "grande"),
            *self._preguntas_subida(preguntas),
            c.fila(c.boton("← Volver al resultado", "volver_resultado", estilo="secundario"),
                   c.boton("Crear personaje", "crear_personaje")),
        ]

    def accion_volver_resultado(self) -> None:
        self.pantalla = "resultado"

    def _preguntas_subida(self, preguntas: list) -> list[dict]:
        """Hitos y preguntas concretas: pulsar una respuesta elegida la quita; en las de varias, al pasarse sale la
        primera marcada."""
        bloques = []
        for pregunta in preguntas:
            actual = self.q.respuestas_subida.get(pregunta.id)
            elegidas = set(actual) if isinstance(actual, list) else {actual}
            bloques += [c.texto(pregunta.titulo, "gris"), c.titulo(pregunta.texto, 3)]
            if pregunta.elegir > 1:
                marcadas = len(elegidas & {r.id for r in pregunta.respuestas})
                bloques.append(c.texto(f"Llevas {marcadas} de {pregunta.elegir}; las que falten se eligen solas.", "gris"))
            bloques.append(c.respuestas(
                [{"id": r.id, "texto": r.texto, "detalle": ((MARCA_PROPUESTA + " ") if r.propuesta else "") + r.detalle,
                  "propuesta": r.propuesta, "elegida": r.id in elegidas} for r in pregunta.respuestas],
                "responder_subida", {"pregunta": pregunta.id},
                2 if len(pregunta.respuestas) > RESPUESTAS_EN_UNA_COLUMNA else 1))
        return bloques

    def accion_responder_subida(self, pregunta: str, respuesta: str) -> None:
        q = self.q
        actual = q.respuestas_subida.get(pregunta)
        if not pregunta.startswith("c:"):
            q.responder_subida(pregunta, None if respuesta == actual else respuesta)
            return
        elegir = next((p.elegir for p in self._preguntas_vigentes() if p.id == pregunta), 1)
        lista = list(actual or [])
        lista = [v for v in lista if v != respuesta] if respuesta in lista else (lista + [respuesta])[-elegir:]
        q.responder_subida(pregunta, lista)

    def _preguntas_vigentes(self) -> list:
        if self.pantalla == "historia":
            return self.q.preguntas_de_historia(self.nivel, **self._eleccion_generar())
        return self.q.preguntas_de_subida(self.subida["niveles"], self.subida["clase"])

    def accion_crear_personaje(self) -> None:
        eleccion = self._eleccion_generar()
        # Fuera las respuestas a preguntas que ya no se plantean (de otra clase elegida antes, p. ej.).
        self.q.conservar_respuestas_subida({p.id for p in self.q.preguntas_de_historia(self.nivel, **eleccion)})
        self.q.generar(nivel=self.nivel, **eleccion)
        if self.nombre:
            self.a.establecer_detalle("nombre", self.nombre)
        self.pantalla, self.paso = "asistente", "resumen"

    # ── asistente ──────────────────────────────────────────────────────────

    def _vista_asistente(self) -> dict:
        a = self.a
        if self.paso not in [p.id for p in a.pasos()]:
            self.paso = "inicio"
        if self.paso == "equipo":
            a.aplicar_equipo()
        contenido = getattr(self, f"_paso_{self.paso}")()
        ficha = a.ficha()
        partes = [ficha.nombre or "Personaje sin nombre", ficha.raza, ficha.clase_y_nivel]
        if a.personaje.clases:
            partes.append(f"PG {ficha.pg_maximos} · CA {ficha.ca}")
        clase = a.personaje.clases[0].clase if a.personaje.clases else None
        ids = [p.id for p in a.pasos()]
        posicion = ids.index(self.paso)
        return {
            "pantalla": "asistente", "paso": self.paso,
            "lateral": [{"id": p.id, "titulo": p.titulo, "icono": nombre_icono("pasos", p.id), "completo": not a.faltan(p.id),
                         "actual": p.id == self.paso} for p in a.pasos()],
            "cabecera": {"texto": "  ·  ".join(p for p in partes if p),
                         "icono": nombre_icono("clases", clase) if clase else None},
            "contenido": contenido,
            "pie": [c.boton("← Anterior", "paso", {"paso": ids[max(0, posicion - 1)]}, desactivado=posicion == 0),
                    c.boton("Siguiente →", "paso", {"paso": ids[min(len(ids) - 1, posicion + 1)]},
                            desactivado=posicion == len(ids) - 1),
                    c.boton("Guardar (.json)", "exportar", {"formato": "json"}, "secundario"),
                    c.boton("Inicio", "ir", {"pantalla": "portada"}, "enlace",
                            confirmar="¿Volver al inicio? El personaje queda guardado en este navegador.")],
        }

    def accion_paso(self, paso: str) -> None:
        if self.paso == "equipo" or paso == "equipo":
            self.a.aplicar_equipo()
        self.paso = paso

    def _cabecera_paso(self, paso: str) -> list[dict]:
        datos = next(p for p in self.a.pasos() if p.id == paso)
        return [c.titulo(datos.titulo, 1, nombre_icono("pasos", paso)), c.texto(datos.ayuda, "gris")]

    def _faltan(self, paso: str | None = None) -> dict:
        return c.avisos(self.a.faltan(paso or self.paso))

    def _elecciones(self, paso: str) -> list[dict]:
        elecciones = self.a.elecciones(paso)
        return ([c.titulo("Elecciones", 3)] + [self._eleccion(e) for e in elecciones]) if elecciones else []

    def _eleccion(self, eleccion) -> dict:
        bloqueadas = self.a.bloqueadas(eleccion)
        if not eleccion.repetible and len(eleccion.opciones) > MAX_DESPLEGABLE:
            modo = "buscador"
        elif eleccion.repetible or len(eleccion.opciones) > MAX_CASILLAS:
            modo = "desplegables"
        else:
            modo = "casillas"
        return {"t": "eleccion", "clave": eleccion.clave, "nombre": eleccion.nombre, "etiqueta": eleccion.etiqueta,
                "elegir": eleccion.elegir, "completa": eleccion.faltan <= 0, "modo": modo, "repetible": eleccion.repetible,
                "opciones": [{"id": o.id, "nombre": o.nombre, "motivo": bloqueadas.get(o.id, "")} for o in eleccion.opciones],
                "seleccion": list(eleccion.seleccion), "accion": "elegir", "args": {"clave": eleccion.clave}}

    def accion_elegir(self, clave: str, valores: list[str]) -> None:
        self.a.elegir(clave, valores)

    def _lista(self, titulo_lista: str, opciones: list, seleccion: str | None, accion: str, args: dict | None,
               icono) -> dict:
        nombres_paquetes = {p.id: p.nombre for p in self.catalogo.paquetes}
        elegida = next((o for o in opciones if o.id == seleccion), None)
        detalle = None
        if elegida is not None:
            origen = nombres_paquetes.get(elegida.paquete, elegida.paquete)
            detalle = {"nombre": elegida.nombre, "icono": icono(elegida.id),
                       "origen": origen + (" · requiere permiso del DM" if elegida.permiso_dm else ""),
                       "perfil": perfil_en_puntos(elegida.perfil) if elegida.perfil else "",
                       "descripcion": elegida.descripcion}
        return c.lista_opciones(titulo_lista, [{"id": o.id, "nombre": o.nombre + ("  (DM)" if o.permiso_dm else "")}
                                               for o in opciones], seleccion, accion, args, detalle)

    # pasos

    def _paso_inicio(self) -> list[dict]:
        a = self.a
        reglas = a.personaje.reglas_opcionales
        maximo = a.nivel_maximo()
        minimo = 1 + sum(e.nivel for e in a.personaje.clases[1:])
        notas = []
        if minimo > 1:
            notas.append("total de todas las clases; el reparto se hace en el paso «Clase»")
        if maximo < 20:
            notas.append(f"los datos de clase llegan, por ahora, hasta nivel {maximo}")
        interruptores = [c.interruptor(texto, a.multiclase_activa() if regla == "multiclase" else reglas.get(regla, defecto),
                                       "regla", {"regla": regla}, ayuda)
                         for regla, texto, defecto, ayuda in interruptores_reglas(set(self.paquetes))]
        return [
            *self._cabecera_paso("inicio"),
            c.caja(c.menu([(str(n), str(n)) for n in range(minimo, maximo + 1)], str(a.nivel), "nivel",
                          etiqueta="Nivel inicial" + (f" ({'; '.join(notas)})" if notas else "")),
                   *interruptores,
                   c.segmentado([("media", "Media"), ("tiradas", "Tiradas")], a.personaje.metodo_pg, "metodo_pg",
                                etiqueta="Puntos de golpe al subir de nivel")),
            c.texto("Paquetes cargados: " + ", ".join(p.nombre for p in self.catalogo.paquetes), "gris"),
        ]

    def accion_nivel(self, valor: str) -> None:
        self.a.establecer_nivel(int(valor))

    def accion_metodo_pg(self, valor: str) -> None:
        self.a.personaje.metodo_pg = "media" if valor == "media" else "tiradas"

    def _paso_raza(self) -> list[dict]:
        a, p = self.a, self.a.personaje
        bloques = [*self._cabecera_paso("raza"),
                   self._lista("Raza", a.razas(), p.raza, "raza", None, lambda i: nombre_icono("razas", i))]
        subrazas = a.subrazas()
        if subrazas:
            bloques.append(self._lista("Subraza", subrazas, p.subraza, "subraza", None,
                                       lambda _i: nombre_icono("razas", p.raza)))
        return bloques + self._elecciones("raza") + [self._faltan()]

    def accion_raza(self, valor: str) -> None:
        self.a.elegir_raza(valor)

    def accion_subraza(self, valor: str) -> None:
        self.a.elegir_subraza(valor)

    def _paso_clase(self) -> list[dict]:
        a, p = self.a, self.a.personaje
        actual = p.clases[0].clase if p.clases else None
        bloques = [*self._cabecera_paso("clase"),
                   self._lista("Clase principal" if len(p.clases) > 1 else "Clase", a.clases(), actual, "clase", None,
                               lambda i: nombre_icono("clases", i))]
        subclases = a.subclases()
        if subclases:
            bloques.append(self._lista("Subclase", subclases, p.clases[0].subclase, "subclase", {"clase": None},
                                       lambda _i: nombre_icono("clases", actual)))
        if p.clases and (a.puede_anadir_clase() or len(p.clases) > 1):
            bloques.append(self._multiclase())
        if a.rasgos_opcionales():
            bloques.append(self._rasgos_opcionales())
        return bloques + self._elecciones("clase") + [self._faltan()]

    def accion_clase(self, valor: str) -> None:
        self.a.elegir_clase(valor)

    def accion_subclase(self, valor: str, clase: str | None = None) -> None:
        self.a.elegir_subclase(valor, clase) if clase else self.a.elegir_subclase(valor)

    def _rasgos_opcionales(self) -> dict:
        nombres = {o.id: o.nombre for o in self.a.clases()}
        opciones = []
        for rasgo, activo in self.a.rasgos_opcionales():
            descripcion = rasgo.get("descripcion", "")
            if len(descripcion) > LARGO_DESCRIPCION_OPCIONAL * 2:
                descripcion = descripcion[:LARGO_DESCRIPCION_OPCIONAL * 2].rsplit(" ", 1)[0] + "…"
            opciones.append(c.interruptor(f"{nombres.get(rasgo['clase'], rasgo['clase'])}: {rasgo['nombre']}", activo,
                                          "rasgo_opcional", {"id": rasgo["id"]}, descripcion))
        return c.caja(c.titulo("Rasgos de clase opcionales (Tasha)", 3),
                      c.texto("Cada uno se toma o se deja por separado, de acuerdo con el DM. Los que dicen «sustituye» "
                              "quitan el rasgo del Manual que nombran.", "gris"), *opciones)

    def accion_rasgo_opcional(self, id: str, valor: bool) -> None:  # noqa: A002
        self.a.usar_rasgo_opcional(id, valor)

    def _multiclase(self) -> dict:
        a, p = self.a, self.a.personaje
        nombres = {o.id: o.nombre for o in a.clases()}
        reparto = " · ".join(f"{nombres.get(e.clase, e.clase)} {e.nivel}" for e in p.clases)
        hijos = [c.titulo("Multiclase", 3),
                 c.texto(f"Nivel total {a.nivel}: {reparto}. Los niveles de las otras clases se le quitan a la principal; el "
                         "equipo inicial y las salvaciones son solo los de la principal.", "gris")]
        principal = p.clases[0]
        for entrada in p.clases[1:]:
            maximo = principal.nivel + entrada.nivel - 1
            requisito = a.requisito_multiclase(entrada.clase)
            hijos.append(c.fila(
                c.texto(nombres.get(entrada.clase, entrada.clase), "negrita"),
                c.menu([(str(n), str(n)) for n in range(1, max(1, maximo) + 1)], str(entrada.nivel), "niveles_clase",
                       {"clase": entrada.clase}, "Niveles"),
                c.texto(f"{'✓' if requisito[1] else '✗'} requisito: {requisito[0]}", "exito" if requisito[1] else "aviso")
                if requisito else None,
                c.boton("Quitar", "quitar_clase", {"clase": entrada.clase}, "secundario")))
            subclases = a.subclases(entrada.clase)
            if subclases:
                hijos.append(self._lista(f"Subclase de {nombres.get(entrada.clase, entrada.clase)}", subclases,
                                         entrada.subclase, "subclase", {"clase": entrada.clase},
                                         lambda _i, cl=entrada.clase: nombre_icono("clases", cl)))
        if not a.multiclase_activa():
            hijos.append(c.texto("La regla de multiclase está desactivada: quita las clases secundarias o actívala en "
                                 "«Edición y reglas».", "aviso"))
            return c.caja(*hijos)
        candidatas = a.clases_para_multiclase()
        if candidatas and a.puede_anadir_clase():
            if principal.nivel <= 1:
                hijos.append(c.texto("Sube el nivel total (paso «Edición y reglas») para tener niveles que repartir.", "gris"))
            else:
                hijos.append(c.menu([(o.id, o.nombre) for o in candidatas], None, "anadir_clase", etiqueta="Añadir otra clase",
                                    vacio="— elige —"))
        return c.caja(*hijos)

    def accion_niveles_clase(self, clase: str, valor: str) -> None:
        self.a.establecer_niveles_clase(clase, int(valor))

    def accion_quitar_clase(self, clase: str) -> None:
        self.a.quitar_clase(clase)

    def accion_anadir_clase(self, valor: str) -> None:
        if valor:
            self.a.anadir_clase(valor)

    def _paso_caracteristicas(self) -> list[dict]:
        a, p = self.a, self.a.personaje
        botones = []
        if p.metodo_caracteristicas == "tirada":
            botones.append(c.boton("Tirar 4d6 × 6", "tirar"))
        if p.clases and (p.metodo_caracteristicas != "tirada" or a.extra.get("tiradas_caracteristicas")) \
                and p.metodo_caracteristicas != "manual":
            botones.append(c.boton("Repartir según mi clase", "sugerir_caracteristicas", estilo="secundario"))
        bloques = [*self._cabecera_paso("caracteristicas"),
                   c.fila(c.menu(list(METODOS_CARACTERISTICAS.items()), p.metodo_caracteristicas, "metodo_caracteristicas",
                                 etiqueta="Método"), *botones)]
        if p.metodo_caracteristicas == "tirada" and a.extra.get("tiradas_caracteristicas"):
            bloques.append(c.texto("Tiradas: " + ", ".join(map(str, a.extra["tiradas_caracteristicas"]))))
        restantes = a.puntos_restantes()
        if restantes is not None:
            bloques.append(c.texto(f"Puntos restantes: {restantes} de 27", "negrita"))
        bonos = a.bonos_raciales()
        ficha = a.ficha()
        disponibles = a.valores_disponibles()
        filas = []
        for car, nombre in CARACTERISTICAS.items():
            valor = ficha.caracteristicas[car]
            asignada = car in p.caracteristicas_base
            bono = bonos.get(car, 0)
            filas.append([nombre, self._celda_base(car, disponibles), f"{bono:+d}" if bono else "—",
                          {"t": "texto", "texto": str(valor.puntuacion) if asignada else "—", "estilo": "negrita"},
                          f"{valor.modificador:+d}" if asignada else "—"])
        bloques.append(c.tabla(["Característica", "Base", "Raza", "Total", "Mod."], filas))
        if p.clases:
            prioridad = ", ".join(CARACTERISTICAS[x] for x in a.prioridad_de_clase()[:3])
            bloques.append(c.texto(f"Más importantes para tu clase: {prioridad}", "gris"))
        return bloques + [self._faltan()]

    def _celda_base(self, car: str, disponibles: list[int]) -> dict:
        p = self.a.personaje
        actual = p.caracteristicas_base.get(car)
        metodo = p.metodo_caracteristicas
        if metodo in ("estandar", "tirada"):
            valores = sorted({*disponibles, *([actual] if actual else [])}, reverse=True)
            return c.menu([(str(v), str(v)) for v in valores], str(actual) if actual else "", "asignar", {"car": car},
                          vacio="—")
        if metodo == "compra":
            valor = actual or 8
            sube = valor < 15 and (self.a.puntos_restantes() or 0) >= COSTE_COMPRA.get(valor + 1, 99) - COSTE_COMPRA[valor]
            return c.fila(c.boton("−", "asignar", {"car": car, "valor": valor - 1}, "secundario", desactivado=valor <= 8),
                          c.texto(str(valor), "negrita"),
                          c.boton("+", "asignar", {"car": car, "valor": valor + 1}, "secundario", desactivado=not sube))
        return c.entrada(str(actual or ""), "asignar", {"car": car}, ancho="corto")

    def accion_metodo_caracteristicas(self, valor: str) -> None:
        self.a.establecer_metodo(valor)

    def accion_tirar(self) -> None:
        self.a.tirar_caracteristicas()

    def accion_sugerir_caracteristicas(self) -> None:
        self.a.sugerir_caracteristicas()

    def accion_asignar(self, car: str, valor) -> None:
        texto = str(valor).strip()
        if not texto:
            self.a.asignar(car, None)
        elif texto.isdigit() and 1 <= int(texto) <= 30:
            self.a.asignar(car, int(texto))
        else:
            raise ValueError("Escribe un número entre 1 y 30")

    def _paso_trasfondo(self) -> list[dict]:
        return [*self._cabecera_paso("trasfondo"),
                self._lista("Trasfondo", self.a.trasfondos(), self.a.personaje.trasfondo, "trasfondo", None,
                            lambda i: nombre_icono("trasfondos", i)),
                *self._elecciones("trasfondo"), self._faltan()]

    def accion_trasfondo(self, valor: str) -> None:
        self.a.elegir_trasfondo(valor)

    def _paso_equipo(self) -> list[dict]:
        a = self.a
        bloques = self._cabecera_paso("equipo")
        oro = a.oro_inicial()
        if oro:
            bloques.append(c.interruptor(f"Usar oro en vez del equipo de clase ({oro.replace('x', ' × ')} po)",
                                         a._seleccion_equipo()["oro"], "usar_oro"))
        for bloque in a.bloques_equipo():
            origen = "De tu clase" if bloque.origen == "clase" else "De tu trasfondo"
            hijos = [c.texto(f"{origen} · {bloque.indice + 1}", "negrita")]
            textos = [" + ".join(f"{linea.cantidad} × {linea.nombre}" if linea.cantidad > 1 else linea.nombre
                                 for linea in alternativa) for alternativa in bloque.alternativas]
            if len(bloque.alternativas) > 1:
                hijos.append(c.radios([(str(i), t) for i, t in enumerate(textos)],
                                      None if bloque.elegida is None else str(bloque.elegida), "alternativa",
                                      {"origen": bloque.origen, "indice": bloque.indice}))
            else:
                hijos.append(c.texto(textos[0]))
            if bloque.elegida is not None:
                hijos += self._huecos(bloque)
            bloques.append(c.caja(*hijos))
        bloques += [self._objetos_magicos(), *self._infusiones_propias()]
        a.aplicar_equipo()
        ficha = a.ficha()
        if ficha.equipo or ficha.monedas:
            bloques += [c.titulo("Inventario resultante", 3), c.texto(", ".join(ficha.equipo))]
            dinero = ", ".join(f"{v} {m}" for m, v in ficha.monedas.items() if v)
            if dinero:
                bloques.append(c.texto(f"Dinero: {dinero}"))
        return bloques + [self._faltan()]

    def _huecos(self, bloque) -> list[dict]:
        menus = []
        for n, linea in enumerate(bloque.alternativas[bloque.elegida]):
            if linea.id is not None:
                continue
            for hueco in range(linea.cantidad):
                actual = self.a.objeto_elegido(bloque.origen, bloque.indice, bloque.elegida, n, hueco)
                menus.append(c.menu(linea.opciones, actual, "objeto_equipo",
                                    {"origen": bloque.origen, "indice": bloque.indice, "alternativa": bloque.elegida,
                                     "linea": n, "hueco": hueco}, vacio="— elige —"))
        return menus

    def accion_usar_oro(self, valor: bool) -> None:
        self.a.usar_oro_en_vez_de_equipo(valor)

    def accion_alternativa(self, origen: str, indice: int, valor: str) -> None:
        self.a.elegir_alternativa(origen, indice, int(valor))

    def accion_objeto_equipo(self, origen: str, indice: int, alternativa: int, linea: int, hueco: int, valor: str) -> None:
        if valor:
            self.a.elegir_objeto(origen, indice, alternativa, linea, hueco, valor)

    def _objetos_magicos(self) -> dict:
        posibles = self.a.objetos_que_pueden_ser_magicos()
        nombres = dict(posibles)
        hijos = [c.titulo("Objetos mágicos", 3),
                 c.texto("Armas, armaduras y escudos de +0 a +3. Si tu equipo ya tiene uno igual, ese pasa a ser el mágico; "
                         "si no, se añade.", "gris")]
        for n, magico in enumerate(self.a.objetos_magicos()):
            hijos.append(c.fila(c.texto(nombres.get(magico["id"], magico["id"]), "negrita"),
                                c.menu([(str(b), f"+{b}") for b in range(4)], str(magico["bonificador"]), "bonificador_magico",
                                       {"indice": n}),
                                c.boton("Quitar", "quitar_magico", {"indice": n}, "secundario")))
        hijos.append(c.fila(c.menu(posibles, self.nuevo_magico["id"], "nuevo_magico", {"campo": "id"}, vacio="— elige —"),
                            c.menu([(str(b), f"+{b}") for b in range(4)], str(self.nuevo_magico["bonificador"]),
                                   "nuevo_magico", {"campo": "bonificador"}),
                            c.boton("Añadir", "anadir_magico", desactivado=not self.nuevo_magico["id"])))
        return c.caja(*hijos)

    def accion_nuevo_magico(self, campo: str, valor: str) -> None:
        self.nuevo_magico[campo] = int(valor) if campo == "bonificador" else (valor or None)

    def accion_anadir_magico(self) -> None:
        if self.nuevo_magico["id"]:
            self.a.anadir_objeto_magico(self.nuevo_magico["id"], self.nuevo_magico["bonificador"])
            self.nuevo_magico["id"] = None

    def accion_bonificador_magico(self, indice: int, valor: str) -> None:
        bonificador = int(valor)
        if not 0 <= bonificador <= 3:
            raise ValueError("El bonificador mágico va de +0 a +3")
        self.a.objetos_magicos()[indice]["bonificador"] = bonificador

    def accion_quitar_magico(self, indice: int) -> None:
        self.a.quitar_objeto_magico(indice)

    def _infusiones_propias(self) -> list[dict]:
        infusiones = self.a.infusiones_propias()
        if not infusiones:
            return []
        hijos = [c.titulo("Infusiones que llevas tú", 3),
                 c.texto("Marca las que llevas tú y en qué objeto, y la ficha sumará su efecto. Las que pones en objetos de "
                         "tus compañeros no se marcan. Cada objeto admite una sola infusión.", "gris")]
        for infusion in infusiones:
            sin_objeto = infusion.necesita_objeto and not infusion.objetos
            fila = [c.interruptor(infusion.nombre, infusion.llevada, "llevar_infusion", {"id": infusion.id},
                                  "No llevas ningún objeto adecuado." if sin_objeto else "")]
            if infusion.llevada and infusion.necesita_objeto and infusion.objetos:
                fila.append(c.menu(infusion.objetos, infusion.objeto, "infusion_objeto", {"id": infusion.id},
                                   vacio="— elige —"))
            if infusion.llevada and infusion.elige_dano:
                fila.append(c.menu(DANOS_ELEGIBLES, infusion.dano, "infusion_dano", {"id": infusion.id}, vacio="— elige —"))
            hijos.append(c.fila(*fila))
        return [c.caja(*hijos)]

    def _infusion(self, id_: str):
        return next(i for i in self.a.infusiones_propias() if i.id == id_)

    def accion_llevar_infusion(self, id: str, valor: bool) -> None:  # noqa: A002
        infusion = self._infusion(id)
        objeto = (infusion.objeto or (infusion.objetos[0][0] if infusion.objetos else None)) if infusion.necesita_objeto else None
        self.a.llevar_infusion(id, valor, objeto, infusion.dano or ("fuego" if infusion.elige_dano else None))

    def accion_infusion_objeto(self, id: str, valor: str) -> None:  # noqa: A002
        self.a.llevar_infusion(id, True, valor or None, self._infusion(id).dano)

    def accion_infusion_dano(self, id: str, valor: str) -> None:  # noqa: A002
        self.a.llevar_infusion(id, True, self._infusion(id).objeto, valor or None)

    def _paso_conjuros(self) -> list[dict]:
        a = self.a
        bloques = self._cabecera_paso("conjuros")
        ficha = a.ficha()
        lanzadores = {lanzador.clase_id: lanzador for lanzador in ficha.lanzadores}
        otras_fuentes = a.conjuros_de_otras_fuentes()
        for plan in a.planes_conjuros():
            nombres = {i: n for opciones in plan.disponibles.values() for i, n in opciones}
            niveles = {i: nivel for nivel, opciones in plan.disponibles.items() for i, _ in opciones}
            lanzador = lanzadores.get(plan.clase_id)
            bloques.append(c.titulo(f"{plan.clase}: CD {lanzador.cd}, ataque {lanzador.ataque:+d}" if lanzador else plan.clase,
                                    2))
            if lanzador and lanzador.siempre_preparados:
                siempre = ", ".join(n for nivel in sorted(lanzador.siempre_preparados)
                                    for n in lanzador.siempre_preparados[nivel])
                bloques.append(c.texto(f"Siempre preparados (no cuentan): {siempre}", "gris"))
            libro = plan.modo == "libro"
            limite_otros = plan.limite_libro if libro else plan.limite_conjuros
            elegidos = [i for i in a.personaje.conjuros.get(plan.clase_id, []) if i in niveles]
            trucos = sum(1 for i in elegidos if niveles[i] == 0)
            otros = len(elegidos) - trucos
            contador = []
            if plan.limite_trucos is not None:
                contador.append(f"Trucos {trucos}/{plan.limite_trucos}")
            if limite_otros is not None:
                palabra = {"conocidos": "Conocidos", "preparados": "Preparados", "libro": "Libro"}[plan.modo]
                contador.append(f"{palabra} {otros}/{limite_otros}")
            bloques.append(c.texto("  ·  ".join(contador), "negrita"))
            for nivel, opciones in plan.disponibles.items():
                limite = plan.limite_trucos if nivel == 0 else limite_otros
                lleno = limite is not None and (trucos if nivel == 0 else otros) >= limite
                bloques.append(c.texto("Trucos" if nivel == 0 else f"Nivel {nivel}", "negrita"))
                bloques.append(c.casillas(
                    [{"id": i, "nombre": n + (" (ya lo tienes)" if i in otras_fuentes else ""), "marcada": i in elegidos,
                      "bloqueada": (lleno or i in otras_fuentes) and i not in elegidos} for i, n in opciones],
                    "alternar_conjuro", {"clase": plan.clase_id}))
            if libro:
                extra = [(i, nombres[i]) for i in a.libro_extra(plan.clase_id) if i in nombres and i not in elegidos]
                bloques += self._preparados_del_libro(plan, [(i, nombres[i]) for i in elegidos if niveles[i] > 0] + extra)
        return bloques + [self._faltan()]

    def _preparados_del_libro(self, plan, libro: list[tuple[str, str]]) -> list[dict]:
        preparados = [i for i in self.a.personaje.preparados.get(plan.clase_id, []) if i in dict(libro)]
        lleno = len(preparados) >= (plan.limite_conjuros or 0)
        return [c.texto(f"Preparados {len(preparados)}/{plan.limite_conjuros}", "negrita"),
                c.texto("Los que puedes lanzar hoy; se cambian tras un descanso largo." if libro else
                        "Primero elige conjuros para el libro.", "gris"),
                c.casillas([{"id": i, "nombre": n, "marcada": i in preparados, "bloqueada": lleno and i not in preparados}
                            for i, n in libro], "alternar_preparado", {"clase": plan.clase_id})]

    def accion_alternar_conjuro(self, clase: str, id: str, marcada: bool) -> None:  # noqa: A002
        actuales = list(self.a.personaje.conjuros.get(clase, []))
        actuales = [i for i in actuales if i != id] + ([id] if marcada else [])
        self.a.elegir_conjuros(clase, actuales)

    def accion_alternar_preparado(self, clase: str, id: str, marcada: bool) -> None:  # noqa: A002
        actuales = [i for i in self.a.personaje.preparados.get(clase, []) if i != id] + ([id] if marcada else [])
        self.a.elegir_preparados(clase, actuales)

    def _paso_detalles(self) -> list[dict]:
        p = self.a.personaje
        sugerencias = self.a.personalidad_sugerida()
        bloques = [*self._cabecera_paso("detalles"),
                   c.fila(c.entrada(p.nombre, "detalle", {"campo": "nombre"}, "Nombre"),
                          c.entrada(p.jugador, "detalle", {"campo": "jugador"}, "Jugador"),
                          c.menu([(x, x) for x in ALINEAMIENTOS], p.detalles.get("alineamiento") or "", "detalle",
                                 {"campo": "alineamiento"}, "Alineamiento", vacio="—")),
                   c.titulo("Personalidad", 3),
                   c.texto("Sirve también para los disparadores de inspiración. Puedes escribir lo tuyo o partir de las "
                           "sugerencias de tu trasfondo.", "gris")]
        for campo, nombre in PERSONALIDAD:
            bloques.append(c.entrada(p.detalles.get(campo, ""), "detalle", {"campo": campo}, nombre, multilinea=True,
                                     ancho="largo", sugerencias=sugerencias.get(campo, [])))
        bloques += [c.titulo("Aspecto e historia", 3),
                    c.fila(*[c.entrada(p.detalles.get(campo, ""), "detalle", {"campo": campo}, nombre, ancho="corto")
                             for campo, nombre in FISICO])]
        for campo, nombre in (("apariencia", "Apariencia"), ("historia", "Historia")):
            bloques.append(c.entrada(p.detalles.get(campo, ""), "detalle", {"campo": campo}, nombre, multilinea=True,
                                     ancho="largo"))
        return bloques + [self._faltan()]

    def accion_detalle(self, campo: str, valor: str) -> None:
        self.a.establecer_detalle(campo, valor.strip() if campo in ("nombre", "jugador") else valor)

    def _paso_resumen(self) -> list[dict]:
        a = self.a
        bloques = self._cabecera_paso("resumen")
        if self.novedades:
            bloques.append(c.avisos(self.novedades, "Novedades de la subida de nivel", completo=True))
        bloques.append(self._faltan())
        pendiente = a.entrenamiento_pendiente()
        if pendiente:
            texto = "; ".join(f"nivel {e['nivel']}: {e['dias']} días y {e['coste_po']} po" for e in pendiente)
            bloques.append(c.caja(c.texto(f"Entrenamiento pendiente (Guía del DM, p. 131): {texto}. Los rasgos nuevos llegan "
                                          "al terminarlo."), c.boton("Hecho", "entrenamiento_hecho")))
        bloques.append(self._subir_nivel())
        ficha = a.ficha()
        if ficha.avisos:
            bloques.append(c.avisos(ficha.avisos, "Revisa antes de jugar"))
        from ..sistemas.dnd5e_2014.salidas import hay_hoja_oficial
        bloques += [
            c.fila(c.boton("Hoja oficial (PDF editable)", "exportar", {"formato": "oficial"}, desactivado=not hay_hoja_oficial()),
                   c.boton("Ficha en PDF", "exportar", {"formato": "pdf"}),
                   c.boton("Nota y guía para Nivel20", "exportar", {"formato": "nota"}),
                   c.boton("Personaje (.json)", "exportar", {"formato": "json"}, "secundario")),
            c.texto("La hoja oficial es la editable en español, rellena (se puede seguir editando). La ficha en PDF es una "
                    "réplica en A4 que no depende de la plantilla. La nota es para Obsidian: propiedades de la plantilla de "
                    "PJ, ficha resumida y los pasos para crearlo en Nivel20. El .json sirve para volver a abrirlo aquí o en "
                    "el programa de escritorio.", "gris"),
            c.preformateado(resumen_ficha(ficha)),
        ]
        return bloques

    def accion_entrenamiento_hecho(self) -> None:
        self.a.entrenamiento_hecho()

    def _subir_nivel(self) -> dict | None:
        a, p = self.a, self.a.personaje
        if not p.clases:
            return None
        quedan = a.nivel_maximo() - a.nivel
        if quedan < 1:
            return c.caja(c.texto(f"Subir de nivel (ahora, nivel {a.nivel}): ya está en el nivel máximo con datos.", "gris"))
        nombres = {o.id: o.nombre for o in a.clases()}
        self.subida["niveles"] = min(self.subida["niveles"], quedan)
        if self.subida["clase"] not in [e.clase for e in p.clases]:
            self.subida["clase"] = None
        hay_preguntas = any(x.get("momento") == "subida" for x in self.catalogo.listar("preguntas"))
        ayuda = ("Con preguntas: un hito de la aventura (Guía del DM) y una pregunta por cada decisión de esos niveles, con las "
                 "opciones reales de tu personaje (subclases, mejoras con sus puntuaciones, dotes, opciones de clase, conjuros). "
                 "Elijo yo: sube el nivel y te lleva a lo que hay que decidir.")
        if not hay_preguntas:
            ayuda += " (Para las preguntas, carga el paquete «Cuestionario de situaciones».)"
        return c.caja(
            c.fila(c.texto(f"Subir de nivel (ahora, nivel {a.nivel}):", "negrita"),
                   c.menu([(str(n), f"+{n}") for n in range(1, quedan + 1)], str(self.subida["niveles"]), "config_subida",
                          {"campo": "niveles"}),
                   c.menu([(e.clase, nombres.get(e.clase, e.clase)) for e in p.clases], self.subida["clase"] or p.clases[0].clase,
                          "config_subida", {"campo": "clase"}) if len(p.clases) > 1 else None,
                   c.boton("Con preguntas…", "subir", {"con_preguntas": True}, desactivado=not hay_preguntas),
                   c.boton("Elijo yo", "subir", {"con_preguntas": False}, "secundario")),
            c.texto(ayuda, "gris"))

    def accion_config_subida(self, campo: str, valor: str) -> None:
        self.subida[campo] = int(valor) if campo == "niveles" else valor

    def accion_subir(self, con_preguntas: bool) -> None:
        a = self.a
        niveles, clase = self.subida["niveles"], self.subida["clase"]
        if con_preguntas:
            self.q = a.sistema.crear_cuestionario(a.personaje, self.catalogo)
            self.a = self.q.asistente
            self.pantalla = "subida"
            return
        a.subir_nivel(niveles, clase)
        pendientes = [x.id for x in a.pasos() if x.id not in ("resumen", "detalles") and a.faltan(x.id)]
        self.novedades = []
        self.paso = pendientes[0] if pendientes else "resumen"

    def _vista_subida(self) -> list[dict]:
        a = self.a
        niveles, clase = self.subida["niveles"], self.subida["clase"]
        decisiones = self.q.decisiones_de_subida(niveles, clase)
        preguntas = self.q.preguntas_de_subida(niveles, clase)
        que = ", ".join(NOMBRES_DECISION[d] for d in ("mejora", "subclase", "opciones", "conjuros") if d in decisiones)
        if preguntas:
            explicacion = (f"Estos niveles traen decisiones: {que}. Cuéntanos qué ha vivido tu personaje desde el último hito "
                           f"de la aventura y lo decidimos con eso. {AYUDA_SUBIDA}")
        elif decisiones:
            explicacion = (f"Estos niveles solo traen elecciones menores ({que}), que se deciden con su forma de ser: no hace "
                           "falta preguntar nada.")
        else:
            explicacion = "Estos niveles no traen decisiones: solo rasgos y puntos de golpe, que se suman solos."
        return [c.titulo(f"Subir de nivel: de {a.nivel} a {a.nivel + niveles}", 1), c.texto(explicacion, "grande"),
                *self._preguntas_subida(preguntas),
                c.fila(c.boton("Subir de nivel →", "aplicar_subida"),
                       c.boton("Cancelar", "cancelar_subida", estilo="secundario"))]

    def accion_aplicar_subida(self) -> None:
        a = self.a
        niveles, clase = self.subida["niveles"], self.subida["clase"]
        antes = a.instantanea()
        self.q.conservar_respuestas_subida({p.id for p in self.q.preguntas_de_subida(niveles, clase)})
        self.q.subir_nivel(niveles, clase)
        self.novedades = a.novedades(antes)
        self.q = None
        self.pantalla, self.paso = "asistente", "resumen"

    def accion_cancelar_subida(self) -> None:
        self.q.respuestas_subida.clear()
        self.q = None
        self.pantalla = "asistente"

    # ── archivos ───────────────────────────────────────────────────────────

    def accion_exportar(self, formato: str) -> dict:
        if formato not in FORMATOS:
            raise ValueError(f"Formato desconocido «{formato}»")
        a = self.a
        a.aplicar_equipo()
        extension, tipo = FORMATOS[formato]
        base = re.sub(r"[^\w\- ]", "", a.personaje.nombre or "personaje", flags=re.UNICODE).strip() or "personaje"
        if formato == "json":
            datos = json.dumps(a.personaje.a_dict(), ensure_ascii=False, indent=2).encode("utf-8")
        elif formato == "nota":
            from ..sistemas.dnd5e_2014.salidas.nota import nota_obsidian
            datos = nota_obsidian(a).encode("utf-8")
        else:
            with tempfile.TemporaryDirectory() as temporal:
                ruta = Path(temporal) / f"ficha{extension}"
                if formato == "pdf":
                    from ..sistemas.dnd5e_2014.salidas.ficha_pdf import generar_ficha_pdf
                    generar_ficha_pdf(a, str(ruta))
                else:
                    from ..sistemas.dnd5e_2014.salidas.pdf_oficial import rellenar_hoja_oficial
                    rellenar_hoja_oficial(a, str(ruta))
                datos = ruta.read_bytes()
        sufijo = {"oficial": " (hoja oficial)", "nota": " (nota)"}.get(formato, "")
        return {"archivo": {"nombre": f"{base}{sufijo}{extension}", "tipo": tipo,
                            "datos": base64.b64encode(datos).decode("ascii")}}
