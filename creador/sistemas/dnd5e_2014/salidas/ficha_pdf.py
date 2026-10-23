"""Réplica de la hoja de personaje oficial de 5e (2014) en PDF, con las etiquetas de la versión en español.

Reproduce la disposición de las tres páginas (personaje, detalles y conjuros) sin logotipos ni ilustraciones,
en A4. Las etiquetas son las de la hoja en blanco oficial en español de Wizards of the Coast. Si un texto no
cabe en su recuadro se reduce la letra; los rasgos que no caben en la primera página se resumen allí y se
dan completos en «Rasgos y atributos adicionales».
"""
from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color, black, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from ..constantes import CARACTERISTICAS, HABILIDADES, RECARGAS

if TYPE_CHECKING:
    from ..asistente import Asistente5e
    from ..ficha import Ficha

ANCHO, ALTO = A4
MARGEN = 24
ARRIBA = 740  # comienzo del cuerpo, bajo la cabecera
ABAJO = 34
GRIS = Color(0.45, 0.45, 0.45)
GRIS_CLARO = Color(0.88, 0.88, 0.88)
LINEA = Color(0.2, 0.2, 0.2)

ETIQUETAS_CARACTERISTICA = {"fue": "FUERZA", "des": "DESTREZA", "con": "CONSTITUCIÓN", "int": "INTELIGENCIA",
                            "sab": "SABIDURÍA", "car": "CARISMA"}
ABREVIATURAS = {"fue": "Fue", "des": "Des", "con": "Con", "int": "Int", "sab": "Sab", "car": "Car"}
# Nombres abreviados de la hoja oficial en español.
NOMBRES_HOJA = {"conocimiento_arcano": "C. Arcano", "trato_con_animales": "T. con Animales"}
MONEDAS = ("pc", "pp", "pe", "po", "ppt")
# Página de conjuros: niveles por columna y renglones de cada nivel (como la hoja oficial).
COLUMNAS_CONJUROS = (((0, 8), (1, 12), (2, 12)), ((3, 12), (4, 12), (5, 9)), ((6, 9), (7, 9), (8, 7), (9, 7)))
PIE = "Hoja generada con el Creador de personajes · Dungeons & Dragons 5.ª edición (2014)"
SUSTITUCIONES = {"−": "-", "●": "*", "○": "o", "→": "->", "≥": ">=", "≤": "<=", "✓": "v"}


def _t(texto) -> str:
    """Texto apto para las fuentes estándar del PDF (codificación WinAnsi)."""
    texto = str(texto)
    for original, cambio in SUSTITUCIONES.items():
        texto = texto.replace(original, cambio)
    try:
        texto.encode("cp1252")
        return texto
    except UnicodeEncodeError:
        return "".join(c if _codificable(c) else unicodedata.normalize("NFKD", c).encode("cp1252", "ignore").decode("cp1252")
                       for c in texto)


def _codificable(caracter: str) -> bool:
    try:
        caracter.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def _signo(valor: int) -> str:
    return f"{valor:+d}"


