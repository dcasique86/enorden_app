from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from datetime import datetime
from decimal import Decimal
import pandas as pd

from database import db as global_db, DatabaseManager
from schemas import (
    ClienteCreate, ClienteRead, ClienteUpdate, UltimoAbono,
    ProveedorCreate, ProveedorRead, ProveedorUpdate,
    TelegramUserCreate, TelegramUserRead
)

class BaseRepository(ABC):
    """Interfaz abstracta base para repositorios"""
    
    @abstractmethod
    def get_all(self) -> List[Any]:
        pass
        
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[Any]:
        pass
        
    @abstractmethod
    def create(self, obj: Any) -> Any:
        pass

class ClienteRepository(BaseRepository, ABC):
    """Interfaz abstracta para el repositorio de Clientes"""
    
    @abstractmethod
    def buscar(self, q: str) -> List[ClienteRead]:
        pass
        
    @abstractmethod
    def get_con_deuda(self) -> List[ClienteRead]:
        pass
        
    @abstractmethod
    def update(self, id: str, obj: ClienteUpdate) -> bool:
        pass
        
    @abstractmethod
    def delete(self, id: str) -> bool:
        pass

class ProveedorRepository(BaseRepository, ABC):
    """Interfaz abstracta para el repositorio de Proveedores"""
    
    @abstractmethod
    def buscar(self, q: str) -> List[ProveedorRead]:
        pass
        
    @abstractmethod
    def update(self, id: str, obj: ProveedorUpdate) -> bool:
        pass
        
    @abstractmethod
    def delete(self, id: str) -> bool:
        pass

class GastoRepository(BaseRepository, ABC):
    """Interfaz abstracta para el repositorio de Gastos Operativos"""
    
    @abstractmethod
    def obtener_gastos_por_fecha(self, fecha_inicio: str, fecha_fin: str) -> List[Any]:
        pass
        
    @abstractmethod
    def obtener_resumen_caja_diaria(self, fecha: str = None) -> Dict[str, Any]:
        pass

# ==================== IMPLEMENTACIONES CONCRETAS EXCEL ====================

