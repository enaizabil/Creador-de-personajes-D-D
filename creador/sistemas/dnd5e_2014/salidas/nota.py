"""Nota de personaje en Markdown (Obsidian) con la ficha resumida y la guía para pasarlo a Nivel20.

Sigue la «Plantilla PJ» de Villaprincipio: las propiedades (``hp``, ``ac``, ``modifier``, pasivas…) son las que
leen la tabla de mesa del DM e Initiative Tracker, y la sección «Ficha de Nivel20» tiene el formato de las
notas de los PJ. Nivel20 no importa personajes de 5e, así que la guía dice qué elegir en cada paso de su
creador.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..constantes import CARACTERISTICAS, RECARGAS
from ..texto import ABREVIATURAS

if TYPE_CHECKING:
    from ...dnd5e_2014.asistente import Asistente5e
    from ..ficha import Ficha

ORIGENES_PASO = (("raza", ("raza:", "subraza:")), ("clase", ("clase:", "subclase:", "opcional:")), ("trasfondo", ("trasfondo:",)))
NOMBRES_METODO = {"estandar": "array estándar", "compra": "compra por puntos", "tirada": "tiradas", "manual": "a mano"}
# Diferencias de nombre ya comprobadas en Nivel20 (notas de Villaprincipio).
NOMBRES_NIVEL20 = {"Abisal": "Demoníaco"}
# Ya los resume la línea de magia.
RASGOS_EN_MAGIA = {"lanzamiento de conjuros", "magia del pacto"}


def _signo(valor: int) -> str:
    """+2 / −1, con el signo menos tipográfico de las notas."""
    return f"+{valor}" if valor >= 0 else f"−{-valor}"


def _lista(nombres: list[str], cursiva: bool = False) -> str:
    return ", ".join(f"*{n}*" if cursiva else n for n in nombres)


def _vision(ficha: Ficha) -> str:
    oscuridad = [pies for sentido, pies in ficha.sentidos.items() if "oscuridad" in sentido.lower()]
    return f"oscuridad {max(oscuridad)} pies" if oscuridad else "normal"


def _yaml(valor) -> str:
    texto = str(valor)
    return f'"{texto}"' if any(c in texto for c in ':#[]{}"') else texto


def _propiedades(a: Asistente5e, ficha: Ficha) -> list[str]:
    p = a.personaje
    clases = [a.catalogo.obtener("clases", e.clase) or {} for e in p.clases]
    subclases = [a.catalogo.obtener("subclases", e.subclase) or {} for e in p.clases if e.subclase]
    propiedades = {
        "tipo": "pj", "jugador": p.jugador, "raza": ficha.raza,
        "clase": " / ".join(c.get("nombre", "") for c in clases),  # multiclase: «Guerrero / Pícaro»
        "nivel": ficha.nivel, "hp": ficha.pg_maximos, "ac": ficha.ca, "modifier": ficha.iniciativa,
        "pasiva_percepcion": ficha.pasivas["percepcion"], "pasiva_perspicacia": ficha.pasivas["perspicacia"],
        "pasiva_investigacion": ficha.pasivas["investigacion"], "vision": _vision(ficha), "px": p.experiencia,
    }
    if subclases:
        propiedades["subclase"] = " / ".join(s.get("nombre", "") for s in subclases)
    propiedades |= {"estado": "activo", "grupo": "", "alineamiento": p.detalles.get("alineamiento", "")}
    lineas = ["---", *(f"{k}: {_yaml(v)}" if v != "" else f"{k}:" for k, v in propiedades.items()), "tags: [pj]", "---"]
    return lineas


def _ficha_nivel20(a: Asistente5e, ficha: Ficha) -> list[str]:
    cabecera = f"**{ficha.raza} · {ficha.clase_y_nivel}** · PG {ficha.pg_maximos} · CA {ficha.ca} · " \
               f"Iniciativa {_signo(ficha.iniciativa)} · Velocidad {ficha.velocidades.get('caminar', 0)} pies · " \
               f"Competencia {_signo(ficha.bonificador_competencia)}"
    abreviaturas = [ABREVIATURAS[c] for c in CARACTERISTICAS]
    salvaciones = [f"**{_signo(t.valor)}**" if t.competente else _signo(t.valor) for t in ficha.salvaciones.values()]
    lineas = ["## Ficha de Nivel20", cabecera, "",
              "| | " + " | ".join(abreviaturas) + " |", "|---" * 7 + "|",
              "| Puntuación | " + " | ".join(str(v.puntuacion) for v in ficha.caracteristicas.values()) + " |",
              "| Salvación | " + " | ".join(salvaciones) + " |", ""]
    competentes = [f"{t.nombre} {_signo(t.valor)}" + (" (pericia)" if t.pericia else "")
                   for t in ficha.habilidades.values() if t.competente]
    lineas.append(f"- **Habilidades con competencia:** {', '.join(competentes) or 'ninguna'}. Resto: el modificador.")
    lineas.append(f"- **Pasivas:** Percepción {ficha.pasivas['percepcion']} · Perspicacia {ficha.pasivas['perspicacia']} · "
                  f"Investigación {ficha.pasivas['investigacion']}.")
    if ficha.ataques:
        ataques = []
        for ataque in ficha.ataques:
            detalle = " ".join(p for p in (ataque.dano, ataque.tipo_dano) if p)
            if ataque.notas:
                detalle += f"; {ataque.notas[0].lower()}{ataque.notas[1:]}"
            ataques.append(f"{ataque.nombre} {_signo(ataque.bonificador)} ({detalle})")
        lineas.append(f"- **Ataques:** {' · '.join(ataques)}.")
    partes = [", ".join(ficha.competencias.get(clave, [])) for clave in ("armaduras", "armas", "herramientas")]
    competencias = "; ".join(p for p in partes if p) or "ninguna"
    lineas.append(f"- **Competencias:** {competencias}. Idiomas: {', '.join(ficha.competencias.get('idiomas', []))}.")
    extras = [f"{n.lower()} {pies} pies" for n, pies in ficha.sentidos.items()]
    extras += [f"resistencia a {', '.join(ficha.resistencias)}"] if ficha.resistencias else []
    extras += [f"inmunidad a {', '.join(ficha.inmunidades)}"] if ficha.inmunidades else []
    if extras:
        lineas.append(f"- **Sentidos y defensas:** {' · '.join(extras)}.")
    rasgos, dotes = [], []
    for rasgo in ficha.rasgos:
        if rasgo.nombre.lower() in RASGOS_EN_MAGIA:
            continue
        usos = f" ({rasgo.usos} por {RECARGAS.get(rasgo.recarga, 'día')})" if rasgo.usos is not None else ""
        resumen = f": {rasgo.resumen.rstrip('.')}." if rasgo.resumen else ""
        if rasgo.nombre.startswith("Dote: "):
            dotes.append(f"  - *{rasgo.nombre[6:]}*{usos}{resumen}")
        else:
            rasgos.append(f"  - *{rasgo.nombre}*{usos}{resumen}")
    if rasgos:
        lineas += ["- **Rasgos:**", *rasgos]
    if dotes:
        lineas += [f"- **Dote{'s' if len(dotes) > 1 else ''}:**", *dotes]
    lineas += _magia(a, ficha)
    if a.personaje.extra.get("cuestionario", {}).get("generado"):
        lineas.append("- Creado con el cuestionario de situaciones del creador de personajes: revisa las elecciones con "
                      "el jugador.")
    return lineas


def _magia(a: Asistente5e, ficha: Ficha) -> list[str]:
    lineas = []
    planes = {plan.clase_id: plan for plan in a.planes_conjuros()}
    for lanzador in ficha.lanzadores:
        plan = planes.get(lanzador.clase_id)
        partes = [f"{n} de nivel {nivel}" for nivel, n in ficha.espacios_conjuro.items()]
        if ficha.magia_pacto:
            partes.append(f"{ficha.magia_pacto['espacios']} de pacto de nivel {ficha.magia_pacto['nivel']}")
        espacios = " y ".join([", ".join(partes[:-1]), partes[-1]] if len(partes) > 1 else partes)
        cantidad = ""
        if plan and plan.limite_conjuros:
            cantidad = f" {'Conoce' if plan.modo == 'conocidos' else 'Prepara'} {plan.limite_conjuros}."
        lineas.append(f"- **Magia ({CARACTERISTICAS[lanzador.caracteristica]}):** CD {lanzador.cd} · ataque "
                      f"{_signo(lanzador.ataque)}. Espacios: {espacios or 'ninguno'}.{cantidad}")
        if lanzador.conjuros.get(0):
            lineas.append(f"  - Trucos: {_lista(lanzador.conjuros[0], True)}.")
        siempre = [n for nivel in sorted(lanzador.siempre_preparados) for n in lanzador.siempre_preparados[nivel]]
        if siempre:
            lineas.append(f"  - Siempre preparados (no cuentan): {_lista(siempre, True)}.")
        resto = [n for nivel in sorted(lanzador.conjuros) if nivel > 0 for n in lanzador.conjuros[nivel]]
        if resto:
            lineas.append(f"  - {'Conocidos' if plan and plan.modo == 'conocidos' else 'Preparados'}: {_lista(resto, True)}.")
        libro = [n for nivel in sorted(lanzador.libro) for n in lanzador.libro[nivel]]
        if libro:
            lineas.append(f"  - Libro de conjuros: {_lista(libro, True)}.")
    if ficha.conjuros_innatos:
        lineas.append(f"- **Conjuros innatos:** {_lista(ficha.conjuros_innatos, True)}.")
    return lineas


def _elecciones_por_paso(a: Asistente5e) -> dict[str, list[str]]:
    pasos: dict[str, list[str]] = {paso: [] for paso, _ in ORIGENES_PASO}
    for eleccion in a.sistema.resolver(a.personaje, a.catalogo).elecciones:
        if not eleccion.seleccion:
            continue
        nombres = {o.id: o.nombre for o in eleccion.opciones}
        elegido = ", ".join(_nombre_nivel20(nombres.get(i, i)) for i in eleccion.seleccion)
        paso = next((p for p, prefijos in ORIGENES_PASO if eleccion.clave.startswith(prefijos)), "clase")
        pasos[paso].append(f"{eleccion.etiqueta} · {eleccion.nombre}: **{elegido}**")
    return pasos


def _nombre_nivel20(nombre: str) -> str:
    return f"{nombre} (en Nivel20, «{NOMBRES_NIVEL20[nombre]}»)" if nombre in NOMBRES_NIVEL20 else nombre


def _guia(a: Asistente5e, ficha: Ficha) -> list[str]:
    p = a.personaje
    catalogo = a.catalogo
    elecciones = _elecciones_por_paso(a)
    raza = catalogo.obtener("razas", p.raza or "") or {}
    subraza = catalogo.obtener("subrazas", p.subraza or "") or {}
    entrada = p.clases[0] if p.clases else None
    clase = catalogo.obtener("clases", entrada.clase) if entrada else {}
    subclase = catalogo.obtener("subclases", entrada.subclase) if entrada and entrada.subclase else None
    trasfondo = catalogo.obtener("trasfondos", p.trasfondo or "") or {}
    secundarias = p.clases[1:]

    def con_elecciones(texto: str, paso: str) -> list[str]:
        return [texto, *(f"   - {e}" for e in elecciones[paso])]

    lineas = ["## Cómo pasarlo a Nivel20",
              "Nivel20 no importa personajes de 5e: hay que crearlo a mano. Sigue los pasos en orden; los nombres de "
              "los menús pueden variar un poco según la versión de la web.", "",
              "1. **Crear:** *Mis personajes → Añadir* y elige **D&D 5e (2014)**, no D&D 5.5 (2024)."]
    lineas += con_elecciones(f"2. **Raza:** {raza.get('nombre', '—')}" +
                             (f", subraza **{subraza['nombre']}**." if subraza else "."), "raza")
    if secundarias:
        texto_clase = (f"3. **Clase inicial:** {(clase or {}).get('nombre', '—')} (es la que da las salvaciones y "
                       f"todas sus competencias), hasta nivel **{entrada.nivel}**")
    else:
        texto_clase = f"3. **Clase:** {(clase or {}).get('nombre', '—')}, nivel **{ficha.nivel}**"
    if subclase:
        texto_clase += f", subclase **{subclase['nombre']}**"
    texto_clase += "."
    if secundarias:
        otras = []
        for otra in secundarias:
            datos = catalogo.obtener("clases", otra.clase) or {}
            sub = catalogo.obtener("subclases", otra.subclase) if otra.subclase else None
            otras.append(f"**{datos.get('nombre', otra.clase)}** ({otra.nivel} nivel{'es' if otra.nivel > 1 else ''}"
                         + (f", subclase **{sub['nombre']}**" if sub else "") + ")")
        texto_clase += (f" Multiclase: al subir de nivel, elige también {' y '.join(otras)}, hasta llegar a nivel "
                        f"**{ficha.nivel}** en total. De esas clases solo se ganan las competencias de multiclase.")
    texto_clase += " Si Nivel20 la crea a nivel 1, súbela nivel a nivel con estas elecciones:"
    lineas += con_elecciones(texto_clase, "clase")
    base = " · ".join(f"{ABREVIATURAS[c]} {p.caracteristicas_base.get(c, '—')}" for c in CARACTERISTICAS)
    total = " · ".join(f"{ABREVIATURAS[c]} {v.puntuacion}" for c, v in ficha.caracteristicas.items())
    lineas += [f"4. **Características** ({NOMBRES_METODO.get(p.metodo_caracteristicas, p.metodo_caracteristicas)}): "
               f"pon los valores base **{base}**. Nivel20 suma los de la raza; deben quedar {total}."]
    lineas += con_elecciones(f"5. **Trasfondo:** {trasfondo.get('nombre', '—')}.", "trasfondo")
    personalidad = [f"   - {nombre}: {p.detalles[campo]}" for campo, nombre in (
        ("rasgos_personalidad", "Rasgos de personalidad"), ("ideales", "Ideal"), ("vinculos", "Vínculo"),
        ("defectos", "Defecto")) if p.detalles.get(campo)]
    lineas += [f"6. **Alineamiento y detalles:** {p.detalles.get('alineamiento') or '—'}.", *personalidad]
    pg = "la media" if p.metodo_pg == "media" else "las tiradas: " + ", ".join(
        str(t) for e in p.clases for t in e.tiradas_pg)
    marcar = [t.nombre + (" (con pericia)" if t.pericia else "") for t in ficha.habilidades.values() if t.competente]
    lineas += [f"7. **Puntos de golpe y competencias:** PG por {pg} (deben salir **{ficha.pg_maximos}**). "
               f"Marca: {', '.join(marcar) or 'ninguna habilidad'}."]
    if ficha.competencias.get("herramientas"):
        lineas.append(f"   - Herramientas: {', '.join(ficha.competencias['herramientas'])} (la concreta, no la genérica).")
    idiomas = [_nombre_nivel20(i) for i in ficha.competencias.get("idiomas", [])]
    lineas.append(f"   - Idiomas: {', '.join(idiomas)}.")
    dinero = ", ".join(f"{v} {m}" for m, v in ficha.monedas.items() if v)
    lineas.append(f"8. **Equipo:** {', '.join(ficha.equipo) or 'nada'}." + (f" Dinero: {dinero}." if dinero else ""))
    paso = 9
    if ficha.lanzadores:
        for lanzador in ficha.lanzadores:
            trucos = lanzador.conjuros.get(0, [])
            resto = [n for nivel in sorted(lanzador.conjuros) if nivel > 0 for n in lanzador.conjuros[nivel]]
            libro = [n for nivel in sorted(lanzador.libro) for n in lanzador.libro[nivel]]
            texto = f"{paso}. **Conjuros de {lanzador.clase}:** trucos {_lista(trucos, True) or '—'}"
            if libro:
                texto += f"; al libro: {_lista(libro, True)}; **marca como preparados** {_lista(resto, True) or '—'}."
            else:
                texto += f"; {_lista(resto, True) or '—'} (si son preparados, **márcalos como preparados**)."
            lineas.append(texto)
        paso += 1
    salvaciones = ", ".join(f"{ABREVIATURAS[c]} {_signo(t.valor)}" for c, t in ficha.salvaciones.items())
    lineas.append(f"{paso}. **Comprueba al final:** PG {ficha.pg_maximos}, CA {ficha.ca}, iniciativa "
                  f"{_signo(ficha.iniciativa)}, salvaciones {salvaciones}, pasivas {ficha.pasivas['percepcion']}/"
                  f"{ficha.pasivas['perspicacia']}/{ficha.pasivas['investigacion']}"
                  + "".join(f", CD de conjuros {lz.cd}" for lz in ficha.lanzadores) + ".")
    lineas += ["", "> [!warning] Ojo en Nivel20",
               "> - No elijas objetos ni conjuros marcados «(2024)»: la campaña es de 2014.",
               "> - El abisal aparece como «Demoníaco».",
               "> - Si el trasfondo da «herramientas de artesano» o un instrumento, marca solo el elegido.",
               "> - Los conjuros preparados hay que marcarlos; si no, no salen en la hoja."]
    if ficha.entrenamiento:
        lineas += ["", "> [!note] Entrenamiento pendiente (Guía del DM, p. 131)",
                   *(f"> - Nivel {e['nivel']}: {e['dias']} días y {e['coste_po']} po" for e in ficha.entrenamiento)]
    if ficha.avisos:
        lineas += ["", "> [!question] Revisar antes de jugar", *(f"> - {aviso}" for aviso in ficha.avisos)]
    return lineas


def nota_obsidian(a: Asistente5e) -> str:
    """La nota completa: propiedades, resumen, disparadores, ficha de Nivel20, equipo y guía."""
    ficha = a.ficha()
    p = a.personaje
    nombre = ficha.nombre or "Personaje sin nombre"
    resumen = " · ".join(x for x in (ficha.raza, ficha.clase_y_nivel, ficha.trasfondo) if x) + "."
    descripcion = [p.detalles[c] for c in ("apariencia", "historia") if p.detalles.get(c)]
    fisico = ", ".join(f"{n} {p.detalles[c]}" for c, n in (("edad", "edad"), ("altura", "altura"), ("peso", "peso"),
                                                         ("ojos", "ojos"), ("piel", "piel"), ("pelo", "pelo"))
                       if p.detalles.get(c))
    lineas = [*_propiedades(a, ficha), f"# {nombre}",
              "%% hp = PG máximos, ac = CA, modifier = iniciativa. Las pasivas son 10 + el modificador de la habilidad. "
              "Generada por el creador de personajes. %%", "", "## Resumen", resumen]
    if fisico:
        lineas.append(fisico[0].upper() + fisico[1:] + ".")
    lineas += descripcion
    lineas += ["", "## Disparadores de inspiración"]
    for campo, etiqueta in (("rasgos_personalidad", "Rasgo"), ("ideales", "Ideal"), ("vinculos", "Vínculo"),
                            ("defectos", "Defecto")):
        lineas.append(f"- **{etiqueta}:** {p.detalles.get(campo, '')}".rstrip())
    lineas += ["", "## Objetivo personal (cierre de trasfondo)", "", "## Ganchos en el mundo", ""]
    lineas += _ficha_nivel20(a, ficha)
    lineas += ["", "## Equipo", *(f"- {objeto}" for objeto in ficha.equipo)]
    dinero = ", ".join(f"{v} {m}" for m, v in ficha.monedas.items() if v)
    if dinero:
        lineas.append(f"- Dinero: {dinero}")
    lineas += ["", *_guia(a, ficha), "", "## Historial", ""]
    return "\n".join(lineas)
