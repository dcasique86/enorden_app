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
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import uvicorn

# Importar módulo de base de datos
from database import db

# Importar esquemas y repositorios para Clientes y Proveedores
from schemas import (
    ClienteCreate, ClienteUpdate, ClienteRead, ApiResponseCliente, ApiResponseClientesList, ApiResponseClientesConDeuda,
    ProveedorCreate, ProveedorUpdate, ProveedorRead, ApiResponseProveedor, ApiResponseProveedoresList,
    MovimientoCreate, MovimientoRead, ApiResponseMovimientosList,
    MovimientoProveedorCreate, MovimientoProveedorRead, ApiResponseMovimientoProveedorList,
    ApiResponseSimple,
    GastoCreate, GastoRead, ApiResponseGasto, ApiResponseGastosList,
    FlujoCajaResumen, ApiResponseFlujoCaja
)
from repository import (
    ClienteRepository, ProveedorRepository, GastoRepository,
    get_cliente_repository, get_proveedor_repository, get_gasto_repository
)

# Importar scheduler de forma opcional (no crítico para la app)
try:
    from scheduler import start_backup_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    print("⚠️ Scheduler no disponible - backups automáticos desactivados")

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



app = FastAPI(
    title="EnOrden",
    description="Sistema de Control de Cuentas por Cobrar",
    version="1.0.0"
)

