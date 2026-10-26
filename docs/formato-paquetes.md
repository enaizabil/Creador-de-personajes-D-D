# Formato de paquetes de contenido — D&D 5e (2014)

Un **paquete** es una carpeta con un manifiesto `paquete.json` y uno o más archivos JSON de contenido. Así se añaden el SRD, el PHB, expansiones (Tasha, Xanathar…) o homebrew sin tocar el código.

## 1. Dónde se buscan

En este orden de prioridad (si un `id` de paquete se repite, gana el primero):

1. `creador/datos/paquetes/` — integrados en el ejecutable.
2. `paquetes/` junto al ejecutable (o en la raíz del proyecto al ejecutar desde el código) — modo portable.
3. `~/.creador-personajes/paquetes/` — carpeta del usuario.

Convención: `paquetes/<sistema>/<id-paquete>/paquete.json`.

## 2. Manifiesto (`paquete.json`)

```json
{
  "id": "tasha",
  "nombre": "Caldero de Tasha para todo",
  "sistema": "dnd5e-2014",
  "version": "1.0.0",
  "tipo": "oficial",
  "licencia": "",
  "descripcion": "Subclases y opciones adicionales",
  "depende_de": ["phb"],
  "archivos": ["subclases.json", "dotes.json"]
}
```

| Campo | Obligatorio | Notas |
|---|---|---|
| `id` | sí | Único entre todos los paquetes instalados. |
| `nombre` | sí | Texto visible. |
| `sistema` | sí | `dnd5e-2014`. Un paquete de otro sistema se rechaza. |
| `version` | sí | Libre (se recomienda `x.y.z`). |
| `archivos` | sí | Rutas relativas a la carpeta del paquete. |
| `depende_de` | no | Se cargan antes y se activan automáticamente. |
| `tipo` | no | `oficial` o `homebrew` (por defecto). |

## 3. Archivos de contenido

Cada archivo es un objeto `{"categoria": [entradas]}`. Un archivo puede mezclar categorías.

Categorías: `razas`, `subrazas`, `clases`, `subclases`, `trasfondos`, `dotes`, `opciones`, `conjuros`, `objetos`, `idiomas`.

Cualquier entrada puede llevar `"requiere_reglas": ["dotes"]` (o `"multiclase"`) si solo existe con esa regla opcional del PHB, como el humano variante: si el personaje la tiene desactivada, el motor avisa.

Cualquier entrada puede llevar `"permiso_dm": true` si el libro la presenta como opción que el DM debe autorizar (p. ej. el Rompejuramentos).

Toda entrada necesita `id` (texto, sin espacios, en minúsculas y sin tildes: `enano_colinas`) y `nombre`. Puede llevar `descripcion` y `fuente` (p. ej. `"PHB p. 20"`).

### Añadir, reemplazar o modificar

| Marca | Efecto |
|---|---|
| (ninguna) | Entrada nueva. Si el `id` ya existe en esa categoría → **error**. |
| `"reemplaza": true` | Sustituye por completo la entrada existente. |
| `"modifica": true` | Fusiona con la existente: los objetos se combinan, las listas **se amplían** y los valores sueltos se sobrescriben. |

Ejemplo: un paquete que añade el conjuro *Luz* a la lista del paladín sin redefinirlo:

```json
{"conjuros": [{"id": "luz", "modifica": true, "listas": ["paladin"]}]}
```

## 4. Campos por categoría

### razas
`velocidad` (pies, entero) · `tamano` (`pequeno`, `mediano`…) · `efectos`.

### subrazas
`raza` (id de la raza) · `efectos`.

