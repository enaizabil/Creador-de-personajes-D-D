# Creador de personajes de D&D

Programa portable para crear personajes de rol, con dos modos (normal y sencillo) y contenido ampliable por paquetes. Primer sistema: **D&D 5ª edición (2014)**.

> **Estado: las 6 fases hechas.** Todas las clases y subclases (SRD, Manual del Jugador y Guía del DM) hasta nivel 20 y conjuros de nivel 0 a 9. Núcleo, motor de reglas de 5e, datos de 5e 2014 (SRD + Manual del Jugador + Guía del DM) e interfaz gráfica con los dos modos: preguntas de situaciones cotidianas (sencillo) y asistente paso a paso (normal), y salidas en PDF (hoja oficial editable rellena y réplica) y Markdown para Obsidian/Nivel20.

## Hoja de ruta

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Núcleo: paquetes, personaje, motor de efectos y elecciones, reglas derivadas de 5e (niveles 1–20) | ✅ |
| 2 | Datos 5e 2014: SRD 5.1 + PHB + Guía del DM (razas, clases, trasfondos, dotes, equipo, conjuros) | ✅ Hasta nivel 20 (dudas en `docs/dudas-contenido.md`) |
| 3 | Modo normal: asistente por pasos con selector de sistema y paquetes (CustomTkinter) | ✅ (con multiclase: reparto de niveles en el paso «Clase») |
| 4 | Modo sencillo: cuestionario de situaciones → raza, clase, trasfondo, características y habilidades | ✅ (17 preguntas; una sola clase o, si se acepta, propuesta de multiclase; el personaje se retoca luego en el modo normal) |
| 5 | Salidas: JSON, réplica de la ficha oficial, rellenado del PDF oficial y guía para Nivel20 | ✅ (hoja editable en español rellena, réplica en A4 y nota de Obsidian con la guía de Nivel20) |
| 6 | Ejecutables para Windows, macOS y Linux (PyInstaller) y gestor de paquetes | ✅ (compilación local en dos ediciones, completa y libre; gestor con importación validada y homebrew de ejemplo) |

## Requisitos

- Python 3.10 o superior con Tkinter (incluido en los instaladores de python.org; en Debian/Ubuntu: `apt install python3-tk`).
- Interfaz y salidas en PDF: `pip install -r requirements.txt` (CustomTkinter, reportlab y pypdf). El núcleo y el resto de la línea de órdenes no tienen dependencias externas.
- Para los tests: `pip install pytest`.

## Ejecutables portables

No se instalan: es una carpeta que se copia donde se quiera (también a un USB). Se compilan en cada sistema
operativo, en local:

- **Windows:** instala Python 3.10+ de [python.org](https://www.python.org/downloads/) (marca «Add python.exe to
  PATH») y haz doble clic en `herramientas\compilar_windows.bat`.
- **macOS / Linux:** `sh herramientas/compilar.sh` (Python con Tkinter; en Linux, `python3-tk` y `python3-venv`).

Salen dos `.zip` en `dist/`:

| Edición | Contenido | ¿Se puede compartir? |
|---|---|---|
| **completa** | SRD 5.1, Manual del Jugador, Guía del DM, cuestionario y hoja oficial editable | **No**: solo para tu grupo de juego |
| **libre** | SRD 5.1 y cuestionario (sin hoja oficial) | Sí |

Cada carpeta trae un `LEEME.txt` y una carpeta `paquetes/` para homebrew. Los ejecutables no están firmados:
Windows (SmartScreen) y macOS (Gatekeeper) avisarán la primera vez.

## Paquetes de homebrew

Desde el programa: **Paquetes…** → **Importar .zip…** o **Importar carpeta…**. Se valida antes de instalarse
(solo datos JSON/Markdown/texto, sin pisar los integrados, con sus dependencias y sin errores de contenido).
Ejemplo para copiar: [`docs/ejemplos/homebrew-ejemplo`](docs/ejemplos/homebrew-ejemplo/LEEME.md); formato completo:
[`docs/formato-paquetes.md`](docs/formato-paquetes.md).

## Uso

```bash
python -m creador                       # abre la interfaz gráfica (también: python -m creador gui)
python -m creador paquetes              # lista los paquetes instalados
python -m creador instalar homebrew.zip # instala un paquete (o una carpeta); quitar <id> lo quita
python -m creador ficha personaje.json  # calcula y muestra la ficha de un personaje
python -m creador exportar personaje.json [--oficial hoja.pdf] [--pdf ficha.pdf] [--nota nota.md]  # salidas
python -m pytest                        # ejecuta los tests
```

## Arquitectura

```
creador/
├── nucleo/                 # independiente del sistema de reglas
│   ├── paquetes.py         # descubrimiento, dependencias, fusión y validación de paquetes
│   ├── personaje.py        # decisiones del jugador (JSON); nunca guarda valores derivados
│   ├── efectos.py          # resolución genérica de efectos y elecciones anidadas
│   ├── sistema.py          # interfaz que implementa cada edición
│   └── rutas.py            # ubicación de datos (código fuente o ejecutable)
├── sistemas/
│   └── dnd5e_2014/         # reglas de 5e: constantes, características, validación, motor, ficha y asistente
├── gui/                    # interfaz CustomTkinter: inicio (edición y paquetes) y vista del asistente de cada sistema
├── datos/paquetes/         # paquetes integrados en el ejecutable
└── entorno.py              # carga sistema + catálogo
docs/formato-paquetes.md    # especificación del formato de contenido
tests/                      # tests con un paquete de prueba propio
```

Principios:

- **El personaje guarda decisiones, no resultados.** CA, PG, bonificadores, etc. se recalculan siempre, así que subir de nivel o cambiar de raza no deja datos incoherentes.
- **Las reglas viven en el sistema y el contenido en los paquetes.** Añadir Tasha's u homebrew es añadir un paquete. Añadir otra edición (5e 2024, 3.5) supone crear un nuevo módulo en `sistemas/`, porque las reglas cambian.
- **Elecciones con clave estable** (`"clase:guerrero:4/mejora"`): la interfaz pregunta solo lo que falta (`elecciones_pendientes`) y los dos modos comparten el mismo motor.

## Contenido y licencias

- El contenido del **SRD 5.1** se distribuye bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode). La atribución obligatoria se añadirá junto con los datos (fase 2).
- El contenido del PHB que no está en el SRD está protegido por derechos de autor. **Este repositorio debe ser privado** antes de incluirlo.
