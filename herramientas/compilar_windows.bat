@echo off
rem Compila el creador de personajes portable para Windows (las dos ediciones).
rem Necesita Python 3.10 o superior de python.org (marca "Add python.exe to PATH" al instalarlo).
cd /d "%~dp0\.."
where py >nul 2>nul && (py -3 -m venv .venv-compilar) || (python -m venv .venv-compilar)
if errorlevel 1 (
  echo No se ha podido crear el entorno: instala Python desde https://www.python.org/downloads/
  pause
  exit /b 1
)
call .venv-compilar\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python herramientas\compilar.py %*
echo.
echo Los .zip estan en la carpeta dist.
pause
