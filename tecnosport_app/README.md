# 🏪 EnOrden - Sistema de Cuentas por Cobrar

**Centro Comercial El Diamante 2**

Sistema profesional para el control de cuentas por cobrar.

---

## 📋 Requisitos

- **Python 3.8+** (se instala automáticamente si no lo tienes)
- **Navegador web** (Safari, Chrome, Firefox, Edge)

### Por Sistema Operativo:

| Sistema | Requisito | Script de Inicio |
|---------|-----------|------------------|
| **macOS** | Python 3 | `EnOrden.command` |
| **Windows** | Python 3 | `ENORDEN_WINDOWS.bat` |
| **Linux** | Python 3 | `EnOrden.command` |

---

## 🚀 Cómo Iniciar la Aplicación

### 🍎 macOS

**Opción 1: Doble Clic**
1. Haz **doble clic** en `EnOrden.command`
2. Se abrirá Terminal y luego el navegador automáticamente

**Opción 2: Crear App (icono en Aplicaciones)**
1. Ejecuta `crear_app.sh` desde Terminal
2. Se creará `EnOrden.app`
3. Muévelo a tu carpeta de Aplicaciones

> ⚠️ **Primera vez**: Click derecho > "Abrir" para autorizar

---

### 🪟 Windows

1. Haz **doble clic** en `ENORDEN_WINDOWS.bat`
2. Se abrirá una ventana de comandos
3. El navegador se abrirá automáticamente

> ⚠️ Si Windows bloquea el script, click derecho > Propiedades > Desbloquear

---

### 🐧 Linux

```bash
cd tecnosport_app
chmod +x EnOrden.command
./EnOrden.command
```

---

### 🌐 Acceso Manual (cualquier sistema)

Si el navegador no se abre automáticamente:
1. Abre tu navegador
2. Ve a: **http://localhost:8000**

---

## 📱 Acceso desde iPhone/Android (misma red WiFi)

1. En tu computadora, averigua tu **IP local**:
   - **Mac**: Preferencias del Sistema > Red
   - **Windows**: `ipconfig` en cmd
   - **Linux**: `ip addr` o `hostname -I`

2. En tu móvil, abre el navegador y ve a:
   ```
   http://TU_IP:8000
   ```
   Ejemplo: `http://192.168.1.100:8000`

---

## 📚 Documentación

- **`docs/DATABASE_SCHEMA.md`** — esquema SQLite, las 5 migraciones y el comportamiento de `codigo_barras`.
- **`CHANGELOG.md`** (raíz del repo) — notas de versión y política de congelamiento de módulos.
- **Módulo congelado**: inventario y códigos de barras (desde `v1.0.0` solo recibe correcciones de errores).

---

## 🧪 Pruebas Rápidas

### Verificar que el servidor está corriendo:

Abre en tu navegador:
- Dashboard: http://localhost:8000
- API Clientes: http://localhost:8000/api/clientes
- API Dashboard: http://localhost:8000/api/dashboard

### Desde Terminal/PowerShell:
```bash
curl http://localhost:8000/api/dashboard
```

---

## 📥 Importar Datos Existentes

1. Ve a **http://localhost:8000/importar**
2. Arrastra tu archivo Excel
3. Configura qué columnas importar
4. Haz clic en "Importar"

### Formatos compatibles:

| Columnas mínimas | Resultado |
|------------------|-----------|
| Solo nombre | Cliente sin deuda |
| Nombre + Deuda | Cliente con saldo inicial |
| Nombre + Préstamos + Abonos | Cliente con historial |

---

## 💾 Respaldos

### Automáticos
- El sistema crea respaldos automáticamente cada día a las 11 PM
- Se guardan en la carpeta `backups/`
- Se mantienen los últimos 30 respaldos

### Manual
- Clic en "Importar" > API: `/api/backups` (POST)
- O copia `datos_tecnosport.xlsx` manualmente

---

## 📊 Estructura de Archivos

```
tecnosport_app/
├── EnOrden.command            ← Iniciar en Mac/Linux
├── ENORDEN_WINDOWS.bat        ← Iniciar en Windows
├── INSTALAR.command           ← Configuración inicial
├── crear_app.sh               ← Crear app macOS
├── main.py                    ← Servidor
├── database.py                ← Base de datos
├── importar_datos.py          ← Script importación
├── datos_tecnosport.xlsx      ← Tus datos
├── backups/                   ← Respaldos
├── templates/                 ← Páginas HTML
├── static/                    ← CSS y JS
└── requirements.txt           ← Dependencias Python
```

---

## 📖 Funcionalidades

### Dashboard
- Total prestado y recuperado
- Deuda activa
- Clientes activos
- Movimientos del día
- Top 5 deudores
- Clientes sin abonos recientes
- Búsqueda rápida de clientes

### Clientes
- Crear, buscar y ver clientes
- Historial completo por cliente
- Deuda actualizada en tiempo real
- Integración con WhatsApp

### Movimientos
- Registrar préstamos
- Registrar abonos
- Descripción libre

### Importación
- Importar desde Excel existente
- Mapeo flexible de columnas
- Vista previa antes de importar

---

## 🛠️ Solución de Problemas

### "Python no está instalado"
1. Descarga Python desde: https://www.python.org/downloads/
2. **Windows**: Marca "Add Python to PATH" durante instalación
3. Reinicia Terminal/CMD y ejecuta nuevamente

### "Puerto 8000 en uso"
1. Cierra otras aplicaciones que usen el puerto
2. O edita `main.py` última línea y cambia `port=8000` a otro puerto

### "No puedo acceder desde móvil"
1. Verifica que ambos dispositivos estén en la misma red WiFi
2. Desactiva temporalmente el firewall
3. Verifica que la IP sea correcta

### "Error de dependencias"
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración Avanzada

### Cambiar días sin abono (default: 30)
Edita `database.py`, línea ~240:
```python
dias_sin_abono = 30  # Cambia este número
```

### Cambiar puerto
Edita `main.py`, última sección:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # Cambia 8000
```

---

## 📞 Soporte

Sistema desarrollado para uso local.
Centro Comercial El Diamante 2.

---

**Versión**: 1.0.0  
**Última actualización**: 2025
