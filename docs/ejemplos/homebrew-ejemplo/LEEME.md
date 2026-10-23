# Homebrew de ejemplo: gentes del río

Paquete mínimo para copiar y convertir en tu propio homebrew. Trae:

| Archivo | Qué contiene |
|---|---|
| `paquete.json` | El manifiesto: id, nombre, sistema, versión, de qué depende y qué archivos carga. |
| `razas.json` | Una raza: **Duende del brezo** (características, sentido, competencia, rasgos e idiomas). |
| `trasfondos.json` | Un trasfondo: **Barquero del río** (competencias, una elección de idioma, rasgo, equipo, dinero y personalidad). |
| `dotes.json` | Una dote: **Ojo de barquero**. |
| `preguntas.json` | Una pregunta para el cuestionario de situaciones, con pesos hacia la raza y el trasfondo. |

## Cómo hacer el tuyo

1. Copia esta carpeta y cámbiale el nombre.
2. En `paquete.json`, cambia **`id`** (minúsculas, números, puntos y guiones; no puede coincidir con uno integrado), `nombre`, `version` y `descripcion`.
3. Edita o borra los archivos de contenido y deja en `archivos` solo los que existan.
4. Cambia también los `id` de cada entrada (`duende_del_brezo`…): dos entradas con el mismo id en la misma categoría chocan.
5. El `perfil` (rasgos de 0 a 3) es lo que usa el cuestionario para recomendar tu raza, clase o trasfondo; sin él, el cuestionario no lo propondrá nunca.

Todos los campos y efectos posibles están en [`docs/formato-paquetes.md`](../../formato-paquetes.md). Para modificar contenido de otro paquete sin copiarlo entero, usa `"modifica": true` en la entrada (ver ese documento).

## Cómo instalarlo

- **En el programa:** pantalla de inicio → **Paquetes…** → **Importar carpeta…** (o **Importar .zip…**). Se valida antes de instalar: si tiene errores, te los enseña y no lo instala.
- **A mano:** copia la carpeta dentro de `paquetes/`, junto al ejecutable.
- **Línea de órdenes:** `python -m creador instalar docs/ejemplos/homebrew-ejemplo`

Un paquete solo puede tener datos (`.json`, `.md`, `.txt`), nunca código.