### clases
| Campo | Notas |
|---|---|
| `dado_golpe` | 6, 8, 10 o 12. |
| `salvaciones` | Ids de característica. Solo las da la clase inicial. |
| `competencias` | Efectos que recibe la **clase inicial** (armaduras, armas, elección de habilidades…). |
| `competencias_multiclase` | Efectos al entrar en la clase por multiclase. |
| `nivel_subclase` | Nivel en que se elige la subclase. |
| `niveles_completos` | Hasta qué nivel están los datos de la clase (por defecto 20). El asistente no deja empezar por encima y la ficha avisa si se supera. |
| `niveles` | `{"1": [efectos], "2": [...], ...}` hasta 20. |
| `lanzamiento` | Ver abajo. |
| `requisitos_multiclase` | Requisito (ver §4.1). Guerrero: `{"alguna_caracteristica": {"fue": 13, "des": 13}}`. |
| `equipo_inicial` | Equipo con alternativas (ver §4.2). |
| `oro_inicial` | Alternativa en oro, como texto: `"5d4x10"`. |

**`lanzamiento`** (también en subclases, p. ej. Caballero Arcano):

```json
{
  "caracteristica": "int",
  "progresion": "completo",
  "trucos_conocidos": [3,3,3,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5],
  "conjuros_conocidos": [ ... 20 valores ... ],
  "preparados": "nivel",
  "libro": {"inicial": 6, "por_nivel": 2},
  "listas": ["mago"],
  "desde_nivel": 1,
  "redondeo_multiclase": "abajo"
}
```

- `progresion`: `completo` (mago, clérigo…), `medio` (paladín, explorador), `tercio` (Caballero Arcano, Embaucador Arcano) o `pacto` (brujo).
- Usa `conjuros_conocidos` (tabla de 20 valores) **o** `preparados`: `nivel` → mod + nivel, o `mitad_nivel` → mod + nivel/2.
- `libro` (mago): los conjuros se eligen para el libro (`inicial` a nivel 1 y `por_nivel` más en cada nivel, siempre de niveles con espacios en ese momento) y los preparados salen del libro. El personaje guarda el libro en `conjuros` y los preparados en `preparados`.
- `listas`: listas de conjuros adicionales a la de la propia clase.
- `desde_nivel` y `redondeo_multiclase` solo hacen falta si difieren del estándar. Ejemplo: el artífice de Tasha es `medio` con `"desde_nivel": 1` y `"redondeo_multiclase": "arriba"` (espacios desde nivel 1 y, en multiclase, la mitad de sus niveles redondeando hacia arriba). Con un solo lanzador `medio` los espacios ya redondean hacia arriba.

### subclases
`clase` (id) · `niveles` · `lanzamiento` opcional · `conjuros_adicionales`: ids de conjuros que pasan a estar en la lista de la clase (lista ampliada del patrón del brujo). Los conjuros de dominio, juramento o círculo se dan con efectos `conjuro` con `clase` y `siempre_preparado` en el nivel que toque. · `niveles_completos`: hasta qué nivel están sus datos (por defecto 20); si el personaje lo supera, el asistente lo marca en el selector («datos hasta nivel 5») y la ficha avisa.

### trasfondos
`efectos` (competencias, idiomas, el rasgo del trasfondo…) · `equipo` (mismo formato que `equipo_inicial`) · `monedas` (`{"po": 15}`) · `personalidad`:

```json
{"rasgos": ["…", "…"], "ideales": [{"texto": "Caridad. …", "alineamiento": "bueno"}],
 "vinculos": ["…"], "defectos": ["…"]}
```

### dotes
`efectos` · `prerrequisito` (requisito, §4.1) · `resumen`, `usos`, `recarga` (como en los rasgos). La dote aparece en la ficha como «Dote: Nombre».

### opciones
Opciones de clase reutilizables: estilos de combate, invocaciones, metamagia, maniobras, enemigos predilectos… `grupo` (obligatorio, p. ej. `estilo_combate`) · `clases` (lista de clases que pueden elegirla) · `efectos` · `prerrequisito` · `resumen`, `usos`, `recarga`, `escala`. Se conceden con una elección:

