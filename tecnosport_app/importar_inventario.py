import os
import sys
import uuid
import pandas as pd
import sqlite3
from datetime import datetime

# Configuración
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "datos_tecnosport.db")

def detectar_estructura(archivo_path):
    try:
        # Intentar leer primero saltando posibles filas vacías si hay problemas
        df = pd.read_excel(archivo_path)
        
        # Limpiar nombres de columnas si están corruptos
        df.columns = [str(c).strip() for c in df.columns]
        
        columnas = list(df.columns)
        print(f"\n📊 Archivo detectado: {archivo_path}")
        print(f"📋 Columnas encontradas ({len(columnas)}):")
        for i, col in enumerate(columnas, 1):
            print(f"   {i}. {col}")
        
        print(f"\n📏 Total filas: {len(df)}")
        print(f"\n📝 Primeras 3 filas:")
        print(df.head(3).to_string())
        
        return columnas, df
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        return None, None

def importar_inventario(df, archivo_path, col_nombre, col_categoria, col_precio_compra, col_precio_venta, col_stock, col_referencia):
    print("\n" + "="*60)
    print("  📥 IMPORTADOR DE INVENTARIO - ENORDEN")
    print("="*60)
    
    # Limpiar datos
    df = df.dropna(subset=[col_nombre], how='all')
    df = df.fillna('')
    
    print(f"✅ Registros a importar: {len(df)}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    productos_importados = 0
    fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for idx, row in df.iterrows():
        try:
            nombre = str(row.get(col_nombre, '')).strip()
            if not nombre or nombre.lower() == 'nan':
                continue
            
            categoria = str(row.get(col_categoria, '')) if col_categoria else ''
            if categoria.lower() == 'nan': categoria = ''
                
            referencia = str(row.get(col_referencia, '')) if col_referencia else ''
            if referencia.lower() == 'nan': referencia = ''
            
            # Obtener valores numéricos con manejo seguro
            def parse_float(val):
                try:
                    if str(val).strip() == '' or str(val).lower() == 'nan': return 0.0
                    # Limpiar posibles símbolos de moneda o comas
                    v = str(val).replace('$', '').replace(',', '').strip()
                    return float(v)
                except:
                    return 0.0
                    
            def parse_int(val):
                try:
                    if str(val).strip() == '' or str(val).lower() == 'nan': return 0
                    v = str(val).replace(',', '').strip()
                    return int(float(v))
                except:
                    return 0
            
            precio_compra = parse_float(row.get(col_precio_compra, 0)) if col_precio_compra else 0.0
            precio_venta = parse_float(row.get(col_precio_venta, 0)) if col_precio_venta else 0.0
            stock = parse_int(row.get(col_stock, 0)) if col_stock else 0
            
            producto_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO productos 
                (id, nombre, categoria, precio_compra, precio_venta, stock, stock_minimo, fecha_creacion, activo, referencia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (producto_id, nombre, categoria, precio_compra, precio_venta, stock, 0, fecha_creacion, 1, referencia))
            
            productos_importados += 1
            
        except Exception as e:
            print(f"   ⚠️ Error en fila {idx}: {e}")
            continue
            
    conn.commit()
    conn.close()
    
    print(f"\n✅ IMPORTACIÓN COMPLETADA")
    print(f"   📦 Productos importados a la base de datos: {productos_importados}")
    
    return True

def modo_interactivo():
    print("\n" + "="*60)
    print("  📦 IMPORTADOR DE INVENTARIO - ENORDEN")
    print("="*60)
    
    print("\n📂 Ingresa la ruta de tu archivo Excel (o arrástralo a esta ventana):")
    archivo_path = input("\n   Ruta: ").strip().strip('"').strip("'")
    
    if not os.path.exists(archivo_path):
        print(f"❌ Archivo no encontrado: {archivo_path}")
        return
        
    columnas, df = detectar_estructura(archivo_path)
    
    if columnas is None:
        return
        
    print("\n" + "-"*60)
    print("🔗 MAPEO DE COLUMNAS PARA INVENTARIO")
    print("-"*60)
    
    print("\n¿Qué columna contiene el NOMBRE del producto? (Obligatorio)")
    print(f"Columnas disponibles: {columnas}")
    col_nombre = input(f"Nombre [por defecto '{columnas[0]}']: ").strip() or columnas[0]
    
    print("\n¿Qué columna contiene el PRECIO DE VENTA? (Enter para saltar)")
    col_precio_venta = input("Precio Venta: ").strip()
    if col_precio_venta not in columnas: col_precio_venta = ''
    
    print("\n¿Qué columna contiene el PRECIO DE COMPRA/COSTO? (Enter para saltar)")
    col_precio_compra = input("Precio Compra: ").strip()
    if col_precio_compra not in columnas: col_precio_compra = ''
    
    print("\n¿Qué columna contiene la CANTIDAD EN STOCK? (Enter para saltar)")
    col_stock = input("Stock: ").strip()
    if col_stock not in columnas: col_stock = ''
    
    print("\n¿Qué columna contiene la CATEGORÍA? (Enter para saltar)")
    col_categoria = input("Categoría: ").strip()
    if col_categoria not in columnas: col_categoria = ''
        
    print("\n¿Qué columna contiene la REFERENCIA/CÓDIGO? (Enter para saltar)")
    col_referencia = input("Referencia: ").strip()
    if col_referencia not in columnas: col_referencia = ''
    
    print("\n" + "-"*60)
    print("📋 RESUMEN DE IMPORTACIÓN:")
    print(f"   Archivo: {archivo_path}")
    print(f"   Columna nombre: {col_nombre}")
    print(f"   Columna precio venta: {col_precio_venta or '(no importar)'}")
    print(f"   Columna precio compra: {col_precio_compra or '(no importar)'}")
    print(f"   Columna stock: {col_stock or '(no importar)'}")
    print(f"   Columna categoría: {col_categoria or '(no importar)'}")
    print(f"   Columna referencia: {col_referencia or '(no importar)'}")
    
    confirmar = input("\n¿Proceder con la importación? (s/n): ").strip().lower()
    
    if confirmar == 's':
        importar_inventario(df, archivo_path, col_nombre, col_categoria, col_precio_compra, col_precio_venta, col_stock, col_referencia)
    else:
        print("❌ Importación cancelada")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada en {DB_PATH}.")
        sys.exit(1)
        
    if len(sys.argv) > 1:
        archivo_path = sys.argv[1]
        if os.path.exists(archivo_path):
            detectar_estructura(archivo_path)
            print("\n" + "-"*60)
            confirmar = input("¿Deseas mapear e importar estos datos? (s/n): ").strip().lower()
            if confirmar == 's':
                modo_interactivo()
        else:
            print(f"❌ Archivo no encontrado: {archivo_path}")
    else:
        modo_interactivo()
