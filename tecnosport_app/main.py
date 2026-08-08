"""
EnOrden - Sistema de Control de Cuentas por Cobrar
Backend API con FastAPI
"""

import os
import sys
import webbrowser
import threading
import time

# Forzar codificacion UTF-8 en Windows para evitar errores con caracteres especiales
if sys.platform == "win32":
    if getattr(sys, "stdout", None) is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    elif hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if getattr(sys, "stderr", None) is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    elif hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import uvicorn

# Importar módulo de base de datos
from database import db, normalizar_codigo_barras

# Importar esquemas y repositorios para Clientes y Proveedores
from schemas import (
    ClienteCreate, ClienteUpdate, ClienteRead, ApiResponseCliente, ApiResponseClientesList, ApiResponseClientesConDeuda,
    ProveedorCreate, ProveedorUpdate, ProveedorRead, ApiResponseProveedor, ApiResponseProveedoresList,
    MovimientoCreate, MovimientoRead, ApiResponseMovimientosList,
    MovimientoProveedorCreate, MovimientoProveedorRead, ApiResponseMovimientoProveedor, ApiResponseMovimientoProveedorList,
    ApiResponseSimple,
    GastoCreate, GastoRead, ApiResponseGasto, ApiResponseGastosList,
    FlujoCajaResumen, ApiResponseFlujoCaja,
    DevolucionClienteCreate, DevolucionProveedorCreate, DevolucionRead, ApiResponseDevolucion, ApiResponseDevolucionesList,
    TelegramUserCreate,
    ProductoRead, ApiResponseProducto, ApiResponseProductosList, ApiResponseProductoDetalle,
    StockMovimientoRead, ApiResponseStockMovimientosList,
    VentaRead, ApiResponseVenta, ApiResponseVentasList,
    StockBajoItem, InventarioStatsRead, ApiResponseInventarioStats
)
from repository import (
    ClienteRepository, ProveedorRepository, GastoRepository,
    get_cliente_repository, get_proveedor_repository, get_gasto_repository
)

# Servicios internos
from services.migraciones import ejecutar_migraciones
from services.prestamo_service import PrestamoService
from services.startup_manager import StartupManager
from services.whatsapp_service import (
    notificar_devolucion_cliente,
    notificar_devolucion_proveedor,
)

prestamo_service = PrestamoService(db)
startup_manager = StartupManager(db)

# ==================== CONFIGURACIÓN ====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")


def _allowed_cors_origins():
    """Limita CORS a origenes locales por defecto."""
    env_value = os.getenv("ENORDEN_CORS_ORIGINS", "")
    if env_value.strip():
        return [origin.strip() for origin in env_value.split(",") if origin.strip()]

    return [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]



from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log_startup("Inicio de la aplicación")
    aplicadas = ejecutar_migraciones(db)
    if aplicadas:
        _log_startup("Migraciones ejecutadas: " + "; ".join(aplicadas))
    convertidos = prestamo_service.verificar_vencimientos()
    if convertidos:
        print(f"📦 {convertidos} préstamo(s) vencido(s) convertido(s) a compra automáticamente")

    startup_manager.iniciar_todo()
    yield
    startup_manager.detener_todo()


app = FastAPI(
    title="EnOrden",
    description="Sistema de Control de Cuentas por Cobrar",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS limitado a la app local; se puede ampliar con ENORDEN_CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Evita que el navegador cachee plantillas HTML (evita ver versiones viejas al actualizar).
@app.middleware("http")
async def no_cache_html_middleware(request, call_next):
    response = await call_next(request)
    ctype = response.headers.get("content-type", "")
    if "text/html" in ctype:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

# Archivos estáticos
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Jinja2 Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ==================== FUNCIÓN: NOMBRE DE TIENDA ====================

def get_nombre_tienda() -> str:
    """
    FUENTE ÚNICA DE VERDAD para el nombre del negocio.
    Lee dinámicamente desde la base de datos SQLite.
    No usa caché - siempre lee el valor actual.
    """
    try:
        valor = db._get_config_value("nombre_tienda")
        return valor if valor else "EnOrden"
    except Exception as e:
        print(f"Error leyendo nombre_tienda: {e}")
        return "EnOrden"

# Los modelos Pydantic de Clientes, Proveedores y Movimientos se importan desde schemas.py

class ProductoCreate(BaseModel):
    nombre: str
    categoria: Optional[str] = ""
    precio_compra: Optional[float] = 0
    precio_venta: Optional[float] = 0
    stock: Optional[int] = 0
    stock_minimo: Optional[int] = 0
    referencia: Optional[str] = None
    codigo_barras: Optional[str] = None

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    precio_compra: Optional[float] = None
    precio_venta: Optional[float] = None
    stock: Optional[int] = None
    stock_minimo: Optional[int] = None
    referencia: Optional[str] = None
    codigo_barras: Optional[str] = None

class AjusteStock(BaseModel):
    cantidad_cambio: int
    nota: Optional[str] = ""

class VentaCreate(BaseModel):
    producto_id: str
    cantidad: int
    precio_unitario: Optional[float] = None
    nota: Optional[str] = ""

# ==================== RUTAS DE PÁGINAS ====================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Página principal - Dashboard"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "dashboard"
    })

@app.get("/clientes", response_class=HTMLResponse)
async def clientes_page(request: Request):
    """Página de gestión de clientes"""
    return templates.TemplateResponse("clientes.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "clientes"
    })

@app.get("/cliente/{cliente_id}", response_class=HTMLResponse)
async def cliente_detalle_page(request: Request, cliente_id: str):
    """Página de detalle de cliente"""
    return templates.TemplateResponse("cliente_detalle.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "clientes"
    })

@app.get("/reporte-cliente/{cliente_id}", response_class=HTMLResponse)
async def reporte_cliente_page(request: Request, cliente_id: str):
    """Página de reporte detallado de un cliente"""
    return templates.TemplateResponse("reporte_cliente.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "clientes"
    })

@app.get("/nuevo-prestamo", response_class=HTMLResponse)
async def nuevo_prestamo_page(request: Request):
    """Página para registrar nuevo préstamo"""
    return templates.TemplateResponse("nuevo_prestamo.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "dashboard"
    })

@app.get("/nuevo-abono", response_class=HTMLResponse)
async def nuevo_abono_page(request: Request):
    """Página para registrar nuevo abono"""
    return templates.TemplateResponse("nuevo_abono.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "dashboard"
    })

@app.get("/importar", response_class=HTMLResponse)
async def importar_page(request: Request):
    """Página para importar datos desde Excel"""
    return templates.TemplateResponse("importar.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "configuracion"
    })

@app.get("/recordatorios", response_class=HTMLResponse)
async def recordatorios_page(request: Request):
    """Página de envío masivo de recordatorios WhatsApp"""
    return templates.TemplateResponse("recordatorios.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "recordatorios"
    })

# ==================== RUTAS DE PÁGINAS - PROVEEDORES ====================

@app.get("/proveedores", response_class=HTMLResponse)
async def proveedores_page(request: Request):
    """Página de gestión de proveedores"""
    return templates.TemplateResponse("proveedores.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "proveedores"
    })

@app.get("/proveedor/{proveedor_id}", response_class=HTMLResponse)
async def proveedor_detalle_page(request: Request, proveedor_id: str):
    """Página de detalle de proveedor"""
    return templates.TemplateResponse("proveedor_detalle.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "proveedores"
    })

@app.get("/reporte-proveedor/{proveedor_id}", response_class=HTMLResponse)
async def reporte_proveedor_page(request: Request, proveedor_id: str):
    """Página de reporte detallado de un proveedor"""
    return templates.TemplateResponse("reporte_proveedor.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "proveedores"
    })

@app.get("/nueva-factura", response_class=HTMLResponse)
async def nueva_factura_page(request: Request):
    """Página para registrar nueva factura de proveedor"""
    return templates.TemplateResponse("nueva_factura.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "dashboard"
    })

@app.get("/nuevo-pago-proveedor", response_class=HTMLResponse)
async def nuevo_pago_proveedor_page(request: Request):
    """Página para registrar nuevo pago a proveedor"""
    return templates.TemplateResponse("nuevo_pago_proveedor.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "dashboard"
    })

@app.get("/configuracion", response_class=HTMLResponse)
async def configuracion_page(request: Request):
    """Página de configuración del sistema"""
    return templates.TemplateResponse("configuracion.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "configuracion"
    })

@app.get("/inventario", response_class=HTMLResponse)
async def inventario_page(request: Request):
    """Pagina de inventario"""
    return templates.TemplateResponse("inventario.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "inventario"
    })

@app.get("/nueva-venta", response_class=HTMLResponse)
async def nueva_venta_page(request: Request):
    """Pagina para registrar ventas"""
    return templates.TemplateResponse("nueva_venta.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "inventario"
    })