```json
{"tipo": "eleccion", "id": "estilo", "nombre": "Estilo de Combate",
 "opciones": {"desde": "opciones", "filtro": {"grupo": "estilo_combate", "clases": "paladin"}},
 "aplicar": [{"tipo": "opcion", "id": "$opcion"}]}
```

### 4.0 Perfil para el modo sencillo

Razas, clases, subclases y trasfondos llevan un `perfil` con los rasgos que más los definen (de 0 a 3; lo que no aparece vale 0). Las subrazas pueden llevar el suyo, que se suma al de la raza. El cuestionario puntúa estos rasgos con las respuestas y recomienda, entre lo **cargado**, lo que mejor encaja: un homebrew entra en el cuestionario solo con declarar su perfil.

```json
"perfil": {"sigilo": 3, "astucia": 2, "agilidad": 2}
```

Rasgos: `combate`, `agilidad`, `aguante`, `proteccion`, `sigilo`, `astucia`, `carisma`, `saber`, `naturaleza`, `fe`, `arcano`, `curacion`. Usa 2-4 rasgos por entrada; reserva el 3 para lo que define a la opción.

### preguntas (modo sencillo)
Situaciones cotidianas; cada respuesta puntúa el perfil del jugador. `nombre` (título corto) · `texto` · `respuestas` (2 o más) · `requiere` opcional (la pregunta solo sale si todo eso está cargado: `["clases:artifice"]`). Cada respuesta: `id` · `texto` y al menos uno de:

- `perfil`: rasgos que suma (`{"combate": 2, "astucia": 1}`).
- `pesos`: empujones directos de -5 a 5 a razas, subrazas, clases, subclases o trasfondos (`{"clases:guerrero": 3}`); cada punto vale 5 de afinidad sobre 100. Si el id no está cargado, no cuenta.
- `eje`: alineamiento, de -3 a 3 (`{"orden": -1, "moral": -2}`); con ±2 acumulado el personaje es legal/caótico o bueno/malvado.

```json
{"id": "lapiz", "nombre": "El lápiz", "texto": "En clase, el de al lado te pide un lápiz. ¿Qué haces?",
 "respuestas": [{"id": "clavar", "texto": "Se lo clavo en la mano.", "perfil": {"combate": 2, "astucia": 1},
                 "eje": {"moral": -2, "orden": -1}}, …]}
```

La recomendación es la afinidad (coseno) entre el perfil del jugador y el de cada raza (más su subraza), clase o trasfondo, más los pesos. Las características siguen a la clase (su característica clave primero) y, el resto, a los rasgos del jugador.

### recomendaciones (modo sencillo)
Preferencias para rellenar lo que el cuestionario no pregunta. `id`: el de la clase (o `general`, para cualquiera) · `nombre` · `conjuros`, `opciones`, `dotes`: ids en orden de preferencia. Lo que no aparece se elige al azar (reproducible: mismas respuestas, mismo personaje).

### 4.1 Requisitos (dotes y multiclase)

| Clave | Significado |
|---|---|
| `caracteristicas` | Todas: `{"des": 13, "sab": 13}` |
| `alguna_caracteristica` | Al menos una: `{"fue": 13, "des": 13}` |
| `competencia` | Id de competencia: `"armaduras_medias"` |
| `lanzador` | `true`: poder lanzar al menos un conjuro |
| `texto` | Requisito que no se puede comprobar automáticamente |

Se comprueban con las puntuaciones finales y generan avisos, no bloquean.

### 4.2 Equipo con alternativas

Lista de **bloques**; cada bloque es una lista de **alternativas** (si solo hay una, es fijo); cada alternativa es una lista de **líneas**. Una línea es `{"id": "objeto", "cantidad": 2}` o `{"desde": "armas", "filtro": {...}, "cantidad": 1}` («cualquier arma marcial»).

