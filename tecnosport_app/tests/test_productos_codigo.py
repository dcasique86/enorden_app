import pytest

from database import normalizar_codigo_barras


class TestNormalizarCodigoBarras:

    def test_trim_y_vacio_devuelve_none(self):
        assert normalizar_codigo_barras("   ") is None
        assert normalizar_codigo_barras("") is None
        assert normalizar_codigo_barras(None) is None

    def test_con_padding(self):
        assert normalizar_codigo_barras("  7701234567890  ") == "7701234567890"

    def test_valor_limpio(self):
        assert normalizar_codigo_barras("7701234567890") == "7701234567890"


class TestProductoCodigoBarras:

    def test_crear_con_codigo(self, db):
        p = db.crear_producto("Camiseta", "Ropa", 100, 200, 5, 0, None, "  7701234567890  ")
        assert p["codigo_barras"] == "7701234567890"

    def test_sin_codigo_devuelve_none(self, db):
        p = db.crear_producto("Camiseta", "Ropa", 100, 200, 5)
        assert p["codigo_barras"] is None

    def test_buscar_por_codigo_exacto(self, db):
        db.crear_producto("Camiseta", "N", 1, 2, 5, 0, None, "7701234567890")
        encontrado = db.buscar_producto_por_codigo("7701234567890")
        assert encontrado is not None
        assert encontrado["nombre"] == "Camiseta"

    def test_buscar_por_codigo_no_existe(self, db):
        db.crear_producto("Camiseta", "N", 1, 2, 5, 0, None, "7701234567890")
        assert db.buscar_producto_por_codigo("999999999") is None

    def test_codigo_en_busqueda_general(self, db):
        db.crear_producto("Zapato", "N", 1, 2, 5, 0, None, "7701234567890")
        resultados = db.buscar_productos("7701234567")
        nombres = [p["nombre"] for p in resultados]
        assert "Zapato" in nombres

    def test_duplicado_lanza_valueerror(self, db):
        db.crear_producto("A", "N", 1, 2, 5, 0, None, "7701234567890")
        with pytest.raises(ValueError, match="código de barras"):
            db.crear_producto("B", "N", 1, 2, 5, 0, None, "7701234567890")

    def test_actualizar_codigo(self, db):
        p = db.crear_producto("A", "N", 1, 2, 5, 0, None, "7701234567890")
        db.actualizar_producto(p["id"], None, None, None, None, None, None, None, "7790000000001")
        assert db.get_producto_by_id(p["id"])["codigo_barras"] == "7790000000001"

    def test_actualizar_a_codigo_duplicado_rechazado(self, db):
        p1 = db.crear_producto("A", "N", 1, 2, 5, 0, None, "7701234567890")
        p2 = db.crear_producto("B", "N", 1, 2, 5, 0, None, "7790000000001")
        with pytest.raises(ValueError, match="código de barras"):
            db.actualizar_producto(p2["id"], None, None, None, None, None, None, None, "7701234567890")

    def test_codigo_reutilizable_despues_de_eliminar(self, db):
        p = db.crear_producto("A", "N", 1, 2, 5, 0, None, "7701234567890")
        assert db.eliminar_producto(p["id"]) is True
        nuevo = db.crear_producto("B", "N", 1, 2, 5, 0, None, "7701234567890")
        assert nuevo["codigo_barras"] == "7701234567890"

    def test_codigo_de_eliminado_no_busca(self, db):
        p = db.crear_producto("A", "N", 1, 2, 5, 0, None, "7701234567890")
        db.eliminar_producto(p["id"])
        assert db.buscar_producto_por_codigo("7701234567890") is None