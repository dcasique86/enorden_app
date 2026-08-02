#!/bin/bash
# ================================================================
# ENORDEN - Script de instalación y compilación para macOS
# Optimizado para MacBook Air M3 (Apple Silicon / ARM64)
# ================================================================

# Detener ante cualquier error
set -e

# Obtener el directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colores para la salida
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================"
echo "  ENORDEN - Preparando entorno y compilando en Mac"
echo -e "================================================${NC}\n"

# 1. Verificar si Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 no está instalado en este Mac.${NC}"
    echo "Por favor instala Python 3 desde https://www.python.org/downloads/ antes de continuar."
    exit 1
fi

echo -e "${GREEN}✓ Python 3 detectado: $(python3 --version)${NC}"

# 2. Crear entorno virtual si no existe
if [ ! -d "venv_mac" ]; then
    echo -e "\n${YELLOW}📦 Creando entorno virtual local (venv_mac)...${NC}"
    python3 -m venv venv_mac
fi

# 3. Activar entorno virtual
echo -e "${GREEN}✓ Activando entorno virtual...${NC}"
source venv_mac/bin/activate

# 4. Actualizar pip e instalar dependencias
echo -e "\n${YELLOW}📥 Instalando dependencias necesarias...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
echo -e "${GREEN}✓ Dependencias listas.${NC}"

# 5. Ejecutar compilación con build_mac.py
echo -e "\n${YELLOW}🔨 Iniciando compilación de la aplicación...${NC}"
python3 build_mac.py

# 6. Finalización e instrucciones
echo -e "\n${GREEN}================================================"
echo "  🎉 PROCESO COMPLETADO CON ÉXITO!"
echo -e "================================================"
echo -e "El ejecutable nativo para Mac está listo en: ${BLUE}dist/EnOrden${NC}"
echo ""
echo "📋 Para ejecutarlo:"
echo "  1. Abre Finder y navega a la carpeta 'dist/' de este proyecto."
echo "  2. Haz doble clic en el archivo 'EnOrden' (se abrirá una terminal)."
echo "  3. El navegador abrirá automáticamente http://localhost:8000."
echo "  4. Para apagar la app, cierra la ventana de la Terminal."
echo ""
echo -e "${YELLOW}⚠️  Nota de Seguridad de macOS (Primera Ejecución):${NC}"
echo "Si macOS dice que no puede verificar el desarrollador:"
echo "  - Ve a Ajustes del Sistema > Privacidad y Seguridad."
echo "  - Baja hasta la sección de seguridad y haz clic en 'Permitir de todos modos'."
echo "================================================${NC}"

# Desactivar venv_mac al finalizar
deactivate