```json
"equipo_inicial": [
  [[{"id": "cota_de_malla"}], [{"id": "armadura_de_cuero"}, {"id": "arco_largo"}, {"id": "flecha", "cantidad": 20}]],
  [[{"desde": "armas", "filtro": {"arma": {"categoria": "marcial"}}}, {"id": "escudo"}]]
]
```

(`desde`: `objetos`, `armas` o `herramientas`.)

### conjuros
`nivel` (0 = truco, hasta 9) · `escuela` (`abjuracion`, `adivinacion`, `conjuracion`, `encantamiento`, `evocacion`, `ilusion`, `nigromancia`, `transmutacion`) · `listas` (ids de clase o subclase). Opcionales: `tiempo`, `alcance`, `componentes`, `duracion`, `ritual`, `concentracion`, `descripcion`.

### objetos
`categoria`: `arma`, `armadura`, `escudo`, `herramienta`, `municion`, `foco`, `equipo`, `montura`, `vehiculo`. Opcionales: `coste`, `peso`.

```json
{"id": "espada_larga", "nombre": "Espada larga", "categoria": "arma",
 "arma": {"categoria": "marcial", "tipo": "cuerpo_a_cuerpo", "dano": "1d8", "tipo_dano": "cortante",
          "propiedades": ["versatil"], "dano_versatil": "1d10"}}

{"id": "cota_de_malla", "nombre": "Cota de mallas", "categoria": "armadura",
 "armadura": {"tipo": "pesada", "ca": 16, "fuerza_minima": 13, "desventaja_sigilo": true}}

{"id": "escudo", "nombre": "Escudo", "categoria": "escudo", "escudo": {"bonificador": 2}}
```

- `arma.tipo`: `cuerpo_a_cuerpo` o `distancia`. Con la propiedad `sutil` se usa la mejor de FUE y DES.
- `armadura.tipo`: `ligera` (CA + DES), `media` (CA + DES hasta `max_des`, 2 por defecto) o `pesada`.

### idiomas
Solo `id` y `nombre` (opcional `tipo`: `estandar` / `exotico`).

## 5. Efectos

Una lista de objetos con `tipo`. Cualquier efecto admite `condicion` (`sin_armadura`, `con_armadura`, `sin_armadura_pesada`, `sin_escudo`, `con_escudo`, o una lista de ellas).

