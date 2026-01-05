@echo off
echo ========================================
echo   Compilando FacturaPro
echo ========================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist main.py (
    echo ERROR: Ejecute este script desde la carpeta del proyecto
    pause
    exit /b 1
)

REM Limpiar builds anteriores
echo Limpiando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Compilar con PyInstaller
echo.
echo Compilando aplicacion...
pyinstaller FacturaPro.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Compilacion exitosa!
echo   El ejecutable esta en: dist\FacturaPro.exe
echo ========================================
echo.

REM Copiar .env.example a dist
copy .env.example dist\.env.example >nul 2>&1

echo Archivos generados:
dir dist\*.exe

pause
