@echo off
REM =====================================================
REM EnOrden - Script de Inicio para Windows
REM =====================================================

cd /d "%~dp0"

echo.
echo ====================================================
echo   ENORDEN - Sistema de Cuentas por Cobrar
echo   Centro Comercial El Diamante 2
echo ====================================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Por favor instala Python 3 desde:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Durante la instalacion, marca la opcion
    echo "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo.
    echo Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        echo Asegurate de tener permisos de escritura en esta carpeta.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
)

REM Activar entorno virtual
echo.
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Actualizar pip (ignorar advertencias)
echo.
echo Verificando pip...
python -m pip install --upgrade pip --quiet 2>nul

REM Instalar dependencias
echo Instalando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] No se pudieron instalar las dependencias.
    echo Revisa el mensaje anterior y verifica tu conexion a internet.
    pause
    exit /b 1
)

REM Verificar imports principales
python -c "import fastapi, uvicorn, pandas, openpyxl, jinja2, pydantic"
if errorlevel 1 (
    echo [ERROR] El entorno virtual quedo incompleto o danado.
    echo Borra la carpeta venv y ejecuta este archivo otra vez.
    pause
    exit /b 1
)

echo [OK] Dependencias listas

echo.
echo ====================================================
echo   Iniciando servidor...
echo   La aplicacion se abrira en tu navegador.
echo   URL: http://localhost:8000
echo ====================================================
echo.
echo Presiona Ctrl+C para detener el servidor.
echo.

REM Esperar un momento antes de abrir el navegador
timeout /t 2 /nobreak >nul

REM Abrir navegador
start http://localhost:8000

REM Ejecutar servidor
python main.py

echo.
echo Servidor detenido.
pause
