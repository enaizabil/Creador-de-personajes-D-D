"""Rellena la hoja de personaje editable en español (la oficial de Wizards con los campos de su versión rellenable).

La plantilla (``datos/plantillas/dnd5e-2014/hoja_editable_es.pdf``) tiene 5 páginas: personaje, detalles,
conjuros, descripción de conjuros y continuación de la historia. Sus campos usan los nombres de la hoja
rellenable de Wizards (``STRscore``, ``Spells9``…).

La hoja trae cálculos propios (modificador = (puntuación − 10) / 2; habilidad = modificador + competencia si
la casilla está marcada) que no contemplan la pericia ni otros bonificadores. Como el motor ya lo calcula todo,
al rellenar se quitan esos cálculos: si no, el visor los rehace al tocar cualquier campo y borra, por ejemplo,
la pericia. Los formatos de número se mantienen.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject
from reportlab.pdfbase.pdfmetrics import stringWidth

from ....nucleo.rutas import directorio_datos_integrados
from ..constantes import CARACTERISTICAS, RECARGAS

if TYPE_CHECKING:
    from ..asistente import Asistente5e
    from ..ficha import Ficha

PLANTILLA = directorio_datos_integrados() / "plantillas" / "dnd5e-2014" / "hoja_editable_es.pdf"
CARACTERISTICA_CAMPO = {"fue": "STR", "des": "DEX", "con": "CON", "int": "INT", "sab": "WIS", "car": "CHA"}
HABILIDAD_CAMPO = {
    "acrobacias": ("Acrobatics", "acroPROF"), "atletismo": ("Athletics", "athPROF"),
    "conocimiento_arcano": ("Arcana", "arcanaPROF"), "engano": ("Deception", "decepPROF"),
    "historia": ("History", "histPROF"), "interpretacion": ("Performance", "perfPROF"),
    "intimidacion": ("Intimidation", "intimPROF"), "investigacion": ("Investigation", "investPROF"),
    "juego_de_manos": ("SleightofHand", "sohPROF"), "medicina": ("Medicine", "medPROF"),
    "naturaleza": ("Nature", "naturePROF"), "percepcion": ("Perception", "perPROF"),
    "perspicacia": ("Insight", "insightPROF"), "persuasion": ("Persuasion", "persPROF"),
    "religion": ("Religion", "religPROF"), "sigilo": ("Stealth", "stealthPROF"),
    "supervivencia": ("Survival", "survPROF"), "trato_con_animales": ("AnHan", "anhanPROF"),
}
MONEDA_CAMPO = {"pc": "Copper", "pp": "Silver", "pe": "Electrum", "po": "Gold", "ppt": "Platinum"}
APTITUD_CAMPO = {"int": "INT", "sab": "SAB", "car": "CAR"}
# Renglones de cada nivel de conjuro en la página 3 (comprobado por la posición de los campos).
RENGLONES_CONJURO = {0: range(1, 9), 1: range(9, 21), 2: range(21, 34), 3: range(34, 47), 4: range(47, 60),
                     5: range(60, 69), 6: range(69, 78), 7: range(78, 87), 8: range(87, 94), 9: range(94, 101)}
ESCUELAS = {"abjuracion": "abjuración", "adivinacion": "adivinación", "conjuracion": "conjuración",
            "encantamiento": "encantamiento", "evocacion": "evocación", "ilusion": "ilusión",
            "nigromancia": "nigromancia", "transmutacion": "transmutación"}
FUENTE = "Helvetica"
MULTILINEA = 1 << 12
TAM_MAXIMO, TAM_MINIMO, TAM_REPARTO = 10, 5, 6.5


def _signo(valor: int) -> str:
    return f"{valor:+d}"


def _nombre(anotacion) -> str:
    partes, nodo = [], anotacion
    while nodo is not None:
        if "/T" in nodo:
            partes.append(str(nodo["/T"]))
        nodo = nodo["/Parent"].get_object() if "/Parent" in nodo else None
    return ".".join(reversed(partes))


def _atributo(anotacion, clave: str):
    nodo = anotacion
    while nodo is not None:
        if clave in nodo:
            return nodo[clave]
        nodo = nodo["/Parent"].get_object() if "/Parent" in nodo else None
    return None


def _partir(texto: str, ancho: float, tam: float) -> list[str]:
    """Renglones del texto partido por palabras con las métricas de la fuente.

    Se entregan ya partidos: el reparto de líneas de pypdf no coincide con el ancho real del campo.
    """
    renglones = []
    for parrafo in texto.split("\n"):
        linea = ""
        for palabra in parrafo.split(" "):
            prueba = f"{linea} {palabra}" if linea else palabra
            if stringWidth(prueba, FUENTE, tam) > ancho and linea:
                renglones.append(linea)
                linea = palabra
            else:
                linea = prueba
        renglones.append(linea)
    return renglones


def _lineas(texto: str, ancho: float, tam: float) -> int:
    return len(_partir(texto, ancho, tam))


class Campo:
    def __init__(self, anotacion):
        self.anotacion = anotacion
        rect = [float(x) for x in anotacion["/Rect"]]
        self.ancho, self.alto = abs(rect[2] - rect[0]), abs(rect[3] - rect[1])
        self.x, self.y = min(rect[0], rect[2]), min(rect[1], rect[3])
        self.multilinea = bool(int(_atributo(anotacion, "/Ff") or 0) & MULTILINEA)
        self.tipo = str(_atributo(anotacion, "/FT"))

    @property
    def ancho_util(self) -> float:
        return self.ancho - 6  # márgenes del visor

    def cabe(self, texto: str, tam: float) -> bool:
        if self.multilinea:
            return _lineas(texto, self.ancho_util, tam) * tam * 1.16 <= self.alto - 2
        return stringWidth(texto, FUENTE, tam) <= self.ancho_util

    def tamano(self, texto: str) -> float:
        """El mayor tamaño de letra con el que cabe (o el mínimo)."""
        tam = min(TAM_MAXIMO, self.alto * 0.72) if not self.multilinea else min(TAM_MAXIMO, 9)
        while tam > TAM_MINIMO and not self.cabe(texto, tam):
            tam -= 0.5
        return tam


class HojaEditable:
    """La plantilla abierta para rellenar: campos por nombre y valores pendientes."""

    def __init__(self, plantilla: Path = PLANTILLA):
        self.escritor = PdfWriter(clone_from=PdfReader(str(plantilla)))
        self.campos: dict[str, Campo] = {}
        self.pagina_de: dict[str, int] = {}
        for numero, pagina in enumerate(self.escritor.pages):
            for anotacion in pagina.get("/Annots", []) or []:
                widget = anotacion.get_object()
                if widget.get("/Subtype") == "/Widget":
                    nombre = _nombre(widget)
                    self.campos[nombre] = Campo(widget)
                    self.pagina_de[nombre] = numero
        self.valores: dict[str, str] = {}

    def poner(self, nombre: str, valor) -> None:
        if nombre not in self.campos:
            raise KeyError(f"La plantilla no tiene el campo «{nombre}»")
        self.valores[nombre] = str(valor)

    def marcar(self, nombre: str, marcado: bool = True) -> None:
        if nombre not in self.campos:
            raise KeyError(f"La plantilla no tiene el campo «{nombre}»")
        self.valores[nombre] = "/Yes" if marcado else "/Off"

    def repartir(self, bloques: list[str], nombres: list[str], separador: str = "\n") -> None:
        """Llena varios campos seguidos con bloques de texto; lo que no cabe en uno pasa al siguiente."""
        restantes = [b for b in bloques if b]
        for i, nombre in enumerate(nombres):
            campo, texto = self.campos[nombre], ""
            while restantes:
                prueba = f"{texto}{separador}{restantes[0]}" if texto else restantes[0]
                if texto and not campo.cabe(prueba, TAM_REPARTO) and i < len(nombres) - 1:
                    break
                texto = prueba
                restantes.pop(0)
            if texto:
                self.poner(nombre, texto)

    def casilla_junto_a(self, nombre: str) -> str | None:
        """La casilla de «preparado» a la izquierda de un renglón de conjuro."""
        renglon = self.campos[nombre]
        candidatas = [(n, c) for n, c in self.campos.items() if c.tipo == "/Btn" and self.pagina_de[n] == self.pagina_de[nombre]
                      and 0 <= renglon.x - (c.x + c.ancho) <= 6 and abs((c.y + c.alto / 2) - (renglon.y + renglon.alto / 2)) <= 5]
        return candidatas[0][0] if candidatas else None

    def guardar(self, ruta) -> None:
        escritor = self.escritor
        formulario = escritor._root_object["/AcroForm"]
        if "/CO" in formulario:  # sin orden de cálculo: los valores son los del motor
            del formulario["/CO"]
        for nombre, campo in self.campos.items():
            acciones = _atributo(campo.anotacion, "/AA")
            if acciones is not None and "/C" in acciones.get_object():
                del acciones.get_object()["/C"]
            valor = self.valores.get(nombre)
            if valor is not None and campo.tipo in ("/Tx", "/Ch"):
                recursos = campo.anotacion.get("/DR")
                fuentes = recursos.get_object().get("/Font", {}) if recursos is not None else {}
                if recursos is not None and not all("/Encoding" in f.get_object() for f in fuentes.values()):
                    # 12 campos traen una /Helv propia sin codificación: el visor que redibuja el campo pierde
                    # los acentos. Sin ella usan la del formulario, que sí la tiene.
                    del campo.anotacion["/DR"]
                tam = campo.tamano(valor)
                campo.anotacion[NameObject("/DA")] = TextStringObject(f"/Helv {tam:g} Tf 0 g")
                if campo.multilinea:
                    self.valores[nombre] = "\n".join(_partir(valor, campo.ancho_util, tam))
        for numero, pagina in enumerate(escritor.pages):
            valores = {n: v for n, v in self.valores.items() if self.pagina_de[n] == numero}
            if valores:
                escritor.update_page_form_field_values(pagina, valores, auto_regenerate=False)
        escritor.set_need_appearances_writer(True)
        with open(ruta, "wb") as salida:
            escritor.write(salida)


# ── contenido ─────────────────────────────────────────────────────────────

def _rasgos(ficha: Ficha) -> list[str]:
    bloques = []
    defensas = [f"{n} {pies} pies" for n, pies in ficha.sentidos.items()]
    defensas += [f"Resistencia a {', '.join(ficha.resistencias)}"] if ficha.resistencias else []
    defensas += [f"Inmunidad a {', '.join(ficha.inmunidades)}"] if ficha.inmunidades else []
    if defensas:
        bloques.append(". ".join(defensas) + ".")
    for rasgo in ficha.rasgos:
        usos = f" ({rasgo.usos} por {RECARGAS.get(rasgo.recarga, 'día')})" if rasgo.usos is not None else ""
        resumen = f": {rasgo.resumen.rstrip('.')}." if rasgo.resumen else "."
        bloques.append(f"{rasgo.nombre}{usos}{resumen}")
    return bloques


def _ids_conjuros(a: Asistente5e) -> list[str]:
    ids = [i for lista in a.personaje.conjuros.values() for i in lista]
    ids += sorted(a.conjuros_de_otras_fuentes())
    return list(dict.fromkeys(ids))


def _descripcion_conjuro(conjuro: dict) -> str:
    nivel = "truco" if conjuro["nivel"] == 0 else f"nivel {conjuro['nivel']}"
    marcas = "".join(m for m, si in ((" (ritual)", conjuro.get("ritual")), (" (concentración)", conjuro.get("concentracion")))
                     if si)
    datos = " · ".join(conjuro[c] for c in ("tiempo", "alcance", "componentes", "duracion") if conjuro.get(c))
    return f"{conjuro['nombre']} ({nivel}, {ESCUELAS.get(conjuro['escuela'], conjuro['escuela'])}){marcas}. {datos}. " \
           f"{conjuro.get('resumen') or conjuro.get('descripcion', '')}".strip()


def _armadura_y_escudo(a: Asistente5e) -> tuple[str, bool]:
    armadura, escudo = "", False
    for objeto in a.personaje.equipo:
        entrada = a.catalogo.obtener("objetos", objeto.id) if objeto.id else None
        if entrada and objeto.equipado:
            if entrada["categoria"] == "armadura" and not armadura:
                armadura = entrada["nombre"]
            escudo |= entrada["categoria"] == "escudo"
    return armadura, escudo


def rellenar_hoja_oficial(a: Asistente5e, ruta, plantilla: Path = PLANTILLA) -> None:
    """Escribe en ``ruta`` la hoja editable rellena con el personaje."""
    ficha = a.ficha()
    p = a.personaje
    hoja = HojaEditable(plantilla)

    # Página 1: cabecera, características, salvaciones, habilidades y combate.
    for campo, valor in (("CharacterName", ficha.nombre), ("ClassLevel", ficha.clase_y_nivel), ("Background", ficha.trasfondo),
                         ("PlayerName", ficha.jugador), ("Race", ficha.raza), ("Alignment", p.detalles.get("alineamiento", "")),
                         ("ExperiencePoints", ficha.experiencia), ("CharacterName 2", ficha.nombre)):
        hoja.poner(campo, valor)
    for car, prefijo in CARACTERISTICA_CAMPO.items():
        valor = ficha.caracteristicas[car]
        hoja.poner(f"{prefijo}score", valor.puntuacion)
        hoja.poner(f"{prefijo}bonus", _signo(valor.modificador))
        salvacion = ficha.salvaciones[car]
        hoja.poner(f"{prefijo}save", _signo(salvacion.valor))
        hoja.marcar(f"{prefijo}savePROF", salvacion.competente)
    for id_, (campo, casilla) in HABILIDAD_CAMPO.items():
        tirada = ficha.habilidades[id_]
        hoja.poner(campo, _signo(tirada.valor))
        hoja.marcar(casilla, tirada.competente)
    hoja.poner("ProfBonus", _signo(ficha.bonificador_competencia))
    hoja.poner("PWP", ficha.percepcion_pasiva)
    hoja.poner("AC", ficha.ca)
    hoja.poner("Init", _signo(ficha.iniciativa))
    hoja.poner("Speed", f"{ficha.velocidades.get('caminar', 0)} pies")
    hoja.poner("HPMax", ficha.pg_maximos)
    if len(ficha.dados_golpe) == 1:
        (dado, cantidad), = ficha.dados_golpe.items()
        hoja.poner("HitDiceTotal", cantidad)
        hoja.poner("Text1", dado)
    else:
        hoja.poner("HitDiceTotal", " + ".join(f"{n}{d}" for d, n in ficha.dados_golpe.items()))
    armadura, escudo = _armadura_y_escudo(a)
    hoja.poner("ArmorWorn", armadura)
    hoja.marcar("shieldyes", escudo)
    hoja.poner("ACworn", ficha.ca)

    for n, ataque in enumerate(ficha.ataques[:3], start=1):
        hoja.poner(f"Attack{n}", ataque.nombre)
        hoja.poner(f"AtkBonus{n}", _signo(ataque.bonificador))
        hoja.poner(f"Damage{n}", f"{ataque.dano} {ataque.tipo_dano}".strip())
    notas = [f"{at.nombre}: {_signo(at.bonificador)}, {at.dano} {at.tipo_dano}".strip() for at in ficha.ataques[3:]]
    notas += [f"{at.nombre}: {at.notas}." for at in ficha.ataques if at.notas]
    notas += [f"Conjuros ({CARACTERISTICAS[lz.caracteristica]}): CD {lz.cd}, ataque {_signo(lz.ataque)}."
              for lz in ficha.lanzadores]
    if ficha.conjuros_innatos:
        notas.append(f"Conjuros innatos: {', '.join(ficha.conjuros_innatos)}.")
    hoja.repartir(notas, ["AttacksSpellsMisc"])

    hoja.repartir([", ".join(ficha.equipo) + "." if ficha.equipo else ""], ["Equipment"])
    for moneda, campo in MONEDA_CAMPO.items():
        if p.monedas.get(moneda):
            hoja.poner(campo, p.monedas[moneda])
    competencias = [f"{t}: {', '.join(ficha.competencias[k])}." for t, k in (
        ("Armaduras", "armaduras"), ("Armas", "armas"), ("Herramientas", "herramientas"), ("Idiomas", "idiomas"))
        if ficha.competencias.get(k)]
    pericias = [t.nombre for t in ficha.habilidades.values() if t.pericia]
    if pericias:
        competencias.append(f"Pericia (ya sumada): {', '.join(pericias)}.")
    hoja.repartir(competencias, ["ProfsLangs"])
    for campo, clave in (("PersonalityTraits", "rasgos_personalidad"), ("Ideals", "ideales"), ("Bonds", "vinculos"),
                         ("Flaws", "defectos")):
        hoja.repartir([p.detalles.get(clave, "")], [campo])
    hoja.repartir(_rasgos(ficha), ["FeaturesTraits", "Feat+Traits", "Feat+Traits 2"])

    # Página 2: detalles e historia (lo que no cabe sigue en la página 5).
    for campo, clave in (("Age", "edad"), ("Height", "altura"), ("Weight", "peso"), ("Eyes", "ojos"), ("Skin", "piel"),
                         ("Hair", "pelo")):
        if p.detalles.get(clave):
            hoja.poner(campo, p.detalles[clave])
    historia = [f"Aspecto: {p.detalles['apariencia']}"] if p.detalles.get("apariencia") else []
    historia += [t for t in re.split(r"\n\s*\n", p.detalles.get("historia", "")) if t.strip()]
    hoja.repartir(historia, ["Backstory", "Backstory 1", "Backstory 2", "Backstory 3"], separador="\n\n")

    # Página 3: conjuros; página 4: su descripción.
    if ficha.lanzadores:
        lanzador = ficha.lanzadores[0]
        hoja.poner("SpellClass", " / ".join(lz.clase for lz in ficha.lanzadores))
        hoja.poner("SpellAbility", APTITUD_CAMPO.get(lanzador.caracteristica, lanzador.caracteristica.upper()))
        hoja.poner("SpellSaveDC", lanzador.cd)
        hoja.poner("SAB", _signo(lanzador.ataque))
        for nivel, espacios in ficha.espacios_conjuro.items():
            hoja.poner(f"SlotsTot{nivel}", espacios)
        if ficha.magia_pacto:
            hoja.poner(f"SlotsTot{ficha.magia_pacto['nivel']}", f"{ficha.magia_pacto['espacios']} (pacto)")
        for nivel, conjuros in _por_nivel(ficha).items():
            renglones = list(RENGLONES_CONJURO[nivel])
            for numero, (nombre, preparado) in zip(renglones, conjuros, strict=False):
                hoja.poner(f"Spells{numero}", nombre)
                casilla = hoja.casilla_junto_a(f"Spells{numero}") if nivel else None
                if casilla and preparado:
                    hoja.marcar(casilla)
    descripciones = [_descripcion_conjuro(c) for c in sorted(
        (a.catalogo.obtener("conjuros", i) for i in _ids_conjuros(a)), key=lambda c: (c["nivel"], c["nombre"])) if c]
    hoja.repartir(descripciones, ["Spells 1", "Spell 2", "Spells 3"], separador="\n\n")
    hoja.guardar(ruta)


def _por_nivel(ficha: Ficha) -> dict[int, list[tuple[str, bool]]]:
    """nivel -> [(nombre, preparado)]; con libro, los no preparados quedan sin marcar."""
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
