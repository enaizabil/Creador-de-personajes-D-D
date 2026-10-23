@echo off
rem Desinstalador del Creador de personajes portable (se copia como Desinstalar.bat junto al .exe).
rem Borra la carpeta del programa y la carpeta de paquetes del usuario; no toca nada mas.
setlocal
set "CARPETA=%~dp0"
set "CARPETA=%CARPETA:~0,-1%"
set "USUARIO=%USERPROFILE%\.creador-personajes"

rem Seguridad: solo actua si esta junto al programa (si se copia a otro sitio, no borra esa carpeta).
if not exist "%CARPETA%\CreadorPersonajes.exe" goto :fuera
if not exist "%CARPETA%\_internal\" goto :fuera
tasklist /fi "imagename eq CreadorPersonajes.exe" 2>nul | find /i "CreadorPersonajes.exe" >nul
if not errorlevel 1 goto :abierto

echo Se va a desinstalar el Creador de personajes. Se borrara:
echo   - Esta carpeta, con todo lo que tenga dentro (tambien los paquetes importados y
echo     los personajes que hayas guardado AQUI):
echo       "%CARPETA%"
if exist "%USUARIO%\" echo   - Tus paquetes de usuario: "%USUARIO%"
echo.
echo Lo que hayas guardado en otras carpetas (personajes, PDF, notas) no se toca.
echo El programa no crea accesos directos ni toca el registro de Windows.
echo.
choice /c SN /m "Desinstalar"
if errorlevel 2 goto :cancelar

if exist "%USUARIO%\" rmdir /s /q "%USUARIO%"
echo Pulsa una tecla para terminar: se borrara la carpeta y se cerrara esta ventana.
pause >nul
rem Las rutas siempre entre comillas: un ampersand sin comillas (como en "D y D" escrito con el simbolo) partiria la orden.
rem Se sale de la carpeta y se borra; este archivo desaparece con ella y cmd termina al no encontrar la linea siguiente.
cd /d "%TEMP%"
rmdir /s /q "%CARPETA%"
exit

:abierto
echo El Creador de personajes esta abierto. Cierralo y vuelve a ejecutar este archivo.
pause
exit /b 1

:cancelar
echo No se ha borrado nada.
pause
exit /b 0

:fuera
echo Este archivo tiene que estar en la carpeta del programa, junto a CreadorPersonajes.exe.
echo No se ha borrado nada.
pause
exit /b 1
