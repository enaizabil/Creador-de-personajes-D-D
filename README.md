# Creador de personajes de D&D

Programa portable para crear personajes de rol, con dos modos (normal y sencillo) y contenido ampliable por paquetes. Primer sistema: **D&D 5ª edición (2014)**.

> **Estado: fases 1 a 4 de 6.** Núcleo, motor de reglas de 5e, datos de 5e 2014 (SRD + Manual del Jugador + Guía del DM) hasta nivel 5 e interfaz gráfica con los dos modos: preguntas de situaciones cotidianas (sencillo) y asistente paso a paso (normal).

## Hoja de ruta

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Núcleo: paquetes, personaje, motor de efectos y elecciones, reglas derivadas de 5e (niveles 1–20) | ✅ |
| 2 | Datos 5e 2014: SRD 5.1 + PHB + Guía del DM (razas, clases, trasfondos, dotes, equipo, conjuros 0-3) hasta nivel 5 | ✅ (niveles 6-20 pendientes; dudas en `docs/dudas-contenido.md`) |
| 3 | Modo normal: asistente por pasos con selector de sistema y paquetes (CustomTkinter) | ✅ (sin multiclase en el asistente) |
| 4 | Modo sencillo: cuestionario de situaciones → raza, clase, trasfondo, características y habilidades | ✅ (17 preguntas; el personaje se retoca luego en el modo normal) |
| 5 | Salidas: JSON, réplica de la ficha oficial, rellenado del PDF oficial y guía para Nivel20 | 🟡 JSON, réplica en PDF (A4) y nota de Obsidian con la guía de Nivel20 hechas; falta rellenar el PDF oficial |
| 6 | Ejecutables para Windows, macOS y Linux (PyInstaller + GitHub Actions) y gestor de paquetes | ⏳ |

## Requisitos

- Python 3.10 o superior con Tkinter (incluido en los instaladores de python.org; en Debian/Ubuntu: `apt install python3-tk`).
- Interfaz y ficha en PDF: `pip install -r requirements.txt` (CustomTkinter y reportlab). El núcleo y el resto de la línea de órdenes no tienen dependencias externas.
- Para los tests: `pip install pytest`.

## Uso

```bash
python -m creador                       # abre la interfaz gráfica (también: python -m creador gui)
python -m creador paquetes              # lista los paquetes instalados
python -m creador ficha personaje.json  # calcula y muestra la ficha de un personaje
python -m creador exportar personaje.json [--pdf ficha.pdf] [--nota nota.md]  # ficha en PDF y nota para Nivel20
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
