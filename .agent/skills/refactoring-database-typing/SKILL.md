---
name: refactoring-database-typing
description: >-
  Skill de Refactorización enfocado en optimizar consultas de base de datos dentro de bucles (problema N+1) utilizando JOINs o precarga en memoria, y asegurar tipado estricto de entrada y salida (response_model, Pydantic) en endpoints de la API.
version: 1.0.0
author: Antigravity
tags:
  - refactoring
  - python
  - fastapi
  - database
  - type-safety
  - optimization
---

# Skill de Refactorización y Tipado Estricto

## Overview
Esta skill guía al agente en la refactorización de código de base de datos y APIs en Python (especialmente con FastAPI). Sus objetivos clave son:
1. **Evitar consultas N+1:** Reemplazar consultas iterativas dentro de bucles `for` por consultas consolidadas usando JOINs (o precarga/mapeo en memoria en el caso de bases de datos basadas en archivos como Excel/Pandas).
2. **Tipado Estricto en APIs:** Garantizar la seguridad de tipos en todos los endpoints de FastAPI definiendo explícitamente tipos de entrada (Pydantic models) y salida (`response_model` o modelos de retorno definidos).

## When to Use
Esta skill debe activarse automáticamente siempre que se edite, revise, depure o desarrolle código del backend o de APIs, especialmente en archivos como [main.py](file:///c:/Users/DENIS%20CASIQUE/Downloads/DENIS/enorden_app/tecnosport_app/main.py) o [database.py](file:///c:/Users/DENIS%20CASIQUE/Downloads/DENIS/enorden_app/tecnosport_app/database.py).

## Instructions

### 1. Detección y Optimización de Consultas N+1 (Bucles y Consultas)
- **Identificación:** Busca patrones donde se recorre una lista y por cada elemento se realiza una llamada a la base de datos o sistema de persistencia (ej. `db.get_cliente_by_id(...)`, `db.get_resumen_proveedor(...)`).
- **Acción:**
  - **En SQL:** Sugiere/implementa una consulta `JOIN` que traiga todos los datos relacionados en una sola operación de base de datos.
  - **En persistencia basada en archivos/Pandas/Excel:** Sugiere precargar los datos relacionados en un diccionario de mapeo en memoria *antes* del bucle `for` (ej. mapear `id -> nombre` de una sola vez leyendo la hoja/tabla), evitando llamadas repetidas a disco/Excel.

### 2. Tipado Estricto de Entrada y Salida en APIs (FastAPI)
- **Identificación:** Inspecciona endpoints de la API (ej. `@app.get(...)`, `@app.post(...)`) que no tengan tipos definidos para los parámetros o que devuelvan diccionarios genéricos (`dict`, `{"success": True}`) sin especificar un `response_model` o un modelo Pydantic estructurado.
- **Acción:**
  - Crea o usa modelos Pydantic heredados de `BaseModel` para representar exactamente la estructura de entrada y de salida.
  - Especifica el parámetro `response_model` en el decorador del endpoint de FastAPI (ej. `@app.get("/api/...", response_model=MiModeloRespuesta)`).
  - Define tipos estrictos para todos los parámetros de ruta (`Path(...)`), consulta (`Query(...)`) y cuerpo (`Body(...)`).

---

## Examples

### Ejemplo 1: Optimización de consultas N+1 en bucles

#### ❌ Antes (Incorrecto - Problema N+1):
```python
@app.get("/api/movimientos")
async def api_get_movimientos(limite: int = Query(100, ge=1, le=500)):
    try:
        movimientos = db.get_movimientos(limite)
        # Se consulta la base de datos/Excel por cada movimiento en un bucle for
        for mov in movimientos:
            cliente = db.get_cliente_by_id(mov['cliente_id'])
            mov['cliente_nombre'] = cliente['nombre'] if cliente else "Desconocido"
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

####  Después (Optimizado - Precarga en memoria):
```python
@app.get("/api/movimientos")
async def api_get_movimientos(limite: int = Query(100, ge=1, le=500)):
    try:
        movimientos = db.get_movimientos(limite)
        
        # Obtenemos los IDs únicos de clientes necesarios
        cliente_ids = {mov['cliente_id'] for mov in movimientos if 'cliente_id' in mov}
        
        # Precargamos los nombres de los clientes en un único mapeo en memoria (Equivalente a un JOIN o lote de datos)
        clientes_map = db.get_clientes_nombres_by_ids(list(cliente_ids)) # Mapeo {id: nombre}
        
        for mov in movimientos:
            mov['cliente_nombre'] = clientes_map.get(mov['cliente_id'], "Desconocido")
            
        return {"success": True, "data": movimientos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Ejemplo 2: Tipado Estricto de Entrada y Salida

#### ❌ Antes (Incorrecto - Sin tipado estricto):
```python
@app.post("/api/proveedores")
async def api_crear_proveedor(proveedor):
    # Sin tipos de entrada (Pydantic model) ni salida (response_model)
    nuevo = db.crear_proveedor(nombre=proveedor.nombre, telefono=proveedor.telefono)
    return {"success": True, "data": nuevo}
```

####  Después (Correcto - Tipado estricto con Pydantic y response_model):
```python
from pydantic import BaseModel, Field

class ProveedorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del proveedor")
    telefono: Optional[str] = Field(default="", description="Teléfono del proveedor")

class ProveedorResponse(BaseModel):
    id: str
    nombre: str
    telefono: str
    activo: bool

class ApiResponseProveedor(BaseModel):
    success: bool
    data: ProveedorResponse
    message: str

@app.post("/api/proveedores", response_model=ApiResponseProveedor)
async def api_crear_proveedor(proveedor: ProveedorCreate):
    try:
        if not db.check_trial_or_raise():
            raise HTTPException(status_code=403, detail="Periodo de prueba finalizado.")
            
        nuevo = db.crear_proveedor(
            nombre=proveedor.nombre.strip(),
            telefono=proveedor.telefono.strip() if proveedor.telefono else ""
        )
        return {
            "success": True, 
            "data": nuevo, 
            "message": "Proveedor creado exitosamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```