@app.get("/gastos", response_class=HTMLResponse)
async def gastos_page(request: Request):
    """Página para registrar y ver gastos operativos"""
    return templates.TemplateResponse("gastos.html", {
        "request": request,
        "nombre_tienda": get_nombre_tienda(),
        "page_id": "gastos"
    })

# ==================== API: CLIENTES ====================

@app.get("/api/clientes", response_model=ApiResponseClientesList)
async def api_get_clientes(repo: ClienteRepository = Depends(get_cliente_repository)):
    """Obtiene todos los clientes"""
    try:
        clientes = repo.get_all()
        return {"success": True, "data": clientes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clientes/buscar", response_model=ApiResponseClientesList)
async def api_buscar_clientes(q: str = Query(""), repo: ClienteRepository = Depends(get_cliente_repository)):
    """Busca clientes por nombre o teléfono"""
    try:
        clientes = repo.buscar(q)
        return {"success": True, "data": clientes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clientes/con-deuda", response_model=ApiResponseClientesConDeuda)
async def api_get_clientes_con_deuda(repo: ClienteRepository = Depends(get_cliente_repository)):
    """Obtiene todos los clientes activos con saldo pendiente > 0, con días sin abonar"""
    try:
        clientes = repo.get_con_deuda()
        return {"success": True, "data": clientes, "total": len(clientes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clientes/{cliente_id}", response_model=ApiResponseCliente)
async def api_get_cliente(cliente_id: str, repo: ClienteRepository = Depends(get_cliente_repository)):
    """Obtiene un cliente por ID"""
    try:
        cliente = repo.get_by_id(cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"success": True, "data": cliente}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clientes", response_model=ApiResponseCliente)
async def api_crear_cliente(cliente: ClienteCreate, repo: ClienteRepository = Depends(get_cliente_repository)):
    """Crea un nuevo cliente"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        if not cliente.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre es requerido")
        
        nuevo = repo.create(cliente)
        return {"success": True, "data": nuevo, "message": "Cliente creado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/clientes/{cliente_id}", response_model=ApiResponseSimple)
async def api_actualizar_cliente(cliente_id: str, cliente: ClienteUpdate, repo: ClienteRepository = Depends(get_cliente_repository)):
    """Actualiza un cliente"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        actualizado = repo.update(cliente_id, cliente)
        if not actualizado:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"success": True, "message": "Cliente actualizado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/clientes/{cliente_id}", response_model=ApiResponseSimple)
async def api_eliminar_cliente(cliente_id: str, repo: ClienteRepository = Depends(get_cliente_repository)):
    """Elimina (desactiva) un cliente"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        eliminado = repo.delete(cliente_id)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"success": True, "message": "Cliente eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: MOVIMIENTOS ====================

@app.get("/api/movimientos", response_model=ApiResponseMovimientosList)
async def api_get_movimientos(limite: int = Query(100, ge=1, le=500)):
    """Obtiene los últimos movimientos"""
    try:
        movimientos = db.get_movimientos(limite)
        clientes = db.get_clientes()
        clientes_map = {str(c['id']): c['nombre'] for c in clientes}
        for mov in movimientos:
            mov['cliente_nombre'] = clientes_map.get(str(mov['cliente_id']), "Desconocido")
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/movimientos/hoy", response_model=ApiResponseMovimientosList)
async def api_get_movimientos_hoy():
    """Obtiene movimientos del día"""
    try:
        movimientos = db.get_movimientos_hoy()
        clientes = db.get_clientes()
        clientes_map = {str(c['id']): c['nombre'] for c in clientes}
        for mov in movimientos:
            mov['cliente_nombre'] = clientes_map.get(str(mov['cliente_id']), "Desconocido")
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/movimientos/{movimiento_id}")
async def api_get_movimiento(movimiento_id: str):
    """Obtiene un movimiento por ID."""
    try:
        mov = db.get_movimiento_by_id(movimiento_id)
        if not mov:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        cliente = db.get_cliente_by_id(mov["cliente_id"])
        mov["cliente_nombre"] = cliente["nombre"] if cliente else "Desconocido"
        return {"success": True, "data": mov}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/movimientos/cliente/{cliente_id}")
async def api_get_movimientos_cliente(cliente_id: str):
    """Obtiene movimientos de un cliente"""
    try:
        movimientos = db.get_movimientos_by_cliente(cliente_id)
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/movimientos")
async def api_crear_movimiento(movimiento: MovimientoCreate):
    """Crea un nuevo movimiento (compra o préstamo de mercancía)"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")

        if movimiento.tipo not in ['prestamo', 'abono']:
            raise HTTPException(status_code=400, detail="Tipo debe ser 'prestamo' o 'abono'")

        if movimiento.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

        # Validar tipo_operacion si se proporciona
        TIPOS_OPERACION_VALIDOS = {"COMPRA", "PRESTAMO_MERCANCIA", "DEVUELTO", "PENDIENTE"}
        tipo_op_raw = movimiento.tipo_operacion
        if tipo_op_raw is not None and tipo_op_raw not in TIPOS_OPERACION_VALIDOS:
            raise HTTPException(
                status_code=400,
                detail=f"tipo_operacion inválido: '{tipo_op_raw}'. Valores permitidos: {', '.join(sorted(TIPOS_OPERACION_VALIDOS))}"
            )

        tipo_op = tipo_op_raw or "COMPRA"

        cliente = db.get_cliente_by_id(movimiento.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        tipo_op = movimiento.tipo_operacion or "COMPRA"
        if tipo_op == "PRESTAMO_MERCANCIA":
            estado_op = "PENDIENTE"
            fecha_venc = PrestamoService.calcular_fecha_vencimiento()
        else:
            estado_op = "COMPRA"
            fecha_venc = None

        nuevo = db.crear_movimiento(
            cliente_id=movimiento.cliente_id,
            tipo=movimiento.tipo,
            descripcion=movimiento.descripcion.strip(),
            monto=movimiento.monto,
            tipo_operacion=tipo_op,
            estado_operacion=estado_op,
            fecha_vencimiento=fecha_venc,
        )

        nuevo['cliente_nombre'] = cliente['nombre']

        # Consecutivo de recibo: solo para ventas (préstamo tipo COMPRA).
        # Los abonos también pasan por aquí, por eso se exige tipo == 'prestamo'.
        nuevo['recibo_numero'] = None
        if movimiento.tipo == 'prestamo' and tipo_op == 'COMPRA':
            nuevo['recibo_numero'] = db.generar_numero_recibo()

        if tipo_op == "PRESTAMO_MERCANCIA":
            msg = "Préstamo de mercancía registrado exitosamente"
        else:
            msg = f"{'Préstamo' if movimiento.tipo == 'prestamo' else 'Abono'} registrado exitosamente"

        return {"success": True, "data": nuevo, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/movimientos/{movimiento_id}/devolver")
async def api_devolver_movimiento(movimiento_id: str):
    """Registra la devolución de un préstamo de mercancía."""
    try:
        result = prestamo_service.registrar_devolucion(movimiento_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado o no está pendiente")
        return {"success": True, "data": result, "message": "Devolución registrada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prestamos-pendientes")
async def api_prestamos_pendientes():
    """Retorna conteos de préstamos de mercancía para el Dashboard."""
    try:
        data = prestamo_service.contar_pendientes()
        lista = prestamo_service.obtener_pendientes()
        return {"success": True, "data": {**data, "lista": lista}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gastos/rango", response_model=ApiResponseGastosList)
def obtener_gastos_por_rango(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    gasto_repo: GastoRepository = Depends(get_gasto_repository)
):
    hoy = datetime.now().strftime("%Y-%m-%d")
    fecha_inicio = desde or hoy
    fecha_fin = hasta or hoy
    try:
        gastos = gasto_repo.obtener_gastos_por_fecha(fecha_inicio, fecha_fin)
        return {"success": True, "data": gastos}
    except Exception as e:
        print(f"Error al obtener gastos: {e}")
        return {"success": True, "data": []}

# ==================== API: DEVOLUCIONES ====================

@app.post("/api/devoluciones/cliente", response_model=ApiResponseDevolucion)
async def registrar_devolucion_cliente(
    devolucion: DevolucionClienteCreate,
):
    """Registra una devolución de mercancía por parte de un cliente"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")

        if not db.check_cliente_exists(devolucion.cliente_id):
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        if devolucion.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

        devolucion = db.crear_devolucion_cliente(
            cliente_id=devolucion.cliente_id,
            descripcion=devolucion.descripcion,
            monto=devolucion.monto,
            observaciones=devolucion.observaciones
        )

        try:
            cliente = db.get_cliente_by_id(devolucion["cliente_id"])
            if cliente and cliente.get("telefono"):
                notificar_devolucion_cliente(
                    cliente_nombre=cliente.get("nombre", "Cliente"),
                    telefono=cliente["telefono"],
                    descripcion=devolucion.get("descripcion", ""),
                    monto=float(devolucion.get("monto", 0)),
                )
        except Exception as wa_err:
            print(f"[WA] Error notificando devolución cliente: {wa_err}")

        return {"success": True, "data": devolucion, "message": "Devolución de cliente registrada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devoluciones/cliente/{cliente_id}", response_model=ApiResponseDevolucionesList)
async def listar_devoluciones_cliente(cliente_id: str):
    """Lista todas las devoluciones de un cliente"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")

        if not db.check_cliente_exists(cliente_id):
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Buscar devoluciones del cliente (abonos con tipo_operacion DEVOLUCION_CLIENTE)
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, cliente_id, tipo, descripcion, monto, fecha, timestamp, 
                       tipo_operacion, estado_operacion
                FROM movimientos 
                WHERE cliente_id = ? AND tipo = 'abono' 
                AND tipo_operacion IN ('DEVOLUCION_CLIENTE')
                ORDER BY timestamp DESC
            """, (cliente_id,))
            devoluciones = [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
        
        return {"success": True, "data": devoluciones, "message": "Devoluciones del cliente obtenidas"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devoluciones/proveedor/{proveedor_id}", response_model=ApiResponseDevolucionesList)
async def listar_devoluciones_proveedor(proveedor_id: str):
    """Lista todas las devoluciones a un proveedor"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")

        if not db.check_proveedor_exists(proveedor_id):
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")

        # Buscar devoluciones del proveedor
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, proveedor_id, tipo, descripcion, monto, fecha, timestamp, 
                       tipo_operacion, estado_operacion
                FROM movimientos_proveedores 
                WHERE proveedor_id = ? AND tipo = 'pago' 
                AND tipo_operacion IN ('DEVOLUCION_PROVEEDOR')
                ORDER BY timestamp DESC
            """, (proveedor_id,))
            devoluciones = [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
        
        return {"success": True, "data": devoluciones, "message": "Devoluciones del proveedor obtenidas"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devoluciones/proveedor", response_model=ApiResponseDevolucion)
async def registrar_devolucion_proveedor(
    devolucion: DevolucionProveedorCreate,
):
    """Registra una devolución a proveedor"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")

        if not db.check_proveedor_exists(devolucion.proveedor_id):
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")

        if devolucion.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

        # Crear la devolución como un pago con tipo_operacion DEVOLUCION_PROVEEDOR
        devolucion_data = db.crear_devolucion_proveedor(
            proveedor_id=devolucion.proveedor_id,
            descripcion=devolucion.descripcion,
            monto=devolucion.monto,
            observaciones=devolucion.observaciones
        )

        try:
            proveedor = db.get_proveedor_by_id(devolucion_data["proveedor_id"])
            if proveedor and proveedor.get("telefono"):
                notificar_devolucion_proveedor(
                    proveedor_nombre=proveedor.get("nombre", "Proveedor"),
                    telefono=proveedor["telefono"],
                    descripcion=devolucion_data.get("descripcion", ""),
                    monto=float(devolucion_data.get("monto", 0)),
                )
        except Exception as wa_err:
            print(f"[WA] Error notificando devolución proveedor: {wa_err}")

        return {"success": True, "data": devolucion_data, "message": "Devolución a proveedor registrada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== API: GASTOS Y FLUJO DE CAJA ====================

@app.get("/api/dashboard/flujo-caja", response_model=ApiResponseFlujoCaja)
def obtener_flujo_caja(
    fecha: Optional[str] = None,
    gasto_repo: GastoRepository = Depends(get_gasto_repository)
):
    try:
        resumen = gasto_repo.obtener_resumen_caja_diaria(fecha)
        return {"success": True, "data": resumen}
    except Exception as e:
        print(f"Error al obtener flujo de caja: {e}")
        return {"success": False, "data": {
            "fecha": fecha or datetime.now().strftime("%Y-%m-%d"),
            "ventas_total": 0, "abonos_total": 0, "pagos_proveedores_total": 0,
            "gastos_total": 0, "efectivo_neto": 0
        }, "message": str(e)}

@app.post("/api/gastos", response_model=ApiResponseGasto)
def registrar_gasto(
    gasto: GastoCreate,
    gasto_repo: GastoRepository = Depends(get_gasto_repository)
):
    try:
        resultado = gasto_repo.create(gasto)
        return {"success": True, "data": resultado}
    except Exception as e:
        print(f"Error al registrar gasto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/gastos/rango", response_model=ApiResponseGastosList)
def obtener_gastos_por_rango(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    gasto_repo: GastoRepository = Depends(get_gasto_repository)
):
    hoy = datetime.now().strftime("%Y-%m-%d")
    fecha_inicio = desde or hoy
    fecha_fin = hasta or hoy
    try:
        gastos = gasto_repo.obtener_gastos_por_fecha(fecha_inicio, fecha_fin)
        return {"success": True, "data": gastos}
    except Exception as e:
        print(f"Error al obtener gastos: {e}")
        return {"success": True, "data": []}

# ==================== API: HISTORIAL Y RESÚMENES ====================

@app.get("/api/historial/{cliente_id}")
async def api_get_historial(cliente_id: str):
    """Obtiene el historial completo de un cliente"""
    try:
        historial = db.get_historial_cliente(cliente_id)
        if not historial:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"success": True, "data": historial}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/cliente/{cliente_id}")
async def api_get_reporte_cliente(cliente_id: str, desde: Optional[str] = None, hasta: Optional[str] = None):
    """Obtiene reporte detallado de un cliente (ventas y abonos) con filtro de fechas"""
    try:
        reporte = db.get_reporte_cliente(cliente_id, desde, hasta)
        if not reporte:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return {"success": True, "data": reporte, "rango": {"desde": desde, "hasta": hasta}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reporte/proveedor/{proveedor_id}")
async def api_get_reporte_proveedor(proveedor_id: str, desde: Optional[str] = None, hasta: Optional[str] = None):
    """Obtiene reporte detallado de un proveedor (facturas y pagos) con filtro de fechas"""
    try:
        reporte = db.get_reporte_proveedor(proveedor_id, desde, hasta)
        if not reporte:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return {"success": True, "data": reporte, "rango": {"desde": desde, "hasta": hasta}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard")
async def api_get_dashboard():
    """Obtiene estadísticas del dashboard"""
    try:
        stats = db.get_dashboard_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: BACKUPS ====================

@app.get("/api/backups")
async def api_get_backups():
    """Lista todos los backups"""
    try:
        backups = db.get_backups()
        return {"success": True, "data": backups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backups/estado")
async def api_get_backup_estado():
    """Estado del programador de backups automáticos"""
    try:
        from scheduler import backup_scheduler
        return {"success": True, "data": backup_scheduler.estado()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: NOTIFICACIONES ====================

@app.get("/api/notificaciones")
async def api_get_notificaciones():
    """Notificaciones de atención: cobros prioritarios, stock bajo y backups."""
    try:
        notificaciones = []

        # 1. Cobros con prioridad alta (>= 31 días sin abonar)
        try:
            stats = db.get_dashboard_stats()
            contados = 0
            for c in stats.get("cola_cobro", []):
                if c.get("prioridad") != "alta" or contados >= 5:
                    continue
                dias = c.get("dias_sin_abonar")
                notificaciones.append({
                    "tipo": "cobro",
                    "icono": "💰",
                    "titulo": f"{c['nombre']} — {dias} días sin abonar",
                    "detalle": f"Saldo pendiente: ${c['saldo']:,.0f}",
                    "url": f"/cliente/{c['id']}"
                })
                contados += 1
        except Exception as e:
            print(f"Error en notificaciones (cobros): {e}")

        # 2. Productos con stock bajo
        try:
            inv = db.get_dashboard_stats_inventario()
            for p in inv.get("stock_bajo", [])[:10]:
                notificaciones.append({
                    "tipo": "stock",
                    "icono": "📦",
                    "titulo": f"Stock bajo: {p['nombre']}",
                    "detalle": f"Quedan {p['stock']} unidades (mínimo {p['stock_minimo']})",
                    "url": "/inventario?filtro=stock_bajo"
                })
        except Exception as e:
            print(f"Error en notificaciones (stock): {e}")

        # 3. Copia de seguridad reciente
        try:
            backups = db.get_backups()
            if backups:
                ultimo = datetime.strptime(backups[0]["fecha"], "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - ultimo) > timedelta(hours=24):
                    notificaciones.append({
                        "tipo": "backup",
                        "icono": "💾",
                        "titulo": "Copia de seguridad pendiente",
                        "detalle": f"Última copia: {backups[0]['fecha']} (hace más de 24 h)",
                        "url": "/configuracion"
                    })
            else:
                notificaciones.append({
                    "tipo": "backup",
                    "icono": "💾",
                    "titulo": "Sin copias de seguridad",
                    "detalle": "Crea tu primera copia de seguridad",
                    "url": "/configuracion"
                })
        except Exception as e:
            print(f"Error en notificaciones (backup): {e}")

        return {"success": True, "data": notificaciones}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backups")
async def api_crear_backup():
    """Crea un backup manual"""
    try:
        mantener = int(db.get_config("backup_mantener", "30") or "30")
        backup_path = db.crear_backup(mantener=mantener)
        return {
            "success": True, 
            "message": "Backup creado exitosamente",
            "data": {"path": backup_path}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backups/{filename}")
async def api_descargar_backup(filename: str):
    """Descarga un archivo de backup"""
    try:
        safe_name = os.path.basename(filename)
        backup_path = os.path.normpath(os.path.join(db.backup_dir, safe_name))
        backup_dir_abs = os.path.abspath(db.backup_dir)
        if not backup_path.startswith(backup_dir_abs):
            raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="Backup no encontrado")
        return FileResponse(
            backup_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=safe_name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: EXPORTAR ====================

@app.get("/api/exportar/excel")
async def api_exportar_excel():
    """Descarga el archivo Excel actual"""
    try:
        return FileResponse(
            db.excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="datos_tecnosport.xlsx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: IMPORTAR ====================

import pandas as pd
import uuid as uuid_module
from openpyxl import load_workbook
import shutil
import tempfile

class ImportConfig(BaseModel):
    col_nombre: str
    col_telefono: Optional[str] = ""
    col_cedula: Optional[str] = ""
    col_direccion: Optional[str] = ""
    col_ciudad: Optional[str] = ""
    col_deuda: Optional[str] = ""
    col_prestamos: Optional[str] = ""
    col_abonos: Optional[str] = ""
    crear_backup: Optional[bool] = True

@app.post("/api/importar/preview")
async def api_importar_preview(file: UploadFile = File(...)):
    """Previsualiza un archivo Excel antes de importar"""
    try:
        # Verificar extensión
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Leer archivo
        df = pd.read_excel(tmp_path)
        
        # Limpiar archivo temporal
        os.unlink(tmp_path)
        
        # Preparar respuesta
        columnas = list(df.columns)
        filas = df.head(5).to_dict('records')
        
        # Convertir valores a serializables
        for fila in filas:
            for key in fila:
                if pd.isna(fila[key]):
                    fila[key] = ""
                elif isinstance(fila[key], (int, float)):
                    fila[key] = float(fila[key]) if not pd.isna(fila[key]) else 0
        
        return {
            "success": True,
            "data": {
                "columnas": columnas,
                "total_filas": len(df),
                "preview": filas
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer archivo: {str(e)}")

@app.post("/api/importar")
async def api_importar_datos(file: UploadFile = File(...), config: str = Form("{}")):
    """Importa datos desde un archivo Excel"""
    import json
    
    try:
        # Parsear configuración
        config_dict = json.loads(config) if isinstance(config, str) else config
        
        col_nombre = config_dict.get('col_nombre', '')
        col_telefono = config_dict.get('col_telefono', '')
        col_cedula = config_dict.get('col_cedula', '')
        col_direccion = config_dict.get('col_direccion', '')
        col_ciudad = config_dict.get('col_ciudad', '')
        col_deuda = config_dict.get('col_deuda', '')
        col_prestamos = config_dict.get('col_prestamos', '')
        col_abonos = config_dict.get('col_abonos', '')
        crear_backup = config_dict.get('crear_backup', True)
        
        if not col_nombre:
            raise HTTPException(status_code=400, detail="Debes especificar la columna de nombre")
        
        # Verificar extensión
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
        
        # Crear backup antes de importar
        if crear_backup:
            db.crear_backup()
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Leer archivo
        df = pd.read_excel(tmp_path)
        
        # Limpiar archivo temporal
        os.unlink(tmp_path)
        
        # Limpiar datos
        df = df.dropna(subset=[col_nombre], how='all')
        df = df.fillna('')
        
        # Abrir archivo destino (legacy, solo para backwards-compat; si no existe se omite)
        excel_legacy = None
        if os.path.exists(db.excel_path):
            try:
                wb = load_workbook(db.excel_path)
                excel_legacy = (wb, wb["clientes"], wb["movimientos"])
            except Exception:
                excel_legacy = None
        
        clientes_importados = 0
        movimientos_importados = 0
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for idx, row in df.iterrows():
            try:
                # Obtener datos del cliente
                nombre = str(row.get(col_nombre, '')).strip()
                if not nombre or nombre == 'nan':
                    continue
                
                telefono = ''
                if col_telefono and col_telefono in df.columns:
                    telefono = str(row.get(col_telefono, '')).strip()
                    if telefono == 'nan':
                        telefono = ''

                cedula = ''
                if col_cedula and col_cedula in df.columns:
                    cedula = str(row.get(col_cedula, '')).strip()
                    if cedula == 'nan':
                        cedula = ''

                direccion = ''
                if col_direccion and col_direccion in df.columns:
                    direccion = str(row.get(col_direccion, '')).strip()
                    if direccion == 'nan':
                        direccion = ''

                ciudad = ''
                if col_ciudad and col_ciudad in df.columns:
                    ciudad = str(row.get(col_ciudad, '')).strip()
                    if ciudad == 'nan':
                        ciudad = ''
                
                # Insertar el cliente en SQLite (fuente principal de datos)
                try:
                    cliente_sqlite = db.crear_cliente(
                        nombre=nombre,
                        telefono=telefono,
                        cedula=cedula,
                        direccion=direccion,
                        ciudad=ciudad
                    )
                except Exception:
                    continue
                
                # Crear ID de cliente
                cliente_id = str(uuid_module.uuid4())
                
                # Agregar cliente al Excel legacy (si existe el archivo existe)
                if excel_legacy:
                    excel_legacy[1].append([
                        cliente_id,
                        nombre,
                        telefono,
                        timestamp_actual,
                        True
                    ])
                
                clientes_importados += 1
                
                # Obtener valores financieros
                deuda = 0
                prestamos = 0
                abonos = 0
                
                # Deuda
                if col_deuda and col_deuda in df.columns:
                    try:
                        deuda = float(row.get(col_deuda, 0) or 0)
                    except:
                        deuda = 0
                
                # Préstamos
                if col_prestamos and col_prestamos in df.columns:
                    try:
                        prestamos = float(row.get(col_prestamos, 0) or 0)
                    except:
                        prestamos = 0
                
                # Abonos
                if col_abonos and col_abonos in df.columns:
                    try:
                        abonos = float(row.get(col_abonos, 0) or 0)
                    except:
                        abonos = 0
                
                # Calcular valores si no están explícitos
                if deuda > 0 and prestamos == 0 and abonos == 0:
                    prestamos = deuda
                elif deuda > 0 and prestamos == 0:
                    prestamos = deuda + abonos
                
                # Crear movimiento de préstamo
                if prestamos > 0:
                    if excel_legacy:
                        excel_legacy[2].append([
                            str(uuid_module.uuid4()),
                            cliente_id,
                            'prestamo',
                            'Saldo inicial importado',
                            prestamos,
                            fecha_actual,
                            timestamp_actual
                        ])
                    try:
                        db.crear_movimiento(
                            cliente_id=cliente_sqlite['id'],
                            tipo='prestamo',
                            descripcion='Saldo inicial importado',
                            monto=prestamos
                        )
                    except Exception:
                        pass
                    movimientos_importados += 1
                
                # Crear movimiento de abono
                if abonos > 0:
                    if excel_legacy:
                        excel_legacy[2].append([
                            str(uuid_module.uuid4()),
                            cliente_id,
                            'abono',
                            'Abonos previos importados',
                            abonos,
                            fecha_actual,
                            timestamp_actual
                        ])
                    try:
                        db.crear_movimiento(
                            cliente_id=cliente_sqlite['id'],
                            tipo='abono',
                            descripcion='Abonos previos importados',
                            monto=abonos
                        )
                    except Exception:
                        pass
                    movimientos_importados += 1
                    
            except Exception as e:
                continue
        
        # Guardar archivo legacy (si existe)
        if excel_legacy:
            excel_legacy[0].save(db.excel_path)
        
        # Invalidar cache
        db._invalidate_cache()
        
        return {
            "success": True,
            "message": "Importación completada",
            "data": {
                "clientes_importados": clientes_importados,
                "movimientos_creados": movimientos_importados
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en importación: {str(e)}")

# ==================== API: PRODUCTOS IMPORTAR / EXPORTAR EXCEL ====================

def _parse_numero(valor):
    try:
        s = str(valor).replace('$', '').replace(' ', '').strip()
        if s == '' or s.lower() == 'nan' or s.lower() == 'none':
            return 0.0
        return float(s.replace(',', '.'))
    except Exception:
        return 0.0

@app.get("/api/productos/exportar")
async def api_exportar_productos():
    """Descarga un Excel con los productos (incluye código de barras)."""
    try:
        productos = db.get_productos()
        import io
        df = pd.DataFrame([{
            "Nombre": p.get("nombre", ""),
            "Categoria": p.get("categoria", ""),
            "Referencia": p.get("referencia", "") or "",
            "Código de barras": p.get("codigo_barras", "") or "",
            "Precio compra": float(p.get("precio_compra", 0) or 0),
            "Precio venta": float(p.get("precio_venta", 0) or 0),
            "Stock": int(p.get("stock", 0) or 0),
            "Stock minimo": int(p.get("stock_minimo", 0) or 0),
        } for p in productos])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="productos")
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=productos.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al exportar: {str(e)}")

@app.post("/api/productos/importar/preview")
async def api_productos_importar_preview(file: UploadFile = File(...)):
    """Previsualiza un archivo Excel antes de importar productos."""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        df = pd.read_excel(tmp_path)
        os.unlink(tmp_path)
        columnas = list(df.columns)
        filas = df.head(5).to_dict('records')
        filas_ser = []
        for fila in filas:
            item = {}
            for c in columnas:
                v = fila.get(c, None)
                if v is None:
                    item[c] = ""
                elif pd.isna(v):
                    item[c] = ""
                elif isinstance(v, (int, float)):
                    item[c] = float(v)
                else:
                    item[c] = str(v)
            filas_ser.append(item)
        return {"success": True, "data": {"columnas": columnas, "total_filas": int(len(df)), "preview": filas_ser}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer archivo: {str(e)}")

@app.post("/api/productos/importar")
async def api_productos_importar(file: UploadFile = File(...), config: str = Form("{}")):
    """Importa productos desde un archivo Excel."""
    import json
    try:
        config_dict = json.loads(config) if isinstance(config, str) else config
        col_nombre = (config_dict.get('col_nombre') or '').strip()
        col_categoria = (config_dict.get('col_categoria') or '').strip()
        col_referencia = (config_dict.get('col_referencia') or '').strip()
        col_codigo_barras = (config_dict.get('col_codigo_barras') or '').strip()
        col_precio_compra = (config_dict.get('col_precio_compra') or '').strip()
        col_precio_venta = (config_dict.get('col_precio_venta') or '').strip()
        col_stock = (config_dict.get('col_stock') or '').strip()
        crear_backup = config_dict.get('crear_backup', True)

        if not col_nombre:
            raise HTTPException(status_code=400, detail="Debes especificar la columna de nombre")
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")

        if crear_backup:
            db.crear_backup()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        df = pd.read_excel(tmp_path)
        os.unlink(tmp_path)
        df = df.dropna(subset=[col_nombre], how='all')
        df = df.fillna('')

        importados = 0
        errores = []
        for idx, row in df.iterrows():
            try:
                nombre = str(row.get(col_nombre, '')).strip()
                if not nombre or nombre.lower() == 'nan':
                    continue
                categoria = str(row.get(col_categoria, '')).strip() if (col_categoria and col_categoria in df.columns) else ''
                if categoria.lower() == 'nan':
                    categoria = ''
                referencia = str(row.get(col_referencia, '')).strip() if (col_referencia and col_referencia in df.columns) else ''
                if referencia.lower() == 'nan':
                    referencia = ''
                codigo_barras = str(row.get(col_codigo_barras, '')).strip() if (col_codigo_barras and col_codigo_barras in df.columns) else ''
                if codigo_barras.lower() in ('nan', 'none'):
                    codigo_barras = ''
                precio_compra = _parse_numero(row.get(col_precio_compra, 0)) if (col_precio_compra and col_precio_compra in df.columns) else 0.0
                precio_venta = _parse_numero(row.get(col_precio_venta, 0)) if (col_precio_venta and col_precio_venta in df.columns) else 0.0
                stock = int(_parse_numero(row.get(col_stock, 0))) if (col_stock and col_stock in df.columns) else 0

                db.crear_producto(
                    nombre=nombre, categoria=categoria,
                    precio_compra=precio_compra, precio_venta=precio_venta,
                    stock=stock, stock_minimo=0, referencia=referencia or None,
                    codigo_barras=codigo_barras or None
                )
                importados += 1
            except ValueError as e:
                errores.append(f"Fila {idx + 1}: {nombre}: {str(e)}")
            except Exception as e:
                errores.append(f"Fila {idx + 1}: error inesperado ({nombre}): {str(e)}")

        db._invalidate_cache()
        return {
            "success": True,
            "message": f"Importación completada: {importados} producto(s) importado(s)",
            "data": {"importados": importados, "errores": errores}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en importación: {str(e)}")

# ==================== API: PROVEEDORES ====================

@app.get("/api/proveedores", response_model=ApiResponseProveedoresList)
async def api_get_proveedores(repo: ProveedorRepository = Depends(get_proveedor_repository)):
    """Obtiene todos los proveedores"""
    try:
        proveedores = repo.get_all()
        return {"success": True, "data": proveedores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/proveedores/buscar", response_model=ApiResponseProveedoresList)
async def api_buscar_proveedores(q: str = Query(""), repo: ProveedorRepository = Depends(get_proveedor_repository)):
    """Busca proveedores por nombre o teléfono"""
    try:
        proveedores = repo.buscar(q)
        return {"success": True, "data": proveedores}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/proveedores/{proveedor_id}", response_model=ApiResponseProveedor)
async def api_get_proveedor(proveedor_id: str, repo: ProveedorRepository = Depends(get_proveedor_repository)):
    """Obtiene un proveedor por ID"""
    try:
        proveedor = repo.get_by_id(proveedor_id)
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return {"success": True, "data": proveedor}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/proveedores", response_model=ApiResponseProveedor)
async def api_crear_proveedor(proveedor: ProveedorCreate, repo: ProveedorRepository = Depends(get_proveedor_repository)):
    """Crea un nuevo proveedor"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        if not proveedor.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre es requerido")
        
        nuevo = repo.create(proveedor)
        return {"success": True, "data": nuevo, "message": "Proveedor creado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/proveedores/{proveedor_id}", response_model=ApiResponseSimple)
async def api_actualizar_proveedor(proveedor_id: str, proveedor: ProveedorUpdate, repo: ProveedorRepository = Depends(get_proveedor_repository)):
    """Actualiza un proveedor"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        actualizado = repo.update(proveedor_id, proveedor)
        if not actualizado:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return {"success": True, "message": "Proveedor actualizado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/proveedores/{proveedor_id}", response_model=ApiResponseSimple)
async def api_eliminar_proveedor(proveedor_id: str, repo: ProveedorRepository = Depends(get_proveedor_repository)):
    """Elimina (desactiva) un proveedor"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        eliminado = repo.delete(proveedor_id)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return {"success": True, "message": "Proveedor eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: MOVIMIENTOS PROVEEDORES ====================

@app.get("/api/movimientos-proveedor", response_model=ApiResponseMovimientoProveedorList)
async def api_get_movimientos_proveedor(limite: int = Query(100, ge=1, le=500)):
    """Obtiene los últimos movimientos de proveedores"""
    try:
        movimientos = db.get_movimientos_proveedor(limite)
        proveedores = db.get_proveedores()
        proveedores_map = {str(p['id']): p['nombre'] for p in proveedores}
        for mov in movimientos:
            mov['proveedor_nombre'] = proveedores_map.get(str(mov['proveedor_id']), "Desconocido")
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/movimientos-proveedor/hoy", response_model=ApiResponseMovimientoProveedorList)
async def api_get_movimientos_proveedor_hoy():
    """Obtiene movimientos de proveedores del día"""
    try:
        movimientos = db.get_movimientos_proveedores_hoy()
        proveedores = db.get_proveedores()
        proveedores_map = {str(p['id']): p['nombre'] for p in proveedores}
        for mov in movimientos:
            mov['proveedor_nombre'] = proveedores_map.get(str(mov['proveedor_id']), "Desconocido")
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/movimientos-proveedor/proveedor/{proveedor_id}")
async def api_get_movimientos_by_proveedor(proveedor_id: str):
    """Obtiene movimientos de un proveedor"""
    try:
        movimientos = db.get_movimientos_by_proveedor(proveedor_id)
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/movimientos-proveedor", response_model=ApiResponseMovimientoProveedor)
async def api_crear_movimiento_proveedor(movimiento: MovimientoProveedorCreate):
    """Crea un nuevo movimiento de proveedor"""
    try:
        # Verificar trial
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        if movimiento.tipo not in ['factura', 'pago']:
            raise HTTPException(status_code=400, detail="Tipo debe ser 'factura' o 'pago'")
        
        if movimiento.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
        # Verificar que el proveedor existe
        proveedor = db.get_proveedor_by_id(movimiento.proveedor_id)
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        # Si se envía el detalle de productos, la opción debe estar activa
        items = None
        if movimiento.items:
            if not _get_config_full().get("facturas_sumar_stock", False):
                raise HTTPException(
                    status_code=400,
                    detail="La opción de sumar stock en facturas está desactivada. Actívala en Configuración > Inventario."
                )
            items = [item.model_dump() for item in movimiento.items]
        
        nuevo = db.crear_movimiento_proveedor(
            proveedor_id=movimiento.proveedor_id,
            tipo=movimiento.tipo,
            descripcion=movimiento.descripcion.strip(),
            monto=movimiento.monto,
            fecha=movimiento.fecha,
            items=items
        )
        
        nuevo['proveedor_nombre'] = proveedor['nombre']
        
        return {
            "success": True, 
            "data": nuevo, 
            "message": f"{'Factura' if movimiento.tipo == 'factura' else 'Pago'} registrado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: HISTORIAL Y RESÚMENES PROVEEDORES ====================

@app.get("/api/historial-proveedor/{proveedor_id}")
async def api_get_historial_proveedor(proveedor_id: str):
    """Obtiene el historial completo de un proveedor"""
    try:
        historial = db.get_historial_proveedor(proveedor_id)
        if not historial:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        return {"success": True, "data": historial}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard-proveedores")
async def api_get_dashboard_proveedores():
    """Obtiene estadísticas del dashboard de proveedores"""
    try:
        stats = db.get_dashboard_stats_proveedores()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: INVENTARIO Y VENTAS ====================

@app.get("/api/productos", response_model=ApiResponseProductosList)
async def api_get_productos():
    """Obtiene productos activos"""
    try:
        return {"success": True, "data": db.get_productos()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productos/buscar", response_model=ApiResponseProductosList)
async def api_buscar_productos(q: str = Query("")):
    """Busca productos por nombre o categoria"""
    try:
        return {"success": True, "data": db.buscar_productos(q)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productos/buscar-por-codigo", response_model=ApiResponseProducto)
async def api_buscar_producto_por_codigo(codigo: str = Query(..., description="Código de barras exacto a buscar")):
    """Busca un producto por código de barras exacto. 200 si existe, 404 si no."""
    try:
        producto = db.buscar_producto_por_codigo(codigo)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"success": True, "data": producto}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productos/{producto_id}", response_model=ApiResponseProductoDetalle)
async def api_get_producto(producto_id: str):
    """Obtiene detalle completo de un producto (datos, precios, movimientos y ventas)"""
    try:
        producto = db.get_producto_detalle(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"success": True, "data": producto}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/productos", response_model=ApiResponseProducto)
async def api_crear_producto(producto: ProductoCreate):
    """Crea un producto"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        if not producto.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre es requerido")
        if (producto.precio_compra or 0) < 0 or (producto.precio_venta or 0) < 0:
            raise HTTPException(status_code=400, detail="Los precios no pueden ser negativos")
        if (producto.stock or 0) < 0 or (producto.stock_minimo or 0) < 0:
            raise HTTPException(status_code=400, detail="El stock no puede ser negativo")

        codigo_normalizado = normalizar_codigo_barras(producto.codigo_barras)
        if codigo_normalizado and db._codigo_barras_en_uso(codigo_normalizado):
            raise HTTPException(status_code=409, detail="Ya existe un producto con ese código de barras")

        nuevo = db.crear_producto(
            nombre=producto.nombre.strip(),
            categoria=(producto.categoria or "").strip(),
            precio_compra=producto.precio_compra or 0,
            precio_venta=producto.precio_venta or 0,
            stock=producto.stock or 0,
            stock_minimo=producto.stock_minimo or 0,
            referencia=(producto.referencia or "").strip() if producto.referencia else None,
            codigo_barras=codigo_normalizado,
        )
        return {"success": True, "data": nuevo, "message": "Producto creado exitosamente"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/productos/{producto_id}", response_model=ApiResponseSimple)
async def api_actualizar_producto(producto_id: str, producto: ProductoUpdate):
    """Actualiza un producto"""
    try:
        if producto.codigo_barras is not None:
            codigo_normalizado = normalizar_codigo_barras(producto.codigo_barras)
            if codigo_normalizado and db._codigo_barras_en_uso(codigo_normalizado, exclude_id=producto_id):
                raise HTTPException(status_code=409, detail="Ya existe un producto con ese código de barras")

        actualizado = db.actualizar_producto(
            producto_id=producto_id,
            nombre=producto.nombre,
            categoria=producto.categoria,
            precio_compra=producto.precio_compra,
            precio_venta=producto.precio_venta,
            stock=producto.stock,
            stock_minimo=producto.stock_minimo,
            referencia=producto.referencia,
            codigo_barras=producto.codigo_barras,
        )
        if not actualizado:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"success": True, "message": "Producto actualizado exitosamente"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/productos/{producto_id}", response_model=ApiResponseSimple)
async def api_eliminar_producto(producto_id: str):
    """Desactiva un producto"""
    try:
        eliminado = db.eliminar_producto(producto_id)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"success": True, "message": "Producto eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ventas", response_model=ApiResponseVentasList)
async def api_get_ventas(limite: int = Query(100, ge=1, le=500)):
    """Obtiene ventas recientes"""
    try:
        return {"success": True, "data": db.get_ventas(limite)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ventas", response_model=ApiResponseVenta)
async def api_crear_venta(venta: VentaCreate):
    """Registra una venta y descuenta inventario"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        if venta.cantidad <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a 0")
        if venta.precio_unitario is not None and venta.precio_unitario < 0:
            raise HTTPException(status_code=400, detail="El precio no puede ser negativo")

        nueva = db.crear_venta(
            producto_id=venta.producto_id,
            cantidad=venta.cantidad,
            precio_unitario=venta.precio_unitario,
            nota=(venta.nota or "").strip(),
        )
        return {"success": True, "data": nueva, "message": "Venta registrada exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/ventas/{venta_id}", response_model=ApiResponseSimple)
async def api_anular_venta(venta_id: str):
    """Anula una venta y devuelve el stock"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        anulado = db.anular_venta(venta_id)
        if not anulado:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        return {"success": True, "message": "Venta anulada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/productos/{producto_id}/ajustar-stock", response_model=ApiResponseSimple)
async def api_ajustar_stock(producto_id: str, ajuste: AjusteStock):
    """Ajusta el stock de un producto rápidamente"""
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        if ajuste.cantidad_cambio == 0:
            raise HTTPException(status_code=400, detail="La cantidad de ajuste no puede ser 0")

        ajustado = db.ajustar_stock(producto_id, ajuste.cantidad_cambio, ajuste.nota)
        if not ajustado:
            raise HTTPException(status_code=404, detail="Producto no encontrado o error en ajuste")
        return {"success": True, "message": "Stock ajustado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard-inventario", response_model=ApiResponseInventarioStats)
async def api_get_dashboard_inventario():
    """Obtiene resumen de inventario"""
    try:
        return {"success": True, "data": db.get_dashboard_stats_inventario()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: TRIAL ====================

@app.get("/api/trial")
async def api_get_trial_info():
    """Obtiene información del período de prueba"""
    try:
        trial_info = db.get_trial_info()
        return {"success": True, "data": trial_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: CONFIGURACIÓN ====================

class ConfigUpdate(BaseModel):
    nombre_tienda: Optional[str] = None
    direccion: Optional[str] = None
    nit: Optional[str] = None
    telefono: Optional[str] = None
    mostrar_montos_dashboard: Optional[bool] = None
    mostrar_resumen_inicio: Optional[bool] = None
    whatsapp_template_abono: Optional[str] = None
    whatsapp_template_prestamo: Optional[str] = None
    whatsapp_template_recordatorio: Optional[str] = None
    whatsapp_template_factura: Optional[str] = None
    whatsapp_template_pago: Optional[str] = None
    qr_pago_activo: Optional[bool] = None
    qr_pago_nequi: Optional[str] = None
    qr_pago_davi: Optional[str] = None
    qr_pago_bancolombia: Optional[str] = None
    facturas_sumar_stock: Optional[bool] = None
    recibo_venta: Optional[bool] = None
    codigo_barras_activo: Optional[bool] = None
    backup_activo: Optional[bool] = None
    backup_hora: Optional[str] = None
    backup_frecuencia: Optional[str] = None
    backup_mantener: Optional[int] = None

# Funciones auxiliares para configuración (sin modificar database.py)
def _get_config_full() -> Dict[str, Any]:
    """Obtiene toda la configuración del sistema"""
    conn = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT clave, valor FROM config")
        rows = cursor.fetchall()
        
        config = {row["clave"]: row["valor"] for row in rows}
        
        return {
            "nombre_tienda": config.get("nombre_tienda", "EnOrden"),
            "direccion": config.get("direccion", ""),
            "nit": config.get("nit", ""),
            "telefono": config.get("telefono", ""),
            "mostrar_montos_dashboard": config.get("mostrar_montos_dashboard", "false").lower() == "true",
            "mostrar_resumen_inicio": config.get("mostrar_resumen_inicio", "false").lower() == "true",
            "whatsapp_template_abono": config.get("whatsapp_template_abono", ""),
            "whatsapp_template_prestamo": config.get("whatsapp_template_prestamo", ""),
            "whatsapp_template_recordatorio": config.get("whatsapp_template_recordatorio", ""),
            "whatsapp_template_factura": config.get("whatsapp_template_factura", ""),
            "whatsapp_template_pago": config.get("whatsapp_template_pago", ""),
            "qr_pago_activo": config.get("qr_pago_activo", "false").lower() == "true",
            "qr_pago_nequi": config.get("qr_pago_nequi", ""),
            "qr_pago_davi": config.get("qr_pago_davi", ""),
            "qr_pago_bancolombia": config.get("qr_pago_bancolombia", ""),
            "facturas_sumar_stock": config.get("facturas_sumar_stock", "false").lower() == "true",
            "recibo_venta": config.get("recibo_venta", "false").lower() == "true",
            "codigo_barras_activo": config.get("codigo_barras_activo", "false").lower() == "true",
            "backup_activo": config.get("backup_activo", "true").lower() == "true",
            "backup_hora": config.get("backup_hora", "23:00"),
            "backup_frecuencia": config.get("backup_frecuencia", "diario"),
            "backup_mantener": int(config.get("backup_mantener", "30"))
        }
    except Exception as e:
        print(f"Error obteniendo config: {e}")
        return {
            "nombre_tienda": "EnOrden",
            "direccion": "",
            "nit": "",
            "telefono": "",
            "mostrar_montos_dashboard": False,
            "mostrar_resumen_inicio": False,
            "whatsapp_template_abono": "",
            "whatsapp_template_prestamo": "",
            "whatsapp_template_recordatorio": "",
            "whatsapp_template_factura": "",
            "whatsapp_template_pago": "",
            "qr_pago_activo": False,
            "qr_pago_nequi": "",
            "qr_pago_davi": "",
            "qr_pago_bancolombia": "",
            "facturas_sumar_stock": False,
            "recibo_venta": False,
            "codigo_barras_activo": False,
            "backup_activo": True,
            "backup_hora": "23:00",
            "backup_frecuencia": "diario",
            "backup_mantener": 30
        }
    finally:
        if conn:
            conn.close()

def _set_config_full(updates: Dict[str, str]) -> bool:
    """Guarda valores de configuración"""
    conn = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        for clave, valor in updates.items():
            cursor.execute(
                "INSERT OR REPLACE INTO config (clave, valor, descripcion) VALUES (?, ?, ?)",
                (clave, str(valor), "")
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error guardando config: {e}")
        return False
    finally:
        if conn:
            conn.close()

def _verificar_integridad_datos() -> Dict[str, Any]:
    """Verifica la integridad de los datos en SQLite"""
    conn = None
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clientes
        cursor.execute("SELECT COUNT(*) FROM clientes WHERE activo = 1")
        clientes_ok = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clientes WHERE nombre IS NULL OR trim(nombre) = ''")
        clientes_sin_nombre = cursor.fetchone()[0]
        
        # Movimientos
        cursor.execute("SELECT COUNT(*) FROM movimientos")
        movimientos_ok = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM movimientos WHERE cliente_id NOT IN (SELECT id FROM clientes)")
        movimientos_huerfanos = cursor.fetchone()[0]
        
        # Proveedores
        cursor.execute("SELECT COUNT(*) FROM proveedores WHERE activo = 1")
        proveedores_ok = cursor.fetchone()[0]
        
        # Movimientos proveedores
        cursor.execute("SELECT COUNT(*) FROM movimientos_proveedores WHERE proveedor_id NOT IN (SELECT id FROM proveedores)")
        movimientos_proveedor_huerfanos = cursor.fetchone()[0]
        
        return {
            "clientes_ok": clientes_ok,
            "clientes_sin_nombre": clientes_sin_nombre,
            "movimientos_ok": movimientos_ok,
            "movimientos_huerfanos": movimientos_huerfanos,
            "proveedores_ok": proveedores_ok,
            "movimientos_proveedor_huerfanos": movimientos_proveedor_huerfanos,
            "errores": []
        }
    except Exception as e:
        return {"errores": [str(e)]}
    finally:
        if conn:
            conn.close()

def _recalcular_todos_saldos() -> Dict[str, Any]:
    """Recalcula saldos de todos los clientes y proveedores"""
    try:
        clientes = db.get_clientes()
        proveedores = db.get_proveedores()
        
        resultados = {
            "clientes_procesados": 0,
            "proveedores_procesados": 0
        }
        
        for cliente in clientes:
            db.get_resumen_cliente(cliente['id'])
            resultados["clientes_procesados"] += 1
        
        for proveedor in proveedores:
            db.get_resumen_proveedor(proveedor['id'])
            resultados["proveedores_procesados"] += 1
        
        return resultados
    except Exception as e:
        return {"errores": [str(e)]}

@app.get("/api/configuracion")
async def api_get_configuracion():
    """Obtiene la configuración del sistema"""
    try:
        config = _get_config_full()
        return {"success": True, "data": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/configuracion")
async def api_update_configuracion(config: ConfigUpdate):
    """Actualiza la configuración del sistema"""
    try:
        updates = {}
        if config.nombre_tienda is not None:
            updates['nombre_tienda'] = config.nombre_tienda
        if config.direccion is not None:
            updates['direccion'] = config.direccion
        if config.nit is not None:
            updates['nit'] = config.nit
        if config.telefono is not None:
            updates['telefono'] = config.telefono
        if config.mostrar_montos_dashboard is not None:
            updates['mostrar_montos_dashboard'] = str(config.mostrar_montos_dashboard).lower()
        if config.mostrar_resumen_inicio is not None:
            updates['mostrar_resumen_inicio'] = str(config.mostrar_resumen_inicio).lower()
        if config.whatsapp_template_abono is not None:
            updates['whatsapp_template_abono'] = config.whatsapp_template_abono
        if config.whatsapp_template_prestamo is not None:
            updates['whatsapp_template_prestamo'] = config.whatsapp_template_prestamo
        if config.whatsapp_template_recordatorio is not None:
            updates['whatsapp_template_recordatorio'] = config.whatsapp_template_recordatorio
        if config.whatsapp_template_factura is not None:
            updates['whatsapp_template_factura'] = config.whatsapp_template_factura
        if config.whatsapp_template_pago is not None:
            updates['whatsapp_template_pago'] = config.whatsapp_template_pago
        if config.qr_pago_activo is not None:
            updates['qr_pago_activo'] = str(config.qr_pago_activo).lower()
        if config.qr_pago_nequi is not None:
            updates['qr_pago_nequi'] = config.qr_pago_nequi
        if config.qr_pago_davi is not None:
            updates['qr_pago_davi'] = config.qr_pago_davi
        if config.qr_pago_bancolombia is not None:
            updates['qr_pago_bancolombia'] = config.qr_pago_bancolombia
        if config.facturas_sumar_stock is not None:
            updates['facturas_sumar_stock'] = str(config.facturas_sumar_stock).lower()
        if config.recibo_venta is not None:
            updates['recibo_venta'] = str(config.recibo_venta).lower()
        if config.codigo_barras_activo is not None:
            updates['codigo_barras_activo'] = str(config.codigo_barras_activo).lower()
        if config.backup_activo is not None:
            updates['backup_activo'] = str(config.backup_activo).lower()
        if config.backup_hora is not None:
            updates['backup_hora'] = config.backup_hora
        if config.backup_frecuencia is not None:
            updates['backup_frecuencia'] = config.backup_frecuencia
        if config.backup_mantener is not None:
            updates['backup_mantener'] = str(max(1, config.backup_mantener))
        
        if updates:
            _set_config_full(updates)
        
        # Si cambió la programación de backups, recalcular próxima copia
        if any(k in updates for k in ('backup_activo', 'backup_hora', 'backup_frecuencia', 'backup_mantener')):
            try:
                from scheduler import backup_scheduler
                backup_scheduler.reconfigurar()
            except Exception:
                pass
        
        return {"success": True, "message": "Configuración actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API: TELEGRAM ====================

class TelegramConfigUpdate(BaseModel):
    token: Optional[str] = None
    admin_id: Optional[str] = None

class TelegramUsuarioUpdate(BaseModel):
    rol: Optional[str] = None
    activo: Optional[bool] = None

_ROLES_TELEGRAM = ("super_admin", "admin", "operador")

def _count_super_admins_activos() -> int:
    """Cuenta super_admins activos para no dejar el bot sin administrador."""
    from repository import telegram_user_repo
    usuarios = telegram_user_repo.get_all()
    return sum(1 for u in usuarios if u["rol"] == "super_admin" and u["activo"])

@app.get("/api/telegram/estado")
async def api_get_telegram_estado():
    """Estado del bot de Telegram para Configuración (no expone el token)."""
    try:
        import telegram_bot
        estado = telegram_bot.get_estado_publico()
        estado["username"] = await telegram_bot.obtener_username_bot()
        return {"success": True, "data": estado}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.put("/api/telegram/config")
async def api_update_telegram_config(config: TelegramConfigUpdate):
    """Guarda credenciales del bot y lo reinicia automáticamente."""
    try:
        updates = {}
        if config.token is not None:
            token = config.token.strip()
            if not token or token in ("your_telegram_bot_token_here", "TU_TELEGRAM_BOT_TOKEN_AQUI"):
                return {"success": False, "mensaje": "El token no es válido"}
            updates['telegram_token'] = token
        if config.admin_id is not None:
            admin = config.admin_id.strip()
            try:
                int(admin)
            except ValueError:
                return {"success": False, "mensaje": "El Admin ID debe ser un número"}
            updates['telegram_admin_id'] = admin
        if not updates:
            return {"success": False, "mensaje": "No hay cambios para guardar"}

        if not _set_config_full(updates):
            return {"success": False, "mensaje": "Error guardando la configuración"}

        try:
            startup_manager.reiniciar_telegram_bot()
        except Exception as e:
            print(f"Error reiniciando el bot: {e}")

        return {"success": True, "message": "Credenciales guardadas y bot reiniciado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/telegram/prueba")
async def api_telegram_mensaje_prueba():
    """Envía un mensaje de prueba al Admin ID del bot."""
    try:
        import telegram_bot
        resultado = await telegram_bot.enviar_mensaje_prueba()
        return {"success": resultado.get("ok", False), "mensaje": resultado.get("mensaje", "")}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.post("/api/telegram/reiniciar")
async def api_telegram_reiniciar():
    """Reinicia el hilo del bot sin reiniciar la app."""
    try:
        startup_manager.reiniciar_telegram_bot()
        return {"success": True, "message": "Bot reiniciado"}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.get("/api/telegram/usuarios")
def api_get_telegram_usuarios():
    """Lista los usuarios autorizados del bot de Telegram."""
    try:
        from repository import telegram_user_repo
        return {"success": True, "data": telegram_user_repo.get_all()}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.post("/api/telegram/usuarios")
def api_create_telegram_usuario(usuario: TelegramUserCreate):
    """Registra un nuevo usuario autorizado del bot."""
    try:
        from repository import telegram_user_repo
        if telegram_user_repo.get_by_telegram_id(usuario.telegram_id):
            return {"success": False, "mensaje": "Ese ID ya está registrado"}
        if usuario.rol not in _ROLES_TELEGRAM:
            return {"success": False, "mensaje": "Rol inválido"}
        creado = telegram_user_repo.create(usuario)
        return {"success": True, "data": creado}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.patch("/api/telegram/usuarios/{telegram_id}")
def api_update_telegram_usuario(telegram_id: int, update: TelegramUsuarioUpdate):
    """Cambia rol o estado activo de un usuario del bot."""
    try:
        from repository import telegram_user_repo
        existente = telegram_user_repo.get_by_telegram_id(telegram_id)
        if not existente:
            return {"success": False, "mensaje": "El usuario no existe"}

        if update.rol is not None:
            if update.rol not in _ROLES_TELEGRAM:
                return {"success": False, "mensaje": "Rol inválido"}
            if existente["rol"] == "super_admin" and update.rol != "super_admin" and _count_super_admins_activos() <= 1:
                return {"success": False, "mensaje": "No se puede quitar el rol al último super_admin"}
            telegram_user_repo.update_rol(telegram_id, update.rol)

        if update.activo is not None:
            if existente["rol"] == "super_admin" and not update.activo and _count_super_admins_activos() <= 1:
                return {"success": False, "mensaje": "No se puede desactivar al último super_admin"}
            telegram_user_repo.set_activo(telegram_id, update.activo)

        return {"success": True, "data": telegram_user_repo.get_by_telegram_id(telegram_id)}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.delete("/api/telegram/usuarios/{telegram_id}")
def api_delete_telegram_usuario(telegram_id: int):
    """Elimina un usuario autorizado del bot."""
    try:
        from repository import telegram_user_repo
        existente = telegram_user_repo.get_by_telegram_id(telegram_id)
        if not existente:
            return {"success": False, "mensaje": "El usuario no existe"}
        if existente["rol"] == "super_admin" and _count_super_admins_activos() <= 1:
            return {"success": False, "mensaje": "No se puede eliminar al último super_admin"}
        telegram_user_repo.delete(telegram_id)
        return {"success": True, "message": "Usuario eliminado"}
    except Exception as e:
        return {"success": False, "mensaje": str(e)}

@app.post("/api/mantenimiento/recalcular")
async def api_recalcular_saldos():
    """Recalcula todos los saldos de clientes y proveedores"""
    try:
        resultado = _recalcular_todos_saldos()
        return {"success": True, "message": "Saldos recalculados", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mantenimiento/verificar")
async def api_verificar_datos():
    """Verifica la integridad de los datos"""
    try:
        resultado = _verificar_integridad_datos()
        return {"success": True, "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== INICIO DE LA APLICACIÓN ====================

def _bloquear_instancia_duplicada():
    """Impide ejecutar dos instancias de EnOrden sobre la misma instalación/datos.
    El handle del mutex vive durante todo el proceso; Windows lo libera al salir.
    Si el mutex no puede crearse (entorno sin soporte), la app arranca igual."""
    try:
        import ctypes
        import hashlib
        nombre = "Local\\EnOrden_" + hashlib.sha256(db.data_dir.encode("utf-8")).hexdigest()[:16]
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, nombre)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(
                None,
                "EnOrden ya está en ejecución en esta instalación.\n\n"
                "Cierre la otra ventana antes de abrir una nueva.",
                "EnOrden",
                0x40 | 0x1000,  # MB_ICONINFORMATION | MB_SYSTEMMODAL
            )
            sys.exit(0)
    except Exception:
        pass  # nunca debe bloquear el arranque


def _log_startup(mensaje: str):
    """Escribe un evento en {data_dir}/logs/startup.log (junto al .exe en modo congelado)."""
    try:
        log_dir = os.path.join(db.data_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "startup.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {mensaje}\n")
    except Exception:
        pass  # el log nunca debe bloquear el arranque


def _encontrar_puerto_libre(inicio: int = 8000, fin: int = 9000) -> int:
    """Busca el primer puerto libre en el rango [inicio, fin] (fallback si 8000 está ocupado)."""
    import socket
    for puerto in range(inicio, fin + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", puerto))
                return puerto
            except OSError:
                continue
    return inicio


def open_browser(puerto: int):
    """Abre el navegador después de un pequeño delay"""
    time.sleep(1.5)
    url = f"http://localhost:{puerto}"
    _log_startup(f"URL abierta en el navegador: {url}")
    webbrowser.open(url)


def run_server(puerto: int = None):
    """Ejecuta el servidor uvicorn en un puerto libre (8000 o superior)."""
    puerto = puerto if puerto is not None else _encontrar_puerto_libre()
    _log_startup(f"Puerto seleccionado: {puerto}")
    _log_startup(f"Base de datos: {db.db_path} ({'existente' if db.bd_previa else 'creada'})")
    _log_startup(f"Backups: {db.backup_dir}")

    print("\n" + "="*50)
    print("  TECNOSPORT - Sistema de Cuentas por Cobrar")
    print("  Centro Comercial El Diamante 2")
    print("="*50)
    print(f"\n  Base de datos: {db.excel_path}")
    print(f"  Backups: {db.backup_dir}")
    print(f"\n  Abriendo en navegador: http://localhost:{puerto}")
    print("\n  Presiona Ctrl+C para detener el servidor")
    print("="*50 + "\n")

    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=puerto,
            log_level="warning"
        )
    except Exception as e:
        import traceback
        _log_startup(f"ERROR iniciando el servidor: {e}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    # Una sola instancia por instalación/datos (aviso y salida si ya hay otra)
    _bloquear_instancia_duplicada()

    # Abrir navegador automáticamente
    # NOTA: Descomentado para lanzar automáticamente el navegador en modo standalone/ejecutable
    puerto = _encontrar_puerto_libre()
    browser_thread = threading.Thread(target=open_browser, args=(puerto,))
    browser_thread.daemon = True
    browser_thread.start()
    
    # Ejecutar servidor
    run_server(puerto)
