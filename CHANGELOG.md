# Changelog

Todas las versiones estables del sistema **EnOrden**.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado semántico.

## [1.0.0] - 2026-08-07

**Etiqueta Git:** `v1.0.0`

### Establecimiento de la versión

Este release congela el **módulo de inventario y códigos de barras**: a partir
de esta etiqueta solo se aceptan **correcciones de errores** en dicho módulo
(ver [Política de congelamiento](#política-de-congelamiento)).

### 🆕 Nuevas funcionalidades

- **Código de barras en productos**
  - Campo `codigo_barras` en el inventario, detalle de producto y formulario de edición.
  - Escáner de códigos de barras en la pantalla de nueva venta (búsqueda instantánea de producto por código).
  - Normalización de códigos (se recortan espacios; vacío se guarda como NULL).
  - Búsqueda por código parcial (`/api/productos/buscar?q=...`) y exacta (`/api/productos/buscar-por-codigo`).
  - Índice único parcial: solo se rechazan duplicados entre productos **activos**; un código de un producto eliminado (soft-delete) se puede reutilizar.
  - Limpieza de código mediante `codigo_barras: ""` en el PUT de producto.
- **Importación/Exportación de productos desde Excel**
  - `GET /api/productos/exportar` (XLSX con nombre, categoría, referencia, código de barras, precios, stock).
  - `POST /api/productos/importar/preview` y `POST /api/productos/importar` con mapeo de columnas configurable y reporte de errores fila por fila.
- **Migraciones de esquema** v1 a v5 gestionadas por `services/migraciones.py` (idempotentes, con registro en `config.schema_version`).
- **Cobertura de pruebas**: 107 pruebas pytest (unitarias de BD, API con TestClient y migraciones).

### 🛠️ Correcciones

- `actualizar_producto` con `codigo_barras=""` generaba SQL ilegal (bindings sobrantes). Ahora limpia el código correctamente.
- `configuracion.html`: acceso seguro a `window.AppConfig` cuando la app no está inicializada.

### 🧪 Sobre pruebas

```bash
cd tecnosport_app
python -m pytest tests -q   # 107 passed
```

---

## Etiquetas anteriores (pre-1.0.0)

Las siguientes etiquetas de Git corresponden a hitos previos sin reporte congelado:

- `git log --reverse` • Primeros commits con integración Telegram, reportes, backups y WhatsApp.

---

## Política de congelamiento

**Módulo congelado**: Inventario y Códigos de Barras (tabla `productos`, endpoints `/api/productos*`, vista `/inventario`, escáner de nueva venta, import/export de productos y migraciones v4/v5).

A partir de `v1.0.0`:

1. No se añadirán nuevas funcionalidades a este módulo sin un ACK explícito de mantenimiento.
2. Solo **hotfixes** (bugs) entrarán por defecto.
3. Toda corrección debe superar la suite: `python -m pytest tests -q`.
4. Las migraciones nuevas deben ir a `services/migraciones.py` de forma incremental (idempotentes).

**Módulos activos (no congelados)**: clientes, proveedores, movimientos/prestamos, dashboard, Telegram y configuración.