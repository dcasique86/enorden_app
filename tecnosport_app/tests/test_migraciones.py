import os

import pytest

from database import DatabaseManager
from services.migraciones import (
    MIGRATIONS,
    _get_applied_versions,
    _set_applied_versions,
    ejecutar_migraciones,
)


@pytest.fixture
def db_fresca(data_dir):
    """DatabaseManager SIN migraciones aplicadas (estado ~legacy)."""
    from tests.conftest import _crear_excel_template

    _crear_excel_template(os.path.join(data_dir, "datos_tecnosport.xlsx"))
    manager = DatabaseManager(data_dir)
    yield manager
    try:
        manager.get_connection().close()
    except Exception:
        pass


def _columnas(conn, tabla):
    return {fila[1] for fila in conn.execute(f"PRAGMA table_info({tabla})")}


def _indices(conn, tabla):
    return {
        fila[1]
        for fila in conn.execute(f"PRAGMA index_list({tabla})")
    }


def _sql_indice(conn, nombre):
    fila = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (nombre,)
    ).fetchone()
    return fila[0] if fila else None


class TestMigracionesAplicanEnBDVacia:

    def test_aplica_todas_las_migraciones(self, db_fresca):
        aplicadas = ejecutar_migraciones(db_fresca)
        assert len(aplicadas) == len(MIGRATIONS)

    def test_es_idempotente(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        aplicadas = ejecutar_migraciones(db_fresca)
        assert aplicadas == []

    def test_registra_schema_version(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        conn = db_fresca.get_connection()
        try:
            assert _get_applied_versions(conn) == {1, 2, 3, 4, 5, 6}
        finally:
            conn.close()

    def test_columnas_migradas_creadas(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        conn = db_fresca.get_connection()
        try:
            columnas_mov = _columnas(conn, "movimientos")
            assert {"tipo_operacion", "estado_operacion", "fecha_vencimiento"} <= columnas_mov
            columnas_mov_prov = _columnas(conn, "movimientos_proveedores")
            assert {"tipo_operacion", "estado_operacion"} <= columnas_mov_prov
            columnas_clientes = _columnas(conn, "clientes")
            assert {"cedula", "direccion", "ciudad"} <= columnas_clientes
            columnas_productos = _columnas(conn, "productos")
            assert "codigo_barras" in columnas_productos
        finally:
            conn.close()

    def test_indice_unico_solo_activos(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        conn = db_fresca.get_connection()
        try:
            assert "idx_productos_codigo_barras" in _indices(conn, "productos")
            sql = _sql_indice(conn, "idx_productos_codigo_barras")
            assert "activo = 1" in sql
        finally:
            conn.close()

    def test_reutiliza_codigo_de_producto_desactivado(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        creado = db_fresca.crear_producto(
            nombre="Primero", codigo_barras="7701234567890"
        )
        db_fresca.eliminar_producto(creado["id"])

        segundo = db_fresca.crear_producto(
            nombre="Segundo", codigo_barras="7701234567890"
        )
        assert segundo["codigo_barras"] == "7701234567890"

    def test_rechaza_codigo_duplicado_de_producto_activo(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        db_fresca.crear_producto(nombre="Activo", codigo_barras="7701234567890")
        with pytest.raises(ValueError):
            db_fresca.crear_producto(nombre="Duplicado", codigo_barras="7701234567890")


class TestVersionTracking:

    def test_ignora_migraciones_y_registradas(self, db_fresca):
        conn = db_fresca.get_connection()
        try:
            _set_applied_versions(conn, {1, 2, 3, 4, 5, 6})
        finally:
            conn.close()

        aplicadas = ejecutar_migraciones(db_fresca)
        assert aplicadas == []

    def test_reanuda_desde_version_parcial(self, db_fresca):
        conn = db_fresca.get_connection()
        try:
            _set_applied_versions(conn, {1, 2, 3})
        finally:
            conn.close()

        aplicadas = ejecutar_migraciones(db_fresca)
        assert len(aplicadas) == 3
        conn = db_fresca.get_connection()
        try:
            assert _get_applied_versions(conn) == {1, 2, 3, 4, 5, 6}
        finally:
            conn.close()

    def test_v6_crea_indice_ventas_fecha(self, db_fresca):
        ejecutar_migraciones(db_fresca)
        conn = db_fresca.get_connection()
        try:
            assert "idx_ventas_fecha" in _indices(conn, "ventas")
            sql = _sql_indice(conn, "idx_ventas_fecha")
            assert "ventas" in sql and "fecha" in sql
        finally:
            conn.close()

    def test_v6_no_volver_a_ejecutarse(self, db_fresca):
        aplicadas = ejecutar_migraciones(db_fresca)
        assert any("Índice de ventas por fecha" in a or "idx_ventas_fecha" in a for a in aplicadas)
        aplicadas = ejecutar_migraciones(db_fresca)
        assert aplicadas == []