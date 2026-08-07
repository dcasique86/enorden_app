# Esquema de Base de Datos

Base de datos local **SQLite**: `tecnosport_app/datos_tecnosport.db`
(archivo Excel `datos_tecnosport.xlsx` se conserva solo para exportación/descarga).

- Gestor: `DatabaseManager` en `tecnosport_app/database.py`
- Datos aislados en tests: directorio temporal por fixture (la BD real nunca se toca en pruebas).

---

## Tablas (esquema base, `_initialize_database`)

### `clientes`
| Columna | Tipo | Notas |
|---|---|---|
| id | TEXT PK | UUID |
| nombre | TEXT NOT NULL | |
| telefono | TEXT | |
| cedula | TEXT | agregada por migración v3 |
| direccion | TEXT | agregada por migración v3 |
| ciudad | TEXT | agregada por migración v3 |
| fecha_creacion | TEXT | |
| activo | INTEGER DEFAULT 1 | |

Índice: `idx_clientes_cedula` (v3).

### `movimientos`
| Columna | Tipo | Notas |
|---|---|---|
| id | TEXT PK | |
| cliente_id | TEXT NOT NULL | FK → `clientes(id)` |
| tipo | TEXT NOT NULL | `'prestamo'` o `'abono'` |
| descripcion | TEXT | |
| monto | REAL NOT NULL | |
| fecha / timestamp | TEXT | |
| tipo_operacion | TEXT DEFAULT 'COMPRA' | migración v1 |
| estado_operacion | TEXT DEFAULT 'COMPRA' | migración v1 |
| fecha_vencimiento | TEXT | migración v1 |

### `proveedores`
| Columna | Tipo |
|---|---|
| id | TEXT PK |
| nombre | TEXT NOT NULL |
| telefono | TEXT |
| fecha_creacion | TEXT |
| activo | INTEGER DEFAULT 1 |

### `movimientos_proveedores`
| Columna | Tipo | Notas |
|---|---|---|
| id | TEXT PK | |
| proveedor_id | TEXT NOT NULL | FK → `proveedores(id)` |
| tipo | TEXT NOT NULL | `'factura'` o `'pago'` |
| descripcion | TEXT | |
| monto | REAL NOT NULL | |
| fecha / timestamp | TEXT | |
| tipo_operacion | TEXT DEFAULT 'COMPRA' | migración v2 |
| estado_operacion | TEXT DEFAULT 'COMPRA' | migración v2 |

### `productos`
| Columna | Tipo | Notas |
|---|---|---|
| id | TEXT PK | UUID |
| nombre | TEXT NOT NULL | |
| categoria | TEXT | |
| precio_compra | REAL DEFAULT 0 | |
| precio_venta | REAL DEFAULT 0 | |
| stock | INTEGER DEFAULT 0 | |
| stock_minimo | INTEGER DEFAULT 0 | |
| fecha_creacion | TEXT | |
| activo | INTEGER DEFAULT 1 | soft-delete: `0` = eliminado |
| referencia | TEXT | |
| codigo_barras | TEXT | índice único parcial — ver **Comportamiento de codigo_barras** |

### `ventas`
| Columna | Tipo |
|---|---|
| id | TEXT PK |
| producto_id | TEXT NOT NULL |
| cantidad | INTEGER |
| precio_unitario | REAL |
| total | REAL |
| timestamp | TEXT |

### `config`
| Columna | Tipo | Notas |
|---|---|---|
| clave | TEXT PK | |
| valor | TEXT | `schema_version` = registra migraciones aplicadas |
| descripcion | TEXT | |

### `gastos`, `historial_precios`, `telegram_users`, `stock_movimientos`
Tablas auxiliares del módulo de gastos, historial de precios de productos, usuarios del bot de Telegram y movimientos de stock (ajuste inicial / ventas / corrección).

---

## Migraciones (`services/migraciones.py`)

Se documentan como **idempotentes**: si `ADD COLUMN` ya existe, se omite; cada versión se registra en `config.schema_version` tras aplicarse; ejecutar de nuevo no repite nada.

| Versión | Cambios |
|---|---|
| **v1** | `movimientos`: `+ tipo_operacion`, `+ estado_operacion`, `+ fecha_vencimiento` |
| **v2** | `movimientos_proveedores`: `+ tipo_operacion`, `+ estado_operacion` |
| **v3** | `clientes`: `+ cedula`, `+ direccion`, `+ ciudad` + índice `idx_clientes_cedula` |
| **v4** | `productos`: `+ codigo_barras` + índice único `idx_productos_codigo_barras` |
| **v5** | Reemplaza el índice único por uno **parcial**: `(codigo_barras) WHERE activo = 1 AND codigo_barras IS NOT NULL AND codigo_barras <> ''` — permite reutilizar códigos de productos desactivados |

Pruebas: `tests/test_migraciones.py` (aplica todo, idempotencia, reanuda parcial,
índice parcial y reutilización/duplicado).

---

## Comportamiento de `codigo_barras`

Definido en `database.py` (`normalizar_codigo_barras`, `crear_producto`,
`actualizar_producto` y main.py/schemas):

1. **Normalización**: `normalizar_codigo_barras(codigo)` hace `strip()`; si queda vacío devuelve `None` → se guarda `NULL`.
2. **Unicidad**: índice único parcial (v5) — solo **productos activos** (`activo = 1`) con código no nulo ni vacío. Duplicados entre activos → `409` / `IntegrityError`.
3. **Reutilización**: al desactivar un producto (`DELETE` soft), su código queda libre y puede asignarse a otro producto nuevo.
4. **Limpieza**: PUT con `codigo_barras: ""` en `actualizar_producto` asigna `NULL` (no se puede limpiar con `None`, que se interpreta como "no tocar").
5. **Búsqueda**:
   - `GET /api/productos/buscar-por-codigo?codigo=` → exacta, 404 si no hay activo con ese código.
   - `GET /api/productos/buscar?q=` → búsqueda parcial (LIKE) por nombre/código.
6. **Import/export**: el XLSX exportado incluye la columna `Código de barras`; al importar se normaliza y los duplicados activos se reportan como errores de fila sin interrumpir el resto.

---

## Ejecución / verificación

```bash
cd tecnosport_app
python -m pytest tests -q          # 107 passed (incluye test_migraciones)
```