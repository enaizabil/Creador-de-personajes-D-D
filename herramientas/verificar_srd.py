"""Contrasta el paquete srd-5.1 con el texto oficial del SRD 5.1 en español.

Comprueba, de forma independiente a quien escribió los datos:
- conjuros de nivel 0 a 3: nombre, nivel, escuela, ritual y listas de clase;
- armas: daño, tipo de daño, categoría (sencilla o marcial) y tipo (cuerpo a cuerpo o distancia);
- armaduras: CA base, tipo y límite de DES.

Uso: python herramientas/verificar_srd.py   (sale con código 1 si hay discrepancias)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from creador.nucleo.texto import clave_alfabetica  # noqa: E402

TEXTO = (RAIZ / "fuentes" / "SRD_5.1_ES_pypdf.txt").read_text(encoding="utf-8").splitlines()
PAQUETE = RAIZ / "creador" / "datos" / "paquetes" / "dnd5e-2014" / "srd-5.1"
NIVEL_MAXIMO_CONJURO = 3

ESCUELAS = {"abjuración": "abjuracion", "adivinación": "adivinacion", "conjuración": "conjuracion",
            "encantamiento": "encantamiento", "evocación": "evocacion", "ilusionismo": "ilusion",
            "nigromancia": "nigromancia", "transmutación": "transmutacion"}
CLASES = {"bardo": "bardo", "brujo": "brujo", "clérigo": "clerigo", "druida": "druida", "explorador": "explorador",
          "hechicero": "hechicero", "mago": "mago", "paladín": "paladin"}
RUIDO = re.compile(r"^(=== Página|Prohibida la reventa|o fotocopiar|Documento de referencia|Nivel \d"
                   r"|Trucos \(nivel 0\)|Listas de conjuros)")


def norma(texto: str) -> str:
    return clave_alfabetica(texto.strip())


def cargar_datos() -> dict[str, list[dict]]:
    datos: dict[str, list[dict]] = {}
    for archivo in sorted(PAQUETE.glob("*.json")):
        if archivo.name == "paquete.json":
            continue
        for categoria, entradas in json.loads(archivo.read_text(encoding="utf-8")).items():
            datos.setdefault(categoria, []).extend(entradas)
    return datos


PATRON_CABECERA = re.compile(r"^(" + "|".join(ESCUELAS) + r")(?: nivel ([1-9])| \(truco\))( \(ritual\))?$", re.IGNORECASE)


def conjuros_del_srd() -> dict[str, dict]:
    """Nombre normalizado -> {nombre, nivel, escuela, ritual} a partir de las descripciones."""
    conjuros = {}
    for i, linea in enumerate(TEXTO):
        m = PATRON_CABECERA.match(linea.strip())
        if not m:
            continue
        j = i - 1
        while j > 0 and (not TEXTO[j].strip() or RUIDO.match(TEXTO[j].strip())):
            j -= 1
        nombre = TEXTO[j].strip()
        conjuros[norma(nombre)] = {"nombre": nombre, "nivel": int(m.group(2) or 0),
                                   "escuela": ESCUELAS[m.group(1).lower()], "ritual": bool(m.group(3))}
    return conjuros


def listas_del_srd(conocidos: dict[str, dict]) -> dict[str, set[str]]:
    """Nombre normalizado -> clases, leyendo las secciones «Conjuros de <clase>» hasta la primera descripción."""
    inicio = next(i for i, linea in enumerate(TEXTO) if linea.strip() == "Conjuros de bardo")
    clase, listas, ultimo = None, {}, None
    for linea in TEXTO[inicio:]:
        texto = linea.strip()
        if PATRON_CABECERA.match(texto):
            # Empiezan las descripciones: la línea anterior era el nombre del primer conjuro, no parte de la lista.
            if ultimo is not None:
                listas[ultimo[0]].discard(ultimo[1])
            break
        cabecera = re.match(r"^Conjuros de (\w+)$", texto)
        if cabecera and cabecera.group(1).lower() in CLASES:
            clase = CLASES[cabecera.group(1).lower()]
            continue
        if not texto or RUIDO.match(texto):
            continue
        clave = norma(texto)
        if clave in conocidos:
            ultimo = None if clase in listas.get(clave, set()) else (clave, clase)
            listas.setdefault(clave, set()).add(clase)
    return listas


def verificar_conjuros(datos: dict) -> list[str]:
    srd = conjuros_del_srd()
    listas = listas_del_srd(srd)
    nuestros = {norma(c["nombre"]): c for c in datos.get("conjuros", [])}
    problemas = []
    for clave, ref in sorted(srd.items()):
        if ref["nivel"] > NIVEL_MAXIMO_CONJURO:
            continue
        propio = nuestros.get(clave)
        if propio is None:
            problemas.append(f"Falta el conjuro del SRD «{ref['nombre']}» (nivel {ref['nivel']})")
            continue
        for campo in ("nivel", "escuela"):
            if propio.get(campo) != ref[campo]:
                problemas.append(f"{ref['nombre']}: {campo} {propio.get(campo)!r}, en el SRD {ref[campo]!r}")
        if bool(propio.get("ritual")) != ref["ritual"]:
            problemas.append(f"{ref['nombre']}: ritual {propio.get('ritual')!r}, en el SRD {ref['ritual']!r}")
        esperadas = listas.get(clave, set())
        if set(propio.get("listas", [])) != esperadas:
            problemas.append(f"{ref['nombre']}: listas {sorted(propio.get('listas', []))}, en el SRD {sorted(esperadas)}")
    for clave, propio in sorted(nuestros.items()):
        if clave not in srd:
            problemas.append(f"«{propio['nombre']}» está en srd-5.1 pero no es un conjuro del SRD "
                             "(¿nombre distinto o es del PHB?)")
    return problemas


PROPIEDADES = {"a dos manos": "a_dos_manos", "arrojadiz": "arrojadiza", "especial": "especial",
               "gran alcance": "gran_alcance", "liger": "ligera", "municion": "municion", "pesad": "pesada",
               "recarga": "recarga", "sutil": "sutil", "versatil": "versatil"}


def _pies(metros: str) -> str:
    """«6/18» (metros) -> «20/60» (pies), con 1,5 m = 5 pies."""
    return "/".join(str(round(float(m.replace(",", ".")) / 1.5 * 5)) for m in metros.split("/"))


def _filas(cabecera: str, grupos: dict[str, object]) -> list[tuple[str, object]]:
    """Filas de una tabla del SRD (texto de pypdf). Las filas van sangradas; una línea en minúscula continúa
    la fila anterior; la tabla acaba con la primera línea sin sangrar que no es cabecera, grupo ni ruido."""
    inicio = next(i for i, linea in enumerate(TEXTO) if linea.strip().startswith(cabecera))
    filas, grupo = [], None
    for linea in TEXTO[inicio + 1:]:
        texto = linea.strip()
        if not texto or RUIDO.match(texto) or texto.startswith(cabecera):
            continue
        if texto in grupos:
            grupo = grupos[texto]
        elif linea.startswith(" ") and grupo is not None:
            filas.append([texto, grupo])
        elif filas and texto[0].islower():
            filas[-1][0] += " " + texto
        else:
            break
    return [tuple(f) for f in filas]


def verificar_armas(datos: dict) -> list[str]:
    grupos = {"Armas cuerpo a cuerpo sencillas": ("sencilla", "cuerpo_a_cuerpo"),
              "Armas a distancia sencillas": ("sencilla", "distancia"),
              "Armas cuerpo a cuerpo marciales": ("marcial", "cuerpo_a_cuerpo"),
              "Armas a distancia marciales": ("marcial", "distancia")}
    fila_re = re.compile(r"^(?P<nombre>.+?) (?P<precio>\d+ p[cpeo]) (?P<dano>\d+d\d+ \w+|\d+ \w+|—)"
                         r" (?P<peso>[\d,]+ k?g|—) +(?P<props>.*)$")
    nuestras = {norma(o["nombre"]): o for o in datos.get("objetos", []) if o.get("categoria") == "arma"}
    problemas, vistas = [], 0
    for fila, (categoria, tipo) in _filas("Nombre Precio Daño Peso Propiedades", grupos):
        m = fila_re.match(fila)
        if not m:
            problemas.append(f"(no se pudo leer la fila del SRD: {fila})")
            continue
        vistas += 1
        nombre = m["nombre"]
        propia = nuestras.get(norma(nombre))
        if propia is None:
            problemas.append(f"Falta el arma «{nombre}»")
            continue
        arma = propia.get("arma", {})
        esperado = {"categoria": categoria, "tipo": tipo}
        if m["dano"] != "—":
            esperado["dano"], esperado["tipo_dano"] = m["dano"].split(" ")
        props_texto = norma(m["props"])
        propiedades = {id_ for clave, id_ in PROPIEDADES.items() if clave in props_texto}
        alcance = re.search(r"alcance ([\d,]+/[\d,]+)", props_texto)
        if alcance:
            esperado["alcance"] = _pies(alcance.group(1))
        versatil = re.search(r"versatil \((\d+d\d+)\)", props_texto)
        if versatil:
            esperado["dano_versatil"] = versatil.group(1)
        for campo, valor in esperado.items():
            if arma.get(campo) != valor:
                problemas.append(f"{nombre}: {campo} {arma.get(campo)!r}, en el SRD {valor!r}")
        if set(arma.get("propiedades", [])) != propiedades:
            problemas.append(f"{nombre}: propiedades {sorted(arma.get('propiedades', []))}, en el SRD {sorted(propiedades)}")
    if vistas < 37:
        problemas.append(f"(solo se leyeron {vistas} filas de armas del SRD)")
    return problemas


def verificar_armaduras(datos: dict) -> list[str]:
    grupos = {"Armaduras ligeras": "ligera", "Armaduras medias": "media", "Armaduras pesadas": "pesada", "Escudos": "escudo"}
    fila_re = re.compile(r"^(?P<nombre>.+?) (?P<precio>\d+ p[cpeo]) +(?P<ca>\+?\d+)(?: \+ modificador por Des(?: \(máx\. 2\))?)?"
                         r" (?P<fue>Fue \d+|—) (?P<sigilo>Desventaja|—)")
    nuestras = {norma(o["nombre"]): o for o in datos.get("objetos", []) if o.get("categoria") in ("armadura", "escudo")}
    problemas = []
    for fila, tipo in _filas("Armadura Precio", grupos):
        m = fila_re.match(fila)
        if not m:
            problemas.append(f"(no se pudo leer la fila del SRD: {fila})")
            continue
        nombre, base = m["nombre"], int(m["ca"].lstrip("+"))
        propia = nuestras.get(norma(nombre))
        if propia is None:
            problemas.append(f"Falta «{nombre}»")
            continue
        if tipo == "escudo":
            if propia.get("escudo", {}).get("bonificador") != base:
                problemas.append(f"{nombre}: bonificador {propia.get('escudo')}, en el SRD +{base}")
            continue
        armadura = propia.get("armadura", {})
        esperado = {"tipo": tipo, "ca": base, "fuerza_minima": int(m["fue"].split()[1]) if m["fue"] != "—" else None,
                    "desventaja_sigilo": m["sigilo"] == "Desventaja"}
        actual = {"tipo": armadura.get("tipo"), "ca": armadura.get("ca"), "fuerza_minima": armadura.get("fuerza_minima"),
                  "desventaja_sigilo": bool(armadura.get("desventaja_sigilo"))}
        for campo, valor in esperado.items():
            if actual[campo] != valor:
                problemas.append(f"{nombre}: {campo} {actual[campo]!r}, en el SRD {valor!r}")
        if tipo == "media" and armadura.get("max_des", 2) != 2:
            problemas.append(f"{nombre}: max_des {armadura.get('max_des')}, en el SRD 2")
    return problemas


def main() -> int:
    datos = cargar_datos()
    secciones = {"Conjuros (niveles 0-3)": verificar_conjuros, "Armas": verificar_armas, "Armaduras": verificar_armaduras}
    total = 0
    for titulo, funcion in secciones.items():
        problemas = funcion(datos)
        total += len(problemas)
        print(f"## {titulo}: {len(problemas)} discrepancias")
        for problema in problemas:
            print(f"- {problema}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
