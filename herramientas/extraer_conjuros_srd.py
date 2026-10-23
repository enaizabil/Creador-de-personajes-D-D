"""Extrae del SRD 5.1 en español los datos de los conjuros de unos niveles (para escribir los paquetes).

    python herramientas/extraer_conjuros_srd.py 4 9 > conjuros.json

Saca nombre, nivel, escuela, ritual, tiempo, alcance (en pies), componentes, duración, concentración, listas de
clase, página y el texto de la descripción (con las distancias en pies). El «resumen» de cada conjuro se escribe
a mano a partir de ese texto. Las listas se leen de las dos extracciones del PDF; si no coinciden, el conjuro
lleva «listas_dudosas» para revisarlo.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verificar_srd as v  # noqa: E402

PAGINA = re.compile(r"^=== Página (\d+) ===")
RUIDO_DESCRIPCION = re.compile(r"^(=== Página|Documento de referencia|Prohibida la reventa|o fotocopiar)")
METROS = re.compile(r"(\d+(?:[.,]\d+)?) (m|km)\b")


def a_pies(texto: str) -> str:
    """«36 m» -> «120 pies», «1,5 m» -> «5 pies», «1,5 km» -> «1 milla» (1,5 m = 5 pies, 1,5 km = 1 milla)."""
    def cambio(m: re.Match) -> str:
        numero = m.group(1)
        # «1.500» es separador de miles; «1,5», decimal.
        valor = float(numero.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", numero) else numero.replace(",", "."))
        if m.group(2) == "km":
            millas = round(valor / 1.5, 2)
            texto_millas = f"{millas:g}".replace(".", ",")
            return f"{texto_millas} milla" + ("" if millas == 1 else "s")
        return f"{round(valor / 1.5 * 5)} pies"
    return METROS.sub(cambio, texto)


def ident(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", v.norma(nombre)).strip("_")


def extraer(minimo: int, maximo: int) -> list[dict]:
    texto = v.TEXTO
    srd = v.conjuros_del_srd()
    listas, alternativas = v.listas_del_srd(srd), v.listas_del_srd(srd, v.TEXTO_ALTERNATIVO)
    cabeceras = [i for i, linea in enumerate(texto) if v.PATRON_CABECERA.match(linea.strip())]
    resultado = []
    for n, i in enumerate(cabeceras):
        m = v.PATRON_CABECERA.match(texto[i].strip())
        nivel = int(m.group(2) or 0)
        if not minimo <= nivel <= maximo:
            continue
        j = i - 1
        while j > 0 and (not texto[j].strip() or v.RUIDO.match(texto[j].strip())):
            j -= 1
        nombre = texto[j].strip()
        pagina = next((int(p.group(1)) for k in range(i, 0, -1) if (p := PAGINA.match(texto[k]))), None)
        # Campos hasta «Duración:», que puede ocupar más de una línea igual que «Componentes:».
        campos, actual, k = {}, None, i + 1
        while k < len(texto):
            linea = texto[k].strip()
            k += 1
            if not linea or RUIDO_DESCRIPCION.match(linea):
                continue
            etiqueta = re.match(r"^(Tiempo de lanzamiento|Alcance|Componentes|Duración):\s*(.*)$", linea)
            if etiqueta:
                actual = etiqueta.group(1)
                campos[actual] = etiqueta.group(2)
            elif actual and actual != "Duración":
                campos[actual] += " " + linea
            else:
                k -= 1
                break
            if actual == "Duración":
                break
        # Descripción: hasta el nombre del conjuro siguiente (la línea anterior a su cabecera).
        fin = len(texto)
        if n + 1 < len(cabeceras):
            fin = cabeceras[n + 1] - 1
            while fin > k and (not texto[fin].strip() or v.RUIDO.match(texto[fin].strip())):
                fin -= 1
        lineas = [texto[x].strip() for x in range(k, fin) if texto[x].strip() and not RUIDO_DESCRIPCION.match(texto[x].strip())]
        duracion = campos.get("Duración", "").strip()
        clave = v.norma(nombre)
        seguras = listas.get(clave, set()) & alternativas.get(clave, set())
        posibles = listas.get(clave, set()) | alternativas.get(clave, set())
        conjuro = {
            "id": ident(nombre), "nombre": nombre, "nivel": nivel, "escuela": v.ESCUELAS[m.group(1).lower()],
            "listas": sorted(posibles), "tiempo": campos.get("Tiempo de lanzamiento", "").strip(),
            "alcance": a_pies(campos.get("Alcance", "").strip()), "componentes": campos.get("Componentes", "").strip(),
            "duracion": duracion, "ritual": bool(m.group(3)), "concentracion": duracion.lower().startswith("concentración"),
            "fuente": f"SRD 5.1 p. {pagina}", "texto": a_pies(" ".join(lineas)),
        }
        if seguras != posibles:
            conjuro["listas_dudosas"] = {"seguras": sorted(seguras), "posibles": sorted(posibles)}
        resultado.append(conjuro)
    return resultado


if __name__ == "__main__":
    minimo, maximo = (int(x) for x in sys.argv[1:3]) if len(sys.argv) >= 3 else (4, 9)
    json.dump(extraer(minimo, maximo), sys.stdout, ensure_ascii=False, indent=1)
