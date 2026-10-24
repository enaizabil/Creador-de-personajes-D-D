"""Ficha de 5e (2014) en texto legible, para la interfaz y la línea de órdenes."""
from __future__ import annotations

from .constantes import CARACTERISTICAS, RECARGAS
from .ficha import Ficha

ABREVIATURAS = {"fue": "FUE", "des": "DES", "con": "CON", "int": "INT", "sab": "SAB", "car": "CAR"}
MODOS_VELOCIDAD = {"caminar": "", "nadar": "nadando ", "trepar": "trepando ", "volar": "volando "}


def _signo(valor: int) -> str:
    return f"{valor:+d}"


def _velocidades(ficha: Ficha) -> str:
    return ", ".join(f"{MODOS_VELOCIDAD.get(modo, modo + ' ')}{pies} pies" for modo, pies in ficha.velocidades.items())


def resumen_ficha(ficha: Ficha) -> str:
    lineas = [
        ficha.nombre or "(sin nombre)",
        " · ".join(p for p in (ficha.raza, ficha.clase_y_nivel, ficha.trasfondo,
                               ficha.detalles.get("alineamiento", "")) if p),
        "",
        f"PG {ficha.pg_maximos} · CA {ficha.ca} · Iniciativa {_signo(ficha.iniciativa)} · "
        f"Velocidad {_velocidades(ficha)} · Competencia {_signo(ficha.bonificador_competencia)}",
        "Dados de golpe: " + " + ".join(f"{n}{dado}" for dado, n in ficha.dados_golpe.items()),
        "",
        "  ".join(f"{ABREVIATURAS[c]} {v.puntuacion} ({_signo(v.modificador)})" for c, v in ficha.caracteristicas.items()),
        "Salvaciones: " + ", ".join(f"{ABREVIATURAS[c]} {_signo(t.valor)}{'*' if t.competente else ''}"
                                    for c, t in ficha.salvaciones.items()),
    ]
    competentes = [f"{t.nombre} {_signo(t.valor)}{' (pericia)' if t.pericia else ''}"
                   for t in ficha.habilidades.values() if t.competente]
    lineas.append("Habilidades con competencia: " + (", ".join(competentes) or "ninguna"))
    lineas.append(f"Pasivas: Percepción {ficha.pasivas['percepcion']}, Perspicacia {ficha.pasivas['perspicacia']}, "
                  f"Investigación {ficha.pasivas['investigacion']}")
    if ficha.sentidos:
        lineas.append("Sentidos: " + ", ".join(f"{n} {a} pies" for n, a in ficha.sentidos.items()))
    if ficha.resistencias:
        lineas.append("Resistencias: " + ", ".join(ficha.resistencias))
    for titulo, clave in (("Armaduras", "armaduras"), ("Armas", "armas"), ("Herramientas", "herramientas"),
                          ("Idiomas", "idiomas")):
        if ficha.competencias.get(clave):
            lineas.append(f"{titulo}: {', '.join(ficha.competencias[clave])}")

    if ficha.ataques:
        lineas += ["", "ATAQUES"]
        for ataque in ficha.ataques:
            notas = f" ({ataque.notas})" if ataque.notas else ""
            tipo = f" {ataque.tipo_dano}" if ataque.tipo_dano else ""
            lineas.append(f"- {ataque.nombre}: {_signo(ataque.bonificador)}, {ataque.dano}{tipo}{notas}")

    if ficha.lanzadores or ficha.conjuros_innatos:
        lineas += ["", "MAGIA"]
        for lanzador in ficha.lanzadores:
            lineas.append(f"{lanzador.clase} ({CARACTERISTICAS[lanzador.caracteristica]}): CD {lanzador.cd}, "
                          f"ataque {_signo(lanzador.ataque)}")
            for nivel in sorted({*lanzador.conjuros, *lanzador.siempre_preparados}):
                titulo = "Trucos" if nivel == 0 else f"Nivel {nivel}" + (" (preparados)" if lanzador.libro else "")
                siempre = [f"{n} (siempre)" for n in lanzador.siempre_preparados.get(nivel, [])]
                nombres = lanzador.conjuros.get(nivel, []) + siempre
                lineas.append(f"  {titulo}: {', '.join(nombres)}")
            if lanzador.libro:
                lineas.append("  Libro de conjuros: " + "; ".join(
                    f"nivel {nivel}: {', '.join(nombres)}" for nivel, nombres in sorted(lanzador.libro.items())))
        if ficha.espacios_conjuro:
            lineas.append("Espacios: " + ", ".join(f"nivel {n}: {e}" for n, e in ficha.espacios_conjuro.items()))
        if ficha.magia_pacto:
            lineas.append(f"Magia de pacto: {ficha.magia_pacto['espacios']} espacios de nivel {ficha.magia_pacto['nivel']}")
        if ficha.conjuros_innatos:
            lineas.append("Conjuros innatos: " + ", ".join(ficha.conjuros_innatos))

    if ficha.rasgos:
        lineas += ["", "RASGOS"]
        for rasgo in ficha.rasgos:
            usos = ""
            if rasgo.usos is not None:
                usos = f" [{rasgo.usos} por {RECARGAS.get(rasgo.recarga, 'día')}]"
            detalle = f": {rasgo.resumen}" if rasgo.resumen else ""
            lineas.append(f"- {rasgo.nombre}{usos}{detalle}")

    if ficha.equipo or ficha.monedas:
        lineas += ["", "EQUIPO"]
        if ficha.equipo:
            lineas.append(", ".join(ficha.equipo))
        if ficha.monedas:
            lineas.append("Dinero: " + ", ".join(f"{v} {m}" for m, v in ficha.monedas.items() if v))

    if ficha.entrenamiento:
        lineas += ["", "ENTRENAMIENTO PENDIENTE (Guía del DM)"] + [
            f"- Nivel {e['nivel']}: {e['dias']} días y {e['coste_po']} po" for e in ficha.entrenamiento]
    if ficha.avisos:
        lineas += ["", "AVISOS"] + [f"- {a}" for a in ficha.avisos]
    return "\n".join(lineas)
