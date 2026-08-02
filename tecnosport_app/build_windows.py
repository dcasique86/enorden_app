import os
import sys
import shutil
import PyInstaller.__main__

def build():
    print("================================================")
    print("  ENORDEN - Compilador para Windows")
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

    # Argumentos para PyInstaller
    args = [
        'main.py',
        '--name=EnOrden',
        '--onefile',
        '--console',
        '--clean',
        '--add-data=templates;templates',
        '--add-data=static;static',
    ]
    
    print("\nEjecutando compilador PyInstaller...")
    print(f"Comando: pyinstaller {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n================================================")
        print("  ¡COMPILACIÓN EXITOSA!")
        print("================================================")
        exe_path = os.path.join(base_dir, 'dist', 'EnOrden.exe')
        print(f"\nEjecutable creado en: {exe_path}")
        print("\nPara ejecutar:")
        print("1. Copia EnOrden.exe a cualquier carpeta.")
        print("2. Haz doble clic en el archivo.")
        print("3. Se abrirá la consola indicando que el servidor está activo y el navegador se lanzará automáticamente.")
        print("4. Para apagar la app, simplemente cierra la ventana de la consola.")
    except Exception as e:
        print(f"\n❌ Error en la compilación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