class Hoja:
    """Primitivas de dibujo de la hoja sobre un lienzo de reportlab."""

    def __init__(self, ruta: str):
        self.c = Canvas(str(ruta), pagesize=A4)
        self.c.setTitle("Hoja de personaje")

    # ── primitivas ────────────────────────────────────────────────────────

    def marco(self, x: float, y: float, w: float, h: float, radio: float = 6, grosor: float = 1, relleno=None) -> None:
        c = self.c
        c.setLineWidth(grosor)
        c.setStrokeColor(LINEA)
        if relleno is not None:
            c.setFillColor(relleno)
        c.roundRect(x, y, w, h, radio, stroke=1, fill=1 if relleno is not None else 0)
        c.setFillColor(black)

    def etiqueta(self, texto: str, x: float, y: float, w: float, tam: float = 6.2, color=black) -> None:
        self.c.setFont("Helvetica-Bold", tam)
        self.c.setFillColor(color)
        self.c.drawCentredString(x + w / 2, y, _t(texto))
        self.c.setFillColor(black)

    def texto(self, texto, x: float, y: float, tam: float = 9, negrita: bool = False, centrado_en: float | None = None,
              color=black, ancho_max: float | None = None) -> None:
        fuente = "Helvetica-Bold" if negrita else "Helvetica"
        texto = _t(texto)
        if ancho_max:
            while tam > 5 and self.c.stringWidth(texto, fuente, tam) > ancho_max:
                tam -= 0.5
        self.c.setFont(fuente, tam)
        self.c.setFillColor(color)
        if centrado_en is not None:
            self.c.drawCentredString(centrado_en, y, texto)
        else:
            self.c.drawString(x, y, texto)
        self.c.setFillColor(black)

    def renglones(self, x: float, y: float, w: float, h: float, paso: float = 12) -> None:
        self.c.setStrokeColor(GRIS_CLARO)
        self.c.setLineWidth(0.5)
        linea = y + h - paso
        while linea > y + 4:
            self.c.line(x + 6, linea, x + w - 6, linea)
            linea -= paso
        self.c.setStrokeColor(LINEA)

    def parrafos(self, bloques: list[str], x: float, y: float, w: float, h: float, tam_max: float = 8,
                 tam_min: float = 5.5) -> bool:
        """Escribe párrafos (con <b>/<i>) dentro del recuadro, reduciendo la letra si hace falta."""
        tam = tam_max
        while True:
            estilo = ParagraphStyle("p", fontName="Helvetica", fontSize=tam, leading=tam * 1.22, alignment=TA_LEFT,
                                    spaceAfter=tam * 0.3)
            parrafos = [Paragraph(_t(b), estilo) for b in bloques if b]
            alturas = [p.wrap(w, h)[1] + estilo.spaceAfter for p in parrafos]
            if sum(alturas) <= h or tam <= tam_min:
                break
            tam -= 0.5
        cabe = sum(alturas) <= h
        cursor = y + h
        for parrafo, alto in zip(parrafos, alturas, strict=True):
            if cursor - alto < y - 1:
                break
            parrafo.drawOn(self.c, x, cursor - alto + estilo.spaceAfter)
            cursor -= alto
        return cabe

    def circulo(self, x: float, y: float, r: float = 3.2, lleno: bool = False) -> None:
        self.c.setLineWidth(0.8)
        self.c.setFillColor(black if lleno else white)
        self.c.circle(x, y, r, stroke=1, fill=1)
        self.c.setFillColor(black)

    def caja_titulada(self, x: float, y: float, w: float, h: float, titulo: str) -> None:
        self.marco(x, y, w, h)
        self.etiqueta(titulo, x, y + 5, w)

    def cabecera(self, nombre: str, etiqueta_nombre: str, campos: list[tuple[str, str]]) -> None:
        """Banda con el nombre a la izquierda y 6 campos (2 filas de 3) a la derecha."""
        self.marco(MARGEN, 762, 200, 46, radio=10)
        self.texto(nombre, MARGEN + 10, 784, tam=15, negrita=True, ancho_max=180)
        self.c.setStrokeColor(GRIS)
        self.c.line(MARGEN + 10, 778, MARGEN + 190, 778)
        self.texto(etiqueta_nombre, MARGEN + 10, 769, tam=6.2, negrita=True)
        x0, ancho = 232, ANCHO - MARGEN - 232
        self.marco(x0, 752, ancho, 64, radio=8)
        columna = ancho / 3
        for i, (etiqueta, valor) in enumerate(campos):
            fila, col = divmod(i, 3)
            base = 795 - fila * 28
            x = x0 + 8 + col * columna
            self.texto(valor, x, base + 4, tam=9, ancho_max=columna - 14)
            self.c.setStrokeColor(GRIS)
            self.c.setLineWidth(0.5)
            self.c.line(x, base, x + columna - 14, base)
            self.texto(etiqueta, x, base - 8, tam=6, negrita=True)

    def pie(self) -> None:
        self.texto(PIE, 0, 16, tam=6.5, centrado_en=ANCHO / 2, color=GRIS)

    def pagina(self) -> None:
        self.pie()
        self.c.showPage()


# ── página 1 ──────────────────────────────────────────────────────────────

