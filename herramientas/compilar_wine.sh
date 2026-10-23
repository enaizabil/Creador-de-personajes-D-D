#!/bin/sh
# Compila el ejecutable de Windows desde Linux con Wine (Ubuntu 24.04, Wine 9 de 64 bits).
#
#   sh herramientas/compilar_wine.sh [--edicion completa|libre|ambas]
#
# PyInstaller no compila para otro sistema, pero funciona dentro de Wine. El instalador de Python es un
# programa de 32 bits y Wine de 64 no lo arranca: se extraen sus MSI con msitools. Necesita: wine64,
# msitools, xvfb y curl. El prefijo de Wine se guarda en $PREFIJO (por defecto ~/.wine-creador).
set -e
cd "$(dirname "$0")/.."
VERSION_PY=3.12.10
PREFIJO=${PREFIJO:-$HOME/.wine-creador}
export WINEPREFIX="$PREFIJO" WINEDEBUG=-all
PY="$PREFIJO/drive_c/Python312"

if [ ! -x "$PY/python.exe" ]; then
  descargas=$(mktemp -d)
  for msi in core exe lib tcltk; do
    curl -sSf -o "$descargas/$msi.msi" "https://www.python.org/ftp/python/$VERSION_PY/amd64/$msi.msi"
  done
  mkdir -p "$PY"
  for msi in core exe lib tcltk; do
    msiextract -C "$PY" "$descargas/$msi.msi" > /dev/null
  done
  rm -rf "$descargas"
  # Wine 9 no implementa CopyFile2, que shutil usa en Windows desde Python 3.12: se vuelve a la copia clásica.
  cat > "$PY/Lib/site-packages/sitecustomize.py" <<'FIN'
# Solo en este Python de compilación bajo Wine 9, que no implementa CopyFile2: shutil usa la copia clásica.
import _winapi

if hasattr(_winapi, "CopyFile2"):
    del _winapi.CopyFile2
FIN
  # Con un proxy que inspecciona TLS, pip necesita su certificado (variable CA_PROXY con la ruta del .crt).
  if [ -n "$CA_PROXY" ]; then cp "$CA_PROXY" "$PREFIJO/drive_c/ca-proxy.crt"; export PIP_CERT='C:\ca-proxy.crt'; fi
  xvfb-run -a sh -c "wine 'C:\\Python312\\python.exe' -m ensurepip --default-pip < /dev/null 2>&1 | tail -1;
    wine 'C:\\Python312\\python.exe' -m pip install --no-warn-script-location -r requirements.txt pyinstaller \
      < /dev/null 2>&1 | tail -1; wineserver -w"
fi

# La salida va por tubería: con la entrada o la salida redirigidas a un archivo, Python en Wine no arranca.
xvfb-run -a sh -c "wine 'C:\\Python312\\python.exe' herramientas/compilar.py $* < /dev/null 2>&1 | cat; wineserver -w"
ls -la dist/*windows*.zip
