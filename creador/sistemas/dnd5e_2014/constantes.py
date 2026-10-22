"""Reglas fijas de D&D 5e (2014) que no dependen de ningún paquete de contenido."""

CARACTERISTICAS = {
    "fue": "Fuerza",
    "des": "Destreza",
    "con": "Constitución",
    "int": "Inteligencia",
    "sab": "Sabiduría",
    "car": "Carisma",
}

# id: (nombre, característica). Nombres según el SRD 5.1 oficial en español.
HABILIDADES = {
    "acrobacias": ("Acrobacias", "des"),
    "atletismo": ("Atletismo", "fue"),
    "conocimiento_arcano": ("Conocimiento Arcano", "int"),
    "engano": ("Engaño", "car"),
    "historia": ("Historia", "int"),
    "interpretacion": ("Interpretación", "car"),
    "intimidacion": ("Intimidación", "car"),
    "investigacion": ("Investigación", "int"),
    "juego_de_manos": ("Juego de Manos", "des"),
    "medicina": ("Medicina", "sab"),
    "naturaleza": ("Naturaleza", "int"),
    "percepcion": ("Percepción", "sab"),
    "perspicacia": ("Perspicacia", "sab"),
    "persuasion": ("Persuasión", "car"),
    "religion": ("Religión", "int"),
    "sigilo": ("Sigilo", "des"),
    "supervivencia": ("Supervivencia", "sab"),
    "trato_con_animales": ("Trato con Animales", "sab"),
}

# Grupos usados en competencias de armas y armaduras.
GRUPOS_COMPETENCIA = {
    "armaduras_ligeras": "Armaduras ligeras",
    "armaduras_medias": "Armaduras medias",
    "armaduras_pesadas": "Armaduras pesadas",
    "escudos": "Escudos",
    "armas_sencillas": "Armas sencillas",
    "armas_marciales": "Armas marciales",
}
GRUPO_ARMADURA = {"ligera": "armaduras_ligeras", "media": "armaduras_medias", "pesada": "armaduras_pesadas"}
GRUPO_ARMA = {"sencilla": "armas_sencillas", "marcial": "armas_marciales"}

CATEGORIAS_COMPETENCIA = ("habilidad", "salvacion", "arma", "armadura", "herramienta", "idioma")

# Habilidades con valor pasivo en la ficha (10 + bonificador).
PASIVAS = ("percepcion", "perspicacia", "investigacion")

RECARGAS = {"corto": "descanso corto o largo", "largo": "descanso largo"}

# Rasgos de perfil para el cuestionario del modo sencillo. Razas, subrazas, clases,
# subclases y trasfondos declaran un "perfil" {rasgo: 0-3}; las respuestas suman a
# estos rasgos y se recomienda lo cargado que mejor encaja.
RASGOS_PERFIL = {
    "combate": "Pelear cuerpo a cuerpo, la fuerza física",
    "agilidad": "Rapidez, puntería, reflejos",
    "aguante": "Resistir golpes, cansancio y penurias",
    "proteccion": "Defender a otros, ponerse delante",
    "sigilo": "Pasar desapercibido, esconderse",
    "astucia": "Engaños, trucos, picardía",
    "carisma": "Hablar, convencer, liderar, actuar",
    "saber": "Estudiar, investigar, recordar",
    "naturaleza": "Vida salvaje, animales, viajes por tierras agrestes",
    "fe": "Devoción, dioses, juramentos",
    "arcano": "Magia estudiada o innata, lo sobrenatural",
    "curacion": "Cuidar, sanar, ayudar",
}
VALOR_MAXIMO_PERFIL = 3

TAMANOS = {
    "diminuto": "Diminuto",
    "pequeno": "Pequeño",
    "mediano": "Mediano",
    "grande": "Grande",
    "enorme": "Enorme",
    "gargantuesco": "Gargantuesco",
}

ESCUELAS_MAGIA = {
    "abjuracion": "Abjuración",
    "adivinacion": "Adivinación",
    "conjuracion": "Conjuración",
    "encantamiento": "Encantamiento",
    "evocacion": "Evocación",
    "ilusion": "Ilusionismo",
    "nigromancia": "Nigromancia",
    "transmutacion": "Transmutación",
}

CATEGORIAS_OBJETO = ("arma", "armadura", "escudo", "herramienta", "municion", "foco", "equipo", "montura", "vehiculo")

# Condiciones que pueden restringir un efecto (campo «condicion»).
CONDICIONES = ("sin_armadura", "con_armadura", "sin_armadura_pesada", "sin_escudo", "con_escudo")

ARRAY_ESTANDAR = (15, 14, 13, 12, 10, 8)
PUNTOS_COMPRA = 27
COSTE_COMPRA = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
PUNTUACION_MAXIMA = 20
NIVEL_MAXIMO = 20

EXPERIENCIA_POR_NIVEL = (
    0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
    85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000,
)

# Espacios de conjuro de un lanzador completo (también la tabla de multiclase).
ESPACIOS_LANZADOR_COMPLETO = {
    1: (2,),
    2: (3,),
    3: (4, 2),
    4: (4, 3),
    5: (4, 3, 2),
    6: (4, 3, 3),
    7: (4, 3, 3, 1),
    8: (4, 3, 3, 2),
    9: (4, 3, 3, 3, 1),
    10: (4, 3, 3, 3, 2),
    11: (4, 3, 3, 3, 2, 1),
    12: (4, 3, 3, 3, 2, 1),
    13: (4, 3, 3, 3, 2, 1, 1),
    14: (4, 3, 3, 3, 2, 1, 1),
    15: (4, 3, 3, 3, 2, 1, 1, 1),
    16: (4, 3, 3, 3, 2, 1, 1, 1),
    17: (4, 3, 3, 3, 2, 1, 1, 1, 1),
    18: (4, 3, 3, 3, 3, 1, 1, 1, 1),
    19: (4, 3, 3, 3, 3, 2, 1, 1, 1),
    20: (4, 3, 3, 3, 3, 2, 2, 1, 1),
}

# Magia de pacto: nivel de brujo -> (espacios, nivel de los espacios)
MAGIA_DE_PACTO = {
    1: (1, 1), 2: (2, 1), 3: (2, 2), 4: (2, 2), 5: (2, 3),
    6: (2, 3), 7: (2, 4), 8: (2, 4), 9: (2, 5), 10: (2, 5),
    11: (3, 5), 12: (3, 5), 13: (3, 5), 14: (3, 5), 15: (3, 5),
    16: (3, 5), 17: (4, 5), 18: (4, 5), 19: (4, 5), 20: (4, 5),
}

# Progresión -> divisor del nivel de clase. Un lanzador de una sola clase usa
# el nivel redondeado hacia arriba en la tabla completa; en multiclase se suma
# redondeando hacia abajo (salvo que la clase indique «redondeo_multiclase»).
PROGRESIONES_LANZAMIENTO = {"completo": 1, "medio": 2, "tercio": 3}
NIVEL_INICIO_PROGRESION = {"completo": 1, "medio": 2, "tercio": 3, "pacto": 1}