def _pagina_personaje(h: Hoja, ficha: Ficha, a: Asistente5e) -> list[str]:
    """Dibuja la página 1 y devuelve los rasgos que solo caben resumidos (para la página 2)."""
    p = a.personaje
    h.cabecera(ficha.nombre, "NOMBRE DEL PERSONAJE", [
        ("CLASE Y NIVEL", ficha.clase_y_nivel), ("TRASFONDO", ficha.trasfondo), ("NOMBRE DEL JUGADOR", ficha.jugador),
        ("RAZA", ficha.raza), ("ALINEAMIENTO", p.detalles.get("alineamiento", "")),
        ("PUNTOS DE EXPERIENCIA", str(ficha.experiencia))])

    # Columna 1: características, inspiración, competencia, salvaciones, habilidades, pasiva, competencias.
    xa, wa, alto_car, hueco = MARGEN, 60, 74, 6
    for i, (car, valor) in enumerate(ficha.caracteristicas.items()):
        y = ARRIBA - (i + 1) * alto_car - i * hueco
        h.marco(xa, y, wa, alto_car, radio=8)
        h.etiqueta(ETIQUETAS_CARACTERISTICA[car], xa, y + alto_car - 11, wa, tam=6.4)
        h.texto(_signo(valor.modificador), 0, y + 30, tam=20, negrita=True, centrado_en=xa + wa / 2)
        h.c.setFillColor(white)
        h.c.setLineWidth(0.9)
        h.c.ellipse(xa + 14, y + 5, xa + wa - 14, y + 23, stroke=1, fill=1)
        h.texto(str(valor.puntuacion), 0, y + 10.5, tam=9, negrita=True, centrado_en=xa + wa / 2)

    xb, wb = MARGEN + wa + 6, 214 - (MARGEN + wa + 6)
    h.marco(xb, ARRIBA - 20, wb, 20, radio=5)
    h.marco(xb + 3, ARRIBA - 17, 20, 14, radio=3)
    h.etiqueta("INSPIRACIÓN", xb + 24, ARRIBA - 13, wb - 24)
    h.marco(xb, ARRIBA - 46, wb, 20, radio=5)
    h.marco(xb + 3, ARRIBA - 43, 20, 14, radio=7)
    h.texto(_signo(ficha.bonificador_competencia), 0, ARRIBA - 39.5, tam=8.5, negrita=True, centrado_en=xb + 13)
    h.etiqueta("BONIFICADOR POR COMPETENCIA", xb + 24, ARRIBA - 39, wb - 24, tam=5.6)

    def linea_tirada(y: float, valor: int, nombre: str, abreviatura: str, competente: bool, pericia: bool = False) -> None:
        h.circulo(xb + 8, y + 2.5, lleno=competente)
        if pericia:
            h.circulo(xb + 8, y + 2.5, r=1.4, lleno=False)
        h.texto(_signo(valor), xb + 15, y, tam=7.5, negrita=True)
        h.texto(nombre, xb + 31, y, tam=7.5, ancho_max=wb - 58 if abreviatura else wb - 36)
        if abreviatura:
            ancho_nombre = h.c.stringWidth(_t(nombre), "Helvetica", 7.5)
            h.texto(f"({abreviatura})", xb + 33 + ancho_nombre, y, tam=6.5, color=GRIS)

    alto_salv = 92
    y_salv = ARRIBA - 52 - alto_salv
    h.marco(xb, y_salv, wb, alto_salv, radio=6)
    for i, (car, tirada) in enumerate(ficha.salvaciones.items()):
        linea_tirada(y_salv + alto_salv - 14 - i * 12, tirada.valor, CARACTERISTICAS[car], "", tirada.competente)
    h.etiqueta("TIRADAS DE SALVACIÓN", xb, y_salv + 4, wb)

    y_fin_car = ARRIBA - 6 * alto_car - 5 * hueco
    y_hab = y_fin_car
    alto_hab = y_salv - 6 - y_hab
    h.marco(xb, y_hab, wb, alto_hab, radio=6)
    paso = (alto_hab - 18) / len(HABILIDADES)
    for i, (id_, tirada) in enumerate(ficha.habilidades.items()):
        nombre = NOMBRES_HOJA.get(id_, HABILIDADES[id_][0])
        linea_tirada(y_hab + alto_hab - 12 - i * paso, tirada.valor, nombre, ABREVIATURAS[HABILIDADES[id_][1]],
                     tirada.competente, tirada.pericia)
    h.etiqueta("HABILIDADES", xb, y_hab + 4, wb)

    y_pas = y_fin_car - 28
    h.marco(MARGEN, y_pas, 214 - MARGEN, 22, radio=8)
    h.marco(MARGEN + 2, y_pas + 2, 30, 18, radio=7)
    h.texto(str(ficha.percepcion_pasiva), 0, y_pas + 7.5, tam=10, negrita=True, centrado_en=MARGEN + 17)
    h.etiqueta("SABIDURÍA (PERCEPCIÓN) PASIVA", MARGEN + 34, y_pas + 8.5, 214 - MARGEN - 36, tam=6)

    y_otras = ABAJO
    alto_otras = y_pas - 6 - y_otras
    h.caja_titulada(MARGEN, y_otras, 214 - MARGEN, alto_otras, "OTRAS COMPETENCIAS E IDIOMAS")
    competencias = [f"<b>{t}:</b> {escape(', '.join(ficha.competencias[k]))}." for t, k in (
        ("Armaduras", "armaduras"), ("Armas", "armas"), ("Herramientas", "herramientas"), ("Idiomas", "idiomas"))
        if ficha.competencias.get(k)]
    h.parrafos(competencias, MARGEN + 7, y_otras + 15, 214 - MARGEN - 14, alto_otras - 22)

    # Columna 2: CA, iniciativa, velocidad, PG, dados de golpe, salvaciones contra muerte, ataques y equipo.
    x2, w2 = 222, 178
    ancho3 = (w2 - 12) / 3
    for i, (etiqueta, valor) in enumerate((("CLASE DE ARMADURA", str(ficha.ca)), ("INICIATIVA", _signo(ficha.iniciativa)),
                                           ("VELOCIDAD", f"{ficha.velocidades.get('caminar', 0)} pies"))):
        x = x2 + i * (ancho3 + 6)
        h.marco(x, ARRIBA - 56, ancho3, 56, radio=8)
        h.texto(valor, 0, ARRIBA - 40, tam=15 if i < 2 else 11, negrita=True, centrado_en=x + ancho3 / 2)
        palabras = etiqueta.split(" DE ") if i == 0 else [etiqueta]
        for j, trozo in enumerate(palabras):
            h.etiqueta(trozo + (" DE" if i == 0 and j == 0 else ""), x, ARRIBA - 12 - j * 7, ancho3, tam=5.8)

    y_pg = ARRIBA - 62 - 72
    h.marco(x2, y_pg, w2, 72, radio=8)
    h.texto("Puntos de golpe máximos", x2 + 8, y_pg + 58, tam=6.5, color=GRIS)
    h.texto(str(ficha.pg_maximos), x2 + 92, y_pg + 58, tam=9, negrita=True)
    h.c.setStrokeColor(GRIS_CLARO)
    h.c.line(x2 + 90, y_pg + 55, x2 + w2 - 8, y_pg + 55)
    h.etiqueta("PUNTOS DE GOLPE ACTUALES", x2, y_pg + 5, w2)
    y_tmp = y_pg - 6 - 46
    h.caja_titulada(x2, y_tmp, w2, 46, "PUNTOS DE GOLPE TEMPORALES")

    y_dg = y_tmp - 6 - 52
    w_dg = (w2 - 6) / 2
    h.marco(x2, y_dg, w_dg, 52, radio=6)
    dados = " + ".join(f"{n}{dado}" for dado, n in ficha.dados_golpe.items())
    h.texto("Total", x2 + 6, y_dg + 40, tam=6.5, color=GRIS)
    h.texto(dados, x2 + 24, y_dg + 40, tam=8, negrita=True, ancho_max=w_dg - 28)
    h.etiqueta("DADOS DE GOLPE", x2, y_dg + 5, w_dg, tam=5.8)
    x_ms = x2 + w_dg + 6
    h.marco(x_ms, y_dg, w_dg, 52, radio=6)
    for j, etiqueta in enumerate(("ÉXITOS", "FALLOS")):
        y = y_dg + 38 - j * 12
        h.texto(etiqueta, x_ms + 5, y, tam=5.6, negrita=True)
        for k in range(3):
            h.circulo(x_ms + 40 + k * 10, y + 2.2, r=3)
    h.etiqueta("SALVACIONES", x_ms, y_dg + 11, w_dg, tam=5.6)
    h.etiqueta("CONTRA MUERTE", x_ms, y_dg + 4, w_dg, tam=5.6)

    y_at = y_dg - 6 - 200
    h.caja_titulada(x2, y_at, w2, 200, "ATAQUES Y LANZAMIENTO DE CONJUROS")
    columnas = ((x2 + 6, 60, "NOMBRE"), (x2 + 70, 34, "BONIFICADOR"), (x2 + 110, 62, "DAÑO/TIPO"))
    for x, ancho, etiqueta in columnas:
        h.texto(etiqueta, x, y_at + 188, tam=5.2, color=GRIS, ancho_max=ancho)
    fila = y_at + 175
    for ataque in ficha.ataques[:6]:
        for (x, w, _), valor in zip(columnas, (ataque.nombre, _signo(ataque.bonificador),
                                               f"{ataque.dano} {ataque.tipo_dano}".strip()), strict=True):
            h.c.setFillColor(GRIS_CLARO)
            h.c.roundRect(x - 2, fila - 3, w, 12, 2, stroke=0, fill=1)
            h.texto(valor, x, fila, tam=7, ancho_max=w - 4)
        fila -= 15
    notas = [f"<b>{escape(at.nombre)}:</b> {escape(at.notas)}." for at in ficha.ataques[:6] if at.notas]
    for lanzador in ficha.lanzadores:
        notas.append(f"<b>Conjuros ({escape(CARACTERISTICAS[lanzador.caracteristica])}):</b> CD {lanzador.cd}, "
                     f"ataque {_signo(lanzador.ataque)}. Ver la hoja de conjuros.")
    if ficha.conjuros_innatos:
        notas.append(f"<b>Conjuros innatos:</b> {escape(', '.join(ficha.conjuros_innatos))}.")
    h.parrafos(notas, x2 + 6, y_at + 15, w2 - 12, fila - y_at - 12, tam_max=7)

    y_eq = ABAJO
    alto_eq = y_at - 6 - y_eq
    h.caja_titulada(x2, y_eq, w2, alto_eq, "EQUIPO")
    for i, moneda in enumerate(MONEDAS):
        y = y_eq + alto_eq - 30 - i * 30
        h.marco(x2 + 5, y, 34, 24, radio=6)
        h.texto(moneda.upper(), x2 + 9, y + 16, tam=5.6, negrita=True, color=GRIS)
        valor = p.monedas.get(moneda)
        if valor:
            h.texto(str(valor), 0, y + 5, tam=8.5, negrita=True, centrado_en=x2 + 22)
    equipo = [escape(", ".join(ficha.equipo)) + "."] if ficha.equipo else []
    h.parrafos(equipo, x2 + 45, y_eq + 15, w2 - 51, alto_eq - 22, tam_max=7.5)

    # Columna 3: personalidad y rasgos.
    x3, w3 = 408, ANCHO - MARGEN - 408
    cursor = ARRIBA
    for campo, etiqueta, alto in (("rasgos_personalidad", "RASGOS DE PERSONALIDAD", 72), ("ideales", "IDEALES", 52),
                                  ("vinculos", "VÍNCULOS", 52), ("defectos", "DEFECTOS", 52)):
        h.caja_titulada(x3, cursor - alto, w3, alto, etiqueta)
        h.parrafos([escape(p.detalles.get(campo, ""))], x3 + 6, cursor - alto + 14, w3 - 12, alto - 18, tam_max=7)
        cursor -= alto + 6
    alto_rasgos = cursor - ABAJO
    h.caja_titulada(x3, ABAJO, w3, alto_rasgos, "RASGOS Y ATRIBUTOS")
    completos = _bloques_rasgos(ficha, completos=True)
    if h.parrafos(completos, x3 + 6, ABAJO + 15, w3 - 12, alto_rasgos - 22, tam_max=7, tam_min=6):
        return []
    # No caben: aquí solo nombres y usos; el texto completo, en la página 2.
    h.c.setFillColor(white)
    h.c.rect(x3 + 2, ABAJO + 13, w3 - 4, alto_rasgos - 17, stroke=0, fill=1)
    h.c.setFillColor(black)
    breves = _bloques_rasgos(ficha, completos=False) + ["<i>Descripción completa en «Rasgos y atributos adicionales».</i>"]
    h.parrafos(breves, x3 + 6, ABAJO + 15, w3 - 12, alto_rasgos - 22, tam_max=7)
    return completos


