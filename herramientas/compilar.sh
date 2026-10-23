#!/bin/sh
# Compila el creador de personajes portable para macOS o Linux (las dos ediciones).
# Necesita Python 3.10 o superior con Tkinter (macOS: el instalador de python.org; Linux: python3-tk y python3-venv).
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv-compilar
. .venv-compilar/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python herramientas/compilar.py "$@"
echo "Los .zip están en la carpeta dist."
