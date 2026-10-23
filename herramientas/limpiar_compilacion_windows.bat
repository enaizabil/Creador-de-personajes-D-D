@echo off
rem Deshace lo que instala compilar_windows.bat: el entorno .venv-compilar, las carpetas de trabajo y,
rem si se pide, los paquetes de compilacion instalados a mano en el Python del sistema.
rem Python no se desinstala: si lo instalaste solo para esto, quitalo desde Configuracion, Aplicaciones.
setlocal
cd /d "%~dp0\.."
if not exist "herramientas\compilar.py" (
  echo Este archivo tiene que estar en la carpeta herramientas del proyecto.
  pause
  exit /b 1
)

echo Se borrara:
echo   - .venv-compilar (Python y paquetes que instalo compilar_windows.bat)
echo   - build y %USERPROFILE%\.creador-compilar (carpetas de trabajo)
echo   - la cache de descargas de pip
choice /c SN /m "Continuar"
if errorlevel 2 exit /b 0
if exist ".venv-compilar\" rmdir /s /q ".venv-compilar"
if exist "build\" rmdir /s /q "build"
if exist "%USERPROFILE%\.creador-compilar\" rmdir /s /q "%USERPROFILE%\.creador-compilar"
if exist "%LOCALAPPDATA%\pip\cache\" rmdir /s /q "%LOCALAPPDATA%\pip\cache"

echo.
choice /c SN /m "Borrar tambien la carpeta dist con los .zip ya compilados"
if not errorlevel 2 if exist "dist\" rmdir /s /q "dist"

echo.
echo Si instalaste PyInstaller u otros paquetes a mano en el Python del sistema (fuera de .venv-compilar),
echo se pueden quitar ahora. Di que no si los usas para otra cosa.
choice /c SN /m "Quitar pyinstaller, customtkinter, reportlab y pypdf del Python del sistema"
if errorlevel 2 goto :fin
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -m pip uninstall -y pyinstaller pyinstaller-hooks-contrib altgraph pefile pywin32-ctypes customtkinter darkdetect reportlab pypdf

:fin
echo.
echo Listo.
pause