def _bloques_rasgos(ficha: Ficha, completos: bool) -> list[str]:
    bloques = []
    defensas = [f"{n} {pies} pies" for n, pies in ficha.sentidos.items()]
    defensas += [f"Resistencia a {', '.join(ficha.resistencias)}"] if ficha.resistencias else []
    defensas += [f"Inmunidad a {', '.join(ficha.inmunidades)}"] if ficha.inmunidades else []
    if defensas:
        bloques.append(escape(". ".join(defensas)) + ".")
    for rasgo in ficha.rasgos:
        usos = f" ({rasgo.usos} por {RECARGAS.get(rasgo.recarga, 'día')})" if rasgo.usos is not None else ""
        texto = f"<b>{escape(rasgo.nombre)}</b>{escape(usos)}"
        if completos and rasgo.resumen:
            texto += f". {escape(rasgo.resumen.rstrip('.'))}."
        bloques.append(texto)
    return bloques


# ── página 2 ──────────────────────────────────────────────────────────────

def _pagina_detalles(h: Hoja, ficha: Ficha, a: Asistente5e, rasgos_adicionales: list[str]) -> None:
    d = a.personaje.detalles
    h.cabecera(ficha.nombre, "NOMBRE DEL PERSONAJE", [(e.upper(), d.get(c, "")) for c, e in (
        ("edad", "Edad"), ("altura", "Altura"), ("peso", "Peso"), ("ojos", "Ojos"), ("piel", "Piel"), ("pelo", "Pelo"))])
    xi, wi, xd = MARGEN, 190, MARGEN + 198
    wd = ANCHO - MARGEN - xd
    h.caja_titulada(xi, 470, wi, ARRIBA - 470, "ASPECTO DEL PERSONAJE")
    h.parrafos([escape(d.get("apariencia", ""))], xi + 7, 485, wi - 14, ARRIBA - 470 - 22)
    h.caja_titulada(xi, ABAJO, wi, 462 - ABAJO, "HISTORIA DEL PERSONAJE")
    h.parrafos([escape(t) for t in d.get("historia", "").split("\n")], xi + 7, ABAJO + 15, wi - 14, 462 - ABAJO - 22)
    h.caja_titulada(xd, 560, wd, ARRIBA - 560, "ALIADOS Y ORGANIZACIONES")
    h.renglones(xd, 574, wd, ARRIBA - 574)
    h.caja_titulada(xd, 230, wd, 552 - 230, "RASGOS Y ATRIBUTOS ADICIONALES")
    if rasgos_adicionales:
        h.parrafos(rasgos_adicionales, xd + 7, 245, wd - 14, 552 - 230 - 22, tam_max=7.5, tam_min=5)
    else:
        h.renglones(xd, 244, wd, 552 - 244)
    h.caja_titulada(xd, ABAJO, wd, 222 - ABAJO, "TESORO")
    h.renglones(xd, ABAJO + 14, wd, 222 - ABAJO - 14)


