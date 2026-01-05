@echo off
echo ========================================
echo   Compilando Siigo DIAN (PyInstaller)
echo ========================================
echo.

REM Verificar Python
python --version
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    pause
    exit /b 1
)

echo.
echo [1/4] Instalando dependencias...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

echo.
echo [2/4] Limpiando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/4] Compilando...
pyinstaller --noconfirm --onedir --windowed ^
    --name "SiigoDIAN" ^
    --add-data "services;services" ^
    --add-data "views;views" ^
    --add-data ".env;." ^
    --hidden-import=flet ^
    --hidden-import=flet_core ^
    --hidden-import=flet_runtime ^
    --hidden-import=sqlalchemy.dialects.mysql.pymysql ^
    --hidden-import=pymysql ^
    --hidden-import=qrcode ^
    --hidden-import=qrcode.image.pil ^
    --hidden-import=PIL ^
    --hidden-import=reportlab ^
    --hidden-import=reportlab.pdfgen ^
    --hidden-import=reportlab.lib ^
    --collect-all=flet ^
    --collect-all=flet_core ^
    --collect-all=flet_runtime ^
    main.py

echo.
echo [4/4] Limpiando archivos temporales...
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
if exist SiigoDIAN.spec del SiigoDIAN.spec

echo.
echo ========================================
echo   Compilacion completada!
echo   El ejecutable esta en: dist\SiigoDIAN\SiigoDIAN.exe
echo ========================================
pause