# CORS limitado a la app local; se puede ampliar con ENORDEN_CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    precio_compra: Optional[float] = None
    precio_venta: Optional[float] = None
    stock: Optional[int] = None
    stock_minimo: Optional[int] = None
    referencia: Optional[str] = None

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
    """Crea un nuevo movimiento"""
    try:
        # Verificar trial
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado. Contacte al proveedor.")
        
        if movimiento.tipo not in ['prestamo', 'abono']:
            raise HTTPException(status_code=400, detail="Tipo debe ser 'prestamo' o 'abono'")
        
        if movimiento.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
        # Verificar que el cliente existe
        cliente = db.get_cliente_by_id(movimiento.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        nuevo = db.crear_movimiento(
            cliente_id=movimiento.cliente_id,
            tipo=movimiento.tipo,
            descripcion=movimiento.descripcion.strip(),
            monto=movimiento.monto
        )
        
        nuevo['cliente_nombre'] = cliente['nombre']
        
        return {
            "success": True, 
            "data": nuevo, 
            "message": f"{'Préstamo' if movimiento.tipo == 'prestamo' else 'Abono'} registrado exitosamente"
        }
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

@app.post("/api/backups")
async def api_crear_backup():
    """Crea un backup manual"""
    try:
        backup_path = db.crear_backup()
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
        backup_path = os.path.join(db.backup_dir, filename)
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="Backup no encontrado")
        return FileResponse(
            backup_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
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
async def api_importar_datos(file: UploadFile = File(...), config: str = "{}"):
    """Importa datos desde un archivo Excel"""
    import json
    
    try:
        # Parsear configuración
        config_dict = json.loads(config) if isinstance(config, str) else config
        
        col_nombre = config_dict.get('col_nombre', '')
        col_telefono = config_dict.get('col_telefono', '')
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
        
        # Abrir archivo destino
        wb = load_workbook(db.excel_path)
        ws_clientes = wb["clientes"]
        ws_movimientos = wb["movimientos"]
        
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
                
                # Crear ID de cliente
                cliente_id = str(uuid_module.uuid4())
                
                # Agregar cliente
                ws_clientes.append([
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
                    ws_movimientos.append([
                        str(uuid_module.uuid4()),
                        cliente_id,
                        'prestamo',
                        'Saldo inicial importado',
                        prestamos,
                        fecha_actual,
                        timestamp_actual
                    ])
                    movimientos_importados += 1
                
                # Crear movimiento de abono
                if abonos > 0:
                    ws_movimientos.append([
                        str(uuid_module.uuid4()),
                        cliente_id,
                        'abono',
                        'Abonos previos importados',
                        abonos,
                        fecha_actual,
                        timestamp_actual
                    ])
                    movimientos_importados += 1
                    
            except Exception as e:
                continue
        
        # Guardar archivo
        wb.save(db.excel_path)
        
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

@app.post("/api/movimientos-proveedor")
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
        
        nuevo = db.crear_movimiento_proveedor(
            proveedor_id=movimiento.proveedor_id,
            tipo=movimiento.tipo,
            descripcion=movimiento.descripcion.strip(),
            monto=movimiento.monto,
            fecha=movimiento.fecha
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

@app.get("/api/productos")
async def api_get_productos():
    """Obtiene productos activos"""
    try:
        return {"success": True, "data": db.get_productos()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productos/buscar")
async def api_buscar_productos(q: str = Query("")):
    """Busca productos por nombre o categoria"""
    try:
        return {"success": True, "data": db.buscar_productos(q)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/productos/{producto_id}")
async def api_get_producto(producto_id: str):
    """Obtiene un producto"""
    try:
        producto = db.get_producto_by_id(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"success": True, "data": producto}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/productos")
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

        nuevo = db.crear_producto(
            nombre=producto.nombre.strip(),
            categoria=(producto.categoria or "").strip(),
            precio_compra=producto.precio_compra or 0,
            precio_venta=producto.precio_venta or 0,
            stock=producto.stock or 0,
            stock_minimo=producto.stock_minimo or 0,
            referencia=(producto.referencia or "").strip() if producto.referencia else None,
        )
        return {"success": True, "data": nuevo, "message": "Producto creado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/productos/{producto_id}")
async def api_actualizar_producto(producto_id: str, producto: ProductoUpdate):
    """Actualiza un producto"""
    try:
        actualizado = db.actualizar_producto(
            producto_id=producto_id,
            nombre=producto.nombre,
            categoria=producto.categoria,
            precio_compra=producto.precio_compra,
            precio_venta=producto.precio_venta,
            stock=producto.stock,
            stock_minimo=producto.stock_minimo,
            referencia=producto.referencia,
        )
        if not actualizado:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return {"success": True, "message": "Producto actualizado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/productos/{producto_id}")
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

@app.get("/api/ventas")
async def api_get_ventas(limite: int = Query(100, ge=1, le=500)):
    """Obtiene ventas recientes"""
    try:
        return {"success": True, "data": db.get_ventas(limite)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ventas")
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

@app.delete("/api/ventas/{venta_id}")
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

@app.post("/api/productos/{producto_id}/ajustar-stock")
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

@app.get("/api/dashboard-inventario")
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
    mostrar_montos_dashboard: Optional[bool] = None
    mostrar_resumen_inicio: Optional[bool] = None
    whatsapp_template_abono: Optional[str] = None
    whatsapp_template_prestamo: Optional[str] = None
    whatsapp_template_recordatorio: Optional[str] = None
    qr_pago_activo: Optional[bool] = None
    qr_pago_nequi: Optional[str] = None
    qr_pago_davi: Optional[str] = None
    qr_pago_bancolombia: Optional[str] = None

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
            "mostrar_montos_dashboard": config.get("mostrar_montos_dashboard", "false").lower() == "true",
            "mostrar_resumen_inicio": config.get("mostrar_resumen_inicio", "false").lower() == "true",
            "whatsapp_template_abono": config.get("whatsapp_template_abono", ""),
            "whatsapp_template_prestamo": config.get("whatsapp_template_prestamo", ""),
            "whatsapp_template_recordatorio": config.get("whatsapp_template_recordatorio", ""),
            "qr_pago_activo": config.get("qr_pago_activo", "false").lower() == "true",
            "qr_pago_nequi": config.get("qr_pago_nequi", ""),
            "qr_pago_davi": config.get("qr_pago_davi", ""),
            "qr_pago_bancolombia": config.get("qr_pago_bancolombia", "")
        }
    except Exception as e:
        print(f"Error obteniendo config: {e}")
        return {
            "nombre_tienda": "EnOrden",
            "mostrar_montos_dashboard": False,
            "mostrar_resumen_inicio": False,
            "whatsapp_template_abono": "",
            "whatsapp_template_prestamo": "",
            "whatsapp_template_recordatorio": "",
            "qr_pago_activo": False,
            "qr_pago_nequi": "",
            "qr_pago_davi": "",
            "qr_pago_bancolombia": ""
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
        if config.qr_pago_activo is not None:
            updates['qr_pago_activo'] = str(config.qr_pago_activo).lower()
        if config.qr_pago_nequi is not None:
            updates['qr_pago_nequi'] = config.qr_pago_nequi
        if config.qr_pago_davi is not None:
            updates['qr_pago_davi'] = config.qr_pago_davi
        if config.qr_pago_bancolombia is not None:
            updates['qr_pago_bancolombia'] = config.qr_pago_bancolombia
        
        if updates:
            _set_config_full(updates)
        
        return {"success": True, "message": "Configuración actualizada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

def open_browser():
    """Abre el navegador después de un pequeño delay"""
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

def run_server():
    """Ejecuta el servidor uvicorn"""
    # Iniciar programador de backups automáticos (si está disponible)
    if SCHEDULER_AVAILABLE:
        try:
            start_backup_scheduler()
        except Exception as e:
            print(f"[WARN] No se pudo iniciar el scheduler: {e}")
    
    print("\n" + "="*50)
    print("  TECNOSPORT - Sistema de Cuentas por Cobrar")
    print("  Centro Comercial El Diamante 2")
    print("="*50)
    print(f"\n  Base de datos: {db.excel_path}")
    print(f"  Backups: {db.backup_dir}")
    print("\n  Abriendo en navegador: http://localhost:8000")
    print("\n  Presiona Ctrl+C para detener el servidor")
    print("="*50 + "\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="warning"
    )

if __name__ == "__main__":
    # Abrir navegador automáticamente
    # NOTA: Descomentado para lanzar automáticamente el navegador en modo standalone/ejecutable
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Ejecutar servidor
    run_server()
