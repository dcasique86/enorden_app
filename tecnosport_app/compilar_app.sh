#!/bin/bash
# ================================================================
# ENORDEN - Script de compilación para macOS Apple Silicon
# ================================================================
# Uso: ./compilar_app.sh
# Esto crea EnOrden.app en la carpeta dist/
# ================================================================

set -e  # Detener en errores

echo ""
echo "================================================"
echo "  ENORDEN - Compilador para macOS"
echo "================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "desktop.py" ]; then
    echo "❌ Error: Ejecuta este script desde la carpeta tecnosport_app/"
    exit 1
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Verificar arquitectura
ARCH=$(uname -m)
echo "✅ Arquitectura: $ARCH"
if [ "$ARCH" != "arm64" ]; then
    echo "⚠️  Advertencia: Este script está optimizado para Apple Silicon (arm64)"
    echo "   Tu Mac es: $ARCH"
fi

# Crear entorno virtual si no existe
if [ ! -d "venv_desktop" ]; then
    echo ""
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv_desktop
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv_desktop/bin/activate

# Instalar dependencias
echo ""
echo "📥 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements_desktop.txt

# Limpiar compilaciones anteriores
echo ""
echo "🧹 Limpiando compilaciones anteriores..."
rm -rf build/ dist/ *.spec.bak

# Compilar con PyInstaller
echo ""
echo "🔨 Compilando aplicación..."
echo "   Esto puede tomar 2-5 minutos..."
echo ""

pyinstaller enorden.spec --clean

# Verificar resultado
if [ -d "dist/EnOrden.app" ]; then
    echo ""
    echo "================================================"
    echo "  ✅ ¡COMPILACIÓN EXITOSA!"
    echo "================================================"
    echo ""
    echo "📁 La aplicación está en: dist/EnOrden.app"
    echo ""
    echo "📋 Para instalar en Aplicaciones:"
    echo "   cp -r dist/EnOrden.app /Applications/"
    echo ""
    echo "📋 Para ejecutar directamente:"
    echo "   open dist/EnOrden.app"
    echo ""
else
    echo ""
    echo "❌ Error: La compilación falló"
    echo "   Revisa los mensajes de error arriba"
    exit 1
fi

# Desactivar entorno virtual
deactivate
