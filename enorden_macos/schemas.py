from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal

# ==================== CLIENTES SCHEMAS ====================

class ClienteBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del cliente")
    telefono: Optional[str] = Field(default="", description="Teléfono del cliente")

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None

class UltimoAbono(BaseModel):
    fecha: str
    monto: Decimal

class ClienteRead(ClienteBase):
    id: str
    fecha_creacion: str
    activo: bool
    saldo: Decimal = Decimal("0.00")
    total_prestado: Decimal = Decimal("0.00")
    total_abonado: Decimal = Decimal("0.00")
    dias_sin_abonar: Optional[int] = None
    ultimo_abono: Optional[UltimoAbono] = None

class ApiResponseCliente(BaseModel):
    success: bool
    data: ClienteRead
    message: Optional[str] = None

class ApiResponseClientesList(BaseModel):
    success: bool
    data: List[ClienteRead]

class ApiResponseClientesConDeuda(BaseModel):
    success: bool
    data: List[ClienteRead]
    total: int

# ==================== PROVEEDORES SCHEMAS ====================

class ProveedorBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del proveedor")
    telefono: Optional[str] = Field(default="", description="Teléfono del proveedor")

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None

class ProveedorRead(ProveedorBase):
    id: str
    fecha_creacion: str
    activo: bool
    saldo: Decimal = Decimal("0.00")
    total_facturas: Decimal = Decimal("0.00")
    total_pagado: Decimal = Decimal("0.00")

class ApiResponseProveedor(BaseModel):
    success: bool
    data: ProveedorRead
    message: Optional[str] = None

class ApiResponseProveedoresList(BaseModel):
    success: bool
    data: List[ProveedorRead]

# ==================== MOVIMIENTOS SCHEMAS ====================

class MovimientoCreate(BaseModel):
    cliente_id: str
    tipo: str  # prestamo o abono
    descripcion: str
    monto: Decimal

class MovimientoRead(BaseModel):
    id: str
    cliente_id: str
    tipo: str
    descripcion: str
    monto: Decimal
    fecha: str
    timestamp: str
    cliente_nombre: Optional[str] = "Desconocido"

class ApiResponseMovimiento(BaseModel):
    success: bool
    data: MovimientoRead
    message: Optional[str] = None

class ApiResponseMovimientosList(BaseModel):
    success: bool
    data: List[MovimientoRead]

# ==================== MOVIMIENTOS PROVEEDOR SCHEMAS ====================

class MovimientoProveedorCreate(BaseModel):
    proveedor_id: str
    tipo: str  # factura o pago
    descripcion: str
    monto: Decimal
    fecha: Optional[str] = None  # Formato YYYY-MM-DD

class MovimientoProveedorRead(BaseModel):
    id: str
    proveedor_id: str
    tipo: str
    descripcion: str
    monto: Decimal
    fecha: str
    timestamp: str
    proveedor_nombre: Optional[str] = "Desconocido"

class ApiResponseMovimientoProveedor(BaseModel):
    success: bool
    data: MovimientoProveedorRead
    message: Optional[str] = None

class ApiResponseMovimientoProveedorList(BaseModel):
    success: bool
    data: List[MovimientoProveedorRead]

# ==================== GENERAL RESPONSES ====================

class ApiResponseSimple(BaseModel):
    success: bool
    message: str

# ==================== GASTOS SCHEMAS ====================

class GastoCreate(BaseModel):
    categoria: str = Field(..., description="Categoría del gasto (Ej: Arriendo, Servicios)")
    monto: Decimal = Field(..., gt=0, description="Monto del gasto")
    descripcion: Optional[str] = Field(default="", description="Descripción detallada del gasto")

class GastoRead(GastoCreate):
    id: int
    fecha: str

class ApiResponseGasto(BaseModel):
    success: bool
    data: GastoRead
    message: Optional[str] = None

class ApiResponseGastosList(BaseModel):
    success: bool
    data: List[GastoRead]

# ==================== CAJA SCHEMAS ====================

class FlujoCajaResumen(BaseModel):
    fecha: str
    ventas_total: Decimal
    abonos_total: Decimal
    pagos_proveedores_total: Decimal
    gastos_total: Decimal
    efectivo_neto: Decimal

class ApiResponseFlujoCaja(BaseModel):
    success: bool
    data: FlujoCajaResumen
    message: Optional[str] = None
