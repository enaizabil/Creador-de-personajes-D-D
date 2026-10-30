"""Componentes de las pantallas web: diccionarios que la página sabe pintar (campo «t», el tipo).

Las acciones se piden con «accion» y «args»; la página añade lo que el usuario elige: «valor» (interruptor, menú,
segmentado, entrada), «valores» (elección), «id» y «marcada» (casillas), «respuesta» (respuestas), «nombre» y
«datos» (archivo, en base64).
"""
from __future__ import annotations


def titulo(texto: str, nivel: int = 2, icono: str | None = None) -> dict:
    return {"t": "titulo", "texto": texto, "nivel": nivel, "icono": icono}


def texto(contenido: str, estilo: str = "") -> dict:
    """Estilos: «gris», «grande», «pequeno», «negrita», «aviso», «exito»."""
    return {"t": "texto", "texto": contenido, "estilo": estilo}


def fila(*hijos: dict | None) -> dict:
    return {"t": "fila", "hijos": [h for h in hijos if h]}


def caja(*hijos: dict | None, estilo: str = "") -> dict:
    """Recuadro; estilos: «aviso», «exito»."""
    return {"t": "caja", "hijos": [h for h in hijos if h], "estilo": estilo}


def boton(contenido: str, accion: str, args: dict | None = None, estilo: str = "primario", desactivado: bool = False,
          confirmar: str | None = None, icono: str | None = None) -> dict:
    """Estilos: «primario», «secundario», «peligro», «enlace». Con «confirmar», la página pregunta antes."""
    return {"t": "boton", "texto": contenido, "accion": accion, "args": args or {}, "estilo": estilo,
            "desactivado": desactivado, "confirmar": confirmar, "icono": icono}


def interruptor(contenido: str, activo: bool, accion: str, args: dict | None = None, ayuda: str = "") -> dict:
    return {"t": "interruptor", "texto": contenido, "activo": activo, "accion": accion, "args": args or {}, "ayuda": ayuda}


def menu(valores: list[tuple[str, str]], actual: str | None, accion: str, args: dict | None = None,
         etiqueta: str = "", vacio: str | None = None) -> dict:
    """Desplegable; «vacio», el texto de la opción sin valor («— elige —»)."""
    return {"t": "menu", "valores": [list(v) for v in valores], "actual": actual, "accion": accion, "args": args or {},
            "etiqueta": etiqueta, "vacio": vacio}


def segmentado(valores: list[tuple[str, str]], actual: str, accion: str, args: dict | None = None,
               etiqueta: str = "") -> dict:
    return {"t": "segmentado", "valores": [list(v) for v in valores], "actual": actual, "accion": accion,
            "args": args or {}, "etiqueta": etiqueta}


def entrada(valor: str, accion: str, args: dict | None = None, etiqueta: str = "", marcador: str = "",
            multilinea: bool = False, ancho: str = "medio", sugerencias: list[str] | None = None) -> dict:
    """Campo de texto; la página manda el valor al terminar de editar (sin repintar mientras se escribe)."""
    return {"t": "entrada", "valor": valor, "accion": accion, "args": args or {}, "etiqueta": etiqueta,
            "marcador": marcador, "multilinea": multilinea, "ancho": ancho, "sugerencias": sugerencias or []}


def lista_opciones(titulo_lista: str, opciones: list[dict], seleccion: str | None, accion: str, args: dict | None,
                   detalle: dict | None) -> dict:
    """Lista excluyente con el detalle de la elegida: {"nombre", "icono", "origen", "perfil", "descripcion"}."""
    return {"t": "lista_opciones", "titulo": titulo_lista, "opciones": opciones, "seleccion": seleccion,
            "accion": accion, "args": args or {}, "detalle": detalle}


def casillas(opciones: list[dict], accion: str, args: dict | None = None, columnas: int = 3) -> dict:
    """[{"id", "nombre", "marcada", "bloqueada"}]; cada clic manda «id» y «marcada»."""
    return {"t": "casillas", "opciones": opciones, "accion": accion, "args": args or {}, "columnas": columnas}


def avisos(mensajes: list[str], titulo_lista: str = "Falta por decidir", completo: bool = False) -> dict:
    return {"t": "avisos", "titulo": titulo_lista, "mensajes": mensajes, "completo": completo}


def barra(valor: float, etiqueta: str = "") -> dict:
    return {"t": "barra", "valor": max(0.0, min(1.0, valor)), "etiqueta": etiqueta}


def respuestas(opciones: list[dict], accion: str, args: dict | None = None, columnas: int = 1) -> dict:
    """Tarjetas pulsables: [{"id", "texto", "detalle", "propuesta", "elegida"}]; el clic manda «respuesta»."""
    return {"t": "respuestas", "opciones": opciones, "accion": accion, "args": args or {}, "columnas": columnas}


def tabla(cabeceras: list[str], filas: list[list]) -> dict:
    """Cada celda es un texto o un componente."""
    return {"t": "tabla", "cabeceras": cabeceras, "filas": filas}


def columnas(*hijos: dict) -> dict:
    """Bloques en columnas que se apilan en pantallas estrechas."""
    return {"t": "columnas", "hijos": list(hijos)}


def preformateado(contenido: str) -> dict:
    return {"t": "preformateado", "texto": contenido}


def archivo(contenido: str, accion: str, aceptar: str, args: dict | None = None, estilo: str = "secundario") -> dict:
    """Botón que abre un archivo del dispositivo y lo manda (nombre y datos en base64)."""
    return {"t": "archivo", "texto": contenido, "accion": accion, "aceptar": aceptar, "args": args or {}, "estilo": estilo}


def radios(opciones: list[tuple[str, str]], seleccion: str | None, accion: str, args: dict | None = None) -> dict:
    """Opciones excluyentes sin detalle (alternativas de equipo); el clic manda «valor»."""
    return {"t": "radios", "opciones": [list(o) for o in opciones], "seleccion": seleccion, "accion": accion,
            "args": args or {}}