class ExcelClienteRepository(ClienteRepository):
    """Implementación en Excel de ClienteRepository usando DatabaseManager"""
    
    def __init__(self, database_manager: DatabaseManager = global_db):
        self.db = database_manager

    def get_all(self) -> List[ClienteRead]:
        clientes = self.db.get_clientes()
        self.db._load_cache()
        movimientos_df = self.db._cache_movimientos.copy()
        
        # Agrupar movimientos en memoria para resolver el problema N+1
        movs_by_cliente = {}
        if len(movimientos_df) > 0:
            for _, row in movimientos_df.iterrows():
                c_id = str(row['cliente_id'])
                if c_id not in movs_by_cliente:
                    movs_by_cliente[c_id] = []
                movs_by_cliente[c_id].append(row.to_dict())
                
        hoy_date = datetime.now().date()
        res = []
        
        for c in clientes:
            c_id = str(c['id'])
            c_movs = movs_by_cliente.get(c_id, [])
            
            prestado = sum(Decimal(str(m['monto'])) for m in c_movs if m['tipo'] == 'prestamo')
            abonado = sum(Decimal(str(m['monto'])) for m in c_movs if m['tipo'] == 'abono')
            saldo = prestado - abonado
            
            abonos = [m for m in c_movs if m['tipo'] == 'abono']
            ultimo_abono = None
            dias_sin_abonar = None
            
            if abonos:
                abonos_sorted = sorted(abonos, key=lambda x: x['timestamp'], reverse=True)
                ultimo_abono = UltimoAbono(
                    fecha=str(abonos_sorted[0]['fecha']),
                    monto=Decimal(str(abonos_sorted[0]['monto']))
                )
                try:
                    fecha_ultimo = datetime.strptime(str(abonos_sorted[0]['fecha']), "%Y-%m-%d").date()
                    dias_sin_abonar = (hoy_date - fecha_ultimo).days
                except Exception:
                    pass
            
            res.append(ClienteRead(
                id=c_id,
                nombre=c['nombre'],
                telefono=c.get('telefono', ''),
                cedula=c.get('cedula', ''),
                direccion=c.get('direccion', ''),
                ciudad=c.get('ciudad', ''),
                fecha_creacion=c['fecha_creacion'],
                activo=c['activo'],
                saldo=saldo,
                total_prestado=prestado,
                total_abonado=abonado,
                dias_sin_abonar=dias_sin_abonar,
                ultimo_abono=ultimo_abono
            ))
        return res

    def get_by_id(self, id: str) -> Optional[ClienteRead]:
        c = self.db.get_cliente_by_id(id)
        if not c:
            return None
            
        resumen = self.db.get_resumen_cliente(id)
        movimientos = self.db.get_movimientos_by_cliente(id)
        
        abonos = [m for m in movimientos if m['tipo'] == 'abono']
        ultimo_abono = None
        dias_sin_abonar = None
        
        if abonos:
            abonos_sorted = sorted(abonos, key=lambda x: x['timestamp'], reverse=True)
            ultimo_abono = UltimoAbono(
                fecha=str(abonos_sorted[0]['fecha']),
                monto=Decimal(str(abonos_sorted[0]['monto']))
            )
            try:
                hoy_date = datetime.now().date()
                fecha_ultimo = datetime.strptime(str(abonos_sorted[0]['fecha']), "%Y-%m-%d").date()
                dias_sin_abonar = (hoy_date - fecha_ultimo).days
            except Exception:
                pass
                
        return ClienteRead(
            id=str(c['id']),
            nombre=c['nombre'],
            telefono=c.get('telefono', ''),
            cedula=c.get('cedula', ''),
            direccion=c.get('direccion', ''),
            ciudad=c.get('ciudad', ''),
            fecha_creacion=c['fecha_creacion'],
            activo=c['activo'],
            saldo=Decimal(str(resumen['saldo'])),
            total_prestado=Decimal(str(resumen['total_prestado'])),
            total_abonado=Decimal(str(resumen['total_abonado'])),
            dias_sin_abonar=dias_sin_abonar,
            ultimo_abono=ultimo_abono
        )

    def create(self, obj: ClienteCreate) -> ClienteRead:
        nuevo = self.db.crear_cliente(
            nombre=obj.nombre.strip(),
            telefono=obj.telefono.strip() if obj.telefono else "",
            cedula=obj.cedula.strip() if obj.cedula else "",
            direccion=obj.direccion.strip() if obj.direccion else "",
            ciudad=obj.ciudad.strip() if obj.ciudad else ""
        )
        return ClienteRead(
            id=str(nuevo['id']),
            nombre=nuevo['nombre'],
            telefono=nuevo['telefono'],
            cedula=nuevo['cedula'],
            direccion=nuevo['direccion'],
            ciudad=nuevo['ciudad'],
            fecha_creacion=nuevo['fecha_creacion'],
            activo=nuevo['activo'],
            saldo=Decimal("0.00"),
            total_prestado=Decimal("0.00"),
            total_abonado=Decimal("0.00")
        )

    def buscar(self, q: str) -> List[ClienteRead]:
        clientes = self.db.buscar_clientes(q)
        self.db._load_cache()
        movimientos_df = self.db._cache_movimientos.copy()
        
        movs_by_cliente = {}
        if len(movimientos_df) > 0:
            for _, row in movimientos_df.iterrows():
                c_id = str(row['cliente_id'])
                if c_id not in movs_by_cliente:
                    movs_by_cliente[c_id] = []
                movs_by_cliente[c_id].append(row.to_dict())
                
        hoy_date = datetime.now().date()
        res = []
        
        for c in clientes:
            c_id = str(c['id'])
            c_movs = movs_by_cliente.get(c_id, [])
            
            prestado = sum(Decimal(str(m['monto'])) for m in c_movs if m['tipo'] == 'prestamo')
            abonado = sum(Decimal(str(m['monto'])) for m in c_movs if m['tipo'] == 'abono')
            saldo = prestado - abonado
            
            abonos = [m for m in c_movs if m['tipo'] == 'abono']
            ultimo_abono = None
            dias_sin_abonar = None
            
            if abonos:
                abonos_sorted = sorted(abonos, key=lambda x: x['timestamp'], reverse=True)
                ultimo_abono = UltimoAbono(
                    fecha=str(abonos_sorted[0]['fecha']),
                    monto=Decimal(str(abonos_sorted[0]['monto']))
                )
                try:
                    fecha_ultimo = datetime.strptime(str(abonos_sorted[0]['fecha']), "%Y-%m-%d").date()
                    dias_sin_abonar = (hoy_date - fecha_ultimo).days
                except Exception:
                    pass
            
            res.append(ClienteRead(
                id=c_id,
                nombre=c['nombre'],
                telefono=c.get('telefono', ''),
                cedula=c.get('cedula', ''),
                direccion=c.get('direccion', ''),
                ciudad=c.get('ciudad', ''),
                fecha_creacion=c['fecha_creacion'],
                activo=c['activo'],
                saldo=saldo,
                total_prestado=prestado,
                total_abonado=abonado,
                dias_sin_abonar=dias_sin_abonar,
                ultimo_abono=ultimo_abono
            ))
        return res

    def get_con_deuda(self) -> List[ClienteRead]:
        all_clientes = self.get_all()
        resultado = [c for c in all_clientes if c.saldo > Decimal("0.00")]
        resultado.sort(key=lambda x: x.saldo, reverse=True)
        return resultado

    def update(self, id: str, obj: ClienteUpdate) -> bool:
        return self.db.actualizar_cliente(
            cliente_id=id,
            nombre=obj.nombre,
            telefono=obj.telefono,
            cedula=obj.cedula,
            direccion=obj.direccion,
            ciudad=obj.ciudad
        )

    def delete(self, id: str) -> bool:
        return self.db.eliminar_cliente(id)


