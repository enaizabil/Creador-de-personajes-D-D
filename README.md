# Creador de personajes de D&D

Programa portable para crear personajes de rol, con dos modos (normal y sencillo) y contenido ampliable por paquetes. Primer sistema: **D&D 5ª edición (2014)**.

> **Estado: las 7 fases hechas.** Todas las clases y subclases (SRD, Manual del Jugador, Guía del DM y Caldero de Tasha, con el artífice) hasta nivel 20 y conjuros de nivel 0 a 9. Se usa como programa de escritorio o [en el navegador](https://enaizabil.github.io/Creador-de-personajes-D-D/), sin instalar nada. Núcleo, motor de reglas de 5e, datos de 5e 2014 (SRD + Manual del Jugador + Guía del DM) e interfaz gráfica con los dos modos: preguntas de situaciones cotidianas (sencillo) y asistente paso a paso (normal), y salidas en PDF (hoja oficial editable rellena y réplica) y Markdown para Obsidian/Nivel20.

## Hoja de ruta

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Núcleo: paquetes, personaje, motor de efectos y elecciones, reglas derivadas de 5e (niveles 1–20) | ✅ |
| 2 | Datos 5e 2014: SRD 5.1 + PHB + Guía del DM (razas, clases, trasfondos, dotes, equipo, conjuros) | ✅ Hasta nivel 20 (dudas en `docs/dudas-contenido.md`) |
| 3 | Modo normal: asistente por pasos con selector de sistema y paquetes (CustomTkinter) | ✅ (con multiclase: reparto de niveles en el paso «Clase») |
| 4 | Modo sencillo: cuestionario de situaciones → raza, clase, trasfondo, características y habilidades | ✅ (batería de 155 situaciones, cotidianas y de fantasía, con 6 respuestas cada una; cada partida saca 10, 20 o 32 al azar y enseña 4 o 6 respuestas; una sola clase o, si se acepta, propuesta de multiclase; el personaje se retoca luego en el modo normal) |
| 5 | Salidas: JSON, réplica de la ficha oficial, rellenado del PDF oficial y guía para Nivel20 | ✅ (hoja editable en español rellena, réplica en A4 y nota de Obsidian con la guía de Nivel20) |
| 6 | Ejecutables para Windows, macOS y Linux (PyInstaller) y gestor de paquetes | ✅ (compilación local en dos ediciones, completa y libre; gestor con importación validada y homebrew de ejemplo) |
| 7 | Versión web: el mismo programa en el navegador (Pyodide), publicada en GitHub Pages | ✅ (los dos modos, subida de nivel, todas las salidas y homebrew; se guarda en el navegador) |

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

## Versión web

**https://enaizabil.github.io/Creador-de-personajes-D-D/** — para pasársela a los jugadores: funciona en el
ordenador y en el móvil, sin instalar nada.

- Es el mismo programa (motor, datos y salidas) en Python, ejecutado en el navegador con
  [Pyodide](https://pyodide.org); la página (`web/`) solo pinta las pantallas que describe `creador/web/sesion.py`.
  Nada se envía a ningún servidor.
- La primera visita descarga unos 20 MB (Python y los libros); después el navegador lo guarda.
- Los personajes se guardan solos en el navegador («Tus personajes en este navegador»). Para no perderlos o
  llevarlos a otro dispositivo: **Guardar (.json)** y, en el otro, **Abrir personaje**. Los paquetes de homebrew
  importados también se quedan en ese navegador.
- Se publica sola en cada push a la rama del repositorio público ([`.github/workflows/web.yml`](.github/workflows/web.yml):
  tests, compilación y publicación). En Settings → Pages, «Source» tiene que ser «GitHub Actions».

Para probarla en local:

```bash
python herramientas/compilar_web.py          # deja la web en dist/web
python -m http.server -d dist/web 8000       # http://localhost:8000
node herramientas/probar_web.js http://localhost:8000   # prueba de punta a punta (Playwright + Chromium)
```

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

- El contenido del **SRD 5.1** se distribuye bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode); atribución en [`ATRIBUCION.md`](creador/datos/paquetes/dnd5e-2014/srd-5.1/ATRIBUCION.md).
- El contenido del Manual del Jugador, la Guía del DM y el Caldero de Tasha que no está en el SRD, y la hoja de personaje editable, son de Wizards of the Coast y están protegidos por derechos de autor. Los textos de los libros van resumidos y adaptados al formato del programa; la hoja se usa como plantilla para rellenarla. Es para uso de un grupo de juego.
- Iconos de la interfaz: [game-icons.net](https://game-icons.net) (Lorc, Delapouite, Cathelineau), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Tipografía de los títulos: Cinzel, [SIL Open Font License 1.1](creador/gui/recursos/fuentes/OFL.txt). Detalle en [CREDITOS.md](creador/gui/recursos/CREDITOS.md).
