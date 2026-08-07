"""
Script de migración de Excel a SQLite para Tecnosport.
Lee datos_tecnosport.xlsx y rellena datos_tecnosport.db de forma segura.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime

# Definir rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH = os.path.join(BASE_DIR, "datos_tecnosport.xlsx")
SQLITE_PATH = os.path.join(BASE_DIR, "datos_tecnosport.db")

def crear_tablas(conn):
    """Crea la estructura de tablas relacionales en SQLite."""
    cursor = conn.cursor()
    
    # 1. Tabla clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        telefono TEXT,
        cedula TEXT,
        direccion TEXT,
        ciudad TEXT,
        fecha_creacion TEXT,
        activo INTEGER DEFAULT 1
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cedula ON clientes(cedula)")
    
    # 2. Tabla movimientos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id TEXT PRIMARY KEY,
        cliente_id TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'prestamo' o 'abono'
        descripcion TEXT,
        monto REAL NOT NULL,
        fecha TEXT,
        timestamp TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    );
    """)
    
    # 3. Tabla proveedores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedores (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        telefono TEXT,
        fecha_creacion TEXT,
        activo INTEGER DEFAULT 1
    );
    """)
    
    # 4. Tabla movimientos_proveedores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_proveedores (
        id TEXT PRIMARY KEY,
        proveedor_id TEXT NOT NULL,
        tipo TEXT NOT NULL, -- 'factura' o 'pago'
        descripcion TEXT,
        monto REAL NOT NULL,
        fecha TEXT,
        timestamp TEXT,
        FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
    );
    """)
    
    # 5. Tabla productos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        categoria TEXT,
        precio_compra REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        stock INTEGER DEFAULT 0,
        stock_minimo INTEGER DEFAULT 0,
        fecha_creacion TEXT,
        activo INTEGER DEFAULT 1,
        referencia TEXT -- Columna nueva
    );
    """)
    
    # 6. Tabla ventas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id TEXT PRIMARY KEY,
        producto_id TEXT NOT NULL,
        producto_nombre TEXT,
        cantidad INTEGER NOT NULL,
        precio_unitario REAL,
        total REAL,
        fecha TEXT,
        timestamp TEXT,
        nota TEXT,
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    );
    """)
    
    # 7. Tabla config
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config (
        clave TEXT PRIMARY KEY,
        valor TEXT,
        descripcion TEXT
    );
    """)
    
    conn.commit()
    print("[OK] Estructura de tablas en SQLite creada con éxito.")

def migrar_datos():
    if not os.path.exists(EXCEL_PATH):
        print(f"[ERROR] No se encontró el archivo Excel en {EXCEL_PATH}")
        return
        
    print(f"[INFO] Leyendo datos desde {EXCEL_PATH}...")
    excel_file = pd.ExcelFile(EXCEL_PATH)
    
    # Conectarse a SQLite (Borrando la anterior para asegurar recreación limpia de schemas)
    if os.path.exists(SQLITE_PATH):
        backup_db = os.path.join(BASE_DIR, f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        print(f"[WARN] La base de datos SQLite ya existe. Creando respaldo en {backup_db}...")
        try:
            import shutil
            shutil.copy2(SQLITE_PATH, backup_db)
            os.remove(SQLITE_PATH)
            print("[INFO] Base de datos SQLite previa eliminada para reconstrucción limpia.")
        except Exception as e:
            print(f"[ERROR] Error al recrear base de datos SQLite: {e}")

    conn = sqlite3.connect(SQLITE_PATH)
    crear_tablas(conn)
    
    # Mapeo de hojas Excel a tablas SQLite
    hojas_tablas = {
        "clientes": "clientes",
        "movimientos": "movimientos",
        "proveedores": "proveedores",
        "movimientos_proveedores": "movimientos_proveedores",
        "productos": "productos",
        "ventas": "ventas",
        "config": "config"
    }
    
    for hoja, tabla in hojas_tablas.items():
        if hoja in excel_file.sheet_names:
            print(f"[MIGRATE] Migrando hoja '{hoja}'...")
            df = pd.read_excel(EXCEL_PATH, sheet_name=hoja)
            
            # Limpiar nans
            df = df.where(pd.notnull(df), None)
            
            # En la hoja productos, agregar columna de referencia por si no existe
            if tabla == "productos" and "referencia" not in df.columns:
                df["referencia"] = None
                
            if len(df) == 0:
                print(f"[INFO] La hoja '{hoja}' está vacía. No hay datos que insertar.")
                continue
                
            cursor = conn.cursor()
            columnas = ", ".join(df.columns)
            placeholders = ", ".join(["?"] * len(df.columns))
            sql = f"INSERT OR REPLACE INTO {tabla} ({columnas}) VALUES ({placeholders})"
            
            datos = [tuple(row) for row in df.itertuples(index=False)]
            cursor.executemany(sql, datos)
            conn.commit()
            print(f"   [SUCCESS] {len(df)} registros insertados en la tabla '{tabla}'.")
        else:
            print(f"[WARN] La hoja '{hoja}' no existe en el archivo Excel.")
            
    conn.close()
    print("\n[FIN] ¡La migración de datos a SQLite se ha completado con éxito!")

if __name__ == "__main__":
    migrar_datos()