class ExcelProveedorRepository(ProveedorRepository):
    """Implementación en Excel de ProveedorRepository usando DatabaseManager"""
    
    def __init__(self, database_manager: DatabaseManager = global_db):
        self.db = database_manager

    def get_all(self) -> List[ProveedorRead]:
        proveedores = self.db.get_proveedores()
        self.db._load_cache()
        movimientos_df = self.db._cache_movimientos_proveedores.copy()
        
        # Agrupar movimientos en memoria para resolver el problema N+1
        movs_by_prov = {}
        if len(movimientos_df) > 0:
            for _, row in movimientos_df.iterrows():
                p_id = str(row['proveedor_id'])
                if p_id not in movs_by_prov:
                    movs_by_prov[p_id] = []
                movs_by_prov[p_id].append(row.to_dict())
                
        res = []
        for p in proveedores:
            p_id = str(p['id'])
            p_movs = movs_by_prov.get(p_id, [])
            
            facturas = sum(Decimal(str(m['monto'])) for m in p_movs if m['tipo'] == 'factura')
            pagos = sum(Decimal(str(m['monto'])) for m in p_movs if m['tipo'] == 'pago')
            saldo = facturas - pagos
            
            res.append(ProveedorRead(
                id=p_id,
                nombre=p['nombre'],
                telefono=p.get('telefono', ''),
                fecha_creacion=p['fecha_creacion'],
                activo=p['activo'],
                saldo=saldo,
                total_facturas=facturas,
                total_pagado=pagos
            ))
        return res

    def get_by_id(self, id: str) -> Optional[ProveedorRead]:
        p = self.db.get_proveedor_by_id(id)
        if not p:
            return None
            
        resumen = self.db.get_resumen_proveedor(id)
        return ProveedorRead(
            id=str(p['id']),
            nombre=p['nombre'],
            telefono=p.get('telefono', ''),
            fecha_creacion=p['fecha_creacion'],
            activo=p['activo'],
            saldo=Decimal(str(resumen['saldo'])),
            total_facturas=Decimal(str(resumen['total_facturas'])),
            total_pagado=Decimal(str(resumen['total_pagado']))
        )

    def create(self, obj: ProveedorCreate) -> ProveedorRead:
        nuevo = self.db.crear_proveedor(
            nombre=obj.nombre.strip(),
            telefono=obj.telefono.strip() if obj.telefono else ""
        )
        return ProveedorRead(
            id=str(nuevo['id']),
            nombre=nuevo['nombre'],
            telefono=nuevo['telefono'],
            fecha_creacion=nuevo['fecha_creacion'],
            activo=nuevo['activo'],
            saldo=Decimal("0.00"),
            total_facturas=Decimal("0.00"),
            total_pagado=Decimal("0.00")
        )

    def buscar(self, q: str) -> List[ProveedorRead]:
        proveedores = self.db.buscar_proveedores(q)
        self.db._load_cache()
        movimientos_df = self.db._cache_movimientos_proveedores.copy()
        
        movs_by_prov = {}
        if len(movimientos_df) > 0:
            for _, row in movimientos_df.iterrows():
                p_id = str(row['proveedor_id'])
                if p_id not in movs_by_prov:
                    movs_by_prov[p_id] = []
                movs_by_prov[p_id].append(row.to_dict())
                
        res = []
        for p in proveedores:
            p_id = str(p['id'])
            p_movs = movs_by_prov.get(p_id, [])
            
            facturas = sum(Decimal(str(m['monto'])) for m in p_movs if m['tipo'] == 'factura')
            pagos = sum(Decimal(str(m['monto'])) for m in p_movs if m['tipo'] == 'pago')
            saldo = facturas - pagos
            
            res.append(ProveedorRead(
                id=p_id,
                nombre=p['nombre'],
                telefono=p.get('telefono', ''),
                fecha_creacion=p['fecha_creacion'],
                activo=p['activo'],
                saldo=saldo,
                total_facturas=facturas,
                total_pagado=pagos
            ))
        return res

    def update(self, id: str, obj: ProveedorUpdate) -> bool:
        return self.db.actualizar_proveedor(
            proveedor_id=id,
            nombre=obj.nombre,
            telefono=obj.telefono
        )

    def delete(self, id: str) -> bool:
        return self.db.eliminar_proveedor(id)

