"""Puntuaciones de característica: modificadores y métodos de generación."""
from __future__ import annotations

import random

from .constantes import ARRAY_ESTANDAR, CARACTERISTICAS, COSTE_COMPRA, PUNTOS_COMPRA


def modificador(puntuacion: int) -> int:
    return puntuacion // 2 - 5


def bonificador_competencia(nivel: int) -> int:
    return (max(1, nivel) - 1) // 4 + 2


def coste_compra(base: dict[str, int]) -> int:
    """Puntos gastados con la compra por puntos. ValueError si alguna puntuación está fuera de 8–15."""
    fuera = [c for c, v in base.items() if v not in COSTE_COMPRA]
    if fuera:
        raise ValueError(f"Con compra por puntos las puntuaciones van de 8 a 15 ({', '.join(fuera)})")
    return sum(COSTE_COMPRA[v] for v in base.values())


def validar_base(metodo: str, base: dict[str, int]) -> list[str]:
    """Avisos sobre las puntuaciones base según el método elegido."""
    faltan = [CARACTERISTICAS[c] for c in CARACTERISTICAS if c not in base]
    if faltan:
        return [f"Faltan puntuaciones base: {', '.join(faltan)}"]
    valores = [base[c] for c in CARACTERISTICAS]

    if metodo == "estandar":
        if sorted(valores, reverse=True) != list(ARRAY_ESTANDAR):
            return [f"Con el array estándar hay que usar exactamente {', '.join(map(str, ARRAY_ESTANDAR))}"]
    elif metodo == "compra":
        try:
            gastados = coste_compra({c: base[c] for c in CARACTERISTICAS})
        except ValueError as exc:
            return [str(exc)]
        if gastados > PUNTOS_COMPRA:
            return [f"La compra por puntos gasta {gastados} de {PUNTOS_COMPRA} puntos"]
        if gastados < PUNTOS_COMPRA:
            return [f"Quedan {PUNTOS_COMPRA - gastados} puntos de compra sin gastar"]
    elif metodo == "tirada":
        if any(not 3 <= v <= 18 for v in valores):
            return ["Las puntuaciones tiradas con 4d6 van de 3 a 18"]
    elif metodo == "manual":
        if any(not 1 <= v <= 30 for v in valores):
            return ["Las puntuaciones van de 1 a 30"]
    else:
        return [f"Método de características desconocido «{metodo}»"]
    return []


def tirar_4d6(rng: random.Random | None = None) -> list[int]:
    """Seis tiradas de 4d6 descartando el dado más bajo, en el orden obtenido."""
    rng = rng or random.Random()
    resultados = []
    for _ in range(6):
        dados = sorted(rng.randint(1, 6) for _ in range(4))
        resultados.append(sum(dados[1:]))
    return resultados


def asignar_por_prioridad(valores: list[int], prioridad: list[str]) -> dict[str, int]:
    """Reparte los valores de mayor a menor siguiendo el orden de características indicado.

    Las características que no aparecen en la prioridad reciben los valores restantes
    en el orden canónico (FUE, DES, CON, INT, SAB, CAR).
    """
    orden = list(dict.fromkeys([*prioridad, *CARACTERISTICAS]))
    desconocidas = [c for c in orden if c not in CARACTERISTICAS]
    if desconocidas:
        raise ValueError(f"Características desconocidas: {', '.join(desconocidas)}")
    if len(valores) != len(CARACTERISTICAS):
        raise ValueError(f"Hacen falta {len(CARACTERISTICAS)} valores")
    return dict(zip(orden, sorted(valores, reverse=True), strict=True))
