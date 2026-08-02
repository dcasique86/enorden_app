#!/bin/bash

# =====================================================
# EnOrden - Script de Configuración Inicial
# Ejecutar este script la primera vez
# =====================================================

clear

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║     🏪 ENORDEN - Configuración Inicial           ║"
echo "║     Centro Comercial El Diamante 2               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Obtener directorio
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Directorio de instalación: $SCRIPT_DIR"
echo ""

# Dar permisos de ejecución
echo "🔧 Configurando permisos..."
chmod +x EnOrden.command 2>/dev/null
chmod +x iniciar.sh 2>/dev/null
chmod +x crear_app.sh 2>/dev/null
echo "✓ Permisos configurados"
echo ""

# Verificar Python
echo "🐍 Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ $PYTHON_VERSION encontrado"
else
    echo "❌ Python 3 no está instalado"
    echo ""
    echo "Por favor instala Python 3 desde:"
    echo "https://www.python.org/downloads/"
    echo ""
    echo "Después de instalar Python, ejecuta este script nuevamente."
    read -p "Presiona Enter para salir..."
    exit 1
fi
echo ""

# Crear entorno virtual
echo "📦 Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Error al crear entorno virtual"
        echo "Intenta ejecutar: python3 -m venv venv"
        read -p "Presiona Enter para salir..."
        exit 1
    fi
    echo "✓ Entorno virtual creado"
else
    echo "✓ Entorno virtual ya existe"
fi
echo ""

# Instalar dependencias
echo "📥 Instalando dependencias..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Error al instalar dependencias"
    read -p "Presiona Enter para salir..."
    exit 1
fi
echo "✓ Dependencias instaladas"
echo ""

# Crear directorios
mkdir -p backups
echo "✓ Directorio de backups creado"
echo ""

# Crear acceso directo en el escritorio (opcional)
echo ""
echo "═════════════════════════════════════════════════════"
echo ""
echo "✅ ¡CONFIGURACIÓN COMPLETADA!"
echo ""
echo "═════════════════════════════════════════════════════"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo ""
echo "   1. Para INICIAR la aplicación:"
echo "      → Doble clic en: EnOrden.command"
echo ""
echo "   2. Para crear un icono de app:"
echo "      → Doble clic en: crear_app.sh"
echo "      → Se creará EnOrden.app"
echo ""
echo "   3. La aplicación se abrirá en:"
echo "      → http://localhost:8000"
echo ""
echo "═════════════════════════════════════════════════════"
echo ""

read -p "¿Deseas iniciar la aplicación ahora? (s/n): " respuesta
if [[ $respuesta == "s" || $respuesta == "S" ]]; then
    echo ""
    echo "🚀 Iniciando EnOrden..."
    ./EnOrden.command
fi
