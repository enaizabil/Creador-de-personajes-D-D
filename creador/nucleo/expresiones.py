"""Expresiones aritméticas seguras para los textos de los paquetes.

Permiten que un rasgo diga «reserva de {nivel_clase*5} PG» o que sus usos sean
``"max(1, mod_car)"`` sin ejecutar código arbitrario: solo números, variables
del contexto, + - * // y las funciones max, min y abs.
"""
from __future__ import annotations

import ast
import re

FUNCIONES = {"max": max, "min": min, "abs": abs}
_OPERADORES = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
               ast.Mult: lambda a, b: a * b, ast.FloorDiv: lambda a, b: a // b}
_HUECO = re.compile(r"\{([^{}]+)\}")


class ErrorExpresion(ValueError):
    pass


def evaluar(expresion: str, contexto: dict[str, int | str]) -> int | str:
    try:
        arbol = ast.parse(expresion.strip(), mode="eval")
    except SyntaxError as exc:
        raise ErrorExpresion(f"expresión mal formada «{expresion}»") from exc
    return _evaluar(arbol.body, contexto, expresion)


def _evaluar(nodo: ast.AST, contexto: dict, texto: str):
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, int) and not isinstance(nodo.value, bool):
        return nodo.value
    if isinstance(nodo, ast.Name):
        if nodo.id not in contexto:
            raise ErrorExpresion(f"variable desconocida «{nodo.id}» en «{texto}»")
        return contexto[nodo.id]
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.left, contexto, texto), _evaluar(nodo.right, contexto, texto))
    if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, ast.USub):
        return -_evaluar(nodo.operand, contexto, texto)
    if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in FUNCIONES
            and not nodo.keywords):
        return FUNCIONES[nodo.func.id](*(_evaluar(a, contexto, texto) for a in nodo.args))
    raise ErrorExpresion(f"operación no permitida en «{texto}»")


def rellenar(plantilla: str, contexto: dict[str, int | str]) -> str:
    """Sustituye cada ``{expresión}`` del texto por su valor."""
    return _HUECO.sub(lambda m: str(evaluar(m.group(1), contexto)), plantilla)


def comprobar(plantilla: str, variables: set[str], es_expresion: bool = False) -> list[str]:
    """Errores de una plantilla (o expresión) usando valores de prueba para las variables."""
    contexto = {v: 1 for v in variables}
    try:
        if es_expresion:
            evaluar(plantilla, contexto)
        else:
            rellenar(plantilla, contexto)
    except ErrorExpresion as exc:
        return [str(exc)]
    except TypeError:
        return [f"tipos incompatibles en «{plantilla}»"]
    return []
