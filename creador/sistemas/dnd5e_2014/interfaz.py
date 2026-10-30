"""Lo que comparten las dos interfaces de 5e (escritorio y web): textos, límites, interruptores de reglas e iconos."""
from __future__ import annotations

from .constantes import RASGOS_PERFIL

PERSONALIDAD = (("rasgos_personalidad", "Rasgos de personalidad"), ("ideales", "Ideales"),
                ("vinculos", "Vínculos"), ("defectos", "Defectos"))
FISICO = (("edad", "Edad"), ("altura", "Altura"), ("peso", "Peso"), ("ojos", "Ojos"), ("piel", "Piel"), ("pelo", "Pelo"))
NOMBRES_PERFIL = {r: r.capitalize() for r in RASGOS_PERFIL} | {"proteccion": "Protección", "curacion": "Curación"}
LARGO_DESCRIPCION_OPCIONAL = 95

MAX_CASILLAS = 10  # con más opciones se usan desplegables
MAX_DESPLEGABLE = 40  # con más aún (Secretos Mágicos: cualquier conjuro), un buscador
MAX_RESULTADOS = 20  # casillas que muestra el buscador a la vez

MARCA_PROPUESTA = "★ Propuesta."
RESPUESTAS_EN_UNA_COLUMNA = 6  # con más, en dos columnas para no hacer la lista eterna
AYUDA_SUBIDA = ("Cada pregunta concreta trae las opciones reales de tu personaje; «★ Propuesta» marca lo que se elegiría "
                "según su forma de ser si no respondes. Puedes dejar preguntas sin responder.")
CUANTAS_RECOMENDACIONES = 3
NOMBRES_DECISION = {"mejora": "mejora de característica o dote", "subclase": "subclase",
                    "opciones": "opciones de clase", "conjuros": "conjuros nuevos"}

# Iconos (archivos de recursos/iconos, sin .png) de game-icons.net: créditos en recursos/CREDITOS.md.
ICONOS_PASO = {"inicio": "dice-twenty-faces-twenty", "raza": "elf-ear", "clase": "crossed-swords",
               "caracteristicas": "muscle-up", "trasfondo": "scroll-unfurled", "equipo": "knapsack",
               "conjuros": "spell-book", "detalles": "quill-ink", "resumen": "checklist"}
ICONOS_CLASE = {"barbaro": "barbarian", "bardo": "lyre", "brujo": "warlock-eye", "clerigo": "holy-symbol",
                "druida": "oak-leaf", "explorador": "high-shot", "guerrero": "broadsword", "hechicero": "magic-swirl",
                "mago": "pointy-hat", "monje": "fist", "paladin": "templar-shield", "picaro": "cloak-dagger",
                "artifice": "gears"}
ICONOS_RAZA = {"humano": "person", "elfo": "woman-elf-face", "enano": "dwarf-face", "mediano": "smoking-pipe",
               "draconido": "dragon-head", "gnomo": "bad-gnome", "semielfo": "elf-ear", "semiorco": "orc-head",
               "tiefling": "devil-mask", "aasimar": "angel-wings", "linaje_personalizado": "dna1"}
ICONO_TRASFONDO = "scroll-unfurled"
ICONO_GENERICO = "dice-twenty-faces-twenty"  # clases y razas de homebrew sin icono propio


def nombre_icono(categoria: str, id_: str | None, generico: bool = True) -> str | None:
    """Archivo del icono de una clase, raza, paso o trasfondo («clases», «razas», «pasos», «trasfondos»)."""
    tabla = {"clases": ICONOS_CLASE, "razas": ICONOS_RAZA, "pasos": ICONOS_PASO}.get(categoria, {})
    nombre = ICONO_TRASFONDO if categoria == "trasfondos" else tabla.get(id_ or "")
    return nombre or (ICONO_GENERICO if generico else None)


def perfil_en_puntos(perfil: dict, nombres: dict[str, str] | None = None) -> str:
    """{"sigilo": 3, "astucia": 2} -> «Sigilo ●●● · Astucia ●●○»."""
    partes = []
    for rasgo, valor in sorted(perfil.items(), key=lambda x: -x[1]):
        if valor:
            nombre = (nombres or NOMBRES_PERFIL).get(rasgo, rasgo.capitalize())
            partes.append(f"{nombre} {'●' * valor}{'○' * (3 - valor)}")
    return " · ".join(partes)


def interruptores_reglas(paquetes: set[str]) -> list[tuple[str, str, bool, str]]:
    """Reglas opcionales que se pueden encender en «Edición y reglas»: (regla, texto, de serie, ayuda)."""
    interruptores = [
        ("dotes", "Dotes (regla opcional del Manual del Jugador)", True, ""),
        ("multiclase", "Multiclase (regla opcional del Manual del Jugador)", False,
         "Reparte los niveles entre varias clases (desde nivel 2, en el paso «Clase»). Es para jugadores con experiencia: "
         "si no sabes qué es, déjala apagada."),
        ("opciones_dm", "Opciones de la Guía del DM que requieren su permiso (aasimar, eladrín…)", False, "")]
    if "tasha-2020" in paquetes:
        interruptores += [
            ("origen_personalizado", "Personalizar tu origen: mover las mejoras de raza a otras características (Tasha)",
             False, ""),
            ("rasgos_opcionales", "Rasgos de clase opcionales (Tasha): listas de conjuros ampliadas, estilos, invocaciones… "
                                  "y rasgos que sustituyen a otros", False, "")]
    if "dmg-2014" in paquetes:
        interruptores += [
            ("equipo_por_nivel", "Oro extra al empezar por encima de nivel 4 (Guía del DM)", False, ""),
            ("entrenamiento", "Entrenarse para subir de nivel: días y coste por nivel (Guía del DM)", False, "")]
    return interruptores