class ExcelGastoRepository(GastoRepository):
    """Implementación de GastoRepository usando DatabaseManager"""
    
    def __init__(self, database_manager: DatabaseManager = global_db):
        self.db = database_manager

    def get_all(self) -> List[Any]:
        return []
        
    def get_by_id(self, id: str) -> Optional[Any]:
        return None
        
    def create(self, obj: Any) -> Any:
        return self.db.registrar_gasto(obj.categoria, float(obj.monto), obj.descripcion)
        
    def obtener_gastos_por_fecha(self, fecha_inicio: str, fecha_fin: str) -> List[Any]:
        return self.db.obtener_gastos_por_fecha(fecha_inicio, fecha_fin)
        
    def obtener_resumen_caja_diaria(self, fecha: str = None) -> Dict[str, Any]:
        return self.db.obtener_resumen_caja_diaria(fecha)

# ==================== TELEGRAM USER REPOSITORY ====================

class TelegramUserRepository:
    """Repositorio para gestión de usuarios del bot de Telegram."""

    def __init__(self, database_manager: DatabaseManager = global_db):
        self.db = database_manager

    def _row_to_dict(self, row) -> Optional[dict]:
        if not row:
            return None
        return {
            "telegram_id": row["telegram_id"],
            "nombre": row["nombre"],
            "rol": row["rol"],
            "activo": bool(row["activo"]),
            "fecha_registro": row["fecha_registro"],
        }

    def get_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM telegram_users WHERE telegram_id = ?",
                (telegram_id,)
            )
            return self._row_to_dict(cursor.fetchone())
        finally:
            conn.close()

    def get_all(self) -> List[dict]:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM telegram_users ORDER BY fecha_registro DESC"
            )
            return [self._row_to_dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def create(self, obj: TelegramUserCreate) -> dict:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telegram_users (telegram_id, nombre, rol, activo) VALUES (?, ?, ?, ?)",
                (obj.telegram_id, obj.nombre, obj.rol, 1 if obj.activo else 0)
            )
            conn.commit()
            return self.get_by_telegram_id(obj.telegram_id)
        finally:
            conn.close()

    def update_rol(self, telegram_id: int, nuevo_rol: str) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE telegram_users SET rol = ? WHERE telegram_id = ?",
                (nuevo_rol, telegram_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def set_activo(self, telegram_id: int, activo: bool) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE telegram_users SET activo = ? WHERE telegram_id = ?",
                (1 if activo else 0, telegram_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete(self, telegram_id: int) -> bool:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM telegram_users WHERE telegram_id = ?",
                (telegram_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()


# ==================== FastAPI Dependency Injection Helpers ====================

def get_cliente_repository() -> ClienteRepository:
    """Retorna la instancia del repositorio de clientes"""
    return ExcelClienteRepository(global_db)

def get_proveedor_repository() -> ProveedorRepository:
    """Retorna la instancia del repositorio de proveedores"""
    return ExcelProveedorRepository(global_db)

def get_gasto_repository() -> GastoRepository:
    """Retorna la instancia del repositorio de gastos"""
    return ExcelGastoRepository(global_db)

# ==================== INSTANCIAS GLOBALES ====================
cliente_repo = ExcelClienteRepository(global_db)
proveedor_repo = ExcelProveedorRepository(global_db)
gasto_repo = ExcelGastoRepository(global_db)
telegram_user_repo = TelegramUserRepository(global_db)
