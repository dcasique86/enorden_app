#!/bin/bash

# =====================================================
# EnOrden - Script de Inicio para macOS
# Centro Comercial El Diamante 2
# =====================================================

# Obtener directorio del script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=================================================="
echo "  🏪 ENORDEN - Sistema de Cuentas por Cobrar"
echo "  Centro Comercial El Diamante 2"
echo "=================================================="
echo -e "${NC}"

# Verificar si Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado.${NC}"
    echo "Por favor, instala Python 3 desde: https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 encontrado${NC}"

# Verificar si pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠ pip3 no encontrado, instalando...${NC}"
    python3 -m ensurepip --upgrade
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creando entorno virtual...${NC}"
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar/actualizar dependencias
echo -e "${YELLOW}📦 Verificando dependencias...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# Crear archivo de datos si no existe
if [ ! -f "datos_tecnosport.xlsx" ]; then
    echo -e "${YELLOW}📊 Creando base de datos inicial...${NC}"
fi

# Crear directorio de backups si no existe
mkdir -p backups

# Abrir navegador en segundo plano
sleep 2 && open "http://localhost:8000" &

echo ""
echo -e "${GREEN}🚀 Iniciando servidor...${NC}"
echo -e "${BLUE}🌐 La aplicación se abrirá en tu navegador${NC}"
echo -e "${YELLOW}⚡ Presiona Ctrl+C para detener el servidor${NC}"
echo ""

# Ejecutar servidor
python3 main.py
