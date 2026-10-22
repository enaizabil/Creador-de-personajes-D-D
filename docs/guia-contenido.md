# Guía de redacción de contenido (5e 2014)

Normas para escribir los paquetes `srd-5.1`, `phb-2014` y cualquier ampliación. El formato técnico está en [formato-paquetes.md](formato-paquetes.md).

## Paquetes

| Paquete | Contenido | Licencia |
|---|---|---|
| `srd-5.1` | Todo lo que está en el SRD 5.1: 9 razas con su subraza, las 12 clases con una subclase cada una, Acólito, Apresador, equipo, conjuros e idiomas del SRD. | CC BY 4.0: se puede copiar el texto, con atribución. |
| `phb-2014` | Lo del Manual del Jugador que **no** está en el SRD: resto de subrazas, humano variante, subclases, trasfondos, dotes, conjuros y opciones. Depende de `srd-5.1`. | Protegido: **solo con palabras propias**, nunca copiado. |

Cuando el PHB amplía algo del SRD (p. ej. añade un conjuro a una lista de clase), se hace con `"modifica": true` desde `phb-2014`.

## Nombres

1. **Contenido del SRD:** el nombre exacto del SRD 5.1 oficial en español (`SRD_CC_v5.1_ES.pdf`), con sus mayúsculas: «Defensa sin Armadura», «Tomar Aliento», «Conocimiento Arcano».
2. **Contenido solo del PHB:** la traducción oficial española del Manual del Jugador (2014). Si no se puede confirmar, se usa la más extendida y se apunta en el informe de dudas como *(sin verificar)*.
3. **Ids:** minúsculas, sin tildes ni eñes, con guion bajo: `juramento_de_venganza`, `engano`. Los ids no cambian aunque cambie el nombre.

## Textos

- `resumen`: una línea para la ficha, con números, al estilo de las fichas de Villaprincipio: «acción adicional, 1d10+{nivel_clase} PG; 1 por descanso». Usa `{expresiones}` para lo que escala.
- `descripcion`: 1-3 frases con lo esencial de la regla. En el PHB, **con palabras propias**. En el SRD se puede resumir o citar.
- Nada de inventar reglas. Si un dato no se puede confirmar, va al informe de dudas, no a los datos.

## Mecánica antes que texto

Todo lo que el motor sabe calcular va como efecto, no solo como texto: competencias, características, velocidad, sentidos, resistencias, CA alternativa, PG extra, conjuros raciales y de dominio, pericias, estilos de combate, ataques sin armas… El texto del rasgo complementa; no sustituye.
