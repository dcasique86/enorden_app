#!/bin/bash

# =====================================================
# EnOrden - Script para crear .app de macOS
# =====================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_NAME="EnOrden"
APP_DIR="$SCRIPT_DIR/$APP_NAME.app"

echo "🏪 Creando aplicación $APP_NAME.app..."

# Crear estructura del .app
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Copiar todos los archivos del proyecto a Resources
cp -R "$SCRIPT_DIR"/* "$APP_DIR/Contents/Resources/" 2>/dev/null

# Crear el ejecutable
cat > "$APP_DIR/Contents/MacOS/$APP_NAME" << 'LAUNCHER'
#!/bin/bash

# Obtener directorio Resources
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"

cd "$RESOURCES_DIR"

# Ejecutar en segundo plano sin terminal
if [ -d "venv" ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
fi

# Abrir navegador después de 2 segundos
(sleep 2 && open "http://localhost:8000") &

# Ejecutar servidor
python3 main.py
LAUNCHER

chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"

# Crear Info.plist
cat > "$APP_DIR/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>EnOrden</string>
    <key>CFBundleDisplayName</key>
    <string>EnOrden</string>
    <key>CFBundleIdentifier</key>
    <string>com.enorden.app</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>EnOrden</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST

echo "✅ Aplicación creada: $APP_DIR"
echo ""
echo "📋 Para usar:"
echo "   1. Arrastra $APP_NAME.app a Aplicaciones"
echo "   2. Doble clic para ejecutar"
echo ""
echo "⚠️  Primera vez: Click derecho > Abrir (para autorizar)"
