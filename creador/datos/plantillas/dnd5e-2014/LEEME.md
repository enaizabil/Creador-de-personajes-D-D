# Plantillas de hoja de personaje (5e 2014)

## hoja_editable_es.pdf
Hoja de personaje rellenable en español: la oficial de Wizards of the Coast (2014) traducida, con los campos y
cálculos de la versión rellenable («form fills and calculations edited by DLH», según sus metadatos) y dos
páginas añadidas (descripción de conjuros y continuación de la historia). La aportó el usuario ya rellena; se
dejó en blanco con `herramientas/vaciar_hoja_pdf.py` (198 valores borrados).

- Licencia de la hoja original: «TM & © 2014 Wizards of the Coast LLC. Permission is granted to photocopy this
  document for personal use». Solo para uso personal: no se redistribuye fuera de este repositorio privado.
- `salidas/pdf_oficial.py` la rellena. Al hacerlo quita sus cálculos (no contemplan la pericia ni otros
  bonificadores del motor) y los recursos de fuente locales sin codificación de 12 campos (perdían los acentos).
