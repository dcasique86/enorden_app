#!/bin/bash
# ================================================================
# ENORDEN - Script para empaquetar la app en un instalador DMG
# Funciona en macOS local y en pipelines de GitHub Actions
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
NC='\033[0m'

echo -e "${BLUE}================================================"
echo "  ENORDEN - Compilando y Creando Instalador DMG"
echo -e "================================================${NC}\n"

# 1. Compilar ejecutable Unix
echo -e "${YELLOW}1. Ejecutando compilación del binario...${NC}"
python3 build_mac.py

# 2. Preparar carpeta temporal para el DMG
echo -e "\n${YELLOW}2. Creando estructura de archivos del instalador...${NC}"
DMG_TEMP_DIR="dmg_temp"
rm -rf "$DMG_TEMP_DIR"
mkdir -p "$DMG_TEMP_DIR"

# Copiar el ejecutable compilado a la carpeta temporal
cp dist/EnOrden "$DMG_TEMP_DIR/"

# Crear un enlace simbólico a la carpeta /Applications de macOS
# Esto permite la acción clásica de arrastrar y soltar para instalar
ln -s /Applications "$DMG_TEMP_DIR/Aplicaciones (Arrastra aquí)"

# 3. Construir la imagen de disco (.dmg) usando la herramienta nativa de macOS hdiutil
echo -e "\n${YELLOW}3. Empaquetando en imagen de disco (.dmg)...${NC}"
DMG_OUTPUT="EnOrden_Instalador.dmg"
rm -f "$DMG_OUTPUT"

hdiutil create -volname "EnOrden Instalador" -srcfolder "$DMG_TEMP_DIR" -ov -format UDZO "$DMG_OUTPUT"

# 4. Limpieza
echo -e "\n${YELLOW}4. Limpiando archivos temporales...${NC}"
rm -rf "$DMG_TEMP_DIR"

echo -e "\n${GREEN}================================================"
echo "  🎉 INSTALADOR DMG CREADO CON ÉXITO!"
echo -e "================================================"
echo -e "Ubicación: ${BLUE}${SCRIPT_DIR}/${DMG_OUTPUT}${NC}"
echo "================================================"
