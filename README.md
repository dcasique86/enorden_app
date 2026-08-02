# EnOrden

Sistema de cuentas por cobrar del **Centro Comercial El Diamante 2**.

Aplicación web local (FastAPI) para el control de clientes, préstamos y abonos, con acceso desde PC y móvil en la misma red WiFi.

## Componentes

| Carpeta | Descripción |
|---------|-------------|
| `tecnosport_app/` | Aplicación principal (backend FastAPI + frontend) |
| `enorden_macos/` | Variante / empaquetado para macOS |
| `.github/workflows/` | Compilación automatizada |

## Aplicación principal (`tecnosport_app/`)

Ver [README de tecnosport_app](tecnosport_app/README.md) para instrucciones detalladas.

### Inicio rápido

**Windows:**
```bat
tecnosport_app\ENORDEN_WINDOWS.bat
```

**macOS / Linux:**
```bash
cd tecnosport_app
./EnOrden.command
```

Luego abre el navegador en **http://localhost:8000**.

### Funciones principales

- Dashboard: total prestado/recuperado, deuda activa, top deudores.
- Gestión de clientes con historial completo e integración con WhatsApp.
- Registro de préstamos y abonos.
- Importación de datos desde Excel con mapeo flexible de columnas.
- Respaldos automáticos diarios (últimos 30).

### API (resumen)

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/clientes` | Listar clientes |
| `GET /api/dashboard` | Datos del dashboard |
| `GET /api/backups` | Respaldos |

### Estructura

```
tecnosport_app/
├── main.py              ← Servidor FastAPI
├── database.py          ← Base de datos (SQLite)
├── repository.py        ← Acceso a datos
├── schemas.py           ← Modelos Pydantic
├── services/            ← Lógica de negocio
├── core/                ← Núcleo / config
├── templates/           ← Páginas HTML (Jinja2)
├── static/              ← CSS y JS
├── tests/               ← Pruebas
└── backups/             ← Respaldos automáticos
```

## Requisitos

- Python 3.8 o superior.
- Navegador web (Chrome, Firefox, Safari, Edge).

## Licencia

Uso interno. Desarrollado para el Centro Comercial El Diamante 2.
