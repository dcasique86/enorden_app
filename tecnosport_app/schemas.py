from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from decimal import Decimal

# ==================== CLIENTES SCHEMAS ====================

class ClienteBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del cliente")
    telefono: Optional[str] = Field(default="", description="Teléfono del cliente")
    cedula: Optional[str] = Field(default="", description="Cédula del cliente")
    direccion: Optional[str] = Field(default="", description="Dirección del cliente")
    ciudad: Optional[str] = Field(default="", description="Ciudad del cliente")

class ClienteCreate(ClienteBase):
    pass

class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None
    cedula: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None

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
    tipo_operacion: Optional[str] = None  # 'COMPRA' | 'PRESTAMO_MERCANCIA' | None=COMPRA
    estado_operacion: Optional[str] = None
    fecha_vencimiento: Optional[str] = None

class MovimientoRead(BaseModel):
    id: str
    cliente_id: str
    tipo: str
    descripcion: str
    monto: Decimal
    fecha: str
    timestamp: str
    cliente_nombre: Optional[str] = "Desconocido"
    tipo_operacion: Optional[str] = None
    estado_operacion: Optional[str] = None
    fecha_vencimiento: Optional[str] = None

class ApiResponseMovimiento(BaseModel):
    success: bool
    data: MovimientoRead
    message: Optional[str] = None

class ApiResponseMovimientosList(BaseModel):
    success: bool
    data: List[MovimientoRead]

# ==================== MOVIMIENTOS PROVEEDOR SCHEMAS ====================

class FacturaItem(BaseModel):
    producto_id: str
    cantidad: int = Field(..., ge=1, description="Cantidad de unidades recibidas")
    precio_compra: Optional[float] = Field(default=None, description="Costo unitario de compra (opcional)")

class MovimientoProveedorCreate(BaseModel):
    proveedor_id: str
    tipo: str  # factura o pago
    descripcion: str
    monto: Decimal
    fecha: Optional[str] = None  # Formato YYYY-MM-DD
    items: Optional[List[FacturaItem]] = Field(default=None, description="Productos incluidos (suma stock cuando facturas_sumar_stock está activa)")

class MovimientoProveedorRead(BaseModel):
    id: str
    proveedor_id: str
    tipo: str
    descripcion: str
    monto: Decimal
    fecha: str
    timestamp: str
    proveedor_nombre: Optional[str] = "Desconocido"
    items_aplicados: Optional[List[Dict[str, Any]]] = None

class ApiResponseMovimientoProveedor(BaseModel):
    success: bool
    data: MovimientoProveedorRead
    message: Optional[str] = None

class ApiResponseMovimientoProveedorList(BaseModel):
    success: bool
    data: List[MovimientoProveedorRead]

# ==================== DEVOLUCIONES SCHEMAS ====================

class DevolucionClienteCreate(BaseModel):
    cliente_id: str
    descripcion: str
    monto: Decimal
    observaciones: Optional[str] = Field(default="", description="Observaciones adicionales")

class DevolucionProveedorCreate(BaseModel):
    proveedor_id: str
    descripcion: str
    monto: Decimal
    observaciones: Optional[str] = Field(default="", description="Observaciones adicionales")

class DevolucionRead(BaseModel):
    id: str
    cliente_id: Optional[str] = None
    proveedor_id: Optional[str] = None
    tipo: str  # 'abono' o 'pago'
    descripcion: str
    monto: Decimal
    fecha: str
    timestamp: str
    tipo_operacion: str
    estado_operacion: str
    cliente_nombre: Optional[str] = None
    proveedor_nombre: Optional[str] = None

class ApiResponseDevolucion(BaseModel):
    success: bool
    data: DevolucionRead
    message: Optional[str] = None

class ApiResponseDevolucionesList(BaseModel):
    success: bool
    data: List[DevolucionRead]

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

# ==================== TELEGRAM USER SCHEMAS ====================

class TelegramUserCreate(BaseModel):
    telegram_id: int
    nombre: str
    rol: str = "operador"
    activo: bool = True

class TelegramUserRead(BaseModel):
    telegram_id: int
    nombre: str
    rol: str
    activo: bool
    fecha_registro: str

# ==================== INVENTARIO / VENTAS SCHEMAS ====================

class ProductoRead(BaseModel):
    id: str
    nombre: str
    categoria: Optional[str] = ""
    precio_compra: float = 0
    precio_venta: float = 0
    stock: int = 0
    stock_minimo: int = 0
    fecha_creacion: Optional[str] = None
    activo: bool = True
    referencia: Optional[str] = None
    codigo_barras: Optional[str] = None

class ApiResponseProducto(BaseModel):
    success: bool
    data: ProductoRead
    message: Optional[str] = None

class ApiResponseProductosList(BaseModel):
    success: bool
    data: List[ProductoRead]

class HistorialPrecioRead(BaseModel):
    id: int
    producto_id: str
    fecha: str
    precio_compra_anterior: Optional[float] = None
    precio_compra_nuevo: Optional[float] = None
    precio_venta_anterior: Optional[float] = None
    precio_venta_nuevo: Optional[float] = None

class StockMovimientoRead(BaseModel):
    id: str
    producto_id: str
    tipo: str  # inicial | venta | ajuste | compra | anulacion
    cantidad: int
    stock_resultante: int
    nota: Optional[str] = None
    referencia_id: Optional[str] = None
    fecha: str
    timestamp: str

class ProductoDetalleRead(ProductoRead):
    historial_precios: List[HistorialPrecioRead] = []
    ultimas_ventas: List[Dict[str, Any]] = []
    movimientos: List[StockMovimientoRead] = []
    unidades_vendidas: int = 0
    total_vendido: float = 0
    ganancia_estimada: float = 0

class ApiResponseProductoDetalle(BaseModel):
    success: bool
    data: ProductoDetalleRead

class ApiResponseStockMovimientosList(BaseModel):
    success: bool
    data: List[StockMovimientoRead]

class VentaRead(BaseModel):
    id: str
    producto_id: str
    producto_nombre: Optional[str] = None
    cantidad: int
    precio_unitario: Optional[float] = None
    total: Optional[float] = None
    fecha: str
    timestamp: str
    nota: Optional[str] = None

class ApiResponseVenta(BaseModel):
    success: bool
    data: VentaRead
    message: Optional[str] = None

class ApiResponseVentasList(BaseModel):
    success: bool
    data: List[VentaRead]

class StockBajoItem(BaseModel):
    id: str
    nombre: str
    stock: int
    stock_minimo: int
    referencia: Optional[str] = ""

class InventarioStatsRead(BaseModel):
    productos_activos: int
    valor_inventario: float
    ventas_hoy: float
    unidades_vendidas_hoy: int
    stock_bajo: List[StockBajoItem]
    stock_bajo_count: int = 0

class ApiResponseInventarioStats(BaseModel):
    success: bool
    data: InventarioStatsRead
