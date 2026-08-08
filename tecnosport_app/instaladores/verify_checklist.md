# Checklist de instalación y prueba — EnOrden v1.0.0

Usar este checklist para dar por buena la versión antes de distribuirla a un cliente.

## Requisitos previos

- [ ] Sistema: Windows 10/11 (64 bits).
- [ ] No dejar el servidor de desarrollo corriendo en el puerto 8000 (no es bloqueante:
      la app busca un puerto libre automáticamente, lo registrará en `logs/startup.log`).

## 1. Instalación

- [ ] Ejecutar `EnOrden-Setup-1.0.0.exe` **desde la carpeta de distribución**
      (no desde la carpeta del proyecto).
- [ ] Instalar con las opciones por defecto → destino: `%LOCALAPPDATA%\EnOrden`.
- [ ] Verificar que se crean los accesos directos (Escritorio y Menú Inicio).
- [ ] Marcar "Iniciar EnOrden ahora" al finalizar la instalación.

## 2. Primer arranque (BD autogenerada)

- [ ] La app abre el navegador en `http://localhost:8000` (u otro puerto libre).
- [ ] Abrir `%LOCALAPPDATA%\EnOrden\logs\startup.log` y comprobar que contiene:
      - `Puerto seleccionado: ...`
      - `Base de datos: ...\(existente | será creada)`
      - `Inicio de la aplicación`
      - `Migraciones ejecutadas` (solo el primer arranque)
      - `URL abierta en el navegador: ...`
- [ ] Confirmar que se creó `datos_tecnosport.db` y la carpeta `backups/` SIN datos previos.

## 3. Uso real (15–20 minutos)

- [ ] Crear un producto (Inventario).
- [ ] Crear un cliente.
- [ ] Registrar un préstamo/abono.
- [ ] Hacer una venta con código de barras (si aplica).
- [ ] Exportar productos a Excel y abrir el archivo.

## 4. Cierre y reapertura

- [ ] Cerrar la aplicación (Task Manager si no hay consola).
- [ ] Volver a abrirla desde el acceso directo.
- [ ] Confirmar que los datos creados siguen presentes.

## 5. Reinicio de Windows

- [ ] Reiniciar Windows.
- [ ] Abrir EnOrden desde el acceso directo.
- [ ] Confirmar que todo sigue funcionando (datos, exportar, puerto).
- [ ] Revisar `logs/startup.log` de nuevo (sin errores).

## 6. Prueba de actualización (cuando exista v1.0.1)

- [ ] Reemplazar solo `%LOCALAPPDATA%\EnOrden\EnOrden.exe` por la nueva versión.
- [ ] Abrir y comprobar que: no se pierden datos, migraciones corren y todo sigue respondiendo.

## 7. Desinstalación (solo si se quiere probar)

- [ ] `Programas y características` → desinstalar EnOrden.
- [ ] Verificar que `datos_tecnosport.db`, `backups/` y `logs/` **permanecen** en
      `%LOCALAPPDATA%\EnOrden` (los datos no se borran al desinstalar).

---

## Criterios de salida v1.0.0

1. [ ] El `.exe` funciona correctamente (arranca, BD autogenerada, migraciones v1–v5).
2. [ ] El instalador instala y desinstala sin problemas.
3. [ ] La actualización conservando datos funciona.
4. [ ] La prueba de uso de 15–20 minutos tras reiniciar Windows no presenta errores.

Marca las casillas conforme se verifica. Si algo falla: corregir el bug → recompilar →
repetir desde el punto 1 (no continuar con el instalador sobre un exe defectuoso).