# ── página 3 ──────────────────────────────────────────────────────────────

def _conjuros_por_nivel(ficha: Ficha) -> dict[int, list[tuple[str, bool]]]:
    """nivel -> [(nombre, preparado)]. Con libro, los no preparados quedan sin marcar."""
    por_nivel: dict[int, list[tuple[str, bool]]] = {}
    for lanzador in ficha.lanzadores:
        for nivel, nombres in lanzador.conjuros.items():
            por_nivel.setdefault(nivel, []).extend((n, nivel > 0) for n in nombres)
        for nivel, nombres in lanzador.siempre_preparados.items():
            por_nivel.setdefault(nivel, []).extend((f"{n} (siempre)", True) for n in nombres)
        for nivel, nombres in lanzador.libro.items():
            preparados = set(lanzador.conjuros.get(nivel, []))
            por_nivel.setdefault(nivel, []).extend((n, False) for n in nombres if n not in preparados)
    return por_nivel


def _pagina_conjuros(h: Hoja, ficha: Ficha) -> None:
    lanzador = ficha.lanzadores[0]
    clases = " / ".join(lz.clase for lz in ficha.lanzadores)
    h.marco(MARGEN, 762, 200, 46, radio=10)
    h.texto(clases, MARGEN + 10, 784, tam=14, negrita=True, ancho_max=180)
    h.c.setStrokeColor(GRIS)
    h.c.line(MARGEN + 10, 778, MARGEN + 190, 778)
    h.texto("CLASE LANZADORA DE CONJUROS", MARGEN + 10, 769, tam=6.2, negrita=True)
    x0, ancho = 232, ANCHO - MARGEN - 232
    h.marco(x0, 752, ancho, 64, radio=8, relleno=GRIS_CLARO)
    tercio = ancho / 3
    for i, (etiquetas, valor) in enumerate(((("APTITUD", "MÁGICA"), CARACTERISTICAS[lanzador.caracteristica]),
                                            (("CD TIRADA DE SALVACIÓN", "DE CONJUROS"), str(lanzador.cd)),
                                            (("BONIFICADOR DE", "ATAQUE DE CONJUROS"), _signo(lanzador.ataque)))):
        x = x0 + i * tercio
        h.marco(x + 14, 780, tercio - 28, 30, radio=8, relleno=white)
        h.texto(valor, 0, 790, tam=12 if i else 9.5, negrita=True, centrado_en=x + tercio / 2, ancho_max=tercio - 34)
        for j, linea in enumerate(etiquetas):
            h.etiqueta(linea, x, 770 - j * 7, tercio, tam=5.6)

    por_nivel = _conjuros_por_nivel(ficha)
    espacios = dict(ficha.espacios_conjuro)
    pacto = ficha.magia_pacto
    ancho_col = (ANCHO - 2 * MARGEN - 16) / 3
    paso = 17.5
    for col, niveles in enumerate(COLUMNAS_CONJUROS):
        x = MARGEN + col * (ancho_col + 8)
        cursor = ARRIBA
        for nivel, renglones in niveles:
            h.marco(x, cursor - 22, ancho_col, 22, radio=6, relleno=GRIS_CLARO)
            h.marco(x + 3, cursor - 19, 16, 16, radio=4, relleno=white)
            h.texto(str(nivel), 0, cursor - 15, tam=9, negrita=True, centrado_en=x + 11)
            if nivel == 0:
                h.etiqueta("TRUCOS", x + 20, cursor - 14, ancho_col - 20, tam=6.5)
            else:
                total = espacios.get(nivel, "")
                if pacto and pacto["nivel"] == nivel:
                    total = f"{total} + {pacto['espacios']} (pacto)" if total else f"{pacto['espacios']} (pacto)"
                h.marco(x + 22, cursor - 19, 44, 16, radio=4, relleno=white)
                h.texto(str(total), 0, cursor - 15, tam=8, negrita=True, centrado_en=x + 44)
                h.marco(x + 70, cursor - 19, ancho_col - 74, 16, radio=4, relleno=white)
                h.texto("ESPACIOS TOTALES", x + 23, cursor + 1.5, tam=4.8, color=GRIS)
                h.texto("ESPACIOS GASTADOS", x + 72, cursor + 1.5, tam=4.8, color=GRIS)
            cursor -= 34
            conjuros = por_nivel.get(nivel, [])
            if len(conjuros) > renglones:
                sobran = len(conjuros) - renglones + 1
                conjuros = conjuros[: renglones - 1] + [(f"… y {sobran} más (ver el resumen)", False)]
            for r in range(renglones):
                y = cursor - r * paso
                h.c.setStrokeColor(GRIS_CLARO)
                h.c.setLineWidth(0.5)
                h.c.line(x + 12, y - 3, x + ancho_col - 4, y - 3)
                if nivel > 0:
                    h.circulo(x + 6, y + 0.5, r=2.8, lleno=r < len(conjuros) and conjuros[r][1])
                if r < len(conjuros):
                    h.texto(conjuros[r][0], x + 13, y - 1, tam=7.5, ancho_max=ancho_col - 18)
            cursor -= renglones * paso + 6
    h.c.saveState()
    h.c.translate(MARGEN - 8, 420)
    h.c.rotate(90)
    h.texto("CONJUROS CONOCIDOS (círculo relleno = preparado)", 0, 0, tam=5.5, color=GRIS)
    h.c.restoreState()


def generar_ficha_pdf(a: Asistente5e, ruta: str) -> None:
    """Escribe la réplica de la hoja oficial: personaje, detalles y (si lanza conjuros) conjuros."""
    ficha = a.ficha()
    hoja = Hoja(ruta)
    hoja.c.setTitle(_t(f"{ficha.nombre or 'Personaje'} · hoja de personaje"))
    rasgos_adicionales = _pagina_personaje(hoja, ficha, a)
    hoja.pagina()
    _pagina_detalles(hoja, ficha, a, rasgos_adicionales)
    hoja.pagina()
    if ficha.lanzadores:
        _pagina_conjuros(hoja, ficha)
        hoja.pagina()
    hoja.c.save()
