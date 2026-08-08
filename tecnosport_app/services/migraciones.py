import logging

logger = logging.getLogger("EnOrdenMigraciones")

MIGRATIONS = [
    {
        "version": 1,
        "description": "Agregar tipo_operacion, estado_operacion, fecha_vencimiento a movimientos",
        "sql": [
            "ALTER TABLE movimientos ADD COLUMN tipo_operacion TEXT DEFAULT 'COMPRA'",
            "ALTER TABLE movimientos ADD COLUMN estado_operacion TEXT DEFAULT 'COMPRA'",
            "ALTER TABLE movimientos ADD COLUMN fecha_vencimiento TEXT",
        ],
    },
    {
        "version": 2,
        "description": "Agregar tipo_operacion, estado_operacion a movimientos_proveedores",
        "sql": [
            "ALTER TABLE movimientos_proveedores ADD COLUMN tipo_operacion TEXT DEFAULT 'COMPRA'",
            "ALTER TABLE movimientos_proveedores ADD COLUMN estado_operacion TEXT DEFAULT 'COMPRA'",
        ],
    },
    {
        "version": 3,
        "description": "Agregar cedula, direccion, ciudad a clientes + indice de busqueda",
        "sql": [
            "ALTER TABLE clientes ADD COLUMN cedula TEXT",
            "ALTER TABLE clientes ADD COLUMN direccion TEXT",
            "ALTER TABLE clientes ADD COLUMN ciudad TEXT",
            "CREATE INDEX IF NOT EXISTS idx_clientes_cedula ON clientes(cedula)",
        ],
    },
    {
        "version": 4,
        "description": "Agregar codigo_barras a productos + indice unico parcial para integridad",
        "sql": [
            "ALTER TABLE productos ADD COLUMN codigo_barras TEXT",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_codigo_barras ON productos(codigo_barras) WHERE codigo_barras IS NOT NULL AND codigo_barras <> ''",
        ],
    },
    {
        "version": 5,
        "description": "Índice único de código de barras solo para productos activos (permite reutilizar códigos de productos eliminados)",
        "sql": [
            "DROP INDEX IF EXISTS idx_productos_codigo_barras",
            "CREATE UNIQUE INDEX idx_productos_codigo_barras ON productos(codigo_barras) WHERE activo = 1 AND codigo_barras IS NOT NULL AND codigo_barras <> ''",
        ],
    },
    {
        "version": 6,
        "description": "Índice de ventas por fecha (rendimiento en consultas de reportes)",
        "sql": [
            "CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha)",
        ],
    },
]


def _column_exists(conn, table: str, column: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _get_applied_versions(conn) -> set:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT valor FROM config WHERE clave = 'schema_version'"
    )
    row = cursor.fetchone()
    if row:
        return set(int(v) for v in row[0].split(",") if v.strip())
    return set()


def _set_applied_versions(conn, versions: set):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO config (clave, valor, descripcion) VALUES (?, ?, ?)",
        ("schema_version", ",".join(str(v) for v in sorted(versions)), "Versiones de esquema aplicadas"),
    )
    conn.commit()


def ejecutar_migraciones(db_instance) -> list[str]:
    """Ejecuta migraciones pendientes de forma segura.
    Retorna lista de migraciones aplicadas en esta ejecución.
    """
    conn = db_instance.get_connection()
    applied = []
    try:
        current_versions = _get_applied_versions(conn)

        for mig in MIGRATIONS:
            v = mig["version"]
            if v in current_versions:
                continue

            logger.info(f"Ejecutando migración v{v}: {mig['description']}")

            for sql in mig["sql"]:
                if "ADD COLUMN" in sql:
                    table = sql.split("ADD COLUMN")[0].split("ALTER TABLE")[1].strip()
                    column = sql.split("ADD COLUMN")[1].strip().split()[0]
                    if not _column_exists(conn, table, column):
                        conn.execute(sql)
                        logger.info(f"  Columna '{column}' agregada a '{table}'")
                else:
                    conn.execute(sql)
                    logger.info(f"  Sentencia ejecutada: {sql[:60]}")

            current_versions.add(v)
            _set_applied_versions(conn, current_versions)
            applied.append(mig["description"])

        logger.info(f"Migraciones ejecutadas: {len(applied)} pendientes")
        return applied

    except Exception as e:
        logger.error(f"Error ejecutando migraciones: {e}", exc_info=True)
        raise
    finally:
        conn.close()