| `tipo` | Campos | Ejemplo de uso |
|---|---|---|
| `caracteristica` | `car`, `valor`, `maximo` (20 por defecto) | +2 CON racial; +4 FUE con máximo 24. |
| `competencia` | `categoria` (`habilidad`, `salvacion`, `arma`, `armadura`, `herramienta`, `idioma`), `id` | Grupos: `armaduras_ligeras`, `armaduras_medias`, `armaduras_pesadas`, `escudos`, `armas_sencillas`, `armas_marciales`. |
| `pericia` | `id` | Pericia del pícaro. |
| `medio_competencia` | `caracteristicas` (`"todas"` o lista), `redondeo` (`abajo`/`arriba`) | Polivalente del bardo, Atleta extraordinario. |
| `velocidad` | `modo` (`caminar`, `nadar`, `trepar`, `volar`), `valor` o `bonificador` | Velocidad nadando 30; +10 de Movimiento rápido. |
| `ignora_penalizacion_armadura` | — | Enanos y armadura pesada. |
| `sentido` | `id`, `nombre`, `alcance` | Visión en la oscuridad 60. |
| `resistencia` | `dano` | Resistencia al veneno. |
| `inmunidad` | `id` | Inmune a una condición o daño. |
| `pg_maximos` | `por_nivel`, `valor`, `clase` (opcional) | Dureza enana (+1/nivel); Resiliencia dracónica (+1/nivel de hechicero). |
| `ca_alternativa` | `base`, `suma` (características) | Defensa sin armadura: `{"base": 10, "suma": ["des", "con"]}`. |
| `bonificador_ca` | `valor` | Estilo Defensa (`"condicion": "con_armadura"`). |
| `bonificador_ataque` | `valor`, `tipo_arma` (opcional) | Estilo Tiro con arco. |
| `bonificador_salvacion` | `valor` (número o expresión), `caracteristicas` (`"todas"` o lista) | Aura de Protección: `"max(1,mod_car)"`. |
| `iniciativa` | `valor` | Dote Alerta. |
| `pasiva` | `habilidad` (`percepcion`, `perspicacia`, `investigacion`), `valor` | Dote Observador (+5). |
| `max_des_armadura_media` | `valor` | Maestro en armaduras medias (3). |
| `ataque_des` | `armas` (ids o grupos), `excluir_propiedades`, `tipo_arma` | Armas de monje: pueden usar DES. |
| `ataque_desarmado` | `dano` (admite `{escala}`), `escala`, `caracteristicas`, `nombre`, `tipo_dano`, `notas` | Artes Marciales. |
| `ataque` | `nombre`, `dano` (admite `{escala}`), `escala`, `caracteristicas` (usa la mejor), `tipo_dano`, `notas` | Arma que da un rasgo y no es un objeto: Espadas Psíquicas, Guanteletes de Trueno. Siempre con competencia. |
| `bonificador_ataque_conjuros` | `valor` | Suma al ataque de conjuros de todas tus clases (Canalizador Arcano Mejorado). |
| `ataque_caracteristica` | `caracteristica`, `solo_magicas` | Las armas atacan y dañan con esa característica si es mejor. Listo para la Batalla: `{"caracteristica": "int", "solo_magicas": true}` (solo con armas mágicas, que se marcan en el paso Equipo). |
| `rasgo` | `nombre`, `descripcion`, `resumen`, `usos`, `recarga`, `escala`, `clase` | Rasgo que aparece en la ficha (ver §5.1). |
| `conjuro` | `id`, `caracteristica`; o `clase` + `siempre_preparado`; `cuenta_como_conocido` | Conjuro racial o innato; o de dominio/juramento (siempre preparado). Con `cuenta_como_conocido` (Secretos Mágicos del bardo) ocupa una plaza de los conjuros conocidos de esa clase. |
| `dote` | `id` | Concede una dote (aplica sus efectos). |
| `opcion` | `id` | Concede una opción de clase. |
| `mejora_caracteristica` | — | Mejora de característica: +2/+1+1 o una dote (si las dotes están activadas). |
| `eleccion` | ver abajo | Cualquier decisión del jugador. |

Cualquier efecto (también una elección) admite `nivel_minimo`: solo se aplica desde ese **nivel de personaje**. Para rasgos de clase no hace falta: ya van en `niveles`. Ejemplo, la magia del tiflin:

```json
{"tipo": "conjuro", "id": "reprension_infernal", "caracteristica": "car", "nivel_minimo": 3}
```

`nivel_clase_minimo` (junto con `clase`) hace lo mismo con el **nivel de una clase**: sirve para lo que se elige una vez y crece después, como los conjuros de círculo del druida de la Tierra (terreno elegido a nivel 2; conjuros a niveles 3 y 5):

```json
{"tipo": "conjuro", "id": "silenciar", "clase": "druida", "siempre_preparado": true, "nivel_clase_minimo": 3}
```

### 5.1 Rasgos con valores calculados

`resumen` es la línea corta de la ficha y puede llevar `{expresiones}`; `usos` es un número, una expresión o una tabla por nivel en la que `null` quita el límite (`{"1": 2, "20": null}`: Furia ilimitada a nivel 20); `recarga` es `corto` o `largo`, o una tabla por nivel (`{"1": "largo", "5": "corto"}`, como la Inspiración Bárdica con Fuente de Inspiración); `escala` es una tabla `{"nivel": valor}` (se toma el último umbral alcanzado) que se usa como `{escala}`.

