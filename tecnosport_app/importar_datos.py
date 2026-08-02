"""
EnOrden - Importador de Datos Excel
Permite importar datos desde un archivo Excel existente
"""

import os
import sys
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
import uuid

# Configuración
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(SCRIPT_DIR, "datos_tecnosport.xlsx")


def detectar_estructura(archivo_path):
    """Detecta la estructura del archivo Excel"""
    try:
        df = pd.read_excel(archivo_path)
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


def importar_datos_simple(archivo_path, 
                          col_nombre='nombre',
                          col_telefono='telefono',
                          col_deuda='deuda',
                          col_abonos='abonos',
                          col_prestamos='prestamos',
                          hoja=0):
    """
    Importa datos desde un archivo Excel simple.
    
    Estructura esperada (ajustable):
    - nombre: Nombre del cliente
    - telefono: Teléfono (opcional)
    - deuda: Deuda actual (opcional si hay préstamos y abonos)
    - prestamos: Total prestado (opcional)
    - abonos: Total abonado (opcional)
    """
    
    print("\n" + "="*60)
    print("  📥 IMPORTADOR DE DATOS - ENORDEN")
    print("="*60)
    
    # Leer archivo origen
    try:
        df = pd.read_excel(archivo_path, sheet_name=hoja)
        print(f"\n✅ Archivo leído: {len(df)} registros")
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        return False
    
    # Limpiar datos
    df = df.dropna(subset=[col_nombre], how='all')
    df = df.fillna('')
    
    print(f"✅ Registros válidos: {len(df)}")
    
    # Cargar o crear archivo destino
    if not os.path.exists(EXCEL_PATH):
        print("\n📦 Creando base de datos nueva...")
        from database import db
    
    # Abrir archivo destino
    wb = load_workbook(EXCEL_PATH)
    ws_clientes = wb["clientes"]
    ws_movimientos = wb["movimientos"]
    
    clientes_importados = 0
    movimientos_importados = 0
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("\n📥 Importando clientes...")
    
    for idx, row in df.iterrows():
        try:
            # Obtener datos del cliente
            nombre = str(row.get(col_nombre, '')).strip()
            if not nombre or nombre == 'nan':
                continue
            
            telefono = str(row.get(col_telefono, '')).strip()
            if telefono == 'nan':
                telefono = ''
            
            # Crear ID de cliente
            cliente_id = str(uuid.uuid4())
            fecha_creacion = timestamp_actual
            
            # Agregar cliente
            ws_clientes.append([
                cliente_id,
                nombre,
                telefono,
                fecha_creacion,
                True  # activo
            ])
            
            clientes_importados += 1
            
            # Obtener valores financieros
            deuda = 0
            prestamos = 0
            abonos = 0
            
            # Intentar obtener deuda
            if col_deuda in df.columns:
                try:
                    deuda = float(row.get(col_deuda, 0) or 0)
                except:
                    deuda = 0
            
            # Intentar obtener préstamos
            if col_prestamos in df.columns:
                try:
                    prestamos = float(row.get(col_prestamos, 0) or 0)
                except:
                    prestamos = 0
            
            # Intentar obtener abonos
            if col_abonos in df.columns:
                try:
                    abonos = float(row.get(col_abonos, 0) or 0)
                except:
                    abonos = 0
            
            # Calcular valores si no están explícitos
            if deuda > 0 and prestamos == 0:
                prestamos = deuda + abonos
            
            # Crear movimiento de préstamo si hay monto
            if prestamos > 0:
                ws_movimientos.append([
                    str(uuid.uuid4()),
                    cliente_id,
                    'prestamo',
                    'Saldo inicial importado',
                    prestamos,
                    fecha_actual,
                    timestamp_actual
                ])
                movimientos_importados += 1
            
            # Crear movimiento de abono si hay monto
            if abonos > 0:
                ws_movimientos.append([
                    str(uuid.uuid4()),
                    cliente_id,
                    'abono',
                    'Abonos previos importados',
                    abonos,
                    fecha_actual,
                    timestamp_actual
                ])
                movimientos_importados += 1
            
            # Si solo hay deuda (sin desglose)
            if deuda > 0 and prestamos == 0 and abonos == 0:
                ws_movimientos.append([
                    str(uuid.uuid4()),
                    cliente_id,
                    'prestamo',
                    'Deuda inicial importada',
                    deuda,
                    fecha_actual,
                    timestamp_actual
                ])
                movimientos_importados += 1
                
        except Exception as e:
            print(f"   ⚠️ Error en fila {idx}: {e}")
            continue
    
    # Guardar archivo
    wb.save(EXCEL_PATH)
    
    print(f"\n✅ IMPORTACIÓN COMPLETADA")
    print(f"   👥 Clientes importados: {clientes_importados}")
    print(f"   📝 Movimientos creados: {movimientos_importados}")
    print(f"   💾 Guardado en: {EXCEL_PATH}")
    
    return True


