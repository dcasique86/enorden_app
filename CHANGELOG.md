# Changelog

Todas las versiones estables del sistema **EnOrden**.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado semántico.

## [Unreleased] - v1.0.1

**Rama Git:** `v1.0.1` (solo correcciones de distribución; sin funcionalidades nuevas).

### 🛠️ Correcciones

- **`startup.log` distingue BD creada vs. existente**: el registro de arranque
  ahora escribe `(creada)` en el primer inicio y `(existente)` cuando la base de
  datos ya existía (antes siempre decía "existente" por cómo se inicializa la BD).
- **Instancia única por instalación/datos**: al abrir una segunda copia de
  EnOrden sobre la misma instalación, se muestra un aviso y la copia termina.
  El bloqueo usa un mutex de Windows (nombre derivado del directorio de datos),
  sin tocar lógica de negocio ni la base de datos.
- **Migración v6**: `CREATE INDEX idx_ventas_fecha ON ventas(fecha)` (rendimiento
  en consultas por fecha). Idempotente y prueba de actualización sobre BD real
  v1.0.0 con datos (2 productos, 2 clientes, 1 venta, configuración) verificada.

### 📦 Gate de actualización v1.0.0 → v1.0.1 (verificado)

1. Instalación v1.0.0 sobre BD real → estado inicial intacto.
2. Sustitución del exe por el build v1.0.1 → BD **no recreada**, `schema_version`
   pasa de `1,2,3,4,5` a `1,2,3,4,5,6` con el índice creado.
3. Datos y configuración intactos; migración ejecutada **una sola vez**
   (no reaparece al reabrir la app ni tras reinicio del sistema).
4. Segunda instancia bloqueada con aviso.
5. Suite completa en verde en la rama: `python -m pytest tests -q` (109 passed).

---

## [1.0.0] - 2026-08-07

**Etiqueta Git:** `v1.0.0`

### 🚀 Distribución compilada (Windows)

- **Ejecutable único** `EnOrden.exe` (PyInstaller 6.21, one-file, sin consola).
- **Instalador** `EnOrden-Setup-1.0.0.exe` (Inno Setup 6.7.3):
  - Destino por defecto: `%LOCALAPPDATA%\EnOrden` (sin permisos de admin).
  - Accesos directos en Escritorio y Menú Inicio con icono provisional.
  - Opción "Iniciar EnOrden al finalizar la instalación".
  - Desinstalador que **conserva** la base de datos, backups y logs.
- **Versión portable** `EnOrden-portable-1.0.0.zip`: se descomprime donde se
  quiera (incluso USB) y la BD/backups/logs se crean en la misma carpeta.
- **Puerto dinámico**: la app intenta el 8000 y, si está ocupado, busca el
  siguiente libre (8001, 8002, …); el navegador se abre en el puerto elegido.
- **`logs/startup.log`**: registra inicio, puerto seleccionado, estado de la
  base de datos, migraciones aplicadas, URL abierta y errores de arranque.
- **BD autogenerada**: no se distribuye ninguna base de datos; en el primer
  inicio se crea vacía (schema v1–v5) junto al ejecutable.
- Herramientas y recursos: `tools/generar_icono.py`, `assets/en_orden.ico`,
  `instaladores/enorden_setup.iss`, `instaladores/LEEME.txt` y
  `instaladores/verify_checklist.md`.

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