import os
import sys
import shutil
import PyInstaller.__main__

def build():
    print("================================================")
    print("  ENORDEN - Compilador para macOS (Apple Silicon)")
    print("================================================")
    
    # Directorio base
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    # Limpiar compilaciones anteriores
    print("\nLimpiando compilaciones anteriores...")
    for folder in ['build', 'dist']:
        path = os.path.join(base_dir, folder)
        if os.path.exists(path):
            print(f"Eliminando carpeta: {folder}")
            shutil.rmtree(path)
            
    spec_file = os.path.join(base_dir, 'EnOrden.spec')
    if os.path.exists(spec_file):
        print("Eliminando archivo spec anterior...")
        os.remove(spec_file)

    # Separador de path para PyInstaller (--add-data)
    # macOS/Linux utiliza ':', Windows utiliza ';'
    separator = ':' if sys.platform != 'win32' else ';'
    
    # Argumentos para PyInstaller
    args = [
        'main.py',
        '--name=EnOrden',
        '--onefile',
        '--console',
        '--clean',
        f'--add-data=templates{separator}templates',
        f'--add-data=static{separator}static',
    ]
    
    print("\nEjecutando compilador PyInstaller...")
    print(f"Comando: pyinstaller {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n================================================")
        print("  ¡COMPILACIÓN EXITOSA EN MAC!")
        print("================================================")
        exe_path = os.path.join(base_dir, 'dist', 'EnOrden')
        print(f"\nEjecutable Unix creado en: {exe_path}")
        print("\nPara ejecutar en tu Mac:")
        print("1. Abre la Terminal y ve a la carpeta dist/ (`cd dist`)")
        print("2. Dale permisos de ejecución: `chmod +x EnOrden` (si es necesario)")
        print("3. Ejecuta con: `./EnOrden` o hazle doble clic en el Finder.")
    except Exception as e:
        print(f"\n❌ Error en la compilación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