```json
{"tipo": "rasgo", "nombre": "Ataque Furtivo", "resumen": "+{escala} de daño una vez por turno",
 "escala": {"1": "1d6", "3": "2d6", "5": "3d6"}}
{"tipo": "rasgo", "nombre": "Imponer las Manos", "resumen": "Reserva de {nivel_clase*5} PG", "recarga": "largo"}
{"tipo": "rasgo", "nombre": "Sentido Divino", "usos": "1+mod_car", "recarga": "largo"}
```

Variables: `nivel` (de personaje), `nivel_clase` (de la clase del rasgo; en rasgos raciales, el de personaje), `competencia`, `mod_fue`…`mod_car`, `escala` y `conjuro` (el nombre del conjuro del campo `conjuro` del rasgo, útil en un `aplicar`: `{"tipo": "rasgo", "conjuro": "$opcion", "resumen": "{conjuro}: sin gastar espacio"}`). Operaciones: `+ - * //`, `max`, `min` y `abs`. `clase` fuerza la clase de referencia.

## 6. Elecciones

```json
{"tipo": "eleccion", "id": "habilidades", "nombre": "Habilidades de guerrero", "elegir": 2,
 "fuente": "habilidades",
 "opciones": ["acrobacias", "atletismo", "historia", "intimidacion", "percepcion", "supervivencia"],
 "aplicar": [{"tipo": "competencia", "categoria": "habilidad", "id": "$opcion"}]}
```

| Campo | Notas |
|---|---|
| `id` | Único dentro de la lista en la que aparece. |
| `elegir` | Número de selecciones (1 por defecto). |
| `repetible` | `true` permite elegir la misma opción varias veces. |
| `opciones` | Lista de ids, lista de objetos `{"id", "nombre", "efectos"}` o una fuente `{"desde": ..., "filtro": {...}}`. |
| `fuente` | Con una lista de ids, de dónde salen los nombres y se valida que existan. |
| `aplicar` | Efectos para cada opción elegida; `$opcion` se sustituye por el id elegido. |

**Fuentes** (`desde`): `caracteristicas`, `habilidades`, `herramientas`, `armas`, o cualquier categoría (`idiomas`, `dotes`, `opciones`, `conjuros`…).

**Ids de habilidad:** `acrobacias`, `atletismo`, `conocimiento_arcano`, `engano`, `historia`, `interpretacion`, `intimidacion`, `investigacion`, `juego_de_manos`, `medicina`, `naturaleza`, `percepcion`, `perspicacia`, `persuasion`, `religion`, `sigilo`, `supervivencia`, `trato_con_animales`. Características: `fue`, `des`, `con`, `int`, `sab`, `car`. El `filtro` compara campos; si el campo es una lista, basta con que contenga el valor: `{"desde": "conjuros", "filtro": {"listas": "mago", "nivel": 0}}`.

**Opciones con efectos propios** (cuando cada opción hace algo distinto):

```json
{"tipo": "eleccion", "id": "estilo", "nombre": "Estilo de combate", "opciones": [
  {"id": "defensa", "nombre": "Defensa", "efectos": [{"tipo": "bonificador_ca", "valor": 1, "condicion": "con_armadura"}]},
  {"id": "arqueria", "nombre": "Tiro con arco", "efectos": [{"tipo": "bonificador_ataque", "valor": 2, "tipo_arma": "distancia"}]}
]}
```

**Elecciones anidadas.** `$opcion` siempre se refiere a la elección más cercana. Una elección interior puede usar la opción exterior en sus campos, pero no en su `aplicar`. Ejemplo (elegir clase y luego un truco de esa clase):

```json
{"tipo": "eleccion", "id": "clase", "opciones": [{"id": "mago", "nombre": "Mago"}, {"id": "bardo", "nombre": "Bardo"}],
 "aplicar": [{"tipo": "eleccion", "id": "truco",
              "opciones": {"desde": "conjuros", "filtro": {"listas": "$opcion", "nivel": 0}},
              "aplicar": [{"tipo": "conjuro", "id": "$opcion"}]}]}
```

