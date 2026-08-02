#!/bin/bash

# =====================================================
# EnOrden - Launcher para macOS (doble clic)
# Centro Comercial El Diamante 2
# =====================================================

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear

echo -e "${BLUE}"
echo "=================================================="
echo "  🏪 ENORDEN - Sistema de Cuentas por Cobrar"
echo "  Centro Comercial El Diamante 2"
echo "=================================================="
echo -e "${NC}"

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado.${NC}"
    echo ""
    echo "Por favor, instala Python 3 desde:"
    echo "https://www.python.org/downloads/"
    echo ""
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo -e "${GREEN}✓ Python 3 encontrado${NC}"
echo -e "${GREEN}✓ Versión: $(python3 --version)${NC}"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creando entorno virtual (solo la primera vez)...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error al crear entorno virtual${NC}"
        read -p "Presiona Enter para salir..."
        exit 1
    fi
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
echo -e "${YELLOW}📦 Verificando dependencias...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al instalar dependencias${NC}"
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# Crear directorios necesarios
mkdir -p backups

echo ""
echo -e "${GREEN}🚀 Iniciando servidor...${NC}"
echo -e "${BLUE}🌐 Abriendo navegador: http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}⚡ PARA DETENER: Cierra esta ventana o presiona Ctrl+C${NC}"
echo ""

# Abrir navegador después de 2 segundos
(sleep 2 && open "http://localhost:8000") &

# Ejecutar servidor
python3 main.py
