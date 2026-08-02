"""
Módulo de base de datos SQLite para EnOrden.
Maneja todas las operaciones con el archivo datos_tecnosport.db,
manteniendo compatibilidad de interfaz de DatabaseManager y cachés de pandas en memoria.
"""

import os
import uuid
import sqlite3
import threading
import shutil
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


class DatabaseManager:
    """Gestor de base de datos SQLite con compatibilidad de caché de dataframes en memoria"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            import sys
            if getattr(sys, "frozen", False):
                data_dir = os.path.dirname(sys.executable)
            else:
                data_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "datos_tecnosport.db")
        self.excel_path = os.path.join(data_dir, "datos_tecnosport.xlsx")  # Mantenido para descargas/backwards-compat
        self.backup_dir = os.path.join(data_dir, "backups")
        
        # Lock de concurrencia y caches en memoria para compatibilidad directa con repository.py
        self._lock = threading.Lock()
        self._cache_timestamp: Optional[datetime] = None
        self._cache_clientes: Optional[pd.DataFrame] = None
        self._cache_movimientos: Optional[pd.DataFrame] = None
        self._cache_proveedores: Optional[pd.DataFrame] = None
        self._cache_movimientos_proveedores: Optional[pd.DataFrame] = None
        self._cache_productos: Optional[pd.DataFrame] = None
        self._cache_ventas: Optional[pd.DataFrame] = None
        
        # Crear directorio de backups
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Inicializar base de datos SQLite
        self._initialize_database()
    
    def get_connection(self):
        """Abre y retorna una conexión a la base de datos SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Habilitar claves foráneas
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _initialize_database(self):
        """Crea las tablas relacionales iniciales en SQLite si no existen."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. clientes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                telefono TEXT,
                fecha_creacion TEXT,
                activo INTEGER DEFAULT 1
            );
            """)
            
            # 2. movimientos
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
            
            # 3. proveedores
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                telefono TEXT,
                fecha_creacion TEXT,
                activo INTEGER DEFAULT 1
            );
            """)
            
            # 4. movimientos_proveedores
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
            
            # 5. productos
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
                referencia TEXT
            );
            """)
            
            # 6. ventas
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
            
            # 7. config
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                descripcion TEXT
            );
            """)
            
            # 8. gastos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                categoria TEXT NOT NULL,
                monto REAL NOT NULL,
                descripcion TEXT
            );
            """)
            
            # 9. historial_precios
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_precios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                precio_compra_anterior REAL,
                precio_compra_nuevo REAL,
                precio_venta_anterior REAL,
                precio_venta_nuevo REAL,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            );
            """)
            
            # 10. telegram_users
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telegram_users (
                telegram_id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'operador' CHECK(rol IN ('super_admin', 'admin', 'operador')),
                activo INTEGER DEFAULT 1,
                fecha_registro TEXT DEFAULT (datetime('now', 'localtime'))
            );
            """)

            # Trigger para historial_precios
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_historial_precios
            AFTER UPDATE OF precio_compra, precio_venta ON productos
            FOR EACH ROW
            WHEN OLD.precio_compra != NEW.precio_compra OR OLD.precio_venta != NEW.precio_venta
            BEGIN
                INSERT INTO historial_precios (
                    producto_id, 
                    precio_compra_anterior, 
                    precio_compra_nuevo, 
                    precio_venta_anterior, 
                    precio_venta_nuevo
                ) VALUES (
                    OLD.id,
                    OLD.precio_compra,
                    NEW.precio_compra,
                    OLD.precio_venta,
                    NEW.precio_venta
                );
            END;
            """)
            
            conn.commit()
        finally:
            conn.close()

    # Métodos dummy o de compatibilidad no-op para evitar errores si se invocan
    def _create_inventory_sheets(self, wb, header_font): pass
    def _ensure_inventory_sheets(self): pass
    def _ensure_proveedores_sheets(self): pass
    def _ensure_config_sheet(self): pass

    def _load_cache(self):
        """Carga las tablas SQLite en dataframes de Pandas en memoria para compatibilidad de N+1 en repository.py."""
        with self._lock:
            if self._cache_timestamp is None or \
               (datetime.now() - self._cache_timestamp).total_seconds() > 5:
                conn = self.get_connection()
                try:
                    self._cache_clientes = pd.read_sql_query("SELECT * FROM clientes", conn)
                    self._cache_movimientos = pd.read_sql_query("SELECT * FROM movimientos", conn)
                    self._cache_proveedores = pd.read_sql_query("SELECT * FROM proveedores", conn)
                    self._cache_movimientos_proveedores = pd.read_sql_query("SELECT * FROM movimientos_proveedores", conn)
                    self._cache_productos = pd.read_sql_query("SELECT * FROM productos", conn)
                    self._cache_ventas = pd.read_sql_query("SELECT * FROM ventas", conn)
                    
                    # Convertir enteros de SQLite a tipos booleanos en los dataframes de cache para Pandas
                    for df in [self._cache_clientes, self._cache_proveedores, self._cache_productos]:
                        if len(df) > 0 and 'activo' in df.columns:
                            df['activo'] = df['activo'].astype(bool)
                finally:
                    conn.close()
                self._cache_timestamp = datetime.now()
    
    def _invalidate_cache(self):
        """Invalida la caché para forzar recarga en la siguiente lectura."""
        with self._lock:
            self._cache_timestamp = None

    def _format_telefono(self, tel: Any) -> str:
        """Convierte un teléfono a string de forma segura manejando float, NaN y None"""
        if pd.isna(tel) or tel is None:
            return ""
        if isinstance(tel, float):
            try:
                if tel == float('inf') or tel == float('-inf'):
                    return ""
                return str(int(tel)) if tel == int(tel) else str(tel)
            except (ValueError, OverflowError):
                return str(tel)
        return str(tel).strip()

    # ==================== GASTOS Y CAJA ====================
    
    def registrar_gasto(self, categoria: str, monto: float, descripcion: str) -> Dict[str, Any]:
        """Registra un nuevo gasto operativo en la base de datos."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO gastos (categoria, monto, descripcion) VALUES (?, ?, ?)",
                (categoria, monto, descripcion)
            )
            gasto_id = cursor.lastrowid
            conn.commit()
            
            cursor.execute("SELECT * FROM gastos WHERE id = ?", (gasto_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def obtener_gastos_por_fecha(self, fecha_inicio: str, fecha_fin: str) -> List[Dict[str, Any]]:
        """Obtiene los gastos operativos en un rango de fechas."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM gastos WHERE DATE(fecha) >= ? AND DATE(fecha) <= ? ORDER BY fecha DESC",
                (fecha_inicio, fecha_fin)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def obtener_resumen_caja_diaria(self, fecha: str = None) -> Dict[str, float]:
        """
        Calcula el resumen de caja diaria usando consultas directas en SQLite.
        Efectivo_Neto = (Ventas en Efectivo + Abonos) - (Pagos a Proveedores + Gastos)
        Si no se pasa fecha, asume el día de hoy.
        """
        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d")
            
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Suma de Ventas en Efectivo del día
            cursor.execute("SELECT SUM(total) FROM ventas WHERE DATE(fecha) = ?", (fecha,))
            ventas_total = cursor.fetchone()[0] or 0.0
            
            # 2. Suma de Abonos del día
            cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo = 'abono' AND DATE(fecha) = ?", (fecha,))
            abonos_total = cursor.fetchone()[0] or 0.0
            
            # 3. Suma de Pagos a Proveedores del día
            cursor.execute("SELECT SUM(monto) FROM movimientos_proveedores WHERE tipo = 'pago' AND DATE(fecha) = ?", (fecha,))
            pagos_prov_total = cursor.fetchone()[0] or 0.0
            
            # 4. Suma de Gastos del día
            cursor.execute("SELECT SUM(monto) FROM gastos WHERE DATE(fecha) = ?", (fecha,))
            gastos_total = cursor.fetchone()[0] or 0.0
        finally:
            conn.close()
        
        efectivo_neto = (ventas_total + abonos_total) - (pagos_prov_total + gastos_total)
        
        return {
            "fecha": fecha,
            "ventas_total": ventas_total,
            "abonos_total": abonos_total,
            "pagos_proveedores_total": pagos_prov_total,
            "gastos_total": gastos_total,
            "efectivo_neto": efectivo_neto
        }

    # ==================== CLIENTES ====================
    
    def get_clientes(self) -> List[Dict[str, Any]]:
        """Obtiene todos los clientes activos"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clientes WHERE activo = 1")
            rows = cursor.fetchall()
        finally:
            conn.close()
        
        clientes = [dict(row) for row in rows]
        for c in clientes:
            c['activo'] = bool(c['activo'])
            c['telefono'] = self._format_telefono(c['telefono'])
        return clientes
    
    def get_cliente_by_id(self, cliente_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un cliente por ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            row = cursor.fetchone()
        finally:
            conn.close()
        
        if not row:
            return None
            
        cliente = dict(row)
        cliente['activo'] = bool(cliente['activo'])
        cliente['telefono'] = self._format_telefono(cliente['telefono'])
        return cliente
    
    def buscar_clientes(self, query: str) -> List[Dict[str, Any]]:
        """Busca clientes por nombre o teléfono"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if not query or not query.strip():
                cursor.execute("SELECT * FROM clientes WHERE activo = 1 LIMIT 20")
            else:
                q = f"%{query.strip().lower()}%"
                cursor.execute(
                    "SELECT * FROM clientes WHERE activo = 1 AND (LOWER(nombre) LIKE ? OR telefono LIKE ?)",
                    (q, q)
                )
            rows = cursor.fetchall()
            
            clientes = [dict(row) for row in rows]
            for c in clientes:
                c['activo'] = bool(c['activo'])
                c['telefono'] = self._format_telefono(c['telefono'])
            return clientes
        except Exception as e:
            print(f"Error en buscar_clientes: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def crear_cliente(self, nombre: str, telefono: str = "") -> Dict[str, Any]:
        """Crea un nuevo cliente"""
        cliente_id = str(uuid.uuid4())
        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        telefono_str = str(telefono).strip() if telefono else ""
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO clientes (id, nombre, telefono, fecha_creacion, activo) VALUES (?, ?, ?, ?, 1)",
                (cliente_id, nombre, telefono_str, fecha_creacion)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        
        return {
            "id": cliente_id,
            "nombre": nombre,
            "telefono": telefono_str,
            "fecha_creacion": fecha_creacion,
            "activo": True
        }
    
    def actualizar_cliente(self, cliente_id: str, nombre: str = None, telefono: str = None) -> bool:
        """Actualiza datos de un cliente"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            updates = []
            params = []
            if nombre is not None:
                updates.append("nombre = ?")
                params.append(nombre)
            if telefono is not None:
                updates.append("telefono = ?")
                params.append(telefono)
                
            if not updates:
                return True
                
            params.append(cliente_id)
            cursor.execute(f"UPDATE clientes SET {', '.join(updates)} WHERE id = ?", params)
            rows_affected = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        return rows_affected > 0
    
    def eliminar_cliente(self, cliente_id: str) -> bool:
        """Elimina (desactiva) un cliente"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE clientes SET activo = 0 WHERE id = ?", (cliente_id,))
            rows_affected = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        return rows_affected > 0
    
    # ==================== MOVIMIENTOS ====================
    
    def get_movimiento_by_id(self, movimiento_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un movimiento por su ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos WHERE id = ?", (movimiento_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_movimientos(self, limite: int = 100) -> List[Dict[str, Any]]:
        """Obtiene los últimos movimientos"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos ORDER BY timestamp DESC LIMIT ?", (limite,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_movimientos_by_cliente(self, cliente_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los movimientos de un cliente"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos WHERE cliente_id = ? ORDER BY timestamp DESC", (cliente_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_movimientos_hoy(self) -> List[Dict[str, Any]]:
        """Obtiene movimientos del día actual"""
        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos WHERE fecha = ? ORDER BY timestamp DESC", (hoy,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def crear_movimiento(self, cliente_id: str, tipo: str, descripcion: str, monto: float,
                          tipo_operacion: Optional[str] = None,
                          estado_operacion: Optional[str] = None,
                          fecha_vencimiento: Optional[str] = None) -> Dict[str, Any]:
        """Crea un nuevo movimiento (préstamo o abono)
        
        Args:
            tipo_operacion: 'COMPRA' o 'PRESTAMO_MERCANCIA' (default: 'COMPRA')
            estado_operacion: 'COMPRA', 'PENDIENTE' o 'DEVUELTO' (default: 'COMPRA')
            fecha_vencimiento: fecha de vencimiento para préstamos de mercancía
        """
        movimiento_id = str(uuid.uuid4())
        fecha = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tipo_op = tipo_operacion or "COMPRA"
        estado_op = estado_operacion or "COMPRA"
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO movimientos (id, cliente_id, tipo, descripcion, monto, fecha, timestamp, "
                "tipo_operacion, estado_operacion, fecha_vencimiento) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (movimiento_id, cliente_id, tipo, descripcion, float(monto), fecha, timestamp,
                 tipo_op, estado_op, fecha_vencimiento)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        
        return {
            "id": movimiento_id,
            "cliente_id": cliente_id,
            "tipo": tipo,
            "descripcion": descripcion,
            "monto": float(monto),
            "fecha": fecha,
            "timestamp": timestamp,
            "tipo_operacion": tipo_op,
            "estado_operacion": estado_op,
            "fecha_vencimiento": fecha_vencimiento,
        }

    def crear_devolucion_cliente(self, cliente_id: str, descripcion: str, monto: float,
                                  observaciones: str = "", usuario: str = "") -> Dict[str, Any]:
        """Crea una devolución de cliente (DEVOLUCION_CLIENTE)"""
        movimiento_id = str(uuid.uuid4())
        fecha = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        descripcion_completa = f"DEVOLUCIÓN: {descripcion}"
        if observaciones:
            descripcion_completa += f" | Obs: {observaciones}"
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO movimientos (id, cliente_id, tipo, descripcion, monto, fecha, timestamp, "
                "tipo_operacion, estado_operacion, fecha_vencimiento) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), cliente_id, 'abono', descripcion_completa, float(monto), 
                 datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 'DEVOLUCION_CLIENTE', 'COMPRA', None)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        
        return {
            "id": movimiento_id,
            "cliente_id": cliente_id,
            "tipo": "abono",
            "descripcion": descripcion_completa,
            "monto": float(monto),
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_operacion": "DEVOLUCION_CLIENTE",
            "estado_operacion": "COMPRA",
            "fecha_vencimiento": None,
        }

    def crear_devolucion_proveedor(self, proveedor_id: str, descripcion: str, monto: float,
                                    observaciones: str = "", usuario: str = "") -> Dict[str, Any]:
        """Crea una devolución a proveedor (DEVOLUCION_PROVEEDOR)"""
        movimiento_id = str(uuid.uuid4())
        fecha = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        descripcion_completa = f"DEVOLUCIÓN A PROVEEDOR: {descripcion}"
        if observaciones:
            descripcion_completa += f" | Obs: {observaciones}"
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO movimientos_proveedores (id, proveedor_id, tipo, descripcion, monto, fecha, timestamp, "
                "tipo_operacion, estado_operacion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), proveedor_id, 'pago', f"DEVOLUCIÓN: {descripcion}", float(monto), 
                 datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 'DEVOLUCION_PROVEEDOR', 'COMPRA')
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        
        return {
            "id": str(uuid.uuid4()),
            "proveedor_id": proveedor_id,
            "tipo": "pago",
            "descripcion": f"DEVOLUCIÓN A PROVEEDOR: {descripcion}",
            "monto": float(monto),
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_operacion": "DEVOLUCION_PROVEEDOR",
            "estado_operacion": "COMPRA",
        }
    
    # ==================== RESÚMENES Y CÁLCULOS ====================
    
    def get_resumen_cliente(self, cliente_id: str) -> Dict[str, Any]:
        """Calcula el resumen financiero de un cliente"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT SUM(monto) FROM movimientos WHERE cliente_id = ? AND tipo = 'prestamo'", (cliente_id,))
            prestamos = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT SUM(monto) FROM movimientos WHERE cliente_id = ? AND tipo = 'abono'", (cliente_id,))
            abonos = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT MAX(timestamp) FROM movimientos WHERE cliente_id = ?", (cliente_id,))
            ultimo_mov = cursor.fetchone()[0]
        finally:
            conn.close()
        
        return {
            "total_prestado": float(prestamos),
            "total_abonado": float(abonos),
            "saldo": float(prestamos - abonos),
            "ultimo_movimiento": ultimo_mov
        }
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Obtiene todas las estadísticas del dashboard (calculadas eficientemente usando pandas cache)"""
        self._load_cache()
        
        clientes_df = self._cache_clientes.copy()
        if len(clientes_df) > 0 and 'activo' in clientes_df.columns:
            clientes_df = clientes_df[clientes_df['activo'] == True]
        
        movimientos_df = self._cache_movimientos.copy()
        
        # Totales generales
        if len(movimientos_df) > 0:
            total_prestado = movimientos_df[movimientos_df['tipo'] == 'prestamo']['monto'].sum()
            total_abonado = movimientos_df[movimientos_df['tipo'] == 'abono']['monto'].sum()
        else:
            total_prestado = 0.0
            total_abonado = 0.0
            
        deuda_activa = total_prestado - total_abonado
        clientes_activos = len(clientes_df)
        
        # Movimientos de hoy
        hoy = datetime.now().strftime("%Y-%m-%d")
        if len(movimientos_df) > 0:
            mov_hoy = movimientos_df[movimientos_df['fecha'] == hoy]
            prestamos_hoy = mov_hoy[mov_hoy['tipo'] == 'prestamo']['monto'].sum()
            abonos_hoy = mov_hoy[mov_hoy['tipo'] == 'abono']['monto'].sum()
            devoluciones_hoy = mov_hoy[
                (mov_hoy['tipo'] == 'abono') & 
                (mov_hoy['tipo_operacion'].isin(['DEVOLUCION_CLIENTE', 'DEVOLUCION_PROVEEDOR']))
            ]['monto'].sum()
            devoluciones_cliente_hoy = mov_hoy[
                (mov_hoy['tipo'] == 'abono') & 
                (mov_hoy['tipo_operacion'] == 'DEVOLUCION_CLIENTE')
            ]['monto'].sum()
            devoluciones_proveedor_hoy = mov_hoy[
                mov_hoy['tipo_operacion'] == 'DEVOLUCION_PROVEEDOR'
            ]['monto'].sum()
            devoluciones_hoy_cnt = len(mov_hoy[
                mov_hoy['tipo_operacion'].isin(['DEVOLUCION_CLIENTE', 'DEVOLUCION_PROVEEDOR'])
            ])
            movimientos_hoy_cnt = len(mov_hoy)
        else:
            prestamos_hoy = 0.0
            abonos_hoy = 0.0
            devoluciones_hoy = 0.0
            devoluciones_cliente_hoy = 0.0
            devoluciones_proveedor_hoy = 0.0
            devoluciones_hoy_cnt = 0
            movimientos_hoy_cnt = 0
        
        # Top 5 clientes con mayor deuda y buckets
        clientes_deuda = []
        cartera_antiguedad = [
            {"label": "0-7 dias", "min": 0, "max": 7, "total": 0.0, "clientes": 0},
            {"label": "8-30 dias", "min": 8, "max": 30, "total": 0.0, "clientes": 0},
            {"label": "31-60 dias", "min": 31, "max": 60, "total": 0.0, "clientes": 0},
            {"label": "61-90 dias", "min": 61, "max": 90, "total": 0.0, "clientes": 0},
            {"label": "90+ dias", "min": 91, "max": None, "total": 0.0, "clientes": 0},
        ]
        cola_cobro = []
        hoy_date = datetime.now().date()

        for _, cliente in clientes_df.iterrows():
            resumen = self.get_resumen_cliente(cliente['id'])
            if resumen['saldo'] > 0:
                c_id = cliente['id']
                if len(movimientos_df) > 0:
                    movs_cliente = movimientos_df[movimientos_df['cliente_id'] == c_id]
                    abonos_cliente = movs_cliente[movs_cliente['tipo'] == 'abono']
                    prestamos_cliente = movs_cliente[movs_cliente['tipo'] == 'prestamo']
                else:
                    abonos_cliente = pd.DataFrame()
                    prestamos_cliente = pd.DataFrame()
                    
                referencia_fecha = None
                ultimo_abono_fecha = None

                if len(abonos_cliente) > 0:
                    ultimo_abono_fecha = abonos_cliente['fecha'].max()
                    referencia_fecha = ultimo_abono_fecha
                elif len(prestamos_cliente) > 0:
                    referencia_fecha = prestamos_cliente['fecha'].min()

                dias_sin_abonar = None
                if referencia_fecha:
                    try:
                        dias_sin_abonar = max((hoy_date - datetime.strptime(str(referencia_fecha), "%Y-%m-%d").date()).days, 0)
                    except Exception:
                        dias_sin_abonar = None

                dias_bucket = dias_sin_abonar if dias_sin_abonar is not None else 999
                for bucket in cartera_antiguedad:
                    if dias_bucket >= bucket["min"] and (bucket["max"] is None or dias_bucket <= bucket["max"]):
                        bucket["total"] += float(resumen['saldo'])
                        bucket["clientes"] += 1
                        break

                prioridad = "alta" if dias_bucket >= 31 else "media" if dias_bucket >= 8 else "normal"
                proxima_accion = "Enviar recordatorio"
                if dias_bucket >= 90:
                    proxima_accion = "Revisar acuerdo de pago"
                elif dias_bucket >= 31:
                    proxima_accion = "Llamar y confirmar fecha de abono"

                clientes_deuda.append({
                    "id": cliente['id'],
                    "nombre": cliente['nombre'],
                    "telefono": cliente.get('telefono', ''),
                    "saldo": resumen['saldo'],
                    "dias_sin_abonar": dias_sin_abonar,
                    "ultimo_abono": ultimo_abono_fecha
                })
                cola_cobro.append({
                    "id": cliente['id'],
                    "nombre": cliente['nombre'],
                    "telefono": cliente.get('telefono', ''),
                    "saldo": resumen['saldo'],
                    "dias_sin_abonar": dias_sin_abonar,
                    "prioridad": prioridad,
                    "proxima_accion": proxima_accion
                })
        
        clientes_deuda.sort(key=lambda x: x['saldo'], reverse=True)
        top_deudores = clientes_deuda[:5]
        
        cola_cobro.sort(key=lambda x: (
            999 if x.get('dias_sin_abonar') is None else x.get('dias_sin_abonar'),
            x.get('saldo', 0)
        ), reverse=True)
        
        # Clientes sin abonos en X días (default 30)
        dias_sin_abono = 30
        fecha_limite = (datetime.now() - timedelta(days=dias_sin_abono)).strftime("%Y-%m-%d")
        
        clientes_sin_abonos = []
        for _, cliente in clientes_df.iterrows():
            c_id = cliente['id']
            if len(movimientos_df) > 0:
                movs_cliente = movimientos_df[movimientos_df['cliente_id'] == c_id]
                abonos_cliente = movs_cliente[movs_cliente['tipo'] == 'abono']
            else:
                abonos_cliente = pd.DataFrame()
                
            if len(abonos_cliente) == 0:
                resumen = self.get_resumen_cliente(c_id)
                if resumen['saldo'] > 0:
                    clientes_sin_abonos.append({
                        "id": c_id,
                        "nombre": cliente['nombre'],
                        "saldo": resumen['saldo'],
                        "dias": "Nunca"
                    })
            else:
                ultimo_abono = abonos_cliente['fecha'].max()
                if ultimo_abono < fecha_limite:
                    resumen = self.get_resumen_cliente(c_id)
                    if resumen['saldo'] > 0:
                        dias = (datetime.now() - datetime.strptime(ultimo_abono, "%Y-%m-%d")).days
                        clientes_sin_abonos.append({
                            "id": c_id,
                            "nombre": cliente['nombre'],
                            "saldo": resumen['saldo'],
                            "dias": dias
                        })
        
        # Últimos abonos
        ultimos_abonos = []
        if len(movimientos_df) > 0:
            ultimos_abonos_df = movimientos_df[movimientos_df['tipo'] == 'abono'].sort_values('timestamp', ascending=False).head(10)
            for _, row in ultimos_abonos_df.iterrows():
                cliente = self.get_cliente_by_id(row['cliente_id'])
                ultimos_abonos.append({
                    "id": row['id'],
                    "cliente_nombre": cliente['nombre'] if cliente else "Desconocido",
                    "monto": float(row['monto']),
                    "fecha": row['fecha'],
                    "descripcion": row['descripcion']
                })
        
        return {
            "total_prestado": float(total_prestado),
            "total_abonado": float(total_abonado),
            "deuda_activa": float(deuda_activa),
            "clientes_activos": clientes_activos,
            "prestamos_hoy": float(prestamos_hoy),
            "abonos_hoy": float(abonos_hoy),
            "devoluciones_hoy": float(devoluciones_hoy),
            "devoluciones_cliente_hoy": float(devoluciones_cliente_hoy),
            "devoluciones_proveedor_hoy": float(devoluciones_proveedor_hoy),
            "top_deudores": top_deudores,
            "clientes_sin_abonos": clientes_sin_abonos[:10],
            "ultimos_abonos": ultimos_abonos,
            "movimientos_hoy": movimientos_hoy_cnt,
            "devoluciones_hoy": float(devoluciones_hoy),
            "devoluciones_cliente_hoy": float(devoluciones_cliente_hoy),
            "devoluciones_proveedor_hoy": float(devoluciones_proveedor_hoy),
            "devoluciones_hoy_cnt": int(devoluciones_hoy_cnt),
            "cartera_antiguedad": [
                {"label": b["label"], "total": float(b["total"]), "clientes": b["clientes"]}
                for b in cartera_antiguedad
            ],
            "cola_cobro": cola_cobro[:8]
        }
    
    def get_historial_cliente(self, cliente_id: str) -> Dict[str, Any]:
        """Obtiene el historial completo de un cliente con resumen"""
        cliente = self.get_cliente_by_id(cliente_id)
        if not cliente:
            return None
        
        resumen = self.get_resumen_cliente(cliente_id)
        movimientos = self.get_movimientos_by_cliente(cliente_id)
        
        # Agregar saldo acumulado a cada movimiento
        saldo_acumulado = 0
        movimientos_ordenados = sorted(movimientos, key=lambda x: x['timestamp'])
        
        for mov in movimientos_ordenados:
            if mov['tipo'] == 'prestamo':
                saldo_acumulado += mov['monto']
            else:
                saldo_acumulado -= mov['monto']
            mov['saldo_acumulado'] = saldo_acumulado
        
        # Devolver en orden descendente (más reciente primero) con saldo calculado
        movimientos = list(reversed(movimientos_ordenados))
        
        return {
            "cliente": cliente,
            "resumen": resumen,
            "movimientos": movimientos
        }
    
    # ==================== BACKUPS ====================
    
    def crear_backup(self) -> str:
        """Crea un backup del archivo SQLite"""
        fecha = datetime.now().strftime("%Y-%m-%d")
        backup_filename = f"backup_{fecha}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # Si ya existe un backup hoy, agregar hora
        if os.path.exists(backup_path):
            hora = datetime.now().strftime("%H%M%S")
            backup_filename = f"backup_{fecha}_{hora}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
        
        shutil.copy2(self.db_path, backup_path)
        
        # Limpiar backups antiguos (mantener últimos 30)
        self._limpiar_backups_antiguos()
        
        return backup_path
    
    def _limpiar_backups_antiguos(self, mantener: int = 30):
        """Elimina backups más antiguos que el número especificado"""
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.startswith("backup_") and (filename.endswith(".db") or filename.endswith(".xlsx")):
                filepath = os.path.join(self.backup_dir, filename)
                backups.append((filepath, os.path.getmtime(filepath)))
        
        backups.sort(key=lambda x: x[1], reverse=True)
        
        for filepath, _ in backups[mantener:]:
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error eliminando backup antiguo: {e}")
    
    def get_backups(self) -> List[Dict[str, Any]]:
        """Lista todos los backups disponibles (.db y .xlsx)"""
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.startswith("backup_") and (filename.endswith(".db") or filename.endswith(".xlsx")):
                filepath = os.path.join(self.backup_dir, filename)
                stat = os.stat(filepath)
                backups.append({
                    "nombre": filename,
                    "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "tamano": round(stat.st_size / 1024, 2)  # KB
                })
        
        backups.sort(key=lambda x: x['fecha'], reverse=True)
        return backups

    # ==================== PROVEEDORES ====================
    
    def get_proveedores(self) -> List[Dict[str, Any]]:
        """Obtiene todos los proveedores activos"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM proveedores WHERE activo = 1")
            rows = cursor.fetchall()
        finally:
            conn.close()
        
        proveedores = [dict(row) for row in rows]
        for p in proveedores:
            p['activo'] = bool(p['activo'])
            p['telefono'] = self._format_telefono(p['telefono'])
        return proveedores
    
    def get_proveedor_by_id(self, proveedor_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un proveedor por ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,))
            row = cursor.fetchone()
        finally:
            conn.close()
        
        if not row:
            return None
            
        proveedor = dict(row)
        proveedor['activo'] = bool(proveedor['activo'])
        proveedor['telefono'] = self._format_telefono(proveedor['telefono'])
        return proveedor
    
    def buscar_proveedores(self, query: str) -> List[Dict[str, Any]]:
        """Busca proveedores por nombre o teléfono"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if not query or not query.strip():
                cursor.execute("SELECT * FROM proveedores WHERE activo = 1 LIMIT 20")
            else:
                q = f"%{query.strip().lower()}%"
                cursor.execute(
                    "SELECT * FROM proveedores WHERE activo = 1 AND (LOWER(nombre) LIKE ? OR telefono LIKE ?)",
                    (q, q)
                )
            rows = cursor.fetchall()
            
            proveedores = [dict(row) for row in rows]
            for p in proveedores:
                p['activo'] = bool(p['activo'])
                p['telefono'] = self._format_telefono(p['telefono'])
            return proveedores
        except Exception as e:
            print(f"Error en buscar_proveedores: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def crear_proveedor(self, nombre: str, telefono: str = "") -> Dict[str, Any]:
        """Crea un nuevo proveedor"""
        proveedor_id = str(uuid.uuid4())
        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        telefono_str = str(telefono).strip() if telefono else ""
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO proveedores (id, nombre, telefono, fecha_creacion, activo) VALUES (?, ?, ?, ?, 1)",
                (proveedor_id, nombre, telefono_str, fecha_creacion)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        
        return {
            "id": proveedor_id,
            "nombre": nombre,
            "telefono": telefono_str,
            "fecha_creacion": fecha_creacion,
            "activo": True
        }
    
    def actualizar_proveedor(self, proveedor_id: str, nombre: str = None, telefono: str = None) -> bool:
        """Actualiza datos de un proveedor"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            updates = []
            params = []
            if nombre is not None:
                updates.append("nombre = ?")
                params.append(nombre)
            if telefono is not None:
                updates.append("telefono = ?")
                params.append(telefono)
                
            if not updates:
                return True
                
            params.append(proveedor_id)
            cursor.execute(f"UPDATE proveedores SET {', '.join(updates)} WHERE id = ?", params)
            rows_affected = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        return rows_affected > 0
    
    def eliminar_proveedor(self, proveedor_id: str) -> bool:
        """Elimina (desactiva) un proveedor"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE proveedores SET activo = 0 WHERE id = ?", (proveedor_id,))
            rows_affected = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        return rows_affected > 0
    
    # ==================== MOVIMIENTOS PROVEEDORES ====================
    
    def get_movimientos_proveedor(self, limite: int = 100) -> List[Dict[str, Any]]:
        """Obtiene los últimos movimientos de proveedores"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos_proveedores ORDER BY timestamp DESC LIMIT ?", (limite,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_movimientos_by_proveedor(self, proveedor_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los movimientos de un proveedor"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos_proveedores WHERE proveedor_id = ? ORDER BY timestamp DESC", (proveedor_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_movimientos_proveedores_hoy(self) -> List[Dict[str, Any]]:
        """Obtiene movimientos de proveedores del día actual"""
        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM movimientos_proveedores WHERE fecha = ? ORDER BY timestamp DESC", (hoy,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def crear_movimiento_proveedor(self, proveedor_id: str, tipo: str, descripcion: str, monto: float, fecha: str = None) -> Dict[str, Any]:
        """Crea un nuevo movimiento de proveedor (factura o pago)"""
        movimiento_id = str(uuid.uuid4())
        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO movimientos_proveedores (id, proveedor_id, tipo, descripcion, monto, fecha, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (movimiento_id, proveedor_id, tipo, descripcion, float(monto), fecha, timestamp)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        
        return {
            "id": movimiento_id,
            "proveedor_id": proveedor_id,
            "tipo": tipo,
            "descripcion": descripcion,
            "monto": float(monto),
            "fecha": fecha,
            "timestamp": timestamp
        }
    
    # ==================== RESÚMENES PROVEEDORES ====================
    
    def get_resumen_proveedor(self, proveedor_id: str) -> Dict[str, Any]:
        """Calcula el resumen financiero de un proveedor"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT SUM(monto) FROM movimientos_proveedores WHERE proveedor_id = ? AND tipo = 'factura'", (proveedor_id,))
            facturas = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT SUM(monto) FROM movimientos_proveedores WHERE proveedor_id = ? AND tipo = 'pago'", (proveedor_id,))
            pagos = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT MAX(timestamp) FROM movimientos_proveedores WHERE proveedor_id = ?", (proveedor_id,))
            ultimo_mov = cursor.fetchone()[0]
        finally:
            conn.close()
        
        return {
            "total_facturas": float(facturas),
            "total_pagado": float(pagos),
            "saldo": float(facturas - pagos),
            "ultimo_movimiento": ultimo_mov
        }
    
    def get_historial_proveedor(self, proveedor_id: str) -> Dict[str, Any]:
        """Obtiene el historial completo de un proveedor con resumen"""
        proveedor = self.get_proveedor_by_id(proveedor_id)
        if not proveedor:
            return None
        
        resumen = self.get_resumen_proveedor(proveedor_id)
        movimientos = self.get_movimientos_by_proveedor(proveedor_id)
        
        # Agregar saldo acumulado a cada movimiento
        saldo_acumulado = 0
        movimientos_ordenados = sorted(movimientos, key=lambda x: x['timestamp'])
        
        for mov in movimientos_ordenados:
            if mov['tipo'] == 'factura':
                saldo_acumulado += mov['monto']
            else:  # pago
                saldo_acumulado -= mov['monto']
            mov['saldo_acumulado'] = saldo_acumulado
        
        # Devolver en orden descendente (más reciente primero) con saldo calculado
        movimientos = list(reversed(movimientos_ordenados))
        
        return {
            "proveedor": proveedor,
            "resumen": resumen,
            "movimientos": movimientos
        }
    
    def get_dashboard_stats_proveedores(self) -> Dict[str, Any]:
        """Obtiene estadísticas del dashboard para proveedores"""
        self._load_cache()
        
        proveedores_df = self._cache_proveedores.copy()
        if len(proveedores_df) > 0 and 'activo' in proveedores_df.columns:
            proveedores_df = proveedores_df[proveedores_df['activo'] == True]
            
        movimientos_df = self._cache_movimientos_proveedores.copy()
        
        # Si no hay movimientos, retornar valores vacíos
        if len(movimientos_df) == 0:
            return {
                "total_facturas": 0.0,
                "total_pagado": 0.0,
                "deuda_activa": 0.0,
                "proveedores_activos": len(proveedores_df),
                "facturas_hoy": 0.0,
                "pagos_hoy": 0.0,
                "top_acreedores": [],
                "movimientos_hoy": 0
            }
        
        # Totales generales
        total_facturas = movimientos_df[movimientos_df['tipo'] == 'factura']['monto'].sum()
        total_pagado = movimientos_df[movimientos_df['tipo'] == 'pago']['monto'].sum()
        deuda_activa = total_facturas - total_pagado  # Lo que debemos a proveedores
        proveedores_activos = len(proveedores_df)
        
        # Movimientos de hoy
        hoy = datetime.now().strftime("%Y-%m-%d")
        mov_hoy = movimientos_df[movimientos_df['fecha'] == hoy]
        facturas_hoy = mov_hoy[mov_hoy['tipo'] == 'factura']['monto'].sum() if len(mov_hoy) > 0 else 0.0
        pagos_hoy = mov_hoy[mov_hoy['tipo'] == 'pago']['monto'].sum() if len(mov_hoy) > 0 else 0.0
        
        # Top 5 proveedores con mayor deuda (acreedores)
        proveedores_deuda = []
        for _, proveedor in proveedores_df.iterrows():
            resumen = self.get_resumen_proveedor(proveedor['id'])
            if resumen['saldo'] > 0:
                proveedores_deuda.append({
                    "id": proveedor['id'],
                    "nombre": proveedor['nombre'],
                    "saldo": resumen['saldo']
                })
        
        proveedores_deuda.sort(key=lambda x: x['saldo'], reverse=True)
        top_acreedores = proveedores_deuda[:5]
        
        return {
            "total_facturas": float(total_facturas),
            "total_pagado": float(total_pagado),
            "deuda_activa": float(deuda_activa),
            "proveedores_activos": proveedores_activos,
            "facturas_hoy": float(facturas_hoy),
            "pagos_hoy": float(pagos_hoy),
            "top_acreedores": top_acreedores,
            "movimientos_hoy": len(mov_hoy)
        }
    
    # ==================== INVENTARIO Y VENTAS ====================

    def get_productos(self) -> List[Dict[str, Any]]:
        """Obtiene todos los productos activos."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos WHERE activo = 1 ORDER BY nombre ASC")
            rows = cursor.fetchall()
        finally:
            conn.close()
        
        productos = [dict(row) for row in rows]
        for p in productos:
            p['activo'] = bool(p['activo'])
        return productos

    def buscar_productos(self, query: str) -> List[Dict[str, Any]]:
        """Busca productos por nombre, categoria o referencia."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if not query or not query.strip():
                cursor.execute("SELECT * FROM productos WHERE activo = 1 ORDER BY nombre ASC LIMIT 50")
            else:
                q = f"%{query.strip().lower()}%"
                cursor.execute(
                    "SELECT * FROM productos WHERE activo = 1 AND (LOWER(nombre) LIKE ? OR LOWER(categoria) LIKE ? OR LOWER(referencia) LIKE ?) ORDER BY nombre ASC LIMIT 50",
                    (q, q, q)
                )
            rows = cursor.fetchall()
            
            productos = [dict(row) for row in rows]
            for p in productos:
                p['activo'] = bool(p['activo'])
            return productos
        except Exception as e:
            print(f"Error en buscar_productos: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_producto_by_id(self, producto_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un producto por ID."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
            row = cursor.fetchone()
        finally:
            conn.close()
        
        if not row:
            return None
            
        producto = dict(row)
        producto['activo'] = bool(producto['activo'])
        return producto

    def crear_producto(self, nombre: str, categoria: str = "", precio_compra: float = 0, precio_venta: float = 0, stock: int = 0, stock_minimo: int = 0, referencia: str = None) -> Dict[str, Any]:
        """Crea un producto de inventario."""
        producto_id = str(uuid.uuid4())
        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO productos (id, nombre, categoria, precio_compra, precio_venta, stock, stock_minimo, fecha_creacion, activo, referencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
                (producto_id, nombre, categoria, float(precio_compra), float(precio_venta), int(stock), int(stock_minimo), fecha_creacion, referencia)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()

        return {
            "id": producto_id,
            "nombre": nombre,
            "categoria": categoria,
            "precio_compra": float(precio_compra),
            "precio_venta": float(precio_venta),
            "stock": int(stock),
            "stock_minimo": int(stock_minimo),
            "fecha_creacion": fecha_creacion,
            "activo": True,
            "referencia": referencia
        }

    def actualizar_producto(self, producto_id: str, nombre: str = None, categoria: str = None, precio_compra: float = None, precio_venta: float = None, stock: int = None, stock_minimo: int = None, referencia: str = None) -> bool:
        """Actualiza un producto."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            updates = []
            params = []
            if nombre is not None:
                updates.append("nombre = ?")
                params.append(nombre)
            if categoria is not None:
                updates.append("categoria = ?")
                params.append(categoria)
            if precio_compra is not None:
                updates.append("precio_compra = ?")
                params.append(float(precio_compra))
            if precio_venta is not None:
                updates.append("precio_venta = ?")
                params.append(float(precio_venta))
            if stock is not None:
                updates.append("stock = ?")
                params.append(int(stock))
            if stock_minimo is not None:
                updates.append("stock_minimo = ?")
                params.append(int(stock_minimo))
            if referencia is not None:
                updates.append("referencia = ?")
                params.append(referencia)
                
            if not updates:
                return True
                
            params.append(producto_id)
            cursor.execute(f"UPDATE productos SET {', '.join(updates)} WHERE id = ?", params)
            rows_affected = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        return rows_affected > 0

    def eliminar_producto(self, producto_id: str) -> bool:
        """Desactiva un producto."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE productos SET activo = 0 WHERE id = ?", (producto_id,))
            rows_affected = cursor.rowcount
            conn.commit()
        finally:
            conn.close()
        
        self._invalidate_cache()
        return rows_affected > 0

    def get_ventas(self, limite: int = 100) -> List[Dict[str, Any]]:
        """Obtiene las ventas recientes."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ventas ORDER BY timestamp DESC LIMIT ?", (limite,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def crear_venta(self, producto_id: str, cantidad: int, precio_unitario: float = None, nota: str = "") -> Dict[str, Any]:
        """Registra una venta y descuenta stock (de forma transaccional y atómica)."""
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")

        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Obtener producto
            cursor.execute("SELECT nombre, precio_venta, stock FROM productos WHERE id = ? AND activo = 1", (producto_id,))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError("Producto no encontrado o inactivo")
                
            stock_actual = int(prod["stock"])
            if stock_actual < cantidad:
                raise ValueError("Stock insuficiente")
                
            precio = float(precio_unitario if precio_unitario is not None else prod["precio_venta"])
            total = precio * cantidad
            venta_id = str(uuid.uuid4())
            fecha = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 2. Descontar stock
            cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, producto_id))
            
            # 3. Guardar venta
            cursor.execute(
                "INSERT INTO ventas (id, producto_id, producto_nombre, cantidad, precio_unitario, total, fecha, timestamp, nota) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (venta_id, producto_id, prod["nombre"], int(cantidad), precio, total, fecha, timestamp, nota)
            )
            
            conn.commit()
            self._invalidate_cache()
            
            return {
                "id": venta_id,
                "producto_id": producto_id,
                "producto_nombre": prod["nombre"],
                "cantidad": int(cantidad),
                "precio_unitario": precio,
                "total": total,
                "fecha": fecha,
                "timestamp": timestamp,
                "nota": nota
            }
            
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_dashboard_stats_inventario(self) -> Dict[str, Any]:
        """Obtiene resumen de inventario y ventas."""
        self._load_cache()
        productos_df = self._cache_productos.copy()
        ventas_df = self._cache_ventas.copy()

        if len(productos_df) > 0 and "activo" in productos_df.columns:
            productos_df = productos_df[productos_df["activo"] == True]

        hoy = datetime.now().strftime("%Y-%m-%d")
        if len(ventas_df) > 0 and "fecha" in ventas_df.columns:
            ventas_hoy_df = ventas_df[ventas_df["fecha"] == hoy]
        else:
            ventas_hoy_df = pd.DataFrame()
            
        stock_bajo = []
        for _, producto in productos_df.iterrows():
            stock = int(producto.get("stock") or 0)
            stock_minimo = int(producto.get("stock_minimo") or 0)
            if stock <= stock_minimo:
                stock_bajo.append({
                    "id": producto["id"],
                    "nombre": producto["nombre"],
                    "stock": stock,
                    "stock_minimo": stock_minimo,
                    "referencia": producto.get("referencia", "")
                })

        valor_inventario = 0.0
        for _, producto in productos_df.iterrows():
            valor_inventario += float(producto.get("precio_compra") or 0) * int(producto.get("stock") or 0)

        return {
            "productos_activos": len(productos_df),
            "valor_inventario": float(valor_inventario),
            "ventas_hoy": float(ventas_hoy_df["total"].sum()) if len(ventas_hoy_df) > 0 and "total" in ventas_hoy_df.columns else 0.0,
            "unidades_vendidas_hoy": int(ventas_hoy_df["cantidad"].sum()) if len(ventas_hoy_df) > 0 and "cantidad" in ventas_hoy_df.columns else 0,
            "stock_bajo": stock_bajo[:10],
        }

    # ==================== CARACTERÍSTICAS DELUXE ADICIONALES ====================
    
    def anular_venta(self, venta_id: str) -> bool:
        """Anula una venta, borrando el registro de venta y devolviendo los productos al stock (transaccional)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Obtener la venta
            cursor.execute("SELECT producto_id, cantidad FROM ventas WHERE id = ?", (venta_id,))
            venta = cursor.fetchone()
            if not venta:
                return False
                
            producto_id = venta["producto_id"]
            cantidad = int(venta["cantidad"])
            
            # 2. Devolver la cantidad al stock del producto
            cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (cantidad, producto_id))
            
            # 3. Eliminar la venta
            cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
            
            conn.commit()
            self._invalidate_cache()
            return True
            
        except Exception as e:
            print(f"Error anulando venta {venta_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def ajustar_stock(self, producto_id: str, cantidad_cambio: int, nota: str = "") -> bool:
        """Realiza un ajuste rápido de stock (+ o -)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar si existe el producto
            cursor.execute("SELECT stock FROM productos WHERE id = ? AND activo = 1", (producto_id,))
            prod = cursor.fetchone()
            if not prod:
                return False
                
            new_stock = max(0, int(prod["stock"]) + cantidad_cambio)
            
            # Actualizar stock
            cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (new_stock, producto_id))
            
            conn.commit()
            self._invalidate_cache()
            return True
            
        except Exception as e:
            print(f"Error ajustando stock para producto {producto_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    # ==================== SISTEMA DE TRIAL ====================
    
    def _get_config_value(self, clave: str) -> Optional[str]:
        """Obtiene un valor de configuración de la tabla config"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM config WHERE clave = ?", (clave,))
            row = cursor.fetchone()
            return row["valor"] if row else None
        except Exception as e:
            print(f"⚠️ Error leyendo config: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _set_config_value(self, clave: str, valor: str, descripcion: str = ""):
        """Guarda un valor de configuración en la tabla config"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO config (clave, valor, descripcion) VALUES (?, ?, ?)",
                (clave, str(valor), descripcion)
            )
            conn.commit()
        except Exception as e:
            print(f"⚠️ Error guardando config: {e}")
        finally:
            if conn:
                conn.close()
    
    def is_trial_active(self) -> Dict[str, Any]:
        """
        Verifica si el período de prueba está activo.
        Retorna información sobre el estado del trial.
        """
        TRIAL_DAYS = 10
        trial_start_str = self._get_config_value("trial_start")
        
        if trial_start_str is None:
            trial_start = datetime.now().strftime("%Y-%m-%d")
            self._set_config_value("trial_start", trial_start, "Fecha de inicio del período de prueba")
            self._set_config_value("trial_days", str(TRIAL_DAYS), "Días de período de prueba")
            return {
                "active": True,
                "trial_start": trial_start,
                "trial_days": TRIAL_DAYS,
                "days_remaining": TRIAL_DAYS,
                "first_run": True
            }
        
        try:
            trial_start = datetime.strptime(trial_start_str, "%Y-%m-%d")
            dias_transcurridos = (datetime.now() - trial_start).days
            return {
                "active": True,  # Trial permanently active
                "trial_start": trial_start_str,
                "trial_days": TRIAL_DAYS,
                "days_remaining": 999,
                "days_elapsed": dias_transcurridos,
                "first_run": False
            }
        except Exception as e:
            return {
                "active": True,
                "trial_start": trial_start_str,
                "trial_days": TRIAL_DAYS,
                "days_remaining": TRIAL_DAYS,
                "error": str(e)
            }
    
    def check_trial_or_raise(self) -> bool:
        """Verifica el trial y siempre retorna True para uso ilimitado."""
        return True
    
    def check_cliente_exists(self, cliente_id: str) -> bool:
        """Verifica si existe un cliente con el ID dado"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM clientes WHERE id = ? AND activo = 1", (cliente_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def check_proveedor_exists(self, proveedor_id: str) -> bool:
        """Verifica si existe un proveedor con el ID dado"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM proveedores WHERE id = ? AND activo = 1", (proveedor_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def get_trial_info(self) -> Dict[str, Any]:
        """Obtiene información completa del trial."""
        return self.is_trial_active()


# Instancia global del gestor de base de datos
db = DatabaseManager()