## 7. Validación

Al cargar, el programa informa de cada error con su ruta exacta, por ejemplo:

```
[mi-homebrew] razas/orco_gris: niveles.3[0].aplicar[1]: falta «car»
[mi-homebrew] subrazas/orco_gris: la raza «orco» no existe
```

Un error de contenido no impide cargar el resto del paquete.

## Campos añadidos para niveles altos, multiclase y subida de nivel

**Efectos y rasgos**

- `no_acumula` (rasgo): `true` deja solo el mejor de los rasgos con ese nombre (Ataque Adicional, Evasión…), según el primer número de su resumen. En `ca_alternativa`, una clave de texto (p. ej. `"defensa_sin_armadura"`) hace que solo cuente la primera fórmula con esa clave.
- `usos_compartidos` (rasgo): clave común. Varias clases con el mismo rasgo (Canalizar Divinidad) comparten una reserva y no suman usos.
- `usos` y `recarga` admiten una tabla por nivel: `{"1": "largo", "5": "corto"}`. Un `null` en `usos` significa ilimitado.
- `al_libro` (efecto `conjuro`): el conjuro va gratis al libro del mago y se puede preparar (Siervos No Muertos, Cambiaformas).
- `en_libro` (rasgo): el conjuro elegido debe estar en el libro de esa clase; si no está, se avisa (Maestría sobre Conjuros, Conjuros Característicos).
- `sin_desventaja_sigilo` (efecto): quita la desventaja en Sigilo de la armadura; `tipo_armadura` opcional (`"media"`).
- `bonificador_salvacion` (efecto): `valor` (número o expresión) y `caracteristicas` opcional.
- `iniciativa` (efecto): `valor` puede ser un número o una expresión (p. ej. `"competencia"`).
- `cuenta_como_conocido` (efecto `conjuro`, con `clase`): ocupa plaza de conjuro conocido.

**Preguntas** (`preguntas.json`, `preguntas_subida.json`)

- `momento`: `"creacion"` (por defecto) o `"subida"`. Las de subida son hitos de la aventura y salen al subir de nivel o, al crear por encima de nivel 1, en «Su historia», después de elegir raza y clase.
- `decide`: lista con `mejora`, `subclase`, `opciones` o `conjuros`. Salen los hitos que tocan alguna decisión de esos niveles: uno si se suben menos de 5 niveles, dos hasta 9 y tres a partir de 10. Se salta el hito de un solo propósito cuya decisión ya tiene pregunta concreta (p. ej., entrenar para la mejora).
- Preguntas concretas: no se escriben en los datos. El programa hace una por cada elección real de esos niveles, con lo que el personaje tiene: la subclase (todas las disponibles), cada mejora de característica (repartos con las puntuaciones de ese momento y las dotes cuyo prerrequisito cumple), las opciones de clase, las pericias y competencias, los conjuros de rasgos como Secretos Mágicos o Arcanum Místico, y la escuela de los conjuros nuevos (con ejemplos de su lista). Los huecos iguales de varios niveles (invocaciones, metamagia, terrenos…) van en una sola pregunta de varias respuestas. Las listas largas se acortan a las 16 que mejor encajan. Lo que no se responde lo decide el perfil, y la respuesta que se elegiría va marcada como «★ Propuesta».
- Los prerrequisitos de las opciones de clase son texto: el programa lee «nivel N de <clase>», «Pacto de…» y «truco <conjuro>». Si un homebrew usa otra fórmula, la opción se ofrece igualmente: detrás de las demás, salvo que esté entre las recomendadas.
- En cada respuesta:
  - `mejora`: `"caracteristicas"` o `"dote"`.
  - `escuelas`: `{"evocacion": 2}`, con valores de -3 a 3.
  - `pesos` admite también `dotes:`, `opciones:` y `conjuros:`.

**Recomendaciones**