def importar_con_historial(archivo_path, hoja_clientes=0, hoja_movimientos=1):
    """
    Importa datos cuando hay hoja separada de clientes y movimientos.
    """
    print("\n" + "="*60)
    print("  📥 IMPORTADOR CON HISTORIAL - ENORDEN")
    print("="*60)
    
    try:
        # Leer hoja de clientes
        df_clientes = pd.read_excel(archivo_path, sheet_name=hoja_clientes)
        print(f"\n👥 Clientes: {len(df_clientes)} registros")
        
        # Leer hoja de movimientos (si existe)
        try:
            df_movimientos = pd.read_excel(archivo_path, sheet_name=hoja_movimientos)
            print(f"📝 Movimientos: {len(df_movimientos)} registros")
            tiene_historial = True
        except:
            print("📝 Sin hoja de movimientos detectada")
            tiene_historial = False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Proceder con importación...
    # (similar a la función anterior pero con mapeo de IDs)
    
    return True


def modo_interactivo():
    """Modo interactivo para importar datos"""
    print("\n" + "="*60)
    print("  📥 IMPORTADOR INTERACTIVO - ENORDEN")
    print("="*60)
    
    # Pedir archivo
    print("\n📂 Ingresa la ruta de tu archivo Excel:")
    print("   (Puedes arrastrar el archivo a esta ventana)")
    archivo_path = input("\n   Ruta: ").strip().strip('"').strip("'")
    
    if not os.path.exists(archivo_path):
        print(f"❌ Archivo no encontrado: {archivo_path}")
        return
    
    # Detectar estructura
    columnas, df = detectar_estructura(archivo_path)
    
    if columnas is None:
        return
    
    # Mapear columnas
    print("\n" + "-"*60)
    print("🔗 MAPEO DE COLUMNAS")
    print("-"*60)
    
    print("\n¿Qué columna contiene el NOMBRE del cliente?")
    print(f"Columnas disponibles: {columnas}")
    col_nombre = input(f"Nombre [por defecto '{columnas[0]}']: ").strip() or columnas[0]
    
    print("\n¿Qué columna contiene el TELÉFONO? (Enter para saltar)")
    col_telefono = input("Teléfono: ").strip() or 'telefono'
    if col_telefono not in columnas:
        col_telefono = ''
    
    print("\n¿Qué columna contiene la DEUDA actual? (Enter para saltar)")
    col_deuda = input("Deuda: ").strip() or 'deuda'
    
    print("\n¿Qué columna contiene el total PRESTADO? (Enter para saltar)")
    col_prestamos = input("Prestamos: ").strip() or 'prestamos'
    
    print("\n¿Qué columna contiene el total ABONADO? (Enter para saltar)")
    col_abonos = input("Abonos: ").strip() or 'abonos'
    
    # Confirmar
    print("\n" + "-"*60)
    print("📋 RESUMEN DE IMPORTACIÓN:")
    print(f"   Archivo: {archivo_path}")
    print(f"   Registros: {len(df)}")
    print(f"   Columna nombre: {col_nombre}")
    print(f"   Columna teléfono: {col_telefono or '(no importar)'}")
    print(f"   Columna deuda: {col_deuda or '(no importar)'}")
    print(f"   Columna préstamos: {col_prestamos or '(no importar)'}")
    print(f"   Columna abonos: {col_abonos or '(no importar)'}")
    
    confirmar = input("\n¿Proceder con la importación? (s/n): ").strip().lower()
    
    if confirmar == 's':
        importar_datos_simple(
            archivo_path,
            col_nombre=col_nombre,
            col_telefono=col_telefono,
            col_deuda=col_deuda,
            col_prestamos=col_prestamos,
            col_abonos=col_abonos
        )
    else:
        print("❌ Importación cancelada")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Modo directo con archivo
        archivo_path = sys.argv[1]
        if os.path.exists(archivo_path):
            detectar_estructura(archivo_path)
            print("\n" + "-"*60)
            confirmar = input("¿Deseas importar estos datos? (s/n): ").strip().lower()
            if confirmar == 's':
                modo_interactivo()
        else:
            print(f"❌ Archivo no encontrado: {archivo_path}")
    else:
        # Modo interactivo
        modo_interactivo()