- Las entradas con `rasgo` (p. ej. `rasgo_combate`) forman la tabla rasgo del perfil → `dotes`, `opciones`, `escuelas` y `conjuros` que encajan con él.
- Solo se usan cuando hay respuestas de subida: el perfil (con lo vivido en esa subida reforzado) ordena las dotes, las opciones y los conjuros nuevos.

**Configuración del cuestionario** (campos de cada pregunta de creación)

- `estilo`: `"cotidiana"` (por defecto), `"fantasia"` o `"comun"` (sale en los dos estilos, p. ej. «¿Has jugado antes a rol?»). Con «Mezcla» se alternan las de los dos estilos hasta el tamaño de uno solo.
- `detalle`: 1, 2 o 3. La pregunta entra en «Rápido» (1), «Recomendado» (1 y 2) o «Preciso» (todas). En el paquete del programa salen 10, 20 y 32 por estilo.
- `sensible`: `true` si el contenido es sensible o bizarro. Solo sale con el interruptor activado, y entonces se suma a las demás de su nivel.
- `sustituye`: id de otra pregunta. Si sus requisitos (`requiere`) están cargados, ocupa el sitio de esa pregunta (así un paquete como Tasha cambia preguntas sin alterar el total).

## Rasgos de clase opcionales (Guía de Tasha)

Con la regla opcional `rasgos_opcionales` activa (interruptor «Rasgos de clase opcionales» en «Edición y reglas» o en la pantalla de opciones del modo sencillo), se aplican las entradas de la categoría `rasgos_opcionales` de las clases del personaje. De serie se usan todas; cada una se puede dejar con `"opcional:<id>": false` en las reglas del personaje (el paso «Clase» tiene una casilla por rasgo).

**Entrada** (`rasgos_opcionales.json`): `id`, `nombre`, `clase` (id) · `descripcion` · `niveles` (como en las subclases: `{"nivel": [efectos]}`, por nivel de esa clase) · `subclase` opcional (solo con esa subclase, p. ej. el Compañero Primigenio del Señor de las Bestias) · `sustituye` opcional: lista de ids de elección o nombres de rasgo de esa clase o de su subclase que dejan de aplicarse (Explorador Hábil: `["terreno_predilecto", …]`; Golpes Bendecidos: `["Golpe Divino", "Lanzamiento Potente"]`). Ojo: no se llama `reemplaza`, que es una palabra reservada del formato (sustituye entradas enteras del catálogo).

**Infusiones que lleva el propio personaje** (`opciones.json`): una opción con `"propia"` puede marcarse en el paso Equipo como «la llevo yo». Campos: `objeto` (`categorias` entre `arma`, `armadura` y `escudo`; `propiedad` opcional, p. ej. `"arrojadiza"`): una unidad corriente de ese objeto del inventario pasa a ser mágica; `bonificador` (`{nivel de la clase: valor}`): lo que suma al ataque y al daño (arma) o a la CA (armadura o escudo); `efectos`: efectos que se aplican mientras la lleva, con `"$bonificador"` como valor si dependen de él; `elige_dano`: el jugador elige un tipo de daño al que gana resistencia. Ejemplo, Defensa Mejorada: `{"objeto": {"categorias": ["armadura", "escudo"]}, "bonificador": {"2": 1, "10": 2}}`.

**Opciones de un rasgo opcional** (`opciones.json`): con `"rasgo_opcional": "<id>"` (o una lista de ids), la opción solo aparece en las elecciones si ese rasgo está activo para el personaje. Así entran los estilos de combate, las invocaciones, las maniobras, las metamagias y el Pacto del Talismán de Tasha.

**Velocidad igual a otra**: el efecto `velocidad` admite `"igual_a": "caminar"` (con `modo`, p. ej. `"trepar"`): esa velocidad vale lo que la de caminar, ya con sus bonificadores.

Los orígenes de las elecciones de estos rasgos empiezan por `opcional:<id>:<nivel>/`; el asistente los muestra en el paso «Clase».